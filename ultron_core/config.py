from dataclasses import asdict, dataclass, replace
import math
from typing import Any

MIN_FOUNDATION_TRAINABLE_PARAMETERS = 60_000_000


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
    num_attention_heads: int = 4
    max_sequence_length: int = 2048

    def __post_init__(self) -> None:
        integer_fields = (
            "vocab_size", "hidden_size", "num_layers", "num_experts", "top_k",
            "expert_multiplier", "max_refinements", "fast_memory_slots", "pad_token_id",
            "num_attention_heads", "max_sequence_length",
        )
        for name in integer_fields:
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
        for name in integer_fields:
            if name != "pad_token_id" and getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.hidden_size % self.num_attention_heads != 0:
            raise ValueError("hidden_size must be divisible by num_attention_heads")
        if self.top_k > self.num_experts:
            raise ValueError("top_k cannot exceed num_experts")
        for name in ("halt_threshold", "dropout"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if not 0.0 <= self.halt_threshold <= 1.0:
            raise ValueError("halt_threshold must be in [0, 1]")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError("dropout must be in [0, 1)")
        if not 0 <= self.pad_token_id < self.vocab_size:
            raise ValueError("pad_token_id outside vocabulary")

    @classmethod
    def foundation(cls) -> "NeuroSparseConfig":
        """Return the minimum 60M-trainable-parameter foundation configuration.

        This only calculates model capacity; it does not allocate model weights
        or initiate training.
        """
        from .math_tokenizer import MathVocabulary

        config = cls(
            vocab_size=len(MathVocabulary.default()),
            hidden_size=512,
            num_layers=3,
            top_k=2,
            expert_multiplier=4,
            max_refinements=3,
            fast_memory_slots=64,
            num_attention_heads=8,
            max_sequence_length=2048,
        )
        trainable = count_parameters(config)
        if trainable < MIN_FOUNDATION_TRAINABLE_PARAMETERS:
            raise ValueError(
                "foundation configuration is below the required "
                f"{MIN_FOUNDATION_TRAINABLE_PARAMETERS:,} trainable parameters "
                f"(computed {trainable:,})"
            )
        return config

    @classmethod
    def expanded(
        cls,
        *,
        hidden_size: int = 768,
        num_layers: int = 4,
        num_experts: int = 12,
        expert_multiplier: int = 4,
        num_attention_heads: int = 12,
        base: "NeuroSparseConfig | None" = None,
    ) -> "NeuroSparseConfig":
        """Build a larger configurable capacity variant without allocating weights.

        Increase width, depth, expert count, or expert width to grow capacity.
        The returned configuration must exceed the foundation's trainable count.
        """
        foundation = cls.foundation()
        source = base or foundation
        config = replace(
            source,
            hidden_size=hidden_size,
            num_layers=num_layers,
            num_experts=num_experts,
            expert_multiplier=expert_multiplier,
            num_attention_heads=num_attention_heads,
        )
        if count_parameters(config) <= count_parameters(foundation):
            raise ValueError("expanded configuration must exceed foundation capacity")
        return config

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def count_total_parameters(config: NeuroSparseConfig) -> int:
    """Exact total parameter count (trainable and fixed) from shapes; no model allocation."""
    if not isinstance(config, NeuroSparseConfig):
        raise TypeError("config must be a NeuroSparseConfig")
    h, e, m = config.hidden_size, config.num_experts, config.expert_multiplier
    block = (15 + 2 * m * e) * h * h + (17 + e * (m + 2)) * h + 1
    # The output head is tied to the token embedding and counted only once.
    return config.vocab_size * h + config.max_sequence_length * h + 2 * h + config.num_layers * block


def count_parameters(config: NeuroSparseConfig) -> int:
    """Count parameters that receive gradients; fixed memory projections are excluded."""
    total = count_total_parameters(config)
    h = config.hidden_size
    # Fast memory's key/value/gate projections are used only inside detached state
    # updates. They are fixed random projections and explicitly frozen in memory.py.
    frozen_per_block = 2 * h * h + h + 1
    return total - config.num_layers * frozen_per_block
