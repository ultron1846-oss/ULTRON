# Foundation model architecture and parameter budget

**Status:** architecture proposal with reproducible parameter-count implementation. Not trained or performance-validated.
**Minimum:** 40,000,000 unique trainable parameters.
**Selected configuration:** 63,400,451 unique trainable parameters.

## Proposed foundation configuration

The factory `NeuroSparseConfig.foundation()` defines:

| Setting | Value |
|---|---:|
| Vocabulary size | 240 |
| Hidden width | 512 |
| Transformer blocks | 3 |
| Attention heads | 8 |
| Experts per block | 8 |
| Top-k experts/token | 2 |
| Expert expansion multiplier | 4 |
| Predictive refinement steps (max) | 3 |
| Fast-memory slots | 64 |
| Learned position table | 2,048 positions |
| Parameter count | **63,400,451** |

The config exceeds the 40M floor. The existing small default config remains the fast CI/CPU smoke config and is not the target model.

## Parameter accounting

`count_parameters(config)` computes the exact unique trainable parameter count from module shapes without allocating the full model. The output embedding and language-model head share one weight matrix and are counted once. Non-trainable fast-memory and episodic buffers are excluded.

The formula is regression-tested against actual parameter enumeration on a small instantiated model. A separate test locks the foundation config to 63,400,451 and checks the 40M floor without instantiating the large model.

## Resource estimate (FP32, theoretical minimum)

- Model weights: 253,601,804 bytes (about 241.9 MiB).
- Weights + gradients + two AdamW moment tensors: about 967.4 MiB, before activations, temporary tensors, runtime overhead, allocator fragmentation, input batches, or checkpoint serialization.
- Full 2,048-token attention can be memory- and compute-intensive. A separately measured microbatch/sequence-length plan and gradient accumulation may be required.
- A checkpoint with optimizer state may approach or exceed 1 GiB depending on serialization and state contents.

These are arithmetic estimates, not a claim that a free provider can train this model. Runtime, device memory, sequence length, precision, and checkpoint transfer must be measured before any training authorization.

## Architecture caveats

- Sparse top-k expert selection is not proof of lower end-to-end latency or FLOPs; Python dispatch overhead and dense attention remain.
- Memory/refinement/router components are experimental and not validated as brain-like, mathematically superior, or more efficient.
- The foundation factory now binds its vocabulary size to the canonical version-1 math tokenizer (240 tokens, including reserved IDs). Regression tests assert the exact vocabulary size and matching parameter count.
- This is a next-token sequence prototype. It does not establish university-level mathematics, theorem proving, or novel formula discovery.

## Dataset integrity milestone

The generator now has deterministic prompt-disjoint train/validation/test partitioning, duplicate prompt collapse, strict manifest/row schema validation, checksum verification, and content-derived example-ID checks. This does not establish broad mathematical coverage; only the three documented generator topics are supported.

## Required before training

1. Audit tokenizer/vocabulary compatibility and special-token IDs.
2. Decide serialization for problem, derivation, answer, and verifier result.
3. Create leakage-safe deterministic train/validation/test splits and evaluate generator coverage.
4. Implement bounded training with gradient accumulation, finite-loss/gradient checks, cancellation, and explicit opt-in.
5. Validate checkpoint resume equivalence, optimizer/scheduler/RNG restoration, and interrupted-save recovery.
6. Benchmark actual resource use on the selected free runtime and document quotas.
7. Complete remaining readiness phases and obtain explicit training authorization.
