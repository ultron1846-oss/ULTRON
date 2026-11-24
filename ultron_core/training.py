import math
import torch
from torch.nn import functional as F


def causal_language_model_loss(logits: torch.Tensor, input_ids: torch.Tensor,
        load_balance: torch.Tensor | None = None, prediction_error: torch.Tensor | None = None,
        balance_weight: float = 0.01, prediction_weight: float = 0.01,
        ignore_index: int | None = 0) -> torch.Tensor:
    if logits.ndim != 3 or input_ids.ndim != 2:
        raise ValueError('expected logits [B,T,V] and input_ids [B,T]')
    if logits.shape[:2] != input_ids.shape:
        raise ValueError('logits/input_ids sequence dimensions must match')
    if input_ids.shape[0] == 0 or input_ids.shape[1] < 2:
        raise ValueError('batch must be non-empty and sequence length must be at least 2')
    for name, weight in (("balance_weight", balance_weight), ("prediction_weight", prediction_weight)):
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight < 0:
            raise ValueError(f"{name} must be a finite non-negative number")
    if not logits.is_floating_point():
        raise TypeError("logits must use a floating-point dtype")
    if logits.shape[-1] <= 0:
        raise ValueError("logits vocabulary dimension must be non-empty")
    if input_ids.dtype not in (torch.int32, torch.int64):
        raise TypeError("input_ids must use int32 or int64 token IDs")
    for name, auxiliary in (("load_balance", load_balance), ("prediction_error", prediction_error)):
        if auxiliary is not None and (not isinstance(auxiliary, torch.Tensor) or auxiliary.numel() != 1):
            raise ValueError(f"{name} must be a scalar tensor")
    targets = input_ids[:, 1:].reshape(-1)
    flat_logits = logits[:, :-1].reshape(-1, logits.shape[-1])
    if ignore_index is not None:
        if not bool((targets != ignore_index).any()):
            raise ValueError('all next-token targets are padding; loss is undefined')
        loss = F.cross_entropy(flat_logits, targets, ignore_index=ignore_index)
    else:
        loss = F.cross_entropy(flat_logits, targets)
    if load_balance is not None:
        loss = loss + balance_weight * load_balance
    if prediction_error is not None:
        loss = loss + prediction_weight * prediction_error
    return loss


def make_optimizer(model: torch.nn.Module, learning_rate: float = 3e-4,
                   weight_decay: float = 0.01):
    if (isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float))
            or not math.isfinite(learning_rate) or learning_rate <= 0):
        raise ValueError('learning_rate must be a finite positive number')
    if (isinstance(weight_decay, bool) or not isinstance(weight_decay, (int, float))
            or not math.isfinite(weight_decay) or weight_decay < 0):
        raise ValueError('weight_decay must be a finite non-negative number')
    return torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
