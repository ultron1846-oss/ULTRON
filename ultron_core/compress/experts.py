"""Expert pruning and merge operations that produce independent model copies."""
from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any, Mapping, Sequence

import torch
from torch import nn


def _expert_layout(model: nn.Module):
    config = getattr(model, "config", None)
    blocks = getattr(model, "blocks", None)
    if config is None or not isinstance(blocks, (nn.ModuleList, list, tuple)) or not blocks:
        raise TypeError("model must expose config and a non-empty blocks sequence")
    expert_count = getattr(config, "num_experts", None)
    top_k = getattr(config, "top_k", None)
    if isinstance(expert_count, bool) or not isinstance(expert_count, int) or expert_count <= 0:
        raise TypeError("model config must define a positive num_experts")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= expert_count:
        raise ValueError("model config top_k must be between 1 and num_experts")
    for layer_index, block in enumerate(blocks):
        experts = getattr(block, "experts", None)
        router = getattr(block, "router", None)
        projection = getattr(router, "proj", None)
        if not isinstance(experts, nn.ModuleList) or len(experts) != expert_count:
            raise ValueError(f"block {layer_index} expert count does not match model config")
        if not isinstance(projection, nn.Linear) or projection.out_features != expert_count:
            raise ValueError(f"block {layer_index} router projection does not match expert count")
    return blocks, expert_count, top_k


def _usage_matrix(model: nn.Module, usage: Any | None, layer_count: int, expert_count: int):
    if usage is None:
        return [[0] * expert_count for _ in range(layer_count)]
    if hasattr(usage, "snapshot") and callable(usage.snapshot):
        usage = usage.snapshot()
    if not isinstance(usage, Mapping) or not isinstance(usage.get("layers"), Mapping):
        raise TypeError("usage must be an ExpertUsageCounter or a snapshot with a 'layers' mapping")
    layers = usage["layers"]
    rows = []
    for layer_index in range(layer_count):
        values = layers.get(str(layer_index), layers.get(layer_index))
        if not isinstance(values, (list, tuple)) or len(values) != expert_count:
            raise ValueError(f"usage for layer {layer_index} must contain {expert_count} expert counts")
        row = []
        for value in values:
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("expert usage counts must be non-negative integers")
            row.append(value)
        rows.append(row)
    return rows


def _parameter_totals(model: nn.Module) -> dict[str, int]:
    total = trainable = 0
    for parameter in model.parameters():
        total += parameter.numel()
        if parameter.requires_grad:
            trainable += parameter.numel()
    return {"total": total, "trainable": trainable, "frozen": total - trainable}


def _replace_experts_and_router(model: nn.Module, selected_by_layer: Sequence[Sequence[int]]) -> None:
    blocks, old_count, _top_k = _expert_layout(model)
    if len(selected_by_layer) != len(blocks):
        raise ValueError("selected expert indices must be supplied for every layer")
    new_count = len(selected_by_layer[0])
    if new_count <= 0 or any(len(row) != new_count for row in selected_by_layer):
        raise ValueError("every layer must retain the same non-zero number of experts")

    for layer_index, (block, selected) in enumerate(zip(blocks, selected_by_layer)):
        if len(set(selected)) != len(selected) or any(
            isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < old_count
            for index in selected
        ):
            raise ValueError(f"invalid selected expert indices for layer {layer_index}")
        original_projection = block.router.proj
        replacement = nn.Linear(
            original_projection.in_features,
            new_count,
            bias=original_projection.bias is not None,
            device=original_projection.weight.device,
            dtype=original_projection.weight.dtype,
        )
        selected_tensor = torch.tensor(
            list(selected), dtype=torch.long, device=original_projection.weight.device
        )
        with torch.no_grad():
            replacement.weight.copy_(original_projection.weight.index_select(0, selected_tensor))
            if replacement.bias is not None:
                replacement.bias.copy_(original_projection.bias.index_select(0, selected_tensor))
        replacement.weight.requires_grad_(original_projection.weight.requires_grad)
        if replacement.bias is not None:
            replacement.bias.requires_grad_(original_projection.bias.requires_grad)
        block.experts = nn.ModuleList([block.experts[index] for index in selected])
        block.router.proj = replacement
        block.router.num_experts = new_count

    model.config = replace(model.config, num_experts=new_count)


def prune_experts(
    model: nn.Module,
    usage: Any,
    *,
    keep_experts: int,
) -> tuple[nn.Module, dict[str, Any]]:
    """Return a new model retaining the globally most-used expert indices.

    Usage is summed across layers so the same expert slots are retained in each
    layer (the ULTRON configuration uses a uniform expert count). Experts are
    copied intact; no parameter averaging or fitting is performed.
    """
    if not isinstance(model, nn.Module):
        raise TypeError("model must be a torch.nn.Module")
    blocks, expert_count, top_k = _expert_layout(model)
    if isinstance(keep_experts, bool) or not isinstance(keep_experts, int):
        raise TypeError("keep_experts must be an integer")
    if not top_k <= keep_experts < expert_count:
        raise ValueError("keep_experts must be at least top_k and less than the current expert count")
    rows = _usage_matrix(model, usage, len(blocks), expert_count)
    totals = [sum(row[index] for row in rows) for index in range(expert_count)]
    ranked = sorted(range(expert_count), key=lambda index: (-totals[index], index))
    selected = sorted(ranked[:keep_experts])

    result = copy.deepcopy(model)
    before = _parameter_totals(model)
    _replace_experts_and_router(result, [selected] * len(blocks))
    after = _parameter_totals(result)
    report = {
        "operation": "prune_experts",
        "expert_count_before": expert_count,
        "expert_count_after": keep_experts,
        "kept_expert_indices": selected,
        "pruned_expert_indices": sorted(set(range(expert_count)) - set(selected)),
        "usage_totals_by_expert": totals,
        "parameter_counts_before": before,
        "parameter_counts_after": after,
        "original_model_modified": False,
        "weight_strategy": "retain_selected_expert_parameters_without_averaging",
    }
    return result, report
