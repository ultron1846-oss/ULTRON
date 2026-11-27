# ULTRON engineering campaign status

This file tracks the 14-stage campaign from `Pasted markdown(2).md`. Statuses distinguish merged implementation from validation or owner acceptance. This is not a training authorization.

## Stage status

| Stage | Status | Evidence / remaining gate |
|---|---|---|
| 0. Establish baseline | Complete | Repository, active PRs, CI, README, architecture, readiness and dependency paths inspected; current work is recorded in README. |
| 1. Finish current dataset improvements | Complete | PR #193 merged; exact-head checks and post-merge checks verified. |
| 2. Dataset infrastructure overhaul | Benchmark merged; stress tests in PR #201 | PR #194–#196 provide verified disk-backed snapshot/index, streamed preflight, integrity checks, and read-only benchmark. PR #201 adds 3,500-row split/stream/random-access stress, integrity-tamper and cleanup tests; CI/review pending. Production dataset measurements remain owner-dependent. |
| 3. Mathematical data pipeline | In progress | PR #197 independently checks all 20 existing extended university templates (2,000 deterministic seed/difficulty cases). PR #201 proposes a new Euclidean algorithm generator with independent gcd/Bézout checks; pending CI/review. Current main still has 59/197 generated university topics and 138 without generators. Full corpus generation/download remains deferred. |
| 4. Tokenizer and mathematical representation | Audit implementation in PR #203; CI pending | PR #203 aligns default config with canonical 240-token v1 vocabulary, checks tokenizer/version/vocabulary/PAD compatibility, extends Unicode and boundary tests, and documents lexical/math representation limits. Existing verified-dataset padding and no-truncation contracts remain. |
| 5. Model architecture and parameter verification | Audit implementation in PR #203; CI pending | PR #203 adds mask-correct router/refiner objectives, left-padding-aware causal loss, deterministic initialization/shape/gradient tests, and meta-device enumeration of 63,400,451 total / 61,826,048 trainable parameters. No foundation weights are allocated. |
| 6. Training engine and recovery | Implemented; owner acceptance pending | Bounded trainer, sampler cursor, checkpoint integrity/metadata, backup recovery and fresh-object synthetic restore tests exist. No ULTRON optimizer step. Owner must validate checkpoint transfer and clean-process resume on a separate runtime. |
| 7. Evaluation and mathematical tools | In progress | Exact arithmetic, symbolic/equation tools, benchmark and evaluation modules exist. Remaining: unify repeatable reports, coverage/error categories, independent benchmark review and frozen transfer benchmark provenance. |
| 8. Inference engine | In progress | Model-only evaluation and checkpoint compatibility components exist. Remaining: verify a public inference interface end-to-end with a verified checkpoint; no trained checkpoint exists yet. |
| 9. Compression toolkit | Implemented; validation pending | Compression/quantization/low-rank pipeline and artifact metadata exist. Remaining: run permitted non-training round-trip/corruption tests and report size/error; quality claims require a trained checkpoint and evaluation. |
| 10. Website and training-control frontend | Automated contract implemented; manual iPad acceptance pending | GitHub Pages build/deploy, account-free UI, local RAM preference, responsive/accessibility contracts are tested. Actual iPad Safari acceptance remains owner-only. |
| 11. Website/backend protocol and resource safeguards | In progress | Runtime config schema and read-only training status exist; no job execution or pairing controls. RAM slider is a local requested preference, not an enforced process-memory limit. Status freshness, offline/disconnect and resource enforcement remain. |
| 12. Security, CI and release quality | In progress | CI workflows, security contracts and database privilege hardening exist. Remaining: consolidated dependency/license/permissions/serialization/network review and clean-branch reproducibility. |
| 13. Full-system validation | Pending | Requires all permitted subsystem tests, non-training smoke tests, frontend build, resource checks and independent readiness review. |
| 14. Final readiness report | Pending | Must record main commit, PRs, CI, model/data/tokenizer/training/checkpoint/evaluation/compression/inference/frontend/resource status, limitations and blockers. |

## Required owner acceptance

- Manual Safari on an actual iPad: portrait/landscape, navigation, touch targets, local memory preference, memory export/import and training page read-only state.
- Separate-runtime checkpoint transfer/resume, preserving checkpoint, SHA-256 manifest, metadata sidecar and relevant backup files.
- Verify free runtime availability, quota, timeout, persistence and no-phone setup.
- Confirm Supabase Auth leaked-password protection setting.
- Confirm zero-cost resource and storage limits.

## Authorization boundary

Do not generate/download the full training corpus, train ULTRON weights, perform optimizer steps, run long training, launch remote compute, or incur cost without separate explicit authorization. Small deterministic unit fixtures and non-training validation are permitted. No pretrained model, weights, external AI API, or external generated training corpus may be used.


## Tokenizer/model audit — PR #203

Implementation and deterministic regression coverage are proposed in PR #203. The PR is open; the final CI/review gate is pending. The report records the 240-token tokenizer contract, checkpoint version rules, mask/loss behavior, 60M+ parameter verification, structural bottlenecks, and unmeasured CUDA/device performance limits.
