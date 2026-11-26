"""Parameter accounting for ULTRON models without allocating foundation weights."""
from __future__ import annotations

import argparse
import json
from typing import Any

import torch
from torch import nn

from ultron_core.config import NeuroSparseConfig, count_parameters, count_total_parameters
from ultron_core.model import NeuroSparseModel

_PARAMETER_TYPES = ("embedding", "attention", "expert", "router", "refinement", "memory", "other")


def _parameter_type(name: str) -> str:
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
    return "other"


def parameter_report(model: nn.Module) -> dict[str, Any]:
    """Count unique parameters by owning module and architectural type."""
    if not isinstance(model, nn.Module):
        raise TypeError("model must be a torch.nn.Module")

    modules: dict[str, dict[str, int]] = {}
    types = {key: {"total": 0, "trainable": 0, "frozen": 0} for key in _PARAMETER_TYPES}
    total = trainable = 0
    # Shared/tied parameters are counted once, as in model.parameters().
    for name, parameter in model.named_parameters():
        count = parameter.numel()
        trainable_parameter = parameter.requires_grad
        category = _parameter_type(name)
        parent_name = name.rpartition(".")[0] or "<root>"
        module_counts = modules.setdefault(parent_name, {"total": 0, "trainable": 0, "frozen": 0})
        module_counts["total"] += count
        module_counts["trainable" if trainable_parameter else "frozen"] += count
        types[category]["total"] += count
        types[category]["trainable" if trainable_parameter else "frozen"] += count
        total += count
        if trainable_parameter:
            trainable += count

    report: dict[str, Any] = {
        "total_parameters": total,
        "trainable_parameters": trainable,
        "frozen_parameters": total - trainable,
        "by_module": dict(sorted(modules.items())),
        "by_type": types,
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
    """Construct on meta device so foundation reporting does not allocate weights."""
    with torch.device("meta"):
        return NeuroSparseModel(config)


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
    report = parameter_report(build_model_for_report(config))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"Total parameters:     {report['total_parameters']:,}")
        print(f"Trainable parameters: {report['trainable_parameters']:,}")
        print(f"Frozen parameters:    {report['frozen_parameters']:,}")
        if "matches_config" in report:
            print(f"Matches config:       {report['matches_config']}")
        print("\nBy type:")
        for name, counts in report["by_type"].items():
            print(f"  {name:12} total={counts['total']:>12,} trainable={counts['trainable']:>12,} frozen={counts['frozen']:>12,}")
        print("\nBy module:")
        for name, counts in report["by_module"].items():
            print(f"  {name:32} total={counts['total']:>12,} trainable={counts['trainable']:>12,} frozen={counts['frozen']:>12,}")
    return 0 if report.get("matches_config", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
