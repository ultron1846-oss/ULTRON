"""SVD-based low-rank factorization for linear modules."""
from __future__ import annotations

import copy
import math
from collections import Counter
from typing import Sequence

import torch
from torch import nn


class LowRankLinear(nn.Module):
    """A linear map represented as two bias-aware low-rank projections."""

    def __init__(self, in_features: int, out_features: int, rank: int, *, bias: bool = True, device=None, dtype=None):
        super().__init__()
        if not 1 <= rank <= min(in_features, out_features):
            raise ValueError("rank must be between one and the smaller matrix dimension")
        self.in_features = in_features
        self.out_features = out_features
        self.rank = rank
        self.down = nn.Linear(in_features, rank, bias=False, device=device, dtype=dtype)
        self.up = nn.Linear(rank, out_features, bias=bias, device=device, dtype=dtype)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.up(self.down(inputs))


def _validate_error_limit(max_relative_error: float) -> float:
    if isinstance(max_relative_error, bool) or not isinstance(max_relative_error, (int, float)) or not math.isfinite(max_relative_error) or not 0.0 <= max_relative_error < 1.0:
        raise ValueError("max_relative_error must be finite and in [0, 1)")
    return float(max_relative_error)


def factorize_linear(linear: nn.Linear, *, max_relative_error: float = 0.05) -> tuple[LowRankLinear, dict]:
    """Return the smallest SVD rank meeting a relative Frobenius weight-error limit.

    This is a tensor reconstruction bound, not a model-quality, task-accuracy,
    speed, or runtime-memory result. The input Linear module is never changed.
    """
    if not isinstance(linear, nn.Linear):
        raise TypeError("linear must be a torch.nn.Linear")
    limit = _validate_error_limit(max_relative_error)
    weight = linear.weight.detach()
    compute_dtype = torch.float64 if weight.dtype == torch.float64 else torch.float32
    matrix = weight.to(dtype=compute_dtype)
    u, singular_values, vh = torch.linalg.svd(matrix, full_matrices=False)
    energy = torch.sum(singular_values.square())

    if float(energy.item()) == 0.0:
        rank = 1
    else:
        total_energy = float(energy.item())
        rank = singular_values.numel()
        for candidate in range(1, singular_values.numel() + 1):
            residual_energy = torch.sum(singular_values[candidate:].square())
            candidate_error = math.sqrt(max(0.0, float(residual_energy.item())) / total_energy)
            if candidate_error <= limit:
                rank = candidate
                break

    factors = LowRankLinear(
        linear.in_features, linear.out_features, rank,
        bias=linear.bias is not None, device=weight.device, dtype=weight.dtype,
    )
    with torch.no_grad():
        if float(energy.item()) == 0.0:
            factors.down.weight.zero_()
            factors.up.weight.zero_()
        else:
            roots = singular_values[:rank].sqrt()
            left = roots.unsqueeze(1) * vh[:rank, :]
            right = u[:, :rank] * roots.unsqueeze(0)
            factors.down.weight.copy_(left.to(device=weight.device, dtype=weight.dtype))
            factors.up.weight.copy_(right.to(device=weight.device, dtype=weight.dtype))
        if linear.bias is not None:
            factors.up.bias.copy_(linear.bias.detach())
    factors.down.weight.requires_grad_(linear.weight.requires_grad)
    if linear.bias is not None:
        factors.up.bias.requires_grad_(linear.bias.requires_grad)
    factors.train(linear.training)

    reconstructed = factors.up.weight.detach().to(compute_dtype) @ factors.down.weight.detach().to(compute_dtype)
    denominator = torch.linalg.vector_norm(matrix)
    measured_error = float((torch.linalg.vector_norm(matrix - reconstructed) / denominator).item()) if float(denominator.item()) > 0.0 else 0.0
    if measured_error > limit + 1e-6:
        raise RuntimeError(f"stored factor dtype cannot satisfy max_relative_error (measured {measured_error:.8g}, limit {limit:.8g})")

    original_parameters = linear.weight.numel() + (linear.bias.numel() if linear.bias is not None else 0)
    factor_parameters = factors.down.weight.numel() + factors.up.weight.numel() + (factors.up.bias.numel() if factors.up.bias is not None else 0)
    return factors, {
        "rank": rank,
        "maximum_rank": min(linear.in_features, linear.out_features),
        "max_relative_error": limit,
        "relative_frobenius_error": measured_error,
        "original_parameters": original_parameters,
        "factor_parameters": factor_parameters,
        "parameter_delta": factor_parameters - original_parameters,
    }


def _set_submodule(model: nn.Module, path: str, replacement: nn.Module) -> None:
    parent_path, _, child_name = path.rpartition(".")
    parent = model.get_submodule(parent_path) if parent_path else model
    if child_name.isdecimal() and isinstance(parent, (nn.ModuleList, nn.Sequential)):
        parent[int(child_name)] = replacement
    else:
        setattr(parent, child_name, replacement)


def factorize_model(model: nn.Module, *, max_relative_error: float = 0.05, target_modules: Sequence[str] | None = None) -> tuple[nn.Module, dict]:
    """Factorize selected Linear modules on an independent deep copy.

    All non-tied Linear modules are candidates by default. Tied parameters,
    including the shared token embedding/output projection, are skipped.
    """
    if not isinstance(model, nn.Module):
        raise TypeError("model must be a torch.nn.Module")
    limit = _validate_error_limit(max_relative_error)
    available = dict(model.named_modules())
    if target_modules is not None:
        if isinstance(target_modules, (str, bytes)) or not isinstance(target_modules, Sequence):
            raise TypeError("target_modules must be a sequence of module paths")
        requested = list(target_modules)
        if any(not isinstance(name, str) or not name for name in requested):
            raise ValueError("target module paths must be non-empty strings")
        if len(set(requested)) != len(requested):
            raise ValueError("target_modules must not contain duplicates")
        for name in requested:
            if name not in available:
                raise ValueError(f"unknown target module: {name}")
            if not isinstance(available[name], nn.Linear):
                raise TypeError(f"target module is not nn.Linear: {name}")
        candidates = requested
    else:
        candidates = [name for name, child in available.items() if name and isinstance(child, nn.Linear)]

    parameter_names = Counter(id(parameter) for _name, parameter in model.named_parameters(remove_duplicate=False))
    tied_ids = {parameter_id for parameter_id, count in parameter_names.items() if count > 1}
    result = copy.deepcopy(model)
    transformed, skipped_tied = [], []
    for name in candidates:
        original = available[name]
        if id(original.weight) in tied_ids:
            skipped_tied.append(name)
            continue
        replacement, layer_report = factorize_linear(original, max_relative_error=limit)
        _set_submodule(result, name, replacement)
        transformed.append({"module": name, **layer_report})

    if target_modules is not None and not transformed and not skipped_tied:
        raise ValueError("no target modules were factorized")
    return result, {
        "operation": "svd_low_rank_factorization",
        "max_relative_error": limit,
        "layers": transformed,
        "skipped_tied_modules": skipped_tied,
        "factorized_layer_count": len(transformed),
        "original_model_modified": False,
        "quality_claim": False,
    }
