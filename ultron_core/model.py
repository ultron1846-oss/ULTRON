import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint as activation_checkpoint
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


def _dispatch_sparse_experts(flat, weights, indices, experts):
    """Dispatch fixed top-k assignments after one expert-id sort.

    CUDA's one-argument torch.where/nonzero needs a dynamic output shape and
    synchronizes with the host. Sorting the fixed-size top-k assignment list
    lets the CUDA path replace one dynamic selection per expert with one
    small counts transfer per block. The CPU path keeps the simpler reference
    implementation because it does not pay device synchronization costs.
    """
    token_count, top_k = indices.shape
    assignment_experts = indices.reshape(-1)
    assignment_tokens = torch.arange(
        token_count, device=flat.device
    ).repeat_interleave(top_k)
    assignment_weights = weights.reshape(-1)

    order = torch.argsort(assignment_experts, stable=True)
    sorted_experts = assignment_experts.index_select(0, order)
    sorted_tokens = assignment_tokens.index_select(0, order)
    sorted_weights = assignment_weights.index_select(0, order)
    counts = torch.bincount(sorted_experts, minlength=len(experts)).cpu().tolist()

    dispatched = torch.zeros_like(flat)
    offset = 0
    for expert, count in zip(experts, counts):
        stop = offset + count
        if count:
            token_pos = sorted_tokens[offset:stop]
            values = expert(flat.index_select(0, token_pos))
            values = values * sorted_weights[offset:stop].unsqueeze(-1)
            dispatched.index_add_(0, token_pos, values)
        offset = stop
    return dispatched



def _causal_attention_with_mha_weights(attention, x, *, causal_mask=None, key_padding_mask=None):
    """Run existing MHA projection weights through SDPA's causal fast path.

    Unpadded batches avoid allocating an S×S triangular mask. With padding,
    combine causal and key-validity masks; SDPA uses True=allowed, unlike MHA.
    Parameter names remain MultiheadAttention-compatible for existing checkpoints.
    """
    batch, sequence, embed_dim = x.shape
    if attention.in_proj_weight is None:
        raise RuntimeError("ULTRON attention requires fused Q/K/V projection weights")
    qkv = F.linear(x, attention.in_proj_weight, attention.in_proj_bias)
    query, key, value = qkv.chunk(3, dim=-1)
    head_dim = embed_dim // attention.num_heads

    def split_heads(tensor):
        return tensor.reshape(batch, sequence, attention.num_heads, head_dim).transpose(1, 2)

    query, key, value = split_heads(query), split_heads(key), split_heads(value)
    if key_padding_mask is None:
        sdpa_mask = None
        is_causal = True
    else:
        if causal_mask is None:
            causal_mask = torch.ones((sequence, sequence), dtype=torch.bool, device=x.device).triu(diagonal=1)
        sdpa_mask = (~key_padding_mask)[:, None, None, :] & (~causal_mask)[None, None, :, :]
        is_causal = False

    attended = F.scaled_dot_product_attention(
        query, key, value,
        attn_mask=sdpa_mask,
        dropout_p=attention.dropout if attention.training else 0.0,
        is_causal=is_causal,
    )
    attended = attended.transpose(1, 2).contiguous().reshape(batch, sequence, embed_dim)
    return F.linear(attended, attention.out_proj.weight, attention.out_proj.bias)

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

    def forward(self, x, write_memory=False, causal_mask=None, key_padding_mask=None, write_mask=None):
        # Pre-normalized causal self-attention is the sequence-mixing path.
        # True entries in PyTorch's boolean attention mask are disallowed.
        attention_input = self.attention_norm(x)
        attention_output = _causal_attention_with_mha_weights(
            self.attention, attention_input,
            causal_mask=causal_mask, key_padding_mask=key_padding_mask,
        )
        # Left-padded query rows can have no causally visible valid key. PyTorch
        # may return NaNs for those padded queries; they are never model targets.
        if key_padding_mask is not None:
            attention_output = attention_output.masked_fill(
                key_padding_mask.unsqueeze(-1), 0.0
            )
        x = x + self.dropout(attention_output)

        residual = x
        normalized = self.norm(x)
        logits, weights, indices = self.router(normalized)
        flat = normalized.reshape(-1, normalized.shape[-1])
        idx = indices.reshape(-1, indices.shape[-1])
        wt = weights.reshape(-1, weights.shape[-1])
        if flat.device.type == "cuda":
            dispatched = _dispatch_sparse_experts(flat, wt, idx, self.experts)
        else:
            # On CPU, retain the straightforward path; sorting assignments
            # would add overhead without removing host/device synchronization.
            dispatched = torch.zeros_like(flat)
            for expert_id, expert in enumerate(self.experts):
                token_pos, slot_pos = torch.where(idx == expert_id)
                if token_pos.numel() == 0:
                    continue
                values = expert(flat.index_select(0, token_pos)) * wt[token_pos, slot_pos].unsqueeze(-1)
                dispatched.index_add_(0, token_pos, values)

        mixed = dispatched.reshape_as(x) + self.memory(x, write=write_memory, write_mask=write_mask)
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
        self.activation_checkpointing = False

    def set_activation_checkpointing(self, enabled: bool) -> None:
        if not isinstance(enabled, bool):
            raise TypeError("activation_checkpointing must be boolean")
        self.activation_checkpointing = enabled

    def reset_memory(self) -> None:
        """Clear mutable fast/episodic memory before processing a new independent example."""
        for block in self.blocks:
            block.memory.reset_memory()

    def forward(self, input_ids: torch.Tensor, write_memory: bool = False, attention_mask: torch.Tensor | None = None):
        if input_ids.ndim != 2:
            raise ValueError("input_ids must be [batch, sequence]")
        if input_ids.shape[0] == 0 or input_ids.shape[1] == 0:
            raise ValueError("batch and sequence dimensions must be non-empty")
        if input_ids.dtype not in (torch.int32, torch.int64):
            raise TypeError("input_ids must be integer")
        sequence_length = input_ids.shape[1]
        if write_memory and self.training and input_ids.shape[0] != 1:
            raise ValueError(
                "training-time memory writes require batch_size=1 because memory state "
                "is shared; reset_memory() between independent examples"
            )
        if sequence_length > self.config.max_sequence_length:
            raise ValueError("sequence length exceeds max_sequence_length")
        if attention_mask is not None:
            if not isinstance(attention_mask, torch.Tensor):
                raise TypeError("attention_mask must be a boolean tensor")
            if attention_mask.dtype != torch.bool:
                raise TypeError("attention_mask must use torch.bool")
            if attention_mask.shape != input_ids.shape:
                raise ValueError("attention_mask must have the same [batch, sequence] shape as input_ids")
            if attention_mask.device != input_ids.device:
                raise ValueError("attention_mask and input_ids must be on the same device")
            if not bool(attention_mask.any(dim=1).all()):
                raise ValueError("every sequence must contain at least one non-padding token")
            key_padding_mask = ~attention_mask
            write_mask = attention_mask
        else:
            key_padding_mask = None
            write_mask = None
        # CPU range checks are cheap; on CUDA, avoid synchronizing the device
        # just to inspect scalar min/max values. Embedding validates indices.
        if input_ids.device.type == "cpu" and (
            input_ids.min() < 0 or input_ids.max() >= self.config.vocab_size
        ):
            raise ValueError("token id outside vocabulary")

        positions = torch.arange(sequence_length, device=input_ids.device)
        x = self.embedding(input_ids.long()) + self.position_embedding(positions).unsqueeze(0)
        # Unpadded batches use SDPA's causal flag and need no dense mask.
        causal_mask = None
        if key_padding_mask is not None:
            causal_mask = torch.ones(
                (sequence_length, sequence_length),
                dtype=torch.bool,
                device=input_ids.device,
            ).triu(diagonal=1)

        balances, errors, steps = [], [], []
        for block in self.blocks:
            if (self.activation_checkpointing and self.training
                    and torch.is_grad_enabled() and not write_memory):
                # Recompute block activations during backward to reduce saved
                # activation memory. Mutable memory writes remain unsupported.
                def block_forward(hidden, current_block=block):
                    return current_block(
                        hidden, write_memory=False, causal_mask=causal_mask,
                        key_padding_mask=key_padding_mask, write_mask=write_mask
                    )
                x, balance, error, count = activation_checkpoint(
                    block_forward, x, use_reentrant=False
                )
            else:
                x, balance, error, count = block(
                    x, write_memory=write_memory, causal_mask=causal_mask,
                    key_padding_mask=key_padding_mask, write_mask=write_mask
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
