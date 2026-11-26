"""Fake-quantized int8 simulation with per-layer sensitivity reports."""
from __future__ import annotations

import copy
import math
from collections import Counter
from typing import Mapping

import torch
from torch import nn
from torch.nn import functional as F


def simulate_int8_quantization(
    model: nn.Module,
    *,
    sensitivity_inputs: Mapping[str, torch.Tensor] | None = None,
) -> tuple[nn.Module, dict]:
    """Return a copied model with symmetric per-layer int8-dequantized weights.

    This is simulated/fake quantization: the returned Linear weights remain in
    their original floating dtype after an int8 round-trip. Per-layer weight
    sensitivity is always measured. Optional output sensitivity is measured
    only for caller-supplied layer inputs; no calibration data is generated.
    """
    if not isinstance(model, nn.Module):
        raise TypeError("model must be a torch.nn.Module")
    if sensitivity_inputs is not None and not isinstance(sensitivity_inputs, Mapping):
        raise TypeError("sensitivity_inputs must be a mapping of module paths to tensors")

    available = dict(model.named_modules())
    candidates = {
        name: module for name, module in available.items()
        if name and isinstance(module, nn.Linear)
    }
    if not candidates:
        raise ValueError("model contains no Linear modules to quantize")
    if sensitivity_inputs is not None:
        unknown = set(sensitivity_inputs) - set(candidates)
        if unknown:
            raise ValueError(f"sensitivity inputs reference unknown/non-Linear modules: {sorted(unknown)}")
        for name, tensor in sensitivity_inputs.items():
            if not isinstance(tensor, torch.Tensor):
                raise TypeError(f"sensitivity input for {name!r} must be a tensor")
            if tensor.ndim < 1 or tensor.shape[-1] != candidates[name].in_features:
                raise ValueError(f"sensitivity input for {name!r} must end in {candidates[name].in_features} features")

    parameter_counts = Counter(
        id(parameter) for _name, parameter in model.named_parameters(remove_duplicate=False)
    )
    tied_ids = {
        parameter_id for parameter_id, count in parameter_counts.items() if count > 1
    }
    result = copy.deepcopy(model)
    layers = {}
    skipped_tied = []

    for name, original in candidates.items():
        if id(original.weight) in tied_ids:
            skipped_tied.append(name)
            continue
        weight = original.weight.detach()
        compute = weight.to(dtype=torch.float32)
        maximum = float(compute.abs().max().item())
        scale = maximum / 127.0 if maximum > 0.0 else 1.0
        quantized = torch.round(compute / scale).clamp(-127, 127).to(torch.int8)
        dequantized = (quantized.to(torch.float32) * scale).to(
            device=weight.device, dtype=weight.dtype
        )
        difference = dequantized.to(torch.float32) - compute
        denominator = torch.linalg.vector_norm(compute)
        relative_weight_error = (
            float((torch.linalg.vector_norm(difference) / denominator).item())
            if float(denominator.item()) > 0.0
            else 0.0
        )
        max_abs_error = float(difference.abs().max().item()) if difference.numel() else 0.0

        output_error = None
        max_absolute_output_error = None
        if sensitivity_inputs is not None and name in sensitivity_inputs:
            sample = sensitivity_inputs[name].to(
                device=weight.device, dtype=weight.dtype
            )
            with torch.no_grad():
                baseline = F.linear(sample, weight, original.bias).to(torch.float32)
                perturbed = F.linear(sample, dequantized, original.bias).to(torch.float32)
                output_difference = perturbed - baseline
                output_norm = torch.linalg.vector_norm(baseline)
                difference_norm = torch.linalg.vector_norm(output_difference)
                output_error = (
                    float((difference_norm / output_norm).item())
                    if float(output_norm.item()) > 0.0
                    else None
                )
                max_absolute_output_error = (
                    float(output_difference.abs().max().item())
                    if output_difference.numel() else 0.0
                )

        copied_layer = result.get_submodule(name)
        copied_layer.weight = nn.Parameter(
            dequantized.clone(), requires_grad=original.weight.requires_grad
        )
        layers[name] = {
            "quantization": "symmetric_per_layer_int8_simulation",
            "scale": scale,
            "zero_point": 0,
            "quantized_min": int(quantized.min().item()),
            "quantized_max": int(quantized.max().item()),
            "relative_weight_error": relative_weight_error,
            "max_absolute_weight_error": max_abs_error,
            "relative_output_error": output_error,
            "max_absolute_output_error": max_absolute_output_error,
            "stored_dtype": str(weight.dtype),
        }

    return result, {
        "operation": "simulated_int8_quantization",
        "layers": layers,
        "quantized_layer_count": len(layers),
        "skipped_tied_modules": skipped_tied,
        "original_model_modified": False,
        "simulation_only": True,
        "calibration_data_generated": False,
        "quality_claim": False,
    }
