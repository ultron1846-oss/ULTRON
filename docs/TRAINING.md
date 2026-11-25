# Training and Model Status

## Current implementation (source-reviewed 2026-11-25)

The repository contains an **experimental untrained PyTorch model**, an original deterministic generator for three narrow topics, a causal next-token loss, an AdamW optimizer factory, checkpoint save/load helpers, and an inference-only benchmark harness. These are prototypes, not a complete training pipeline.

- `ultron_core/model.py`: experimental sparse-expert causal sequence model.
- `ultron_core/config.py`: small default config for fast smoke tests plus `NeuroSparseConfig.foundation()`, a proposed 63,400,451-parameter configuration.
- `ultron_core/data_generation.py`: deterministic exact-validated examples for arithmetic, rational arithmetic, simple linear equations, and polynomial derivatives (generator v0.2.0); prompt-disjoint deterministic splits; manifest/checksum and content-derived example-ID verification.
- `ultron_core/training.py`: loss/optimizer factory plus a bounded authorized controller with gradient accumulation, clipping, finite checks, cancellation, memory reset, scheduler/checkpoint callbacks, and step/time caps. The controller has only been tested with a mock model/optimizer and has not been run on real weights. Python/Torch/CUDA seeding and a dedicated DataLoader generator are available; exact restart reproducibility still requires sampler state and a clean-runtime resume test.
- `ultron_core/preflight.py`: no-allocation validation of model-size floor, tokenizer compatibility, dataset split integrity, workload bounds, and FP32 persistent-state estimate. It always reports training unauthorized and zero optimizer steps.
- `ultron_core/checkpoint.py`: versioned model/optimizer/scheduler checkpoint, Python/Torch RNG restoration, optional data cursor bound to dataset manifest SHA-256, backup fallback, and transactional restore rollback.
- `ultron_core/benchmark.py`: synthetic-token inference timing, not mathematical quality evaluation.
- `ultron_core/evaluation.py`: exact rational answer scoring for caller-supplied predictions; no model inference or training.

The small default config is a CI/CPU smoke model, not the 40M minimum target. The foundation config is exactly 63,400,451 unique trainable parameters by formula; it has not been trained.

## Safety and scope

Actual model training remains disabled until the user separately authorizes it. Until then, implementation is limited to reproducible infrastructure, tests, data validation, resource planning, and dry-run checks that do not call `optimizer.step()`.

No pretrained model/weights, external AI API, or externally generated training corpus may be introduced. GitHub Pages is static hosting only and must not run model training.

## Before training

Complete [PRETRAINING_READINESS.md](PRETRAINING_READINESS.md), including model/vocabulary audit, leakage-safe splits, robust checkpoint recovery, verified math evaluation, free-runtime measurements, manual iPad acceptance, and the outstanding Supabase Auth setting. Do not claim parameter counts, accuracy, training progress, or checkpoints unless actually measured/created.
