import torch
from torch import nn
from torch.nn import functional as F


class SparseRouter(nn.Module):
    def __init__(self, hidden_size: int, num_experts: int, top_k: int):
        super().__init__()
        if not 1 <= top_k <= num_experts:
            raise ValueError("top_k must be between 1 and num_experts")
        self.num_experts, self.top_k = num_experts, top_k
        self.proj = nn.Linear(hidden_size, num_experts, bias=False)

    def forward(self, x: torch.Tensor):
        logits = self.proj(x)
        probs = F.softmax(logits.float(), dim=-1).to(logits.dtype)
        weights, indices = torch.topk(probs, self.top_k, dim=-1)
        weights = weights / weights.sum(dim=-1, keepdim=True).clamp_min(1e-9)
        return logits, weights, indices


def load_balance_loss(logits: torch.Tensor, indices: torch.Tensor) -> torch.Tensor:
    """Switch-style balance penalty; assignment frequency sums to one."""
    if logits.ndim != 2 or indices.ndim != 2 or logits.shape[0] != indices.shape[0]:
        raise ValueError("expected logits [tokens, experts] and indices [tokens, top_k]")
    if logits.shape[0] == 0:
        return logits.new_zeros(())
    experts = logits.shape[-1]
    if indices.numel() and (indices.min() < 0 or indices.max() >= experts):
        raise ValueError("expert index out of range")
    importance = F.softmax(logits.float(), dim=-1).mean(dim=0)
    counts = F.one_hot(indices, num_classes=experts).float().sum(dim=1)
    frequency = counts.sum(dim=0) / (indices.shape[0] * indices.shape[1])
    return experts * torch.sum(importance * frequency.to(importance.dtype))
