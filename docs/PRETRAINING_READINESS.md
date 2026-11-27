# ULTRON pre-training readiness plan

**Status:** phased readiness checklist; not a training authorization.
**Model size:** minimum **60,000,000 trainable parameters** (at least 60 million). The earlier 3–5M target is retired.
**Budget:** $0 planned compute; free-tier capacity and limits must be verified at time of use.
**Workflow:** website-first, iPad-compatible; no actual training until the final gate is approved.

## Phase 1 — Project specification

- [ ] Define first-release mathematical capabilities and unsupported scope.
- [ ] Distinguish deterministic math operations, learned outputs, conjectures, and verified proofs.
- [ ] Preserve from-scratch constraints: no pretrained weights/models, external AI APIs, or externally generated training corpus.
- [ ] Document initial curriculum and evaluation tasks.
- [x] Establish ≥60M minimum and add a 63,400,451-total / 61,826,048-trainable candidate configuration.
- [x] Add exact parameter-count formula and small-model cross-check.
- [x] Add theoretical FP32/optimizer memory estimate.
- [ ] Final architecture review and tokenizer-vocabulary compatibility audit.

**Exit criteria:** reviewed capability/curriculum specification, architecture, exact parameter count, resource estimate, and bounded scope.

## Phase 2 — Website completion and acceptance

Automated frontend hardening and the disabled Training Control readiness page are merged, but manual iPad acceptance is **not recorded**.

- [x] Add Training Control page with generic public status only; no job, checkpoint mutation, or pairing control is exposed.
- [x] Add automated regression coverage for navigation state, fallback/error contract, and honest untrained status (browser/device rendering remains a separate manual check).
- [x] Add math-engine tests for supported/unsupported Math Agent inputs, arithmetic edge cases, equation grammar, malformed input, unsafe symbols, and no-fabrication behavior.
- [x] Add automated Memory Vault coverage for save/retry, record display/list, export/import, duplicate handling, merge-by-ID and IndexedDB persistence simulation. Real Safari persistence remains part of manual acceptance.
- [x] Verify account-free frontend contract: no login/sign-up/owner route; private backend records are not exposed.
- [x] Verify the 2–10 GB workload slider persists as a browser-local preference and does not allocate physical RAM.
- [x] Add automated responsive checks for viewport metadata, mobile breakpoint, safe-area inset, and 44 px touch-target minimum.
- [ ] Complete manual iPad Safari acceptance using docs/IPAD_FRONTEND_ACCEPTANCE.md (owner device test required).
- [ ] Connect requested memory budget to an approved runtime configuration and enforce live RAM/VRAM limits; no runtime allocation exists yet.
- [x] Add automated responsive/keyboard/storage contract checks for narrow layout, narrow landscape, touch target, focus, navigation, IndexedDB and backup/restore.
- [ ] Test Safari portrait/landscape, touch, keyboard, IndexedDB, and backup/restore on an actual iPad.
- [ ] Record device/browser/date/pass-fail; do not mark untested as passed.

## Phase 3 — Security audit

The authenticated-role TRUNCATE privilege on six owner-linked tables was revoked and verified. See [Phase 3 audit](SECURITY_AUDIT_PHASE3.md).

- [x] Inspect public table RLS and role grants.
- [x] Review deployed Edge Function auth/owner checks and retired device-control endpoint.
- [x] Revoke and verify TRUNCATE on six owner-linked tables.
- [x] Re-run security advisor after live policy/endpoint review (2026-11-26); three retired-table INFO findings and the leaked-password WARN remain.
- [ ] Owner: enable Supabase Auth leaked-password protection and re-run advisors after the dashboard change.
- [x] Recheck deployed public table grants, owner policies, TRUNCATE privileges, SECURITY DEFINER function grants and deployed Edge Function contracts (2026-11-26).
- [ ] Final deployed-policy/endpoint review after the owner changes leaked-password protection.

## Phase 4 — Architecture and model sizing

- [x] Add proposed foundation config with 63,400,451 total and 61,826,048 trainable parameters.
- [x] Add separate exact total/trainable parameter formulas and tests.
- [x] Freeze detached memory key/value/gate projections and verify actual trainable count.
- [x] Document FP32 weights plus trainable gradient/AdamW memory estimate and limitations.
- [x] Bind foundation vocabulary to canonical tokenizer size (240) and reserved-token IDs.
- [x] Freeze and validate canonical task serialization schema v1 for problem, derivation, answer, and scoped verifier receipt in [PR #174](https://github.com/ultron1846-oss/ULTRON/pull/174). Code/test revision `e5f1f86a7852e2422a89828774728d27d66fc6a9` passed Node, Python AI Core, and Level 1 Math Tooling CI; see [TASK_SERIALIZATION.md](TASK_SERIALIZATION.md).
- [ ] Decide whether experimental memory/refinement remain based on ablations.

**Exit criteria:** architecture reviewed, count independently reproduced, vocabulary/task format frozen.

## Phase 5 — Data generation and dataset integrity

- [x] Audit generator scope: eight exact-synthetic topics (arithmetic, rationals, linear equations, polynomial derivative/integral, 2x2 determinant/system/inverse); no broad university curriculum claim.
- [x] Add deterministic prompt-group split and duplicate prompt collapse.
- [x] Split by normalized prompt hash so duplicate prompts cannot cross train/validation/test.
- [x] Strengthen row schema, content-derived example ID, and manifest/checksum validation.
- [x] Add deterministic corpus-level topic/difficulty balance, duplicate prompt/ID, validation, and split leakage/membership report.
- [ ] Add independent validators for broader topics.
- [x] Add bounded polynomial derivative generation with an independent exact polynomial parser/validator.
- [x] Add exact definite polynomial-integral generation and independent rational antiderivative evaluation.
- [x] Add exact 2x2 matrix inverse generation with an independent determinant-based rational validator (generator v0.5.0).
- [ ] Expand further topics only with independent exact validators.
- [ ] Ensure ULTRON-generated data only; no external generated corpus.

**Exit criteria:** reproducible manifest, split audit, zero invalid examples, documented coverage.

## Phase 6 — Training-loop implementation (not execution)

- [x] Add no-allocation preflight for trainable parameter floor, tokenizer, splits, and workload bounds.
- [x] Preflight memory estimate distinguishes all weights from gradients/optimizer state for trainable parameters.
- [x] Implement bounded orchestration with explicit authorization, complete preflight contract, accumulation, clipping, finite checks, cancellation, and step/time caps.
- [x] Include gradient accumulation, clipping, finite loss/gradient checks, cancellation, and step/time caps.
- [x] Add Python/Torch/CUDA RNG seeding and dedicated deterministic DataLoader generator.
- [x] Require preflight memory budget to cover persistent state and enforce batch/sequence/accumulation limits.
- [x] Preserve checkpoint-restored RNG on resume; require checkpoint/preflight dataset hash match.
- [x] Check expected dataset hash inside checkpoint loader before mutating model/optimizer/scheduler/RNG state.
- [x] Require the loader's dataset_hash_verified flag at trainer resume; fail closed if a checkpoint data cursor is loaded without an expected manifest hash.
- [ ] Restore sampler/data-loader cursor and verify exact reproducibility across a clean runtime restart.
- [ ] Add measured resource cap enforcement (current controller checks only the preflight budget; no live RAM/VRAM monitor).
- [x] Add model-level reset for mutable memory and reject multi-example training writes; trainer must reset between independent examples.
- [x] Reset mutable memory before and after each independent batch; memory writing defaults off.
- [ ] Implement and test validation-set isolation and real-model trainer execution.
- [ ] Keep remote dispatch disabled; require explicit owner authorization for any run.
- [x] Add preflight report that performs no optimizer steps and never authorizes training.

**Exit criteria:** unit tests and dry-run pass; no training performed.

## Phase 7 — Evaluation and benchmark protocol

- [x] Add exact answer scoring for rational arithmetic, polynomial derivatives/integrals, 2x2 determinants, and 2x2 linear systems, including coverage/abstention and per-topic metrics.
- [ ] Add broader independently verified mathematical task suites.
- [ ] Keep validation and final test sets separate from training data.
- [x] Report exact correctness, coverage, abstention, invalid output, and topic-level metrics for all eight generated topics.
- [x] Add model-only inference with command tools unavailable to the model and separate model-only/tool-assisted metric reports.
- [x] Add core concept/prerequisite taxonomy for all eight generator topics, concept-balanced sampling, and a validated held-out concept-transfer split protocol (see `docs/CONCEPT_TRANSFER_EVALUATION.md`).
- [x] Complete issue #135 engineering acceptance: model-only/tool-disabled evaluation, separate metrics, target leakage regression tests, concept-aware sampling, and full university prerequisite mapping. No training is authorized by this completion.
- [x] Add an initial curated prerequisite graph for Foundations and Linear Algebra (26/197 topics) with DAG validation and topological ordering.
- [x] Extend the graph to Calculus and Real analysis (31 additional topics; 57/197 total).
- [x] Extend the graph to Complex analysis, Abstract algebra, and Number theory (32 additional topics; 89/197 total).
- [x] Extend the graph to Topology, Discrete mathematics, Probability, and Statistics (44 additional topics; 133/197 total).
- [x] Extend the graph to Differential equations, Optimization, and Numerical mathematics (34 additional topics; 167/197 total).
- [x] Complete the prerequisite graph for all 197 university curriculum topics across 17 fields, with exact coverage and DAG validation.
- [ ] Extend prerequisite mapping to relevant grade-band curricula.
- [ ] Curate a frozen concept-transfer benchmark with semantic near-duplicate review and independent answer verification.
- [x] Separate attempted-answer coverage from valid-answer rate so invalid outputs are not counted as abstentions.
- [x] Count malformed non-string predictions as invalid outputs rather than aborting evaluation.
- [x] Benchmark parameter report separates total, trainable, fixed, and structural expert-active estimates.
- [x] Add exact semantic equivalence for the supported polynomial derivative grammar and rational/fraction equality for rational/integral answers; schema-v3 error classes.
- [ ] Add general symbolic equivalence, independent proof-checker acceptance, and richer error classes for broader task families.
- [ ] Benchmark baseline and foundation configs only on an approved runtime.
- [ ] Record actual latency, peak memory, profiler FLOPs where supported, and hardware/software metadata.
- [ ] Do not infer mathematical capability from random-token smoke tests.

## Phase 8 — Checkpoint and recovery

- [x] Save model, optimizer, scheduler state, global step, config, RNG state, and optional data cursor metadata.
- [x] Bind checkpoint data cursor to a validated dataset manifest SHA-256 (format v4).
- [x] Validate model state before restore and roll back model/optimizer/scheduler/RNG on restore failure.
- [x] Expose optimizer/scheduler state-presence and restoration flags; reject resume unless optimizer state and any checkpointed scheduler state were actually restored (merged PR #176; all final PR and post-merge checks passed).
- [x] Test corrupted current checkpoint fallback to last verified backup.
- [x] Test RNG replay and data cursor restoration.
- [x] Carry global step, epoch, next-batch cursor, seed, accumulation, and dataset hash through trainer checkpoint callbacks; require explicit next-batch cursor on resume.
- [x] Rewind cursor for uncommitted accumulation groups that are discarded.
- [x] Add dataset-bound deterministic resumable random sampler with seed/epoch/sample cursor and permutation-tail tests.
- [x] Integrate sampler restore/save into the bounded trainer; require the attached DataLoader sampler, `num_workers=0`, `drop_last=False`, matching preflight batch/train sizes, aligned sample/batch cursors, and rewind to the last committed optimizer step.
- [ ] Owner notebook: construct the sampler/DataLoader, persist callback `data_state`, and verify clean-runtime resume with `num_workers=0`.
- [ ] Prove resumed execution matches uninterrupted execution within tolerance (requires separately authorized tiny training test).
- [ ] Document storage and backup limits.

## Phase 9 — Free runtime and operations

- [x] Review official Colab, Lightning AI, Hugging Face Spaces, and ZeroGPU constraints with current sources.
- [x] Add website Training Control page for generic public status and readiness blockers; no owner-specific job history or execution action.
- [x] Document the single-runtime, checkpoint-resumable strategy and current no-phone constraint.
- [x] Record that free Hugging Face ZeroGPU quota is short/shared and not a dependable long training host.
- [ ] Owner: verify actual Colab access, hardware, quotas, idle timeout, and persistence from a clean iPad session.
- [ ] Owner: test notebook setup without phone verification or payment activation.
- [ ] Validate checkpoint transfer and resume across sessions.
- [ ] Keep website status read-only and never expose secrets.
- [ ] Confirm zero-cost compute/storage/time limits before any run.

## Final training gate — blocked

Training is **not approved**. It requires Phases 1–9 review, outstanding iPad acceptance and Supabase Auth setting, clean validation, resource-budget confirmation, and separate explicit authorization. A >60M parameter count alone is not readiness.

## Next engineering handoff

1. Owner notebook: construct the train-split DataLoader with ResumableRandomSampler, persist callback data_state, and pass the expected dataset SHA-256 when loading checkpoints.
2. Complete clean-runtime checkpoint/resume equivalence only after separate authorization for a tiny optimizer-step test; no real-weight training.
3. Add measured live RAM/VRAM resource cap enforcement and document checkpoint storage/backup limits.
4. Owner: complete iPad Safari acceptance, enable leaked-password protection in Supabase Auth, and validate the free-cloud runtime/session workflow.
5. Extend prerequisite mapping to relevant grade-band curricula; curate and independently verify a frozen transfer benchmark with near-duplicate review.
6. Continue broader independently validated university-math tasks, general symbolic equivalence, and proof-checker metrics.
7. Keep real-weight training and remote execution disabled until separate explicit authorization.
