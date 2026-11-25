# Training and Model Status

## Current implementation (source-reviewed 2026-11-25)

The repository contains an **experimental untrained PyTorch model**, an original deterministic generator for seven narrow exact-synthetic topics, a causal next-token loss, an AdamW optimizer factory, checkpoint save/load helpers, and a bounded local training controller. This is not yet a complete end-to-end training pipeline or validated training run.

- `ultron_core/model.py`: experimental sparse-expert causal sequence model.
- `ultron_core/config.py`: small default config for fast smoke tests plus `NeuroSparseConfig.foundation()`, a proposed 63,400,451-total / 61,826,048-trainable configuration.
- `ultron_core/data_generation.py`: deterministic exact-validated examples for arithmetic, rational arithmetic, simple linear equations, and polynomial derivatives and exact definite polynomial integrals (generator v0.3.0); prompt-disjoint deterministic splits; manifest/checksum and content-derived example-ID verification.
- `ultron_core/training.py`: loss/optimizer factory plus a bounded authorized controller with gradient accumulation, clipping, finite checks, cancellation, memory reset, scheduler/checkpoint callbacks, and step/time caps. The controller has only been tested with a mock model/optimizer and has not been run on real weights. Its preflight gate now requires a complete non-authorizing report, sufficient persistent-state budget, matching batch/sequence/accumulation limits, and local-only flags. Memory writes default off and are rejected by the current trainer until sequential chunk semantics exist; the wall-time cap is best-effort at batch/step boundaries. Python/Torch/CUDA seeding and a dedicated DataLoader generator are available; resume now skips initial reseeding when valid checkpoint metadata confirms RNG restoration and matching dataset hash. Checkpoint callbacks now carry global step, epoch, next batch index, seed, accumulation setting, and dataset hash; resume requires explicit epoch/next-batch cursor and global step. The caller must restore the sampler/iterator from that cursor. If the controller discards a partial accumulation group, its returned cursor rewinds to the last completed optimizer step so those examples are replayed. Exact restart reproducibility still requires sampler state and a clean-runtime resume test.
- `ultron_core/preflight.py`: no-allocation validation of model-size floor, tokenizer compatibility, dataset split integrity, workload bounds, and FP32 persistent-state estimate. It always reports training unauthorized and zero optimizer steps.
- `ultron_core/checkpoint.py`: versioned model/optimizer/scheduler checkpoint, Python/Torch RNG restoration, optional data cursor bound to dataset manifest SHA-256, expected-dataset validation before state mutation, backup fallback, and transactional restore rollback.
- `ultron_core/resumable_sampler.py`: deterministic epoch-based shuffled sampler with dataset-manifest-bound state, exact sample cursor restore, and validation against changed dataset size/hash/seed. Exact mid-epoch state requires `DataLoader(num_workers=0)` unless consumed-cursor accounting compensates for prefetch.
- `ultron_core/benchmark.py`: synthetic-token inference timing; CI now runs a tiny CPU smoke benchmark, not a foundation-model or mathematical-quality baseline.
- `ultron_core/evaluation.py`: schema-v3 exact-answer scoring for caller-supplied predictions, exact supported polynomial equivalence, and mutually exclusive answer-error classes; no model inference or training.

The small default config is a CI/CPU smoke model, not the 40M minimum target. The foundation config is exactly 63,400,451 total parameters and 61,826,048 trainable parameters by formula; it has not been trained. The generator's matrix tasks are exact synthetic exercises, not broad linear algebra or university-level competence.

## Safety and scope

Actual model training remains disabled until the user separately authorizes it. CI uses only a mock optimizer for controller tests; no optimizer step has been run on ULTRON's real weights. Resource monitoring is currently preflight-budget-only, not live device telemetry.

No pretrained model/weights, external AI API, or externally generated training corpus may be introduced. GitHub Pages is static hosting only and must not run model training.

## Before training

Complete [PRETRAINING_READINESS.md](PRETRAINING_READINESS.md), including model/vocabulary audit, leakage-safe splits, robust checkpoint recovery, verified math evaluation, free-runtime measurements, manual iPad acceptance, and the outstanding Supabase Auth setting. Do not claim parameter counts, accuracy, training progress, or checkpoints unless actually measured/created.
