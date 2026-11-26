"""Transactional orchestration for independent compression transformations."""
from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Sequence

from torch import nn

from .artifact import _json_safe, _validate_artifact_version, save_compression_artifact
from .expert_usage import ExpertUsageCounter
from .experts import merge_experts, prune_experts
from .low_rank import factorize_model
from .quantization import simulate_int8_quantization


def _manifest_options(options: Mapping[str, Any]) -> dict:
    recorded = {}
    for key, value in options.items():
        if key == "sensitivity_inputs":
            if not isinstance(value, Mapping):
                raise TypeError("sensitivity_inputs must be a mapping")
            recorded["sensitivity_input_layer_paths"] = sorted(value)
        elif key == "usage" and isinstance(value, ExpertUsageCounter):
            recorded[key] = value.snapshot()
        else:
            recorded[key] = value
    return _json_safe(recorded, field="pipeline step options")


def _dispatch_step(model: nn.Module, name: str, options: dict):
    if name == "prune_experts":
        return prune_experts(model, **options)
    if name == "merge_experts":
        return merge_experts(model, **options)
    if name == "factorize":
        return factorize_model(model, **options)
    if name == "quantize_int8":
        return simulate_int8_quantization(model, **options)
    raise ValueError(f"unsupported compression step: {name}")


def _model_counts(model: nn.Module) -> dict[str, int]:
    total = trainable = 0
    for parameter in model.parameters():
        total += parameter.numel()
        if parameter.requires_grad:
            trainable += parameter.numel()
    return {"total": total, "trainable": trainable, "frozen": total - trainable}


def run_compression_pipeline(
    model: nn.Module,
    steps: Sequence[Mapping[str, Any]],
    *,
    parent_checkpoint_id: str,
    artifact_version: str = "1.0.0",
    artifact_path: str | Path | None = None,
) -> tuple[nn.Module, dict]:
    """Apply transforms to copies; any error rolls the whole pipeline back.

    Each step is a mapping with a name and optional options. Supported names
    are prune_experts, merge_experts, factorize, and quantize_int8. A versioned
    artifact is written only after every step succeeds, using an atomic file write.
    """
    if not isinstance(model, nn.Module):
        raise TypeError("model must be a torch.nn.Module")
    if isinstance(steps, (str, bytes)) or not isinstance(steps, Sequence) or not steps:
        raise ValueError("steps must be a non-empty sequence")
    if not isinstance(parent_checkpoint_id, str) or not parent_checkpoint_id.strip():
        raise ValueError("parent_checkpoint_id must be a non-empty stable identifier")
    version = _validate_artifact_version(artifact_version)

    original_counts = _model_counts(model)
    working = copy.deepcopy(model)
    completed = []
    current_step = None
    try:
        for index, specification in enumerate(steps):
            if not isinstance(specification, Mapping):
                raise TypeError(f"compression step {index} must be a mapping")
            if set(specification) - {"name", "options"}:
                raise ValueError(f"compression step {index} contains unknown fields")
            name = specification.get("name")
            options = specification.get("options", {})
            if not isinstance(name, str) or not name:
                raise ValueError(f"compression step {index} must have a name")
            if not isinstance(options, Mapping):
                raise TypeError(f"options for compression step {name!r} must be a mapping")
            current_step = name
            next_model, step_report = _dispatch_step(working, name, dict(options))
            working = next_model
            completed.append({
                "name": name,
                "options": _manifest_options(options),
                "report": _json_safe(step_report, field=f"report for {name}"),
            })

        artifact_info = None
        if artifact_path is not None:
            artifact_info = save_compression_artifact(
                artifact_path,
                working,
                parent_checkpoint_id=parent_checkpoint_id,
                artifact_version=version,
                compression_steps=completed,
            )
        return working, {
            "success": True,
            "rolled_back": False,
            "completed_steps": len(completed),
            "steps": completed,
            "parent_checkpoint_id": parent_checkpoint_id,
            "artifact_version": version,
            "artifact": artifact_info,
            "parameter_counts_before": original_counts,
            "parameter_counts_after": _model_counts(working),
            "model_scope": "compressed_deployment_artifact",
            "foundation_parameter_floor_applies": False,
            "original_model_modified": False,
            "quality_claim": False,
            "speed_claim": False,
            "memory_claim": False,
        }
    except Exception as exc:
        return copy.deepcopy(model), {
            "success": False,
            "rolled_back": True,
            "completed_steps": len(completed),
            "steps": completed,
            "failed_step": current_step,
            "error": f"{type(exc).__name__}: {exc}",
            "artifact_written": False,
            "parameter_counts_before": original_counts,
            "parameter_counts_after": original_counts,
            "original_model_modified": False,
        }
