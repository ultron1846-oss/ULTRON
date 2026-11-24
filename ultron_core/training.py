import torch
from torch.nn import functional as F


def causal_language_model_loss(logits: torch.Tensor, input_ids: torch.Tensor,
        load_balance: torch.Tensor | None = None, prediction_error: torch.Tensor | None = None,
        balance_weight: float = 0.01, prediction_weight: float = 0.01) -> torch.Tensor:
    if logits.ndim != 3 or input_ids.ndim != 2:
        raise ValueError('expected logits [B,T,V] and input_ids [B,T]')
    if logits.shape[:2] != input_ids.shape:
        raise ValueError('logits/input_ids sequence dimensions must match')
    if input_ids.shape[0] == 0 or input_ids.shape[1] < 2:
        raise ValueError('batch must be non-empty and sequence length must be at least 2')
    if balance_weight < 0 or prediction_weight < 0:
        raise ValueError('auxiliary loss weights must be non-negative')
    loss = F.cross_entropy(logits[:, :-1].reshape(-1, logits.shape[-1]),
                           input_ids[:, 1:].reshape(-1))
    if load_balance is not None:
        loss = loss + balance_weight * load_balance
    if prediction_error is not None:
        loss = loss + prediction_weight * prediction_error
    return loss


def make_optimizer(model: torch.nn.Module, learning_rate: float = 3e-4,
                   weight_decay: float = 0.01):
    if learning_rate <= 0 or weight_decay < 0:
        raise ValueError('invalid optimizer hyperparameters')
    return torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
