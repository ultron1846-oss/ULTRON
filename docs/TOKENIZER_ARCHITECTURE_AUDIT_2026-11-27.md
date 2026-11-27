# ULTRON tokenizer and model architecture audit

**Audit date:** 2026-11-27  
**Work areas:** Prompt 2, work areas 3–4  
**Status:** Implementation and regression coverage added on `audit/tokenizer-model-architecture-v3-2026-11-27`; GitHub Actions validation and review pending.  
**Training status:** Not authorized and not performed.

## Executive findings

The canonical math tokenizer is a fixed version-1 lexical vocabulary of 240 entries. It preserves supported source spelling and whitespace, including the reserved IDs PAD=0, BOS=1, EOS=2. It is deterministic and lossless for its documented character/operator subset, but it is not a general Unicode tokenizer, full LaTeX tokenizer, parser, or semantic representation.

The foundation model configuration has **63,400,451 total parameters and 61,826,048 trainable parameters**, preserving the minimum 60,000,000-trainable-parameter requirement. The formula was already checked against a small instantiated model; this audit adds a meta-device instantiation test to independently enumerate the foundation module's parameter shapes without allocating 60M real weights.

Two padding-path correctness defects were identified and fixed in this branch:

1. The default `NeuroSparseConfig` declared a vocabulary size of 256 even though the canonical tokenizer has 240 entries. The default now derives from the canonical vocabulary constant. Config compatibility also checks PAD ID 0, and both preflight paths enforce tokenizer version, vocabulary size, and reserved padding ID.
2. The main token loss ignored PAD target IDs, but it did not receive the batch attention mask. Left-padded batches could therefore train the model to predict the first real token from a PAD query position. The loss now accepts the boolean attention mask and only counts adjacent source/target positions that are both valid. The bounded trainer passes the same mask used by the model.

The router-balance and predictive-refinement auxiliary metrics also previously included padded positions. The validity mask is now propagated into both components, so right-padding does not change their reported objectives. Regression tests compare valid logits and auxiliary metrics between padded and unpadded representations.

## Work area 3 — tokenizer and representation

### Contract verified by source and regression tests

- Fixed vocabulary size: 240; reserved IDs are PAD=0, BOS=1, EOS=2.
- Longest-match tokenization for explicitly listed multi-character TeX commands/operators; remaining supported symbols are single lexical tokens.
- Stable token IDs from canonical source order; vocabulary JSON rejects duplicate keys, extra schema fields, duplicate tokens, reordered/noncanonical tokens, and unsupported versions.
- Encode/decode preserves exact supported characters and whitespace; BOS/EOS are optional and special-token skipping is explicit.
- Unknown symbols fail closed with the Python string code-point offset; the tokenizer does not silently map them to UNK or grow its vocabulary.
- Checkpoint model config records tokenizer version and vocabulary size. Legacy configs missing the version field are interpreted as version 1; unsupported explicit versions are rejected. The compatibility check also validates the canonical PAD ID.

### Boundary and edge-case coverage added

Regression fixtures cover empty strings, all canonical token round trips, longest-match operator boundaries, Unicode mathematics, newlines/tabs/CR, astral emoji rejection, combining-mark and non-breaking-space rejection, exact code-point offsets, malformed/non-text input, invalid decode IDs, special tokens, and a fixed-vocabulary/no-growth invariant.

The existing verified-dataset tests cover right-padding with PAD ID 0, boolean attention masks, and refusal to truncate over-length examples. Tokenizer encode/decode itself does not silently pad or truncate.

### Representation limitations

- The 240-token vocabulary is character/command granular. Multi-digit numbers are several digit tokens, so long numeric expressions consume many sequence positions.
- Only explicitly listed Unicode symbols and TeX commands are supported. Combining marks, non-breaking spaces, emoji, and unlisted TeX macros are rejected.
- No Unicode normalization is performed. Mathematically equivalent source spellings remain distinct.
- Lexical preservation is not parsing or semantics: `2x`, `2*x`, and `2 × x` remain distinct; unary minus is not interpreted; a recognized symbol does not imply implemented mathematical meaning.
- There is no unknown-token fallback, tokenizer-side padding, or tokenizer-side truncation. The verified dataset adapter prepends BOS/appends EOS, rejects sequences beyond its limit, and the collator right-pads.
- A future vocabulary/normalization change must use a new tokenizer version and a deliberate checkpoint compatibility/migration policy; it must not silently reorder version-1 IDs.

## Work area 4 — architecture

### Model structure reviewed

The current model is a pre-normalized causal Transformer-style sequence model with learned token and position embeddings, tied input/output token weights, causal multi-head self-attention, top-k sparse expert routing, a predictive GRU refiner, and a fast-weight/episodic memory component. The fast-memory key, value, and gate projections are frozen; the query projection and remaining model parameters are trainable.

Attention masking uses a boolean `[batch, sequence]` mask where True means real token. Attention keys and padded query outputs are masked; masked positions are also excluded from router/refiner auxiliary objectives and cannot be written to episodic memory when memory writes are requested.

### Parameter-count result

| Measure | Result |
|---|---:|
| Total parameters | 63,400,451 |
| Trainable parameters | 61,826,048 |
| Frozen parameters | 1,574,403 |
| Required trainable floor | 60,000,000 |
| Margin above floor | 1,826,048 |

The foundation configuration binds vocabulary size to the canonical 240-entry tokenizer. The new meta-device test instantiates the module graph without materializing real weights and compares `sum(parameter.numel())` and the trainable subset against the formula-based constants. The actual 60M-weight model is not allocated by the test.

### Shape, initialization, gradients, masking, and numerical checks

Existing tests cover forward shape `[B,T,V]`, sequence upper bounds, tied output embeddings, parameter immutability in evaluation mode, attention causal isolation, key padding, invalid token IDs/masks, parameter-formula agreement on an instantiated small model, and finite backward gradients without an optimizer step.

This audit adds checks for finite initialization, neutral LayerNorm initialization, meta-device foundation parameter enumeration, padded/unpadded equivalence for valid logits and auxiliary metrics, non-integer input rejection, and left-padding-aware causal loss. The causal loss remains chunked and casts logits to FP32 for cross-entropy accumulation.

No optimizer step, real foundation weight allocation, CUDA stress run, or training run is included.

## Architecture bottlenecks and recommended follow-up

1. **Vocabulary/sequence efficiency:** the 240-entry lexical representation creates long sequences for ordinary prose and multi-digit expressions. Evaluate a versioned math-aware subword/byte fallback only as a separate tokenizer design; require exact source round trips, bounded vocabulary growth, checkpoint migration rules, and math-specific benchmark parity before adoption.
2. **Attention scaling:** dense causal attention has quadratic sequence-length work and memory pressure as context grows. Profile target hardware before choosing grouped-query attention, sliding-window/local attention, or other context mechanisms; do not trade away mathematical long-range dependencies without held-out evidence.
3. **Sparse expert dispatch:** expert routing is sparse mathematically, but the implementation still performs per-expert dispatch loops. The CUDA path sorts assignments and transfers per-expert counts to the host, introducing synchronization; the CPU path loops through experts. Profile a representative batch before considering grouped GEMM or fused dispatch.
4. **Predictive refinement:** the refiner can execute multiple predictor/GRU passes per token. CPU early exit is data-dependent; accelerator execution uses a fixed bounded iteration count to avoid host synchronization. Measure the quality/latency trade-off before changing the refinement budget.
5. **Stateful memory:** fast/episodic memory is mutable shared state with reset and write-mask requirements. Keep training writes disabled unless the ownership and sequence semantics are separately validated. Its detached projections do not contribute to the trainable count.

These are structural observations from the implementation, not measured performance claims.

## Validation and release gates

- Regression tests have been added to the Python suite; the PR's exact-head GitHub Actions results are still pending.
- After PR CI completes, inspect all relevant Python AI Core, Node, Level 1, and any configured static-analysis checks against the exact PR head.
- No actual model training, optimizer step, full-corpus generation/download, remote compute, pretrained model, or external AI API was used.
- No trained checkpoint exists or is claimed.
- Owner acceptance for actual iPad Safari, free-runtime quotas/persistence, clean-process checkpoint transfer, and the remaining Supabase Auth setting is unchanged.
