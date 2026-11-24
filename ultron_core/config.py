from dataclasses import asdict, dataclass
from typing import Any

@dataclass(frozen=True)
class NeuroSparseConfig:
    vocab_size: int = 256
    hidden_size: int = 128
    num_layers: int = 2
    num_experts: int = 8
    top_k: int = 2
    expert_multiplier: int = 2
    max_refinements: int = 3
    halt_threshold: float = 0.02
    fast_memory_slots: int = 64
    dropout: float = 0.0
    pad_token_id: int = 0

    def __post_init__(self) -> None:
        for name in ("vocab_size","hidden_size","num_layers","num_experts","top_k","expert_multiplier","max_refinements","fast_memory_slots"):
            if getattr(self,name) <= 0: raise ValueError(f"{name} must be positive")
        if self.top_k > self.num_experts: raise ValueError("top_k cannot exceed num_experts")
        if not 0.0 <= self.halt_threshold <= 1.0: raise ValueError("halt_threshold must be in [0, 1]")
        if not 0.0 <= self.dropout < 1.0: raise ValueError("dropout must be in [0, 1)")
        if not 0 <= self.pad_token_id < self.vocab_size: raise ValueError("pad_token_id outside vocabulary")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
