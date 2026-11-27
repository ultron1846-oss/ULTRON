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
- [x] Define strict versioned runtime-config schema and browser JSON export with non-authorizing flags; JavaScript and Python validation plus the preflight adapter are merged in PR #182.
- [ ] Connect exported configuration to an approved runtime and enforce live RAM/VRAM limits; no website-to-runtime connection or runtime allocation exists yet.
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
- [x] Merge bounded semantic JSONL verification in PR #192; preserve exact-answer, identity, duplicate, topic-count, and digest checks with bounded line reads.
- [x] Merge PR #193 disk-backed prompt-group indexing and filtered split-row loading; exact-head Node, Python AI Core, and Level 1 checks passed. Post-merge Node, Python, Level 1, Pages build, deploy, and report checks passed on main. This reduces split/preflight metadata memory.
- [x] Merge PR #194 lazy disk-backed verified dataset loader; exact-head Node, Python AI Core, and Level 1 checks passed. It uses a temporary verified snapshot and SQLite byte-offset index; records are decoded on demand and row hashes checked. Temporary disk usage can approach the existing 1 GiB dataset cap.
- [ ] Integrate indexed disk loaders into the owner preflight path; current batch streams token-length checks from the verified snapshot instead of materializing selected rows and MathExample objects, adds bounded indexed iteration, explicit preflight close(), and notebook cleanup. CI and review pending.
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
- [x] Add sampled process RSS + CUDA allocator-reserved budget enforcement at controller boundaries (merged PR #180; cannot interrupt an individual tensor operation; measurement sources and limitations documented in docs/RESOURCE_MONITORING.md).
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
- [x] Reject data-cursor and nested sampler manifest hashes that disagree with the checkpoint's top-level dataset hash before restoring runtime state (merged PR #178; final PR and all six post-merge checks passed on `main` at `6415d2322c1bae8879943399066ab4506be51d0b`).
- [x] Validate model state before restore and roll back model/optimizer/scheduler/RNG on restore failure.
- [x] Expose optimizer/scheduler state-presence and restoration flags; reject resume unless optimizer state and any checkpointed scheduler state were actually restored (merged PR #176; all final PR and post-merge checks passed).
- [x] Test corrupted current checkpoint fallback to last verified backup.
- [x] Test RNG replay and data cursor restoration.
- [x] Carry global step, epoch, next-batch cursor, seed, accumulation, and dataset hash through trainer checkpoint callbacks; require explicit next-batch cursor on resume.
- [x] Rewind cursor for uncommitted accumulation groups that are discarded.
- [x] Add dataset-bound deterministic resumable random sampler with seed/epoch/sample cursor and permutation-tail tests.
- [x] Integrate sampler restore/save into the bounded trainer; require the attached DataLoader sampler, `num_workers=0`, `drop_last=False`, matching preflight batch/train sizes, aligned sample/batch cursors, and rewind to the last committed optimizer step.
- [x] Construct read-only train/validation/test split DataLoaders in the owner notebook; train uses ResumableRandomSampler, `num_workers=0`, `drop_last=False`, and sequence truncation is disabled (PR #186).
- [x] Add non-authorizing verified-dataset readiness report with exact MathExample validation, canonical tokenization and runtime sequence-limit checks, parameter/memory formulas, and one-snapshot loader construction (PR #187).
- [x] Define and test a pure resumable data-cursor contract for dataset/sampler hashes, sizes, saved batch size, seeds, epochs, accumulation, and batch/sample alignment (PR #188 merged as `7adf369549206eec139bc3fdb1a390631113e662`).
- [x] Wire the verified loader/sampler cursor into the bounded trainer checkpoint callback and restore the sampler before iterator creation; metadata persistence and resume gates are covered by PRs #186, #190, and existing controller tests.
- [x] Add mock-only fresh-object model/optimizer/scheduler checkpoint restoration with sampler cursor rehydration; seed and assert synthetic optimizer momentum state plus scheduler state without an optimizer step (PR #191 updated; CI rerunning).
- [ ] Owner: verify a clean-process/remote-runtime resume with `num_workers=0` and a transferred checkpoint bundle.
- [ ] Prove numerical resumed-vs-uninterrupted training equivalence within tolerance only after separate authorization for a tiny mock/approved optimizer-step test; this remains distinct from sampler-sequence equivalence.
- [x] Document checkpoint storage, backup, and integrity limitations (current portability batch; CI pending).

## Phase 9 — Free runtime and operations

- [x] Review official Colab, Lightning AI, Hugging Face Spaces, and ZeroGPU constraints with current sources.
- [x] Add website Training Control page for generic public status and readiness blockers; no owner-specific job history or execution action.
- [x] Document the single-runtime, checkpoint-resumable strategy and current no-phone constraint.
- [x] Record that free Hugging Face ZeroGPU quota is short/shared and not a dependable long training host.
- [ ] Owner: verify actual Colab access, hardware, quotas, idle timeout, and persistence from a clean iPad session.
- [ ] Owner: test notebook setup without phone verification or payment activation.
- [x] Add automated checkpoint bundle copy/restore integrity coverage (PR #191 updated; CI rerunning).
- [ ] Owner: validate actual checkpoint transfer and resume across separate free-cloud sessions.
- [ ] Keep website status read-only and never expose secrets.
- [ ] Confirm zero-cost compute/storage/time limits before any run.

## Final training gate — blocked

Training is **not approved**. It requires Phases 1–9 review, outstanding iPad acceptance and Supabase Auth setting, clean validation, resource-budget confirmation, and separate explicit authorization. A >60M parameter count alone is not readiness.

## Next engineering handoff

1. PR #191 merged as `ac10b09cb281547e47a2ec82ecd84ae9543a011a` after exact-head Node, Python AI Core, and Level 1 checks passed. Fresh-object restore covers model weights, synthetic optimizer momentum, scheduler state, and sampler cursor without an optimizer step.
2. Current code batch: bounded semantic JSONL ingestion and split-row loading (PR #192). Exact answer verification, content-derived IDs, duplicate ID/index checks, topic counts, and SHA-256 remain authoritative; raw full-file byte/string copies are removed and each input line is bounded. Synthetic regression tests cover limits, malformed/duplicate content, mutation between passes, and split compatibility; exact-head CI is pending.
3. The split builder still retains parsed row objects and split-ID metadata in memory (hard cap 100,000 rows). This reduces duplicate memory copies but is not constant-memory DataLoader streaming; a future index/streaming row-selection design must preserve split integrity.
4. Owner: test clean-process checkpoint transfer/restore in a separate free-cloud session with `num_workers=0`, and record device/quota/persistence limitations. This is owner acceptance, not a training run.
5. Owner: complete iPad Safari acceptance, enable leaked-password protection in Supabase Auth, and validate the free-cloud runtime/session workflow.
6. Extend prerequisite mapping to relevant grade-band curricula; curate and independently verify a frozen transfer benchmark with near-duplicate review; continue broader math/proof-checker metrics.
7. Keep real-weight training, optimizer steps on ULTRON weights, and remote execution disabled until separate explicit authorization.

## Owner notebook setup scaffold — 2026-11-27

The preflight notebook checks repository presence, validates the browser-exported schema-v1 runtime config, and calculates foundation parameter counts without allocating model weights. It is not full dataset preflight or a training notebook. Dataset loading/split verification, sampler/DataLoader construction, checkpoint callback persistence, and clean-runtime resume remain open.

## Manifest-bound split preflight — PR #185 (2026-11-27)

The owner notebook verifies an existing JSONL dataset and sidecar, creates only deterministic split-ID metadata, and validates the result against exact dataset digest and prompt-group hash assignment. It does not generate rows, download data, instantiate model/optimizer/DataLoader, restore checkpoints, or train. Sampler/DataLoader integration and cursor persistence remain open.


## Verified split DataLoader scaffold — PR #186 (2026-11-27)

Added a read-only tokenized dataset view and DataLoader builder for verified existing corpus splits. Train uses ResumableRandomSampler bound to the full dataset SHA-256; validation/test are sequential. Notebook only constructs loaders and reports initial cursor state, without iterating or training. Checkpoint callback wiring and actual trainer execution remain open.



## Verified dataset readiness report — PR #187 (2026-11-27)

The preflight package validates the existing dataset and split manifest, adapts selected rows into the semantic MathExample contract, checks exact topic answers, verifies canonical tokenization and sequence limits, estimates model persistent-state memory from formula-based parameter counts, and constructs all three loaders from one verified split snapshot. The report is non-authorizing and marks data/activation/workspace/allocator memory as incomplete. It does not instantiate a model or optimizer, consume batches, restore checkpoints, or train.

The split seed and resumable sampler seed are independent; the sampler seed is stored in the initial data cursor and must match TrainingSettings.seed later. Combined loader construction avoids independently rebuilding the verified dataset three times. It still relies on the existing in-memory JSONL parser and does not establish streaming-scale dataset access.

## Checkpoint metadata compatibility batch — PR #189 merged (2026-11-27)

PR #189 merged as `582533c7267babf3035f1d4126e96fde4429592e`; exact-head Node, Python AI Core, and Level 1 checks passed (runs `45973714005`, `45973713970`, and `45973713967`). It validates new-format resumable cursor metadata at checkpoint boundaries, adds a checkpoint-digest-bound JSON sidecar, and provides a metadata-only compatibility inspector. The inspector hashes checkpoint bytes and reads the sidecar; it does not call `torch.load`, deserialize checkpoint tensors, or load weights. This remains a non-authorizing report. Actual checkpoint restore and valid training are still gated.


## Resume cursor and checkpoint gate regression batch — PR #190 merged as `ab8e08ff9e482fca52cdc801e376212d42a8eb80`

The verified preflight already constructs train/validation/test DataLoaders from one verified split snapshot; train uses `ResumableRandomSampler`, while evaluation loaders are sequential. The existing bounded controller requires that sampler to be the DataLoader's sampler, uses `num_workers=0`, validates the cursor before batch iteration, and supplies committed cursor metadata to the caller-provided checkpoint callback after a completed step. The new regression file tests sampler sequence equivalence across an interrupted/resumed cursor, rejects dataset/seed mismatch, and verifies a wrong expected dataset SHA-256 is rejected before model/optimizer/scheduler state restoration. Tests are synthetic and do not run ULTRON training or optimizer steps.


## Checkpoint portability, interrupted-save recovery, and streaming scan — PR #191 open; latest-head CI pending

The current four-phase batch adds (1) a fresh-object checkpoint restore regression that rehydrates model, optimizer, scheduler, and sampler cursor without an optimizer step; (2) integrity inspection and restore after copying the checkpoint, SHA-256 manifest, and metadata sidecar to a different directory; (3) fault injection at the checkpoint-manifest commit boundary to verify recovery from the previous integrity-checked backup; and (4) a bounded JSONL structural scanner that hashes and parses one line at a time under explicit byte/row/line limits. The scanner reports only structural checks and intentionally does not verify exact math answers, content-derived IDs, duplicate IDs, or prompt-split leakage. Full dataset semantic verification remains authoritative. No corpus is generated/downloaded, no ULTRON weights are trained, and no remote job is dispatched.


### Checkpoint storage and backup limits

A checkpoint generation currently consists of three files: the serialized checkpoint (`.pt`), its SHA-256 integrity manifest (`.pt.sha256`), and the metadata-only compatibility sidecar (`.pt.metadata.json`). The save path retains at most one previous verified generation using matching `.bak` files for these components; it is not an unlimited backup history. The checkpoint and its temporary replacement are written in the same directory, then replaced individually. The checkpoint, checksum manifest, and metadata sidecar are **not one atomic multi-file transaction**. If a save is interrupted after the checkpoint replacement but before the matching checksum manifest is replaced, the current pair will fail integrity verification and load will fall back to the previous verified backup when one exists. A first-ever save has no previous generation to fall back to. If neither current nor backup checkpoint/checksum pair verifies, restore fails closed.

For transfer between sessions, copy the current checkpoint, `.sha256`, and `.metadata.json` together and preserve their basename; include the corresponding `.bak` files only when backup recovery is also required. The metadata sidecar is advisory and is not a substitute for the payload integrity check performed by `load_checkpoint`. Storage capacity must accommodate at least the current checkpoint plus one prior checkpoint generation and temporary-write/transfer overhead. Actual free-tier disk quotas, upload limits, and cross-session persistence are owner/runtime-specific and remain unverified.

- [ ] Merge PR #197's ten university analysis generators after exact-head generator, registry-sync, coverage-audit, Python, Level 1, and Node checks pass. Coverage changes from 59/197 to 69/197 generator-available; this does not mean mastery. No corpus generation is included.
