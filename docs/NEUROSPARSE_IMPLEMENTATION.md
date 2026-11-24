# NeuroSparse Section C — Prototype Implementation

**Status:** experimental code prototype. It is not trained, not benchmarked for competitive performance, and not evidence of mathematical discovery.

## Components

- Configurable PyTorch sequence model and validated configuration.
- Top-k router with per-expert token gather/dispatch and weighted scatter-add. It skips unselected expert token rows, but Python dispatch overhead can erase theoretical FLOP savings.
- Bounded predictive latent refinement using a fixed MSE threshold. This is not a validated free-energy estimator.
- Dual memory experiment: one fast-weight associative matrix plus a bounded content-addressable episodic key/value store. Both are experimental; neither guarantees perfect recall.
- Typed mathematical expression IR with explicit assumption metadata.
- Hand-authored formula-candidate templates and finite-domain counterexample probes. A successful probe is experimental support, never proof or novelty evidence.
- Training loss and optimizer helpers. The next-token loss ignores the configured padding ID by default (pass a different `ignore_index` or `None` explicitly when needed). Importing the package does not start training.
- Atomic checkpoint file replacement with SHA-256 integrity manifest and weights-only loading. Load only trusted local files.
- CPU/GPU forward/backward smoke tool and optional torch.profiler FLOP/memory reporting.

## Honest accounting

The active expert ratio is top_k / num_experts. The default is 2/8 = 25%, not the proposed <=2% research target. It excludes shared embedding, router, refinement, memory and output weights; it is not the full-model active parameter fraction. No speed, energy or quality advantage is claimed.

The current code is not a fixed 3–5M, 40M or 100M parameter model. There is no tokenizer, deterministic training-data generator, curriculum engine, full symbolic algebra, formal proof kernel, literature novelty search, Lean/Coq/Isabelle adapter, or autonomous theorem discovery. Causal self-attention and learned positional embeddings are now implemented in the architecture follow-up described below. The formula templates are seed examples only.

## Checks

Install a PyTorch wheel suitable for the target CPU/GPU, then run from repository root:

    python -m unittest discover -s tests/python -v
    python -m ultron_core.smoke --device cpu --batch 2 --sequence 16
    python -m ultron_core.smoke --device cuda --profile

The smoke tool performs forward and backward propagation only. It performs no optimizer step, training loop, corpus generation, remote job or external AI API call. CUDA requires a CUDA-enabled PyTorch installation and compatible GPU.

## Known limitations

1. The Python expert dispatch and sequential fast-memory writes are reference implementations, not optimized GPU kernels.
2. The predictive halting threshold is fixed and needs calibration and stability analysis.
3. Fast-weight memory is lossy; episodic memory is bounded and overwrites old slots.
4. The finite-domain verifier cannot prove identities or establish mathematical novelty.
5. The checkpoint integrity manifest detects accidental modification but is not a signature or defense against a malicious writer who can replace both files.
6. No training or remote execution was performed for this milestone.


## Read-only memory projection optimization

Read-only memory calls now compute only the query projection. Key and value projections are required only for a write performed while the module is in training mode; they are skipped for ordinary inference and for write requests made while the module is in evaluation mode. This removes two hidden-size linear projections from the common read-only path without changing memory state or recall equations. Regression tests use module hooks to verify the skipped projections in both empty-memory and populated-memory read-only cases. Performance gains remain unquantified until measured on target hardware.


## Core validation and reproducibility hardening

Configuration fields now reject booleans/fractional values where integer dimensions or token IDs are required, and reject non-finite threshold/dropout settings. The routing balance helper validates non-empty top-k assignments, integer index dtype, device consistency, index range and duplicate expert assignments. The predictive refiner validates rank and non-empty dimensions. The expression IR validates node kinds, child tuples, integer atoms, rational literals and symbol identifiers before evaluation. Loss/optimizer helpers reject malformed weights and hyperparameters. The inference benchmark isolates its CPU RNG seed and restores the caller's CPU thread count after execution. These checks improve API safety and experiment reproducibility; they do not make the current prototype a context-aware LLM or a theorem prover.


## Checkpoint validation hardening

Checkpoint save/load now validates non-negative integer step values, checks that serialized configuration matches the model configuration, validates manifest syntax and payload structure before loading, and atomically replaces the checksum manifest through a temporary file. Optimizer restoration now fails explicitly if the caller requests an optimizer restore but the checkpoint contains no optimizer state. The SHA-256 sidecar remains an accidental-corruption check, not an authenticity signature; do not load checkpoints from untrusted sources.


## Accelerator synchronization reduction

The model now skips explicit token min/max checks on accelerator inputs and relies on the embedding operation for index validation; CPU inputs retain the explicit friendly range error. The internal load-balancing call accepts a validation switch: external/default calls still validate index range and uniqueness, while the model disables those scalar checks because indices are produced by PyTorch top-k. Predictive refinement retains CPU early exit but avoids a Python boolean conversion of CUDA activity masks, which would synchronize the device on every refinement iteration. Episodic-memory writes read the ring cursor once per forward and update it once after the sequential write loop rather than synchronizing once per token. These changes reduce host/device synchronization; they do not claim measured throughput gains until benchmarked on accelerator hardware.


## Trusted mathematical knowledge gate

The prototype has no formal proof kernel or verifiable proof-receipt type. Consequently, FormulaCandidate.can_enter_trusted_knowledge() now fails closed for every candidate. A caller-supplied FORMALLY_VERIFIED enum value or free-form evidence string is metadata, not a checked proof. Re-enable trusted admission only when a proof backend can return a structured receipt that ULTRON validates independently.


## Causal sequence architecture — 2026-11-24

The prototype now includes pre-normalized multi-head causal self-attention and learned absolute position embeddings.

- Each block applies causal self-attention before sparse expert routing, predictive refinement and memory recall.
- The boolean attention mask blocks keys at positions strictly later than the current query position. The mask is created on the input device and shared across blocks for that forward pass.
- Learned position embeddings make token order explicit. The configurable max_sequence_length bounds the position table; longer inputs fail with a clear error.
- num_attention_heads is configurable and the configuration rejects hidden sizes that are not divisible by the head count.
- Regression tests check both directions of the causal contract: changing an earlier token can affect later logits, while changing future tokens cannot affect earlier logits.
- This is a small reference implementation using PyTorch MultiheadAttention, not a measured high-performance attention kernel. No flash-attention, KV cache, streaming decode, rotary embeddings, relative positions or long-context scaling is claimed.
- The model remains untrained and still lacks a tokenizer, original deterministic mathematical corpus generator, curriculum, full symbolic algebra, formal proof kernel and demonstrated mathematical capability. Causal attention is a necessary language-modeling prerequisite, not evidence of university-level math ability.

Validation remains the CPU Python regression suite and forward/backward smoke check. These checks do not execute an optimizer step or start training.


### Checkpoint compatibility note

The causal-attention and positional-embedding parameters change the model state and configuration schema. Checkpoint format is now version 2. Version 1 checkpoints from the feed-forward-only prototype are rejected rather than partially loaded or silently initialized; no automatic migration is implemented. This is safe for the current untrained prototype, but a future trained release must provide a deliberate, tested migration or a documented fresh-start boundary.


## Checkpoint and verifier boundary hardening — 2026-11-24

- Checkpoint loading now compares the complete saved state-dictionary key set, tensor types, shapes and dtypes against the target model before calling load_state_dict. This prevents a malformed but checksum-consistent payload from partially mutating the target model before a later shape/key error is raised.
- Finite-domain probing now requires an explicit tuple/list of exact rational samples: integers, rational strings or Fraction values. Floats and booleans are rejected to avoid silently treating binary floating-point approximations as exact mathematical domain points.
- Rational samples are normalized before probing and duplicate equivalent values are rejected, so sample counts cannot be inflated by entries such as 1 and "1/1".
- Regression tests verify that malformed checkpoint tensor shapes leave every target parameter unchanged and that finite-probe domains are exact and unambiguous.
- The SHA-256 manifest remains an accidental-corruption check, not an authenticity signature. Do not load untrusted checkpoint files.


- FormulaCandidate now validates its expression type, enum status, identifier, and immutable tuple-of-string metadata fields at construction. This prevents malformed candidate objects from entering evaluator code through annotation-only assumptions.
