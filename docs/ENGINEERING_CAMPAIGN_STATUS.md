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
| 8. Inference engine | In progress | Model-only evaluation and checkpoint compatibility components exist. Remaining: verify a public inference interface end-to-end with a verified checkpoint; no trained checkpoint exists yet. |
| 9. Compression toolkit | Implemented; validation pending | Compression/quantization/low-rank pipeline and artifact metadata exist. Remaining: run permitted non-training round-trip/corruption tests and report size/error; quality claims require a trained checkpoint and evaluation. |
| 10. Website and training-control frontend | Automated website/runtime improvements in Prompt 5 branch; manual iPad acceptance pending | Account-free UI, 900px tablet navigation, safe areas/touch/reduced motion, strict provider manifest validation, requested GiB preference and status freshness/offline tests. Actual iPad Safari acceptance remains owner-only. |
| 11. Website/backend protocol and resource safeguards | Public status improved; runtime resource enforcement pending | Generic status freshness/stale/offline states and mocked tests added; no public job execution or pairing controls. GiB slider is still a local requested preference, not an enforced process-memory limit. |
| 12. Security, CI and release quality | Focused audit CI passed; owner hardening pending | PR #206 exact-head Node, Python AI Core, Level 1 and security/dependency workflows passed (runs 46105870615, 46105870624, 46105870635, 46105870639). npm audit, static frontend scan and pip-audit for runtime/test/seed dependencies passed; no known vulnerabilities were reported. Remaining: full transitive license inventory, full-SHA action pinning, owner Supabase leaked-password/table/function tasks and secret-scanning settings verification. |
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


## Prompt 5 implementation note — 2026-11-28

The website/runtime/security batch is in branch website-runtime-security-batch-6-2026-11-28, with exact-head CI green; independent PR review remains pending. It adds a shared status freshness/offline monitor with mocked tests, strict non-executable provider manifest validation, an iPad-width navigation breakpoint, clearer requested-resource semantics, removal of the remote font import, npm/pip dependency checks, Dependabot and a heuristic static source audit. The frontend remains account-free and does not dispatch jobs. Actual iPad Safari validation and Supabase cleanup/configuration remain owner-only. No Supabase mutation, training, optimizer step, AI API use, or remote job occurred.
