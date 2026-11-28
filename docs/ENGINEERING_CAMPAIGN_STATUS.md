# ULTRON engineering campaign status

This file tracks the 14-stage campaign from `Pasted markdown(2).md`. Statuses distinguish merged implementation from validation or owner acceptance. This is not a training authorization.

## Stage status

| Stage | Status | Evidence / remaining gate |
|---|---|---|
| 0. Establish baseline | Complete | Repository, active PRs, CI, README, architecture, readiness and dependency paths inspected; current work is recorded in README. |
| 1. Finish current dataset improvements | Complete | PR #193 merged; exact-head checks and post-merge checks verified. |
| 2. Dataset infrastructure overhaul | Engineering stress suite merged; production measurement pending | PR #194–#196 provide verified disk-backed snapshot/index, streamed preflight, integrity checks, and read-only benchmark. PR #201 merged as `15bac227ca4335a3b8cd3f43c63601830b495956`; exact-head Node, Python AI Core, and Level 1 checks passed. Adds 3,500-row split/stream/random-access stress, 2,400-row benchmark smoke, integrity and cleanup tests. Post-merge Node, Python AI Core, Level 1, and Pages build/deploy checks passed (runs 46003403936, 46003403876, 46003404073, and 46003403018). Production dataset measurements remain owner-dependent; split-ID metadata still scales O(N) within the 100,000-row cap. |
| 3. Mathematical data pipeline | In progress | PR #197 independently checks all 20 existing extended university templates (2,000 deterministic seed/difficulty cases). PR #201 adds the Euclidean algorithm generator with independent gcd/Bézout/quotient checks. Main now has 60/197 university topics with generators and 137 catalogued topics still without generators. Full corpus generation/download remains deferred. |
| 4. Tokenizer and mathematical representation | Core contract audit merged; remaining export audit | PR #195 adds canonical token round trips, Unicode/whitespace, BOS/EOS, unknown-character offsets, strict duplicate-key rejection, and vocabulary persistence tests. Check model/export vocabulary compatibility before release. |
| 5. Model architecture and parameter verification | Implemented; final audit pending | NeuroSparse model/config, parameter formulas and tests exist; foundation target and CPU forward/backward smoke are covered. Remaining: component-by-component architecture review and reproducible shape/gradient/numerical stability report. |
| 6. Training engine and recovery | Implemented; owner acceptance pending | Bounded trainer, sampler cursor, checkpoint integrity/metadata, backup recovery and fresh-object synthetic restore tests exist. No ULTRON optimizer step. Owner must validate checkpoint transfer and clean-process resume on a separate runtime. |
| 7. Evaluation and mathematical tools | In progress | Exact arithmetic, symbolic/equation tools, benchmark and evaluation modules exist. Remaining: unify repeatable reports, coverage/error categories, independent benchmark review and frozen transfer benchmark provenance. |
| 8. Inference engine | Implemented in PR #205; validation pending | Public checkpoint-backed inference API with config/tokenizer checks, bounded greedy generation, cleanup, and compressed-artifact integration; exact-head CI and review remain. No trained-checkpoint capability result exists. |
| 9. Compression toolkit | Implementation and tests in PR #205; validation pending | Round-trip, corruption/truncation/version checks, strict reconstruction, logical tensor bytes, actual artifact size, and numerical smoke errors are covered on initialized weights; exact-head CI/review remain. Quality requires a trained checkpoint and verified evaluation. |
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


## Prompt 4 implementation note — 2026-11-28

PR #205 adds the checkpoint-backed inference entry point and connects compressed-artifact reconstruction to that inference API. The tests use only small initialized weights and temporary files. Compression reports logical state-dict tensor bytes and actual artifact file bytes separately; these are not process RSS, device memory, latency, or quality measurements. Exact-head CI and review remain required before merge. Trained-checkpoint capability and quality remain unmeasured.
