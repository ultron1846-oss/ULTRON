"""Explicit mixed-precision controls for ULTRON training.

BF16 is opt-in and FP32 remains the default. FP16 is intentionally not enabled
until the controller persists and restores GradScaler state in checkpoints.
"""
from contextlib import nullcontext

import torch

_SUPPORTED = {"fp32", "bf16"}


def validate_training_precision(precision: str) -> str:
    if not isinstance(precision, str) or precision not in _SUPPORTED:
        raise ValueError("precision must be 'fp32' or 'bf16'")
    return precision


def training_autocast(device: str | torch.device, precision: str = "fp32"):
    """Return a scoped autocast context; reject unsupported BF16 devices early."""
    precision = validate_training_precision(precision)
    target = torch.device(device)
    if precision == "fp32":
        return nullcontext()
    if target.type not in {"cpu", "cuda"}:
        raise RuntimeError("BF16 autocast is currently supported only on CPU/CUDA")
    if target.type == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA BF16 requested but CUDA is unavailable")
        if not torch.cuda.is_bf16_supported():
            raise RuntimeError("BF16 requested but this CUDA device does not support BF16")
    return torch.autocast(device_type=target.type, dtype=torch.bfloat16)
