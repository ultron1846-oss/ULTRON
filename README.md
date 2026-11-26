# ULTRON — Mathematics Intelligence Workspace

**Status snapshot: 2026-11-26**

ULTRON is an independent mathematics-learning and reasoning project under development. The website and deterministic math tooling are not a trained general-purpose AI model. No capability claims should be inferred from generator coverage, exact-checking utilities, or tool-assisted answers.

## Current status

- The repository contains a Python mathematics core, bounded symbolic/exact arithmetic components, an account-free browser workspace, curriculum generators, and agent/tool interfaces.
- Training remains disabled and has not been authorized in this work. No optimizer steps, training runs, or cloud/remote execution are part of this task.
- PRs #136–#143 are merged; issue #135 is closed after its tool-independence and concept-first acceptance requirements were implemented and tested. Seed importer/source registration is tooling only: no corpus upload or import is claimed.
- Generator packages include Grades 1–4, 5–8, 8–12, university topics, and the core generator. A shared canonical Problem adapter and verifier interface now bridge them; the combined registry includes core topics and is checked against generator declarations. Source generator implementations remain unchanged.
- The repository includes exact algebra components and identity checkers. These are bounded exact checks, not a formal proof kernel. Lean integration is design-only and not yet connected to a real Lean checker.
- PR C (#139) added fixed-seed SymPy differential tests: 1,000 cases per engine area passed CI. This is a software cross-check, not a model-capability result.

## Implemented / tested / not done

### Implemented in the repository
- Static browser-based mathematics workspace and frontend integration code.
- Python core model and training/preflight/checkpoint infrastructure.
- Deterministic core examples and separate curriculum generator packages.
- Bounded mathematical parser/IR, exact rational and polynomial operations, and conservative symbolic utilities.
- Exact polynomial/rational identity checks with certificate serialization.
- Math Agent tools and topic/guided-learning interfaces.

### Tests and verification
- CI contains Node and Python test suites and multiple validation/smoke workflows. Check the latest PR or Actions run for the actual status of each commit.
- This README does not imply that every test suite was run during the current session.
- Fixed-seed SymPy differential tests are merged and run in CI; they are a software cross-check, not a model-capability result.

### Not implemented or not accepted
- No trained ULTRON weights or demonstrated grade/university-level competence.
- No approved training run, optimizer steps, corpus generation, or cloud execution.
- The public static website requires no login or sign-up. The owner sign-in route and browser auth module were removed in merged PR #155; private Supabase records remain protected server-side and are not exposed by the frontend.
- Lean remains design-only: an abstract checker interface and integration plan exist, but no Lean toolchain, proof receipt, or theorem-proving capability is claimed.
- Generator implementations still use source-specific record formats internally; the common Problem adapter normalizes them at the boundary.
- No claim that lexical tokenizer coverage means semantic/parser/model support.
- No distributed multi-host trainer or guaranteed free GPU capacity.

## Architecture

- `ultron_core/`: model, tokenizer, parser/IR, exact math engine, verification, memory, agent tools, training and checkpoint components.
- `tools/math_generators/`: grade-band and university curriculum generators, topic metadata and registries.
- `tests/`: Python and Node regression, contract, and integration tests.
- `docs/`: architecture, mathematical engine, training/preflight, evaluation, security, runtime constraints, and staged Lean design documents.
- `index.html` and associated frontend assets: browser workspace.

The shared Problem contract and generated combined registry were added in merged PR #138. Source records are adapted without rewriting generator logic.

## Safety and trust boundaries

- No external AI API or pretrained weights are used for the from-scratch model plan.
- A generated problem or tool result is not evidence of model capability.
- Exact algebra checkers emit `EXACT_CHECKED`; this status does not, by itself, admit a candidate to trusted knowledge. Trust remains fail-closed.
- Bounded exact algebra checkers are not formal proof systems. `FORMALLY_VERIFIED` is reserved for a future genuine proof-kernel receipt.
- Training, optimizer updates, corpus generation, cloud execution, and remote execution are disabled for the current task.
- Do not expose secrets or change Supabase/Pages configuration without separate authorization. The frontend must not require account authentication.

## Current handoff

- PRs #136–#163 are merged; issue #135 is closed as completed. PR #163 merged at `cca21b1c5d701684a125abbfb4193ef6a04cd121`; its required Node, Python AI Core, and Level 1 Math Tooling checks passed on head `5b3b0eccc669d9ab124b4c9ea49ea8cbb8004247`.
- PR #155 removed the owner sign-in route and browser auth module; PR #156 removed disabled job/checkpoint buttons, the checkpoint-count tile, and retired pairing controls from the public UI.
- The static website requires no login or sign-up. The Memory Vault remains browser-local; no account-specific training history, pairing, job controls, or checkpoint mutation controls are exposed.
- The seed importer and arithmetic source registration provide tooling only; no dataset has been downloaded or uploaded. The manual importer remains gated by `confirm_download=true` and `ULTRON_SEED_IMPORT_ENABLED=true`.
- No dataset import artifact, optimizer step, model training, or remote execution is claimed. Do not enable the import gate or dispatch training workflows without separate explicit authorization.
- PR #157 added automated responsive checks and docs/IPAD_FRONTEND_ACCEPTANCE.md; PR #158 refreshed the README handoff. Manual iPad Safari acceptance is still pending; CI cannot verify the deployed site on an actual iPad.
- The 2–10 GB slider is a browser-local preference only. It does not allocate physical RAM or control a hosted runtime; connecting it to an approved runtime configuration and live memory cap remains unfinished.
- Latest Pages build/deploy run #45793501681 succeeded for PR #163 merge commit `cca21b1c5d701684a125abbfb4193ef6a04cd121`. The deployment job is verified; actual Safari rendering and iPad interaction remain unverified.
- Owner to-do (manual, not attempted): open https://ultron1846-oss.github.io/ULTRON/ in iPad Safari and complete docs/IPAD_FRONTEND_ACCEPTANCE.md. Later runtime readiness must verify free-runtime availability and safe checkpoint portability through a separate approved runtime design; the current account-free website has no checkpoint transfer controls. Supabase Auth leaked-password protection is a separate backend dashboard security setting and is not required for the public frontend.

## Brief dated history

- **2026-11-26:** PR #160 merged; configuration enforces a ≥60M trainable-parameter foundation minimum and validates expandable capacity. Python AI core, Node, and Level 1 tests passed for the PR head. No foundation weight allocation, resource profiling, or training was performed.

- **2026-11-24:** Browser workspace hardening; Python math-core and exact arithmetic foundations; parser/IR, polynomial/rational operations, real-root and algebraic-number utilities; checkpoint, memory, and trust-boundary reviews.
- **2026-11-25:** Math Agent tools and tutor-first direction; Grades 1–4, 5–8, 8–12 and university generator expansion; university topic registry work; model/training preflight and free-runtime review; exact identity verifier documentation.
- **2026-11-26:** Requested separate PRs for README consolidation, generator unification, SymPy differential testing, exact-verification status naming, and Lean readiness design.

See [docs/HISTORY.md](docs/HISTORY.md) for the preserved milestone detail and [docs/](docs/) for topic-specific specifications.

## Guided learning and command independence — 2026-11-26

The Math Agent's ordinary input path gives hints and requests an intermediate attempt instead of automatically revealing arithmetic, word-problem, or equation answers. Slash commands are explicit tools, but equation-solving commands are also tutor-first: they provide a first-step hint or check a learner-submitted attempt without displaying the correct final value. `/calc` requires the learner's proposed result and reports only whether it matches. Graphing and table/numerical tools remain scoped to the requested visualization or operation. See `tests/guided-learning.test.js` and `tests/math-tools.test.js` for regressions. This is deterministic tutoring/tool behavior, not trained-model capability.


## Cognitive behavior profile hardening — 2026-11-26

The cognitive behavior profile now rejects non-finite numeric weights (`NaN`, positive infinity, and negative infinity) and exposes factuality, conversational naturalness, creativity, and empathy/context weights in the selected runtime policy. Regression tests cover every numeric weight and customized policy values. This remains a configuration contract—not evidence of trained capability. No training or data import was performed.

## Model/tool independence — 2026-11-26

ULTRON's deterministic slash commands are external support and verification tools; their outputs are not evidence that the neural model has learned a skill and must not be treated as the model's supervised reasoning target. The model-only evaluator passes token IDs directly to the model with no command tools or tool-result context. Model-only and tool-assisted scores are reported separately. The Level 1 training source serializes only allowlisted ULTRON-generated prompt, worked steps, and answer fields; the exact verifier is validation-only.

Issue #135's engineering acceptance requirements are implemented and tested. No external dataset was downloaded/imported, no corpus was generated as part of this work, and no optimizer step or training was run.

## Level 1 exact math tooling — CI scope (2026-11-26)

The Level 1 arithmetic and linear-equation package is an exact, deterministic tooling prototype with SymPy differential tests and a separately defined 500-item held-out evaluation benchmark. CI runs the package regression suite only; it no longer generates or writes the held-out benchmark. The benchmark scripts remain opt-in for a separately authorized local evaluation and must never be used as training data. The training-source adapter is a guarded interface, not a training run. No optimizer step, corpus generation, model training, or remote training execution was performed.

## Seed importer CI safety regression — 2026-11-26

The importer test suite now verifies that the workflow has no push trigger and is skipped unless both the dispatch confirmation and owner-controlled repository variable are enabled. This test uses the checked-in workflow text only; it does not dispatch or download data.

## Seed-data import authorization boundary — 2026-11-26

The Hugging Face seed importer is available as tooling only. Its workflow has no push trigger and runs only when the manual confirm_download input is true and the owner-controlled repository variable ULTRON_SEED_IMPORT_ENABLED is set to true. That variable remains unset. Offline mocked tests validate the importer; no dataset download, corpus import, optimizer step, or training run was performed. Do not enable the variable or dispatch the workflow until separate explicit authorization is given.


## Basic arithmetic seed source preparation — 2026-11-26

Added the MIT-licensed `ChrisMcCormick/basic-arithmetic` Hugging Face training split (10,000 source rows) to the seed importer registry. The importer independently validates arithmetic against integer operands, accepts only exact integer division, limits operand magnitude to 10,000, rejects mismatched answers/unsupported operations, and marks these records as answer-only rather than worked reasoning. Validation and test splits are not configured for import.

This is source/importer support only. No dataset rows have been downloaded or uploaded, no workflow was dispatched, and no training or optimizer step occurred. The manual importer remains gated by `confirm_download=true` and `ULTRON_SEED_IMPORT_ENABLED=true`. Review the PR and run the gated workflow separately to produce the seed-data artifact.


## Model-only evaluation slice — 2026-11-26

PR #145 adds `ultron_core/model_only_evaluation.py`: a bounded greedy inference runner that calls the model with token IDs only, without passing command tools or tool results to the model. It also reports model-only and optional tool-assisted prediction metrics separately. The tool-assisted map is caller-supplied and is not generated by this evaluator.

CI uses a tiny mock model for regression tests. This is evaluation infrastructure only; the foundation model remains untrained, no real-weight inference or training was run, and the issue's target-leakage, concept-curation, and transfer-evaluation acceptance criteria remain unfinished.


## Training target provenance boundary — 2026-11-26

PR #146 adds an allowlisted serializer for the existing ULTRON-generated Level 1 training source. The supervised sequence is assembled only from the generator's prompt, worked steps, and answer. Unknown record fields (including `tool_output` or `tool_answer`) are excluded. The verifier must return the literal boolean `True`; its result is validation-only and is not serialized as a target.

The dataset exposes and hashes a target contract identifying the generator, worked-solution target type, and verifier role. Regression tests inject a sentinel tool-output field and verify it does not appear in tokenized targets. This is a source-specific safeguard, not a general external-corpus curation pipeline. No training, corpus generation, or dataset import was performed.


## Core concept taxonomy and transfer protocol — 2026-11-26

PR #147 adds `ultron_core/concepts.py`: 10 concept nodes (including prerequisite-only concepts), mapping all eight core exact-synthetic generator topics. The registry validates prerequisite references and acyclicity. Concept-balanced sampling selects only existing examples and creates no new data.

The transfer split validator checks example-ID and normalized-prompt isolation, numeric novelty for the unseen-value category, multi-concept annotations, prerequisite-sensitive labels, and unseen-concept claims. The protocol is documented in `docs/CONCEPT_TRANSFER_EVALUATION.md`.

This is core-topic readiness infrastructure, not evidence of concept mastery. The 197-topic university curriculum still lacks prerequisite mapping, semantic near-duplicate review is required, and no benchmark, training corpus, or model training was run.


## University prerequisite map — 2026-11-26

PRs #148–#153 completed and validated the prerequisite graph for all 197 topics across 17 fields. The loader verifies exact coverage, rejects dangling edges/cycles, and provides topological ordering.

These curated edges are learning dependencies, not proof of mastery or a universal course order. Grade-band prerequisite mapping and a frozen concept-transfer benchmark remain future readiness work. See docs/UNIVERSITY_PREREQUISITES.md.


## Account-free website contract — 2026-11-26

The public website has no login or sign-up requirement and no owner sign-in page. Private Supabase records remain protected on the backend and are not accessed by the static frontend. The local Memory Vault uses IndexedDB and does not sync to an account. The website exposes only generic read-only status: no job start/pause/stop/resume controls, checkpoint mutation controls, pairing controls, or account-specific training history.

## iPad frontend acceptance — 2026-11-26

Automated static checks cover viewport metadata, responsive breakpoints, safe-area handling, a 44 px touch-target minimum, and local persistence of the 2–10 GB preferred-memory slider. Manual Safari acceptance on an actual iPad remains pending. The slider is a browser-local preference only; it does not allocate physical RAM or change hosted-runner limits. See docs/IPAD_FRONTEND_ACCEPTANCE.md.


## GitHub Pages deployment verification — 2026-11-26

The GitHub Pages build-and-deployment run #146 completed successfully for main commit `394ecd1da246c642de2ac3cc3515265358d5da4e`. The build, status-report, and deploy jobs all reported success. This verifies the GitHub Actions deployment workflow, not manual browser acceptance or the live site's interactive behavior. Manual iPad Safari acceptance remains pending.

## Phase execution handoff — 2026-11-26

This phase status records the current readiness review; it does not authorize training or claim that manual device acceptance has passed.

| Phase | Status | Verified boundary / remaining action |
|---|---|---|
| 1. Website completion | **BLOCKED — owner device check** | Pages deployment workflow succeeded. Manual iPad Safari acceptance, live-site interaction checks, and runtime connection remain pending. |
| 2. Deployment documentation | **COMPLETE** | PR #159 merged after required checks passed; deployment guide and README handoff updated. |
| 3. Math engine / Stage A | **IMPLEMENTED; MODEL EVALUATION PENDING** | Deterministic generators include bounded polynomial derivatives and definite integrals with exact validators. Evaluation and paired-comparison infrastructure exist. No trained-model prediction file or actual Fable 5.2 comparison is available; do not claim a benchmark pass. |
| 4. Seed-data pipeline | **TOOLING IMPLEMENTED; UPLOAD BLOCKED** | Source registry/importer and validation gates exist. No dataset artifact has been uploaded. Available Hugging Face connection is read-only for dataset file writes; no remote job or dataset duplication was used as a workaround. |
| 5. Training-control design | **DESIGN DOCUMENTED; RUNTIME NOT CONNECTED** | Generic status/readiness page and runtime research exist. The RAM slider is a local preference, not a live resource cap. Free-runtime and clean-session acceptance remain pending. |
| 6. From-scratch model | **MODEL CODE / CONFIG IMPLEMENTED; UNTRAINED** | PR #160 enforces ≥60M trainable parameters and guarded expansion. CI passed foundation/expansion capacity tests and compared the parameter-count formula with an instantiated small model. Foundation allocation, device resource profiling, and model capability evaluation remain unverified. |
| 7. Training / scale-up | **NOT AUTHORIZED; NOT STARTED** | No optimizer steps, training runs, generated corpus, or remote training execution. Requires a separate explicit authorization after readiness gates. |
| 8. Final verification / handoff | **IN PROGRESS** | README handoff updated after PR #161; main is `8d0ecf405a22ff22798b2e3166f830c0fab0175e`. Node, Python AI Core, and Level 1 Math Tooling post-merge workflows passed. Complete final verification after owner iPad acceptance; maintain exact verified/unverified boundaries. |

No phase status above supersedes the training authorization gate. Keep actual training, optimizer steps, corpus generation, and remote execution disabled.


## Model capacity requirement — 2026-11-26

ULTRON's foundation model target is **at least 60,000,000 trainable parameters**. The configuration code must enforce that minimum using the parameter-count formula; it must not rely on a descriptive label. Model capacity is expandable by increasing hidden width, depth, expert count, or expert width through validated configurations. The parameter-count formula was cross-checked against an instantiated small model in PR #160 CI. The 60M foundation itself was not instantiated by that regression; expanded sizes are not resource-tested. This is an architecture requirement only: the model remains untrained, and no optimizer step or training was performed.


## Phase 2 Math Agent, Memory Vault and security recheck — 2026-11-26

PR #163 adds comprehensive math parser coverage, expands the deterministic linear equation grammar to support fractional/decimal coefficients and grouped linear expressions, and explicitly rejects nonlinear or unsupported equations without fabricating a result. See [Math Agent input contract](docs/MATH_AGENT_INPUTS.md). The conversational Math Agent remains tutor-first and does not reveal final answers.

The local Memory Vault implementation now validates backup size and store names, rejects malformed generic record IDs, deduplicates duplicate IDs in an imported backup (last entry wins), and preserves merge-by-ID behavior. Automated IndexedDB contract tests cover save/list/reload persistence, simulated storage-write failure and retry, export/import round-trip, duplicate handling, malformed/oversized backup rejection, and local merge behavior. Browser real-world persistence still requires manual Safari testing.

Responsive/keyboard contract tests cover narrow layouts, portrait and landscape CSS, touch-target minimums, focus visibility, navigation dismissal and fallback states. These are automated static contract checks, not a real-device browser run. Manual iPad Safari acceptance remains pending.

The live Supabase policy and deployed-function review was repeated read-only on 2026-11-26. All nine inspected public tables have RLS enabled; the six owner-linked tables retain owner-only policies with both USING and WITH CHECK; anon has no SELECT grants; authenticated has no TRUNCATE; and the inspected public SECURITY DEFINER function is not executable by anon/authenticated. The security advisor still reports leaked-password protection disabled (owner dashboard action required) and three informational RLS-without-policy findings for retired pairing/device tables. See [Phase 3 security audit](docs/SECURITY_AUDIT_PHASE3.md).

No Supabase configuration was changed, no dataset was imported, and no training, optimizer step, corpus generation, or remote execution was performed.


## Latest handoff — 2026-11-26

- PR #163 is merged; merge commit: `cca21b1c5d701684a125abbfb4193ef6a04cd121`.
- PR-head checks passed: Node tests, Python AI Core, and Level 1 Math Tooling. Main post-merge checks all passed: Node, Python AI Core (including CPU forward/backward smoke), and Level 1 Math Tooling. Pages build and deploy also passed.
- GitHub Pages build/deploy run #45793501681 succeeded for the PR #163 merge commit.
- Phase 2 automated work is complete for Math Agent parser/input validation, Memory Vault import/export hardening, and responsive/keyboard/storage contract tests. These do not substitute for manual Safari acceptance.
- Remaining owner/device actions: (1) enable Supabase Auth leaked-password protection in the project dashboard, then re-run security advisors and final policy/endpoint review; (2) test the deployed site on an actual iPad Safari in portrait and landscape and record results.
- Continue the remaining Phase 1 specification and Phase 4 task-serialization/architecture items before any training. No training, optimizer step, dataset import/generation, or remote execution was performed.


## Compression parameter reporting — 2026-11-26

PR #165 adds parameter accounting only; it does not implement compression transformations. The report reuses the existing no-allocation configuration counters, **count_total_parameters(config)** and **count_parameters(config)**, and checks the foundation result against **63,400,451 total / 61,826,048 trainable** parameters. Model enumeration deduplicates tied parameters by Python object identity (id(parameter)), not storage address. The real foundation module structure is checked so category totals cover the full count and the other bucket contains only explicitly named normalization parameters.

The 60M trainable-parameter floor applies only to the foundation training checkpoint. Compressed models are separate, versioned deployment artifacts that record their parent checkpoint and the steps applied; they never replace the foundation checkpoint and are never described as meeting that floor. See [docs/COMPRESSION.md](docs/COMPRESSION.md).

Compression quality can only be judged on a trained model with a verified benchmark. **No calibration corpus has been generated**, and no compression-quality result is claimed. PR #165 remains unmerged pending all required CI checks. No training, optimizer step, corpus/calibration generation, cloud execution, or remote execution was performed. Do not start PR 2 until separately instructed.
