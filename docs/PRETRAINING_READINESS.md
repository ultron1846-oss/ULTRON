# ULTRON pre-training readiness plan

**Status:** phased readiness checklist; not a training authorization.
**Model size:** minimum **40,000,000 unique trainable parameters**. The earlier 3–5M target is retired.
**Budget:** $0 planned compute; free-tier capacity and limits must be verified at time of use.
**Workflow:** website-first, iPad-compatible; no actual training until the final gate is approved.

## Phase 1 — Project specification

- [ ] Define first-release mathematical capabilities and unsupported scope.
- [ ] Distinguish deterministic math operations, learned outputs, conjectures, and verified proofs.
- [ ] Preserve from-scratch constraints: no pretrained weights/models, external AI APIs, or externally generated training corpus.
- [ ] Document initial curriculum and evaluation tasks.
- [x] Establish 40M minimum and add a 63,400,451-parameter candidate configuration.
- [x] Add exact parameter-count formula and small-model cross-check.
- [x] Add theoretical FP32/optimizer memory estimate.
- [ ] Final architecture review and tokenizer-vocabulary compatibility audit.

**Exit criteria:** reviewed capability/curriculum specification, architecture, exact parameter count, resource estimate, and bounded scope.

## Phase 2 — Website completion and acceptance

Automated frontend hardening is merged, but manual iPad acceptance is **not recorded**.

- [ ] Verify navigation, fallback/error states, and honest untrained status.
- [ ] Test supported/unsupported Math Agent inputs and equation edge cases.
- [ ] Verify explicit memory save/retry, vault display, export/import, and local persistence.
- [ ] Verify owner sign-in, refresh, sign-out, and server-side non-owner rejection.
- [ ] Verify workload slider is a preference, not actual RAM allocation.
- [ ] Test Safari portrait/landscape, touch, keyboard, IndexedDB, and backup/restore.
- [ ] Record device/browser/date/pass-fail; do not mark untested as passed.

## Phase 3 — Security audit

The authenticated-role TRUNCATE privilege on six owner-linked tables was revoked and verified. See [Phase 3 audit](SECURITY_AUDIT_PHASE3.md).

- [x] Inspect public table RLS and role grants.
- [x] Review deployed Edge Function auth/owner checks and retired device-control endpoint.
- [x] Revoke and verify TRUNCATE on six owner-linked tables.
- [ ] Owner: enable Supabase Auth leaked-password protection and re-run advisors.
- [ ] Final deployed-policy/endpoint review after dashboard change.

## Phase 4 — Architecture and model sizing

- [x] Add proposed foundation config with 63,400,451 unique trainable parameters.
- [x] Add exact parameter-count formula and tests.
- [x] Document FP32/AdamW memory floor and limitations.
- [x] Bind foundation vocabulary to canonical tokenizer size (240) and reserved-token IDs.
- [ ] Freeze task serialization for problem, derivation, answer, and verifier result.
- [ ] Decide whether experimental memory/refinement remain based on ablations.

**Exit criteria:** architecture reviewed, count independently reproduced, vocabulary/task format frozen.

## Phase 5 — Data generation and dataset integrity

- [x] Audit generator scope: three narrow topics only; no calculus/university curriculum coverage claim.
- [x] Add deterministic prompt-group split and duplicate prompt collapse.
- [x] Split by normalized prompt hash so duplicate prompts cannot cross train/validation/test.
- [x] Strengthen row schema, content-derived example ID, and manifest/checksum validation.
- [ ] Add corpus-level balance/coverage reports and independent validators for broader topics.
- [ ] Expand topics only with independent exact validators.
- [ ] Ensure ULTRON-generated data only; no external generated corpus.

**Exit criteria:** reproducible manifest, split audit, zero invalid examples, documented coverage.

## Phase 6 — Training-loop implementation (not execution)

- [x] Add no-allocation preflight for parameter floor, tokenizer, splits, and workload bounds.
- [ ] Implement bounded orchestration only after architecture/data gates.
- [ ] Include gradient accumulation, clipping, finite loss/gradient checks, deterministic seeds, cancellation, and step/time/resource caps.
- [ ] Reset/isolate mutable memory across examples, batches, and validation.
- [ ] Keep remote dispatch disabled; require explicit owner authorization for any run.
- [x] Add preflight report that performs no optimizer steps and never authorizes training.

**Exit criteria:** unit tests and dry-run pass; no training performed.

## Phase 7 — Evaluation and benchmark protocol

- [x] Add exact-rational answer scoring for the three current generator topics, including coverage/abstention and per-topic metrics.
- [ ] Add broader independently verified mathematical task suites.
- [ ] Keep validation and final test sets separate from training data.
- [x] Report exact correctness, coverage, abstention, invalid output, and topic-level metrics for exact rational tasks.
- [ ] Add symbolic equivalence, proof-checker acceptance, and richer error classes.
- [ ] Benchmark baseline and foundation configs only on an approved runtime.
- [ ] Record actual latency, peak memory, profiler FLOPs where supported, and hardware/software metadata.
- [ ] Do not infer mathematical capability from random-token smoke tests.

## Phase 8 — Checkpoint and recovery

- [x] Save model, optimizer, scheduler state, global step, config, RNG state, and optional data cursor metadata.
- [ ] Include dataset manifest hash in the training cursor.
- [x] Validate model state before restore and roll back model/optimizer/scheduler/RNG on restore failure.
- [x] Test corrupted current checkpoint fallback to last verified backup.
- [x] Test RNG replay and data cursor restoration.
- [ ] Prove resumed execution matches uninterrupted execution within tolerance.
- [ ] Document storage and backup limits.

## Phase 9 — Free runtime and operations

- [ ] Verify current free-tier hardware, quotas, idle timeout, and persistence.
- [ ] Test notebook setup from a clean session without assuming phone verification.
- [ ] Validate checkpoint transfer and resume across sessions.
- [ ] Keep website status read-only and never expose secrets.
- [ ] Confirm zero-cost compute/storage/time limits before any run.

## Final training gate — blocked

Training is **not approved**. It requires Phases 1–9 review, outstanding iPad acceptance and Supabase Auth setting, clean validation, resource-budget confirmation, and separate explicit authorization. A 40M parameter count alone is not readiness.

## Next-chat handoff

1. Review PR 43 and CI.
2. Continue Phase 5 generator and split-integrity review in its own PR.
3. Then harden checkpoint/recovery and add a no-optimizer dry-run.
4. Update README at every meaningful milestone.
5. Do not enable training or remote training jobs without separate authorization.
