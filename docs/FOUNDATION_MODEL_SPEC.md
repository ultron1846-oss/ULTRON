# Foundation model architecture and parameter budget

**Status:** architecture proposal with reproducible parameter-count implementation. Not trained or performance-validated.
**Minimum:** 40,000,000 unique trainable parameters.
**Selected configuration:** 63,400,451 total parameters, of which 61,826,048 are trainable.

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
| Total parameter count | **63,400,451** |
| Trainable parameter count | **61,826,048** |

The config exceeds the 40M floor. The existing small default config remains the fast CI/CPU smoke config and is not the target model.

## Parameter accounting

`count_total_parameters(config)` computes the exact total parameter count from module shapes without allocating the full model. `count_parameters(config)` counts parameters that receive gradients. The output embedding and language-model head share one weight matrix and are counted once. Fast-memory key/value/gate projections are used only in detached memory updates, so they are frozen and excluded from the trainable count; fast-memory and episodic buffers are non-parameter state and excluded from both counts.

Both formulas are regression-tested against total and `requires_grad` parameter enumeration on a small instantiated model. The foundation config is locked to 63,400,451 total / 61,826,048 trainable and checked against the 40M trainable floor without instantiating the large model.

## Resource estimate (FP32, theoretical minimum)

- All model weights (including frozen projections): 253,601,804 bytes (about 241.9 MiB).
- Gradients + two AdamW moment tensors for 61,826,048 trainable parameters: 741,912,576 bytes (about 707.5 MiB).
- Combined FP32 persistent state: 995,514,380 bytes (about 949.4 MiB), before activations, temporary tensors, runtime overhead, allocator fragmentation, input batches, or checkpoint serialization.
- Full 2,048-token attention can be memory- and compute-intensive. A separately measured microbatch/sequence-length plan and gradient accumulation may be required.
- A checkpoint with optimizer state may approach or exceed 1 GiB depending on serialization and state contents.

These are arithmetic estimates, not a claim that a free provider can train this model. Runtime, device memory, sequence length, precision, and checkpoint transfer must be measured before any training authorization.

## Architecture caveats

- Sparse top-k expert selection is not proof of lower end-to-end latency or FLOPs; Python dispatch overhead and dense attention remain.
- Memory/refinement/router components are experimental and not validated as brain-like, mathematically superior, or more efficient.
- The foundation factory now binds its vocabulary size to the canonical version-1 math tokenizer (240 tokens, including reserved IDs). Regression tests assert the exact vocabulary size, total parameter count, and trainable parameter count.
- This is a next-token sequence prototype. It does not establish university-level mathematics, theorem proving, or novel formula discovery.

## Dataset integrity milestone

The generator now has deterministic prompt-disjoint train/validation/test partitioning, duplicate prompt collapse, strict manifest/row schema validation, checksum verification, and content-derived example-ID checks. This does not establish broad mathematical coverage; only five narrow documented generator topics are supported.

## Required before training

1. Tokenizer vocabulary/special IDs are aligned; freeze the complete task serialization and target-mask convention.
2. Decide serialization for problem, derivation, answer, and verifier result.
3. Leakage-safe deterministic train/validation/test splitting is implemented; complete corpus balance/coverage audit.
4. Bounded training controller is implemented and mock-tested; do not execute it without separate authorization and live resource monitoring.
5. Checkpoint state/RNG/hash/backup recovery is implemented; verify sampler cursor and uninterrupted-versus-resumed equivalence only after separate tiny-run authorization.
6. Benchmark actual resource use on the selected free runtime and document quotas.
7. Complete remaining readiness phases and obtain explicit training authorization.
