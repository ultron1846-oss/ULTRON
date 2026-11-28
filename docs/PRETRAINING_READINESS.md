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
- [x] Merge PR #195 indexed disk preflight and curriculum audit; exact-head Node (`45994243531`), Python AI Core (`45994243605`), and Level 1 (`45994243669`) checks passed. Preflight streams token checks from the same verified snapshot as its loaders, closes temporary storage explicitly, and does not materialize selected rows/MathExample objects. Registry/curriculum audit and tokenizer contract tests are included.
- [x] Add deterministic corpus-level topic/difficulty balance, duplicate prompt/ID, validation, and split leakage/membership report.
- [x] Add independent mathematical invariant checks for all 20 existing extended university generator templates in PR #197 (2,000 deterministic seed/difficulty cases); broader catalog generation remains incomplete.
- [x] Add bounded polynomial derivative generation with an independent exact polynomial parser/validator.
- [x] Add exact definite polynomial-integral generation and independent rational antiderivative evaluation.
- [x] Add exact 2x2 matrix inverse generation with an independent determinant-based rational validator (generator v0.5.0).
- [ ] Expand further topics only with independent exact validators.
- [x] Merge PR #201: deterministic Euclidean algorithm generator for the existing catalog topic; independent 500-seed gcd/Bézout/quotient-trace tests and registry synchronization passed exact-head CI. Coverage is now 60/197 university topics; 137 remain without generators. Generator availability is not mastery.
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

- [x] Merge PR #196 read-only indexed dataset benchmark as `faa4b8ea31415598355afa36414092482b1a8e00`; exact-head CI and post-merge Node, Python AI Core, Level 1, and Pages build/deploy passed. The synthetic fixture is not a production memory benchmark; owner-supplied production dataset measurements remain pending.


## Prompt 6 — integrated full-system readiness (2026-11-28)

The combined validation candidate is [PR #207](https://github.com/ultron1846-oss/ULTRON/pull/207), based on main commit `2ba3340dbc841699ad98e651c86f2e227be8cac0`. Implementation/test revision `bfb48af944c9dfba8e387d9c39f9a1b39a31145f` passed Node Tests (127), Python AI Core (722), Level 1 Math Tooling (5 tests plus 5,000 randomized cases), and the security/dependency audit (npm audit 0 vulnerabilities; pip-audit no known vulnerabilities in declared dependency groups). Exact run IDs and the detailed classification matrix are in [FULL_SYSTEM_READINESS_2026-11-28.md](FULL_SYSTEM_READINESS_2026-11-28.md).

**Readiness status:** automated fixture/software integration is verified; foundation-scale execution, production dataset/curriculum coverage, trained-model evaluation, actual iPad Safari, live runtime/resource enforcement, free-tier quota/persistence and owner security/license settings are not accepted. The configured foundation is 63,400,451 total / 61,826,048 trainable parameters, but no full-size model instantiation, training or hardware memory profile has been run. 60/197 university topics have generators; 137 remain without generators.

**Training gate remains blocked.** No optimizer step on ULTRON weights, production data generation/download, calibration-data generation, Supabase mutation, deployment, external AI API call or remote job was performed. Controller step-count tests use a meta-device mock model and a mock optimizer that only increments a counter; CI smoke is forward/backward only.

**Historical next-task note:** the Green's theorem task described at this point was subsequently implemented in Phase 2 PR #209. See the dated Phase 2 addenda below for current scope and validation.


## Phase 2 — curriculum and Green's theorem expansion (2026-11-28)

The former 197-topic university curriculum has been revised to 199 topics by splitting the combined Green/Stokes/divergence umbrella into three separate theorem entries. The exact-rational Green generator is bounded to sparse polynomial vector fields of total degree at most 5 on non-degenerate axis-aligned rational rectangles. It independently checks the oriented rectangle-boundary integral against the double integral of dQ/dx − dP/dy. Clockwise traversal reverses both signs. **Stokes' theorem and the divergence theorem remain catalogued but unimplemented.**

The new coverage model distinguishes catalogue presence, generator availability, independent exercise validation, measured trained-model benchmarking and mastery. The current stacked candidate counts are 255 catalogue entries overall, 115 with generators, 64 independently validated exercise topics, zero trained-model benchmarks and zero mastered topics. University coverage is 62/202 generator-available and 140/202 not implemented. These are registry evidence states, not trained-model capability. The historical 60/197 statement above is the pre-Phase-2 baseline, not the current curriculum state. See docs/MATH_CURRICULUM_AUDIT_2026-11-28.md and tools/math_generators/validation_manifest.json for scope and evidence.

This is still an engineering/catalogue statement, not a model-capability claim. No ULTRON training, optimizer step, production corpus generation/download, external AI API, remote job, or deployment was performed.


## Phase 2 follow-up — bounded first-order ODE scope (2026-11-28)

The 199-topic post-Green university curriculum is now expanded to 202 by splitting the broad first_order_ODEs row into four scoped families. homogeneous_constant_coefficient_first_order_ODEs is available for y'=k y with y(0)=y0. separable_first_order_ODEs is available only for the bounded rational power-law family y'=c*x^m*y^n, with an independent exact derivative/initial-value validator. linear_first_order_variable_coefficient_ODEs and exact_first_order_ODEs remain catalogued but unimplemented. The validator checks the exact solution y(t)=y0 exp(k t), the differential identity, the initial condition, and the complete generated problem object.

Current combined coverage candidate: 255 catalogue entries, 115 generator-available, 64 independently validated exercise topics, zero trained-checkpoint benchmarks and zero mastered topics. University coverage: 62/202 generator-available, 140/202 not implemented. The university prerequisite map contains 202 topics and 378 edges.

This is a scope and exercise-verification improvement, not trained-model capability evidence. No ULTRON weights were trained or updated; no production corpus or remote job was created.


The separable ODE family is restricted to c≠0, rational initial data with y0>0, integer m=0..3 and n=0..2 under difficulty-specific bounds; n=2 is valid only where the reciprocal solution denominator is nonzero. This is not general separable-equation support. No ULTRON training or optimizer step was performed.


## Latest mathematics curriculum scope handoff — 2026-11-28

**Candidate branch:** `phase2/curriculum-scope-expansion-batch-8-2026-11-28` (proposed PR #213, based on PR #212 head `dc0ee7763b2a7c6e7f01e9e310a25da8975fb573`).

This batch tightens implementation claims before further expansion. General catalogue rows remain unimplemented where existing templates cover only specific subfamilies. It scopes the quadratic Taylor template, affine-polynomial rectangular double integrals, diagonal linear rectangular substitutions, constant-vector-field segment integrals, flat rectangular surface integrals, and divergence of diagonal linear vector fields. It splits the former complex-number/topology and complex Taylor/Laurent compound labels. Newly added independent families cover exact rational complex arithmetic and homogeneous variable-coefficient linear first-order ODEs restricted to `y' + a*x^m*y = 0`, `m ∈ {1,2}`.

Current candidate counts: **211 university topics**, **64 generator-available**, **147 catalogued but not implemented**; **264 combined entries**, **117 generator-available**, **66 independently validated**; **397 prerequisite edges**; **0 compatible trained-checkpoint benchmarks** and **0 mastered topics**. Exact-head CI passed on PR #213 head `3ad04c01bfe48bd0debf46017e9351d017c6ae4a`: Node run 46140324038, Python AI Core run 46140323910, Level 1 Math Tooling run 46140323952 (5,000 randomized cases), and Security/dependency run 46140323947. The Python workflow performed only a CPU forward/backward smoke, with no optimizer step.

No model training, optimizer step, production corpus generation/download, external AI API, remote training job, Pages deployment, Supabase mutation, or model-weight publication was performed. Continue with the remaining dependency-aware topic batches and a per-topic difficulty audit; do not infer broad capability from narrow templates.


Batch 8 exact-head CI is recorded in README.md and docs/MATH_CURRICULUM_AUDIT_2026-11-28.md. The PR remains a stacked review candidate; it has not been merged.


## Phase 2 — bounded vector-calculus theorem follow-up

**Candidate branch:** `phase2/vector-calculus-theorem-families-2026-11-28`, based on PR #213 head `efcadcacd459f7a2049d2247ac1dfbf91dcf187f`.

The batch adds `stokes_theorem_horizontal_rectangles` for affine ((P,Q,0)) fields on horizontal rectangles, and `divergence_theorem_axis_aligned_boxes` for diagonal linear fields on rectangular boxes. Both validators independently reconstruct the boundary/face integral and compare it with the curl/divergence integral. Broad Stokes and divergence theorem support remains unimplemented.

Candidate coverage: **213 university topics**, **66 generator-available**, **147 not implemented**, **213 prerequisite nodes and 401 edges**; **266 combined entries**, **119 generator-available**, **68 independently validated**. Benchmarks and mastery remain zero. Exact-head CI is pending.


## Phase 2 — bounded exact first-order ODE follow-up

**Candidate branch:** `phase2/quadratic-potential-exact-ode-2026-11-28`, based on the bounded vector-calculus theorem candidate.

Adds `quadratic_potential_exact_first_order_ODEs` for exact one-forms generated by a quadratic potential and rational initial point. The implicit solution is the corresponding potential level set. The broad `exact_first_order_ODEs` topic remains unimplemented. Independent Fraction tests validate the potential gradient, matching mixed partials, and initial-point level set. Exact-head CI is pending.


## Phase 2 — second-order ODE and transport PDE follow-up

**Candidate branch:** `phase2/second-order-ode-pde-transport-2026-11-28`.

Adds the bounded `distinct_real_root_second_order_linear_homogeneous_ODEs` and `constant_speed_transport_polynomial_initial_data_PDEs` families. The broad second-order ODE and characteristics-PDE catalogue entries remain incomplete. Tests independently validate characteristic-root equations, initial conditions, transport PDE residuals, and initial profiles. Exact-head CI is pending.


## Phase 2 — finite probability/statistics follow-up

**Candidate branch:** `phase2/finite-distribution-probability-statistics-2026-11-28`.

Adds exact moment calculations for three-point finite distributions and exact point-probability/moment calculations for binomial distributions. Both are separate scoped curriculum IDs with 500-seed independent validation; the binomial tests check normalization across the full PMF support. Broad discrete-distribution and general expectation/variance topics remain incomplete. Exact-head CI is pending.
