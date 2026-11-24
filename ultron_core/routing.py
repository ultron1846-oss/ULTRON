import torch
from torch import nn
from torch.nn import functional as F


class SparseRouter(nn.Module):
    def __init__(self, hidden_size: int, num_experts: int, top_k: int):
        super().__init__()
        for name, value in (("hidden_size", hidden_size), ("num_experts", num_experts), ("top_k", top_k)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
        if hidden_size <= 0 or num_experts <= 0:
            raise ValueError("hidden_size and num_experts must be positive")
        if not 1 <= top_k <= num_experts:
            raise ValueError("top_k must be between 1 and num_experts")
        self.num_experts, self.top_k = num_experts, top_k
        self.proj = nn.Linear(hidden_size, num_experts, bias=False)

    def forward(self, x: torch.Tensor):
        if x.ndim < 2 or x.shape[-1] != self.proj.in_features:
            raise ValueError("router input must have shape [..., hidden_size]")
        logits = self.proj(x)
        probs = F.softmax(logits.float(), dim=-1).to(logits.dtype)
        weights, indices = torch.topk(probs, self.top_k, dim=-1)
        weights = weights / weights.sum(dim=-1, keepdim=True).clamp_min(1e-9)
        return logits, weights, indices


def load_balance_loss(
    logits: torch.Tensor, indices: torch.Tensor, *, validate_indices: bool = True
) -> torch.Tensor:
    """Switch-style balance penalty; assignment frequency sums to one."""
    if logits.ndim != 2 or indices.ndim != 2 or logits.shape[0] != indices.shape[0]:
        raise ValueError("expected logits [tokens, experts] and indices [tokens, top_k]")
    if not logits.is_floating_point():
        raise TypeError("router logits must use a floating-point dtype")
    experts = logits.shape[-1]
    if experts <= 0 or indices.shape[1] <= 0 or indices.shape[1] > experts:
        raise ValueError("expert and top-k dimensions must be valid and non-empty")
    if indices.dtype not in (torch.int8, torch.int16, torch.int32, torch.int64, torch.uint8):
        raise TypeError("expert indices must have an integer dtype")
    if indices.device != logits.device:
        raise ValueError("logits and expert indices must be on the same device")
    if logits.shape[0] == 0:
        return logits.new_zeros(())
    indices = indices.to(dtype=torch.long)
    if validate_indices:
        if indices.numel() and (indices.min() < 0 or indices.max() >= experts):
            raise ValueError("expert index out of range")
        ordered = indices.sort(dim=-1).values
        if indices.shape[1] > 1 and bool((ordered[:, 1:] == ordered[:, :-1]).any()):
            raise ValueError("each token must select distinct experts")
    importance = F.softmax(logits.float(), dim=-1).mean(dim=0)
    counts = F.one_hot(indices, num_classes=experts).float().sum(dim=1)
    frequency = counts.sum(dim=0) / (indices.shape[0] * indices.shape[1])
    return experts * torch.sum(importance * frequency.to(importance.dtype))
