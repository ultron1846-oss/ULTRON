"""Parameter accounting for ULTRON models without allocating foundation weights."""
from __future__ import annotations

import argparse
import json
import re
from typing import Any

import torch
from torch import nn

from ultron_core.config import NeuroSparseConfig, count_parameters, count_total_parameters
from ultron_core.model import NeuroSparseModel

_PARAMETER_TYPES = ("embedding", "attention", "expert", "router", "refinement", "memory", "other")
_EXPLICIT_OTHER_PARAMETER = re.compile(
    r"^(?:blocks\.\d+\.(?:attention_norm|norm)|final_norm)\.(?:weight|bias)$"
)


def _parameter_type(name: str) -> str:
    """Map a known model parameter name to one architectural category.

    The only parameters intentionally placed in the other bucket are the
    explicitly recognized normalization tensors. Unknown future parameters
    raise instead of being silently hidden in that bucket.
    """
    parts = name.split(".")
    if parts[0] in ("embedding", "position_embedding"):
        return "embedding"
    if "attention" in parts:
        return "attention"
    if "experts" in parts:
        return "expert"
    if "router" in parts:
        return "router"
    if "refiner" in parts:
        return "refinement"
    if "memory" in parts:
        return "memory"
    if _EXPLICIT_OTHER_PARAMETER.fullmatch(name):
        return "other"
    raise ValueError(f"parameter is not assigned to a compression category: {name!r}")


def parameter_report(model: nn.Module) -> dict[str, Any]:
    """Count parameters by module/type, deduplicating by Parameter object identity."""
    if not isinstance(model, nn.Module):
        raise TypeError("model must be a torch.nn.Module")

    modules: dict[str, dict[str, int]] = {}
    types = {key: {"total": 0, "trainable": 0, "frozen": 0} for key in _PARAMETER_TYPES}
    other_parameter_names: list[str] = []
    seen_parameter_ids: set[int] = set()
    total = trainable = 0

    # remove_duplicate=False exposes aliases; id(parameter) ensures each
    # Parameter object is counted once without conflating distinct objects
    # that happen to share an underlying storage/data_ptr.
    for name, parameter in model.named_parameters(remove_duplicate=False):
        parameter_id = id(parameter)
        if parameter_id in seen_parameter_ids:
            continue
        seen_parameter_ids.add(parameter_id)

        count = parameter.numel()
        trainable_parameter = parameter.requires_grad
        category = _parameter_type(name)
        parent_name = name.rpartition(".")[0] or "<root>"
        module_counts = modules.setdefault(parent_name, {"total": 0, "trainable": 0, "frozen": 0})
        module_counts["total"] += count
        module_counts["trainable" if trainable_parameter else "frozen"] += count
        types[category]["total"] += count
        types[category]["trainable" if trainable_parameter else "frozen"] += count
        if category == "other":
            other_parameter_names.append(name)
        total += count
        if trainable_parameter:
            trainable += count

    report: dict[str, Any] = {
        "total_parameters": total,
        "trainable_parameters": trainable,
        "frozen_parameters": total - trainable,
        "by_module": dict(sorted(modules.items())),
        "by_type": types,
        "other_parameter_names": sorted(other_parameter_names),
        "category_breakdown_available": True,
        "count_method": "meta_model_parameter_identity",
        "fallback_reason": None,
    }
    config = getattr(model, "config", None)
    if isinstance(config, NeuroSparseConfig):
        report["config_expected_total"] = count_total_parameters(config)
        report["config_expected_trainable"] = count_parameters(config)
        report["matches_config"] = (
            total == report["config_expected_total"]
            and trainable == report["config_expected_trainable"]
        )
    return report


def build_model_for_report(config: NeuroSparseConfig) -> NeuroSparseModel:
    """Construct on meta device so foundation reporting does not allocate weights.

    This function deliberately lets construction errors propagate; the
    config-reporting entry point below converts an unsupported meta device
    into an explicit analytical fallback.
    """
    with torch.device("meta"):
        return NeuroSparseModel(config)


def parameter_report_for_config(config: NeuroSparseConfig) -> dict[str, Any]:
    """Report a config, falling back to existing analytical counters if meta fails."""
    if not isinstance(config, NeuroSparseConfig):
        raise TypeError("config must be a NeuroSparseConfig")

    try:
        model = build_model_for_report(config)
    except Exception as exc:
        # These are the repository's existing no-allocation formulas. Do not
        # introduce a second shape-counting implementation for this fallback.
        total = count_total_parameters(config)
        trainable = count_parameters(config)
        return {
            "total_parameters": total,
            "trainable_parameters": trainable,
            "frozen_parameters": total - trainable,
            "by_module": {},
            "by_type": {},
            "other_parameter_names": [],
            "category_breakdown_available": False,
            "count_method": "analytical_config_fallback",
            "fallback_reason": f"{type(exc).__name__}: {exc}",
            "config_expected_total": total,
            "config_expected_trainable": trainable,
            "matches_config": True,
        }

    return parameter_report(model)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report ULTRON parameters without allocating foundation weights.")
    parser.add_argument("--small", action="store_true", help="Use a small random model for development.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON.")
    args = parser.parse_args(argv)
    if args.small:
        config = NeuroSparseConfig(
            vocab_size=64, hidden_size=32, num_layers=1, num_experts=4,
            top_k=2, expert_multiplier=2, fast_memory_slots=8,
            num_attention_heads=4, max_sequence_length=32,
        )
    else:
        config = NeuroSparseConfig.foundation()

    report = parameter_report_for_config(config)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Total parameters:     {report['total_parameters']:,}")
        print(f"Trainable parameters: {report['trainable_parameters']:,}")
        print(f"Frozen parameters:    {report['frozen_parameters']:,}")
        print(f"Count method:         {report['count_method']}")
        if report["fallback_reason"] is not None:
            print("WARNING: meta-device model construction failed; used the existing analytical configuration counters.")
            print(f"Fallback reason: {report['fallback_reason']}")
        if "matches_config" in report:
            print(f"Matches config:       {report['matches_config']}")
        if report["category_breakdown_available"]:
            print("\nBy type:")
            for name, counts in report["by_type"].items():
                print(f"  {name:12} total={counts['total']:>12,} trainable={counts['trainable']:>12,} frozen={counts['frozen']:>12,}")
            print("\nBy module:")
            for name, counts in report["by_module"].items():
                print(f"  {name:32} total={counts['total']:>12,} trainable={counts['trainable']:>12,} frozen={counts['frozen']:>12,}")
        else:
            print("Category/module breakdown: unavailable because no meta-device model was constructed.")
    return 0 if report.get("matches_config", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
