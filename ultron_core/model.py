import torch
from torch import nn
from .config import NeuroSparseConfig
from .routing import SparseRouter, load_balance_loss
from .memory import FastWeightMemory
from .predictive import PredictiveRefiner


class SparseExpert(nn.Module):
    def __init__(self, h: int, multiplier: int, dropout: float):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(h, h * multiplier),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(h * multiplier, h),
        )

    def forward(self, x):
        return self.net(x)


class NeuroSparseBlock(nn.Module):
    def __init__(self, c: NeuroSparseConfig):
        super().__init__()
        h = c.hidden_size
        self.attention_norm = nn.LayerNorm(h)
        self.attention = nn.MultiheadAttention(
            embed_dim=h,
            num_heads=c.num_attention_heads,
            dropout=c.dropout,
            batch_first=True,
        )
        self.norm = nn.LayerNorm(h)
        self.router = SparseRouter(h, c.num_experts, c.top_k)
        self.experts = nn.ModuleList([
            SparseExpert(h, c.expert_multiplier, c.dropout)
            for _ in range(c.num_experts)
        ])
        self.memory = FastWeightMemory(h, c.fast_memory_slots)
        self.refiner = PredictiveRefiner(h, c.max_refinements, c.halt_threshold)
        self.dropout = nn.Dropout(c.dropout)

    def forward(self, x, write_memory=False, causal_mask=None):
        # Pre-normalized causal self-attention is the sequence-mixing path.
        # True entries in PyTorch's boolean attention mask are disallowed.
        attention_input = self.attention_norm(x)
        attention_output, _ = self.attention(
            attention_input,
            attention_input,
            attention_input,
            attn_mask=causal_mask,
            need_weights=False,
        )
        x = x + self.dropout(attention_output)

        residual = x
        normalized = self.norm(x)
        logits, weights, indices = self.router(normalized)
        flat = normalized.reshape(-1, normalized.shape[-1])
        idx = indices.reshape(-1, indices.shape[-1])
        wt = weights.reshape(-1, weights.shape[-1])
        dispatched = torch.zeros_like(flat)
        for expert_id, expert in enumerate(self.experts):
            token_pos, slot_pos = torch.where(idx == expert_id)
            if token_pos.numel() == 0:
                continue
            values = expert(flat.index_select(0, token_pos)) * wt[token_pos, slot_pos].unsqueeze(-1)
            dispatched.index_add_(0, token_pos, values)

        mixed = dispatched.reshape_as(x) + self.memory(x, write=write_memory)
        refined, error, steps = self.refiner(mixed)
        # Router top-k guarantees valid, unique indices. Skip redundant
        # host-visible validation in this performance-critical internal path.
        balance = load_balance_loss(
            logits.reshape(-1, logits.shape[-1]), idx, validate_indices=False
        )
        return residual + self.dropout(refined), balance, error, steps


class NeuroSparseModel(nn.Module):
    def __init__(self, config: NeuroSparseConfig):
        super().__init__()
        self.config = config
        self.embedding = nn.Embedding(
            config.vocab_size, config.hidden_size, padding_idx=config.pad_token_id
        )
        self.position_embedding = nn.Embedding(
            config.max_sequence_length, config.hidden_size
        )
        self.blocks = nn.ModuleList([
            NeuroSparseBlock(config) for _ in range(config.num_layers)
        ])
        self.final_norm = nn.LayerNorm(config.hidden_size)
        self.lm_head = nn.Linear(config.hidden_size, config.vocab_size, bias=False)
        self.lm_head.weight = self.embedding.weight

    def forward(self, input_ids: torch.Tensor, write_memory: bool = False):
        if input_ids.ndim != 2:
            raise ValueError("input_ids must be [batch, sequence]")
        if input_ids.shape[0] == 0 or input_ids.shape[1] == 0:
            raise ValueError("batch and sequence dimensions must be non-empty")
        if input_ids.dtype not in (torch.int32, torch.int64):
            raise TypeError("input_ids must be integer")
        sequence_length = input_ids.shape[1]
        if sequence_length > self.config.max_sequence_length:
            raise ValueError("sequence length exceeds max_sequence_length")
        # CPU range checks are cheap; on CUDA, avoid synchronizing the device
        # just to inspect scalar min/max values. Embedding validates indices.
        if input_ids.device.type == "cpu" and (
            input_ids.min() < 0 or input_ids.max() >= self.config.vocab_size
        ):
            raise ValueError("token id outside vocabulary")

        positions = torch.arange(sequence_length, device=input_ids.device)
        x = self.embedding(input_ids.long()) + self.position_embedding(positions).unsqueeze(0)
        causal_mask = torch.ones(
            (sequence_length, sequence_length),
            dtype=torch.bool,
            device=input_ids.device,
        ).triu(diagonal=1)

        balances, errors, steps = [], [], []
        for block in self.blocks:
            x, balance, error, count = block(
                x, write_memory=write_memory, causal_mask=causal_mask
            )
            balances.append(balance)
            errors.append(error)
            steps.append(count.to(x.dtype))
        logits = self.lm_head(self.final_norm(x))
        return {
            "logits": logits,
            "load_balance_loss": torch.stack(balances).mean(),
            "prediction_error": torch.stack(errors).mean(),
            "refinement_steps": torch.stack(steps).float().mean(),
        }

    def active_parameter_fraction(self) -> float:
        # Expert-only selection ratio; not full-model active parameter fraction.
        return self.config.top_k / self.config.num_experts
