import torch
from torch import nn
from torch.nn import functional as F


class FastWeightMemory(nn.Module):
    """Fast-weight associative matrix plus a bounded content-addressable episodic store."""
    def __init__(self, hidden_size: int, slots: int, decay: float = 0.995):
        super().__init__()
        if not 0.0 <= decay <= 1.0:
            raise ValueError("decay must be in [0, 1]")
        self.hidden_size, self.decay = hidden_size, decay
        self.key = nn.Linear(hidden_size, hidden_size, bias=False)
        self.value = nn.Linear(hidden_size, hidden_size, bias=False)
        self.query = nn.Linear(hidden_size, hidden_size, bias=False)
        self.gate = nn.Linear(hidden_size, 1)
        self.register_buffer("fast_weights", torch.zeros(hidden_size, hidden_size))
        self.register_buffer("episodic_keys", torch.zeros(slots, hidden_size))
        self.register_buffer("episodic_values", torch.zeros(slots, hidden_size))
        self.register_buffer("valid", torch.zeros(slots, dtype=torch.bool))
        self.register_buffer("cursor", torch.zeros((), dtype=torch.long))

    def reset_memory(self):
        self.fast_weights.zero_()
        self.episodic_keys.zero_()
        self.episodic_values.zero_()
        self.valid.zero_()
        self.cursor.zero_()

    def forward(self, x: torch.Tensor, write: bool = False) -> torch.Tensor:
        # Key/value projections are only consumed by the write path. Avoid two
        # full hidden-size projections during ordinary read-only inference.
        should_write = write and self.training
        if should_write:
            keys = F.normalize(self.key(x), dim=-1)
            values = self.value(x)
        else:
            keys = values = None
        queries = F.normalize(self.query(x), dim=-1)
        fast_recall = torch.matmul(queries, self.fast_weights.to(dtype=x.dtype))
        if bool(self.valid.any()):
            scores = torch.matmul(queries, self.episodic_keys.to(dtype=x.dtype).transpose(0, 1))
            scores = scores.masked_fill(~self.valid.unsqueeze(0).unsqueeze(0), -torch.inf)
            attention = F.softmax(scores.float(), dim=-1).to(x.dtype)
            episodic_recall = torch.matmul(attention, self.episodic_values.to(dtype=x.dtype))
        else:
            episodic_recall = torch.zeros_like(x)
        recalled = fast_recall + episodic_recall

        if should_write:
            # Sequential delta updates preserve update order; this prototype path is not GPU-optimized.
            with torch.no_grad():
                gates = torch.sigmoid(self.gate(x)).squeeze(-1)
                for b in range(x.shape[0]):
                    for t in range(x.shape[1]):
                        key = keys[b, t].detach()
                        value = values[b, t].detach()
                        prediction = torch.mv(self.fast_weights, key)
                        delta = (value - prediction) * gates[b, t].detach()
                        self.fast_weights.mul_(self.decay).add_(torch.outer(delta, key))
                        slot = int(self.cursor.item())
                        self.episodic_keys[slot].copy_(key)
                        self.episodic_values[slot].copy_(value)
                        self.valid[slot] = True
                        self.cursor.add_(1).remainder_(self.episodic_keys.shape[0])
        return recalled
