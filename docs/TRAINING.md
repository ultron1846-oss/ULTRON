# Training and Model Status

## Current implementation (source-reviewed 2026-11-25)

The repository contains an **experimental untrained PyTorch model**, an original deterministic generator for eight narrow exact-synthetic topics, a causal next-token loss, an AdamW optimizer factory, checkpoint save/load helpers, and a bounded local training controller. This is not yet a complete end-to-end training pipeline or validated training run.

- `ultron_core/model.py`: experimental sparse-expert causal sequence model.
- `ultron_core/config.py`: small default config for fast smoke tests plus `NeuroSparseConfig.foundation()`, a proposed 63,400,451-total / 61,826,048-trainable configuration.
- `ultron_core/data_generation.py`: deterministic exact-validated examples for arithmetic, rational arithmetic, simple linear equations, and polynomial derivatives and exact definite polynomial integrals (generator v0.3.0); prompt-disjoint deterministic splits; manifest/checksum and content-derived example-ID verification.
- `ultron_core/training.py`: loss/optimizer factory plus a bounded authorized controller with gradient accumulation, clipping, finite checks, cancellation, memory reset, scheduler/checkpoint callbacks, step/time caps, and a runtime memory guard that samples process RSS plus CUDA allocator-reserved bytes at controller boundaries. The controller has only been tested with a mock model/optimizer and has not been run on real weights. Its preflight gate now requires a complete non-authorizing report, sufficient persistent-state budget, matching batch/sequence/accumulation limits, and local-only flags. Memory writes default off and are rejected by the current trainer until sequential chunk semantics exist; the wall-time cap is best-effort at batch/step boundaries. Python/Torch/CUDA seeding and a dedicated DataLoader generator are available; resume now skips initial reseeding when valid checkpoint metadata confirms RNG restoration and matching dataset hash. Checkpoint callbacks carry global step, epoch, next batch index, seed, accumulation setting, dataset hash, and—when a `ResumableRandomSampler` is supplied—its exact sampler state. The trainer restores sampler state before DataLoader iterator creation, requires that sampler to be attached to the supplied DataLoader, enforces `num_workers=0` and `drop_last=False`, matches the loader batch size and sampler dataset size to preflight, and checks sample-cursor/batch-cursor alignment. It rewinds sampler state when a partial accumulation group is discarded. The notebook caller must save callback `data_state` in the checkpoint and verify clean-runtime resume; the website's Training Control page is a generic public status/readiness panel with all execution controls disabled; exact uninterrupted-vs-resumed equivalence remains pending.
- `ultron_core/preflight.py`: no-allocation validation of model-size floor, tokenizer compatibility, dataset split integrity, workload bounds, and FP32 persistent-state estimate. It always reports training unauthorized and zero optimizer steps.
- `ultron_core/checkpoint.py`: versioned model/optimizer/scheduler checkpoint, Python/Torch RNG restoration, optional data cursor bound to dataset manifest SHA-256, expected-dataset validation before state mutation, backup fallback, and transactional restore rollback.
- `ultron_core/resumable_sampler.py`: deterministic epoch-based shuffled sampler with dataset-manifest-bound state, exact sample cursor restore, and validation against changed dataset size/hash/seed. Exact mid-epoch state requires `DataLoader(num_workers=0)` unless consumed-cursor accounting compensates for prefetch.
- `ultron_core/benchmark.py`: synthetic-token inference timing; CI now runs a tiny CPU smoke benchmark, not a foundation-model or mathematical-quality baseline.
- `ultron_core/evaluation.py`: schema-v3 exact-answer scoring for caller-supplied predictions, exact supported polynomial equivalence, and mutually exclusive answer-error classes.
- `ultron_core/model_only_evaluation.py`: bounded greedy model-only inference with no command-tool interface passed to `forward`, plus separate model-only/tool-assisted metrics for caller-supplied prediction maps. CI tests use a tiny mock model; no foundation-model inference or training has been run.
- `ultron_core/level1_training.py`: the authorized Level 1 source now serializes only allowlisted generator prompt/steps/answer fields, records a generator-owned target contract in its manifest hash, and treats the exact verifier as validation-only. Unknown tool-output fields are excluded by regression tests; this is not yet a generic external-data ingestion guard.
- `ultron_core/concepts.py`: stable concept/prerequisite metadata for the eight core generator topics, validated as an acyclic graph; deterministic concept-balanced sampling and a category-aware train/test transfer-split validator. See `docs/CONCEPT_TRANSFER_EVALUATION.md`. This maps core topics only, not the full curriculum.
- `ultron_core/curriculum_prerequisites.py`: validated loader for the curated prerequisite graph covering all 197 university curriculum topics across 17 fields; grade-band curricula are not yet mapped. See `docs/UNIVERSITY_PREREQUISITES.md`.

The small default config is a CI/CPU smoke model, not the >60M trainable target. The foundation config is exactly 63,400,451 total parameters and 61,826,048 trainable parameters by formula; it has not been trained. The generator's matrix tasks are exact synthetic exercises, not broad linear algebra or university-level competence.

## Safety and scope

Actual model training remains disabled until the user separately authorizes it. CI uses only a mock optimizer for controller tests; no optimizer step has been run on ULTRON's real weights. The bounded controller samples process RSS plus CUDA allocator-reserved memory against the preflight byte budget at safe boundaries. It cannot interrupt a single tensor operation, and platform-specific RSS fallback limitations apply. See [RESOURCE_MONITORING.md](RESOURCE_MONITORING.md).

No pretrained model/weights, external AI API, or externally generated training corpus may be introduced. GitHub Pages is static hosting only and must not run model training.

## Before training

Complete [PRETRAINING_READINESS.md](PRETRAINING_READINESS.md), including model/vocabulary audit, leakage-safe splits, robust checkpoint recovery, verified math evaluation, free-runtime measurements, manual iPad acceptance, and the outstanding Supabase Auth setting. Do not claim parameter counts, accuracy, training progress, or checkpoints unless actually measured/created.


## Memory-aware loss and optimizer selection

`causal_language_model_loss(..., loss_chunk_size=1024)` computes FP32 cross-entropy in token chunks per batch row. The chunk size bounds the temporary FP32 logits tensor; the loss is normalized by the total count of non-padding next-token targets, so padding and uneven final chunks do not change the mean. Use a smaller chunk to reduce peak loss memory (at the cost of more kernel launches) or a larger chunk for fewer launches when memory permits. Regression tests compare scalar loss and gradients with the original full-tensor reference.

`make_optimizer(..., fused=None)` automatically requests fused AdamW only when all trainable parameters are on one CUDA device. Automatic mode falls back to ordinary AdamW if the installed build rejects fused mode. `fused=False` forces the portable implementation; `fused=True` requires one CUDA device. Benchmark on target hardware before claiming a throughput improvement. The default learning rate and weight decay are unchanged.


## Training-loop host synchronization

The controller retains detached scalar losses on-device instead of converting each microbatch loss to a Python float. At the optimizer boundary it checks accumulated loss scalars and the clipped global gradient norm with one small device-to-host transfer. A non-finite gradient makes the global norm non-finite, so separate per-parameter host checks are unnecessary. Checkpoint loss values are transferred only when requested, and the overall mean is materialized at finalization.

Non-finite loss or gradients still prevent the optimizer step. The regression test counts explicit host transfers and expects one per optimizer step rather than one per microbatch. Benchmark on target hardware before quantifying performance impact.


## Causal attention memory optimization

The model routes its existing fused Q/K/V and output-projection parameters through PyTorch scaled-dot-product attention. For unpadded batches, it uses the built-in causal flag instead of allocating an explicit boolean sequence-by-sequence mask. This preserves the MultiheadAttention parameter names and checkpoint layout. Padded batches use a combined causal/key-validity mask with SDPA's True-means-allowed convention. Regression tests compare outputs and input gradients against the previous MultiheadAttention reference path. The fast path removes one explicit quadratic mask allocation; measured throughput and device-specific peak-memory improvement remain unverified until benchmarked on target hardware.


## Bounded training loss metrics

The training controller retains only the current gradient-accumulation group's detached losses for finite-value validation and checkpoint metrics. The session-wide mean is tracked with a single on-device scalar sum and a count, then materialized once at finalization. This prevents a long training session from retaining one CUDA scalar tensor per microbatch or constructing a full-session stack at the end. The metric remains the arithmetic mean of all processed microbatch losses, including a final incomplete group that is discarded from optimizer updates. Regression coverage simulates 20 microbatches and asserts that stack sizes remain bounded by the accumulation group. This is a memory-growth fix; no training or device benchmark was run.


## Tool-independence acceptance — 2026-11-26

Issue #135's engineering acceptance is implemented: model-only inference with no tools passed to the model; separate model-only/tool-assisted reports; tool-disabled and target-leakage regression tests; explicit generator/verifier provenance; concept-aware sampling; a validated concept-transfer split protocol; and prerequisite edges for all 197 university curriculum topics.

This does not authorize or report dataset import, benchmark row generation, optimizer steps, or model training. The frozen concept-transfer benchmark and grade-band mapping remain pre-training readiness tasks.


## Account-free frontend controls — 2026-11-26

The public website displays generic runtime status only. It does not expose Start/Pause/Stop/Resume/Save checkpoint buttons, device pairing controls, or account-specific job/checkpoint history. The local Memory Vault remains browser-local; private Supabase records are not read by the static frontend. Training and remote execution remain disabled.


## iPad and memory preference status — 2026-11-26

Automated static frontend checks verify the viewport, mobile breakpoint, safe-area inset, 44 px touch-target minimum, and local persistence of the 2–10 GB preferred training-memory slider. Manual Safari acceptance on an iPad remains pending. The slider is a local preference only; it is not connected to live RAM/VRAM allocation or a training runtime.


## Versioned runtime configuration handoff — PR #182 merged

The Settings page can export `ultron-runtime-config.json` using schema version 1. The file includes the browser-selected 2–10 GiB memory budget, bounded batch/sequence/accumulation defaults, and explicit `training_authorized: false` / `remote_execution_enabled: false` values. The browser `runtime-config.js` module validates the generated schema, and Python's `RuntimeConfig` parser independently rejects unknown or missing fields, duplicate JSON keys, out-of-range values, oversize input, and any attempt to enable training or remote execution. `preflight_training_plan_from_runtime_config(...)` forwards only the validated workload and budget fields into the existing preflight. Its `preflight_kwargs()` returns only the workload and memory-budget fields accepted by preflight.

This is a validated file-based configuration handoff—not a live website-to-runtime connection. PR #182 was squash-merged as `87db245d7147690d986535fa6b80f60015634d5e` after Node, Python AI Core, and Level 1 PR checks passed; all six post-merge main checks passed (Python AI Core `45924733525`, Level 1 `45924733537`, Node `45924733492`, Pages build/report/deploy `45924733234`). It does not allocate RAM/VRAM, authenticate with a provider, run preflight by itself, authorize training, or start a job. The real runtime integration and device acceptance remain outstanding. See [RUNTIME_CONFIG.md](RUNTIME_CONFIG.md).
