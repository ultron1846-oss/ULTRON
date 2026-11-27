# ULTRON engineering campaign status

This file tracks the 14-stage campaign from `Pasted markdown(2).md`. Statuses distinguish merged implementation from validation or owner acceptance. This is not a training authorization.

## Stage status

| Stage | Status | Evidence / remaining gate |
|---|---|---|
| 0. Establish baseline | Complete | Repository, active PRs, CI, README, architecture, readiness and dependency paths inspected; current work is recorded in README. |
| 1. Finish current dataset improvements | Complete | PR #193 merged; exact-head checks and post-merge checks verified. |
| 2. Dataset infrastructure overhaul | Engineering benchmark merged; production measurement pending | PR #194, #195, and #196 merged: verified disk-backed snapshot/index, streamed preflight, integrity checks, and read-only benchmark. Synthetic 2,000-row tests passed; a benchmark against an owner-supplied production dataset remains pending. |
| 3. Mathematical data pipeline | In progress | PR #197 adds independent checks for all 20 existing extended university templates (2,000 deterministic seed/difficulty cases). 138/197 university catalog topics still lack generators; full corpus generation/download remains deferred. |
| 4. Tokenizer and mathematical representation | Core contract audit merged; remaining export audit | PR #195 adds canonical token round trips, Unicode/whitespace, BOS/EOS, unknown-character offsets, strict duplicate-key rejection, and vocabulary persistence tests. Check model/export vocabulary compatibility before release. |
| 5. Model architecture and parameter verification | Implemented; final audit pending | NeuroSparse model/config, parameter formulas and tests exist; foundation target and CPU forward/backward smoke are covered. Remaining: component-by-component architecture review and reproducible shape/gradient/numerical stability report. |
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
