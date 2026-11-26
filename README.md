# ULTRON — Mathematics Intelligence Workspace

**Status snapshot: 2026-11-26**

ULTRON is an independent mathematics-learning and reasoning project under development. The website and deterministic math tooling are not a trained general-purpose AI model. No capability claims should be inferred from generator coverage, exact-checking utilities, or tool-assisted answers.

## Current status

- The repository contains a Python mathematics core, bounded symbolic/exact arithmetic components, a browser workspace, curriculum generators, and agent/tool interfaces.
- Training remains disabled and has not been authorized in this work. No optimizer steps, training runs, or cloud/remote execution are part of this task.
- Seed-corpus importer work is tracked separately in open PR #136. The corpora are not claimed to be downloaded or present in the repository unless that PR’s artifact run is confirmed.
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
- PR C will add fixed-seed SymPy differential tests; those tests must report disagreements with reproducible inputs.

### Not implemented or not accepted
- No trained ULTRON weights or demonstrated grade/university-level competence.
- No approved training run, optimizer steps, corpus generation, or cloud execution.
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
- Do not expose secrets, change authentication/Supabase/Pages configuration, or make production changes without separate authorization.

## Current handoff

- PRs #136–#143 are merged. PR #134 was closed without merge and superseded by merged PR #142.
- This README handoff refresh is proposed in PR #144; check its current status before treating it as merged.
- Issue #135 remains open and defines the next pre-training acceptance work: tool-disabled model-only evaluation, separate model-only/tool-assisted metrics, regression protection against command-output leakage into training targets, concept/prerequisite curation, and held-out concept-transfer evaluation.
- The seed importer and the basic-arithmetic source registration are merged. They provide import tooling only; they do not mean the dataset has been downloaded or uploaded. The manual importer remains gated by `confirm_download=true` and the owner-controlled `ULTRON_SEED_IMPORT_ENABLED=true` variable.
- No dataset import artifact, optimizer step, model training, or remote training execution is claimed. Do not enable the import gate or dispatch the workflow without separate explicit authorization.
- Owner to-dos (not attempted): complete iPad Safari acceptance; enable Supabase Auth leaked-password protection; verify free-runtime access and checkpoint transfer from a clean iPad session.

## Brief dated history

- **2026-11-24:** Browser workspace hardening; Python math-core and exact arithmetic foundations; parser/IR, polynomial/rational operations, real-root and algebraic-number utilities; checkpoint, memory, and trust-boundary reviews.
- **2026-11-25:** Math Agent tools and tutor-first direction; Grades 1–4, 5–8, 8–12 and university generator expansion; university topic registry work; model/training preflight and free-runtime review; exact identity verifier documentation.
- **2026-11-26:** Requested separate PRs for README consolidation, generator unification, SymPy differential testing, exact-verification status naming, and Lean readiness design.

See [docs/HISTORY.md](docs/HISTORY.md) for the preserved milestone detail and [docs/](docs/) for topic-specific specifications.

## Guided learning and command independence — 2026-11-26

The Math Agent's ordinary input path gives hints and requests an intermediate attempt instead of automatically revealing arithmetic, word-problem, or equation answers. Slash commands are explicit tools, but equation-solving commands are also tutor-first: they provide a first-step hint or check a learner-submitted attempt without displaying the correct final value. `/calc` requires the learner's proposed result and reports only whether it matches. Graphing and table/numerical tools remain scoped to the requested visualization or operation. See `tests/guided-learning.test.js` and `tests/math-tools.test.js` for regressions. This is deterministic tutoring/tool behavior, not trained-model capability.


## Cognitive behavior profile hardening — 2026-11-26

The cognitive behavior profile now rejects non-finite numeric weights (`NaN`, positive infinity, and negative infinity) and exposes factuality, conversational naturalness, creativity, and empathy/context weights in the selected runtime policy. Regression tests cover every numeric weight and customized policy values. This remains a configuration contract—not evidence of trained capability. No training or data import was performed.

## Level 1 exact math tooling — CI scope (2026-11-26)

The Level 1 arithmetic and linear-equation package is an exact, deterministic tooling prototype with SymPy differential tests and a separately defined 500-item held-out evaluation benchmark. CI runs the package regression suite only; it no longer generates or writes the held-out benchmark. The benchmark scripts remain opt-in for a separately authorized local evaluation and must never be used as training data. The training-source adapter is a guarded interface, not a training run. No optimizer step, corpus generation, model training, or remote training execution was performed.

## Seed importer CI safety regression — 2026-11-26

The importer test suite now verifies that the workflow has no push trigger and is skipped unless both the dispatch confirmation and owner-controlled repository variable are enabled. This test uses the checked-in workflow text only; it does not dispatch or download data.

## Seed-data import authorization boundary — 2026-11-26

The Hugging Face seed importer is available as tooling only. Its workflow has no push trigger and runs only when the manual confirm_download input is true and the owner-controlled repository variable ULTRON_SEED_IMPORT_ENABLED is set to true. That variable remains unset. Offline mocked tests validate the importer; no dataset download, corpus import, optimizer step, or training run was performed. Do not enable the variable or dispatch the workflow until separate explicit authorization is given.


## Basic arithmetic seed source preparation — 2026-11-26

Added the MIT-licensed `ChrisMcCormick/basic-arithmetic` Hugging Face training split (10,000 source rows) to the seed importer registry. The importer independently validates arithmetic against integer operands, accepts only exact integer division, limits operand magnitude to 10,000, rejects mismatched answers/unsupported operations, and marks these records as answer-only rather than worked reasoning. Validation and test splits are not configured for import.

This is source/importer support only. No dataset rows have been downloaded or uploaded, no workflow was dispatched, and no training or optimizer step occurred. The manual importer remains gated by `confirm_download=true` and `ULTRON_SEED_IMPORT_ENABLED=true`. Review the PR and run the gated workflow separately to produce the seed-data artifact.
