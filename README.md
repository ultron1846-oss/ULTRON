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
- No Lean proof-kernel receipt flow; no theorem-proving capability claim.
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

Work through the requested small PRs in order: A (README/history), B (generator contract and registry), C (SymPy differential tests), D (verification status rename), E (Lean design and fake-checker interface). For each, inspect current main/open PRs first, avoid duplicating existing work, make only scoped changes, review the final diff, and report exact test results. Merge only after the required Node, Python AI Core, CPU smoke, and Python 3.11 CI checks pass. Do not run training, optimizer steps, corpus generation, or cloud/remote execution.

Owner to-dos (not attempted):
- Enable Supabase leaked-password protection in the dashboard.
- Run the iPad Safari frontend acceptance pass.
- Update free-runtime documentation: Lightning excluded; Colab primary; Kaggle internet access also requires phone verification, so Kaggle automation is not assumed.

## Brief dated history

- **2026-11-24:** Browser workspace hardening; Python math-core and exact arithmetic foundations; parser/IR, polynomial/rational operations, real-root and algebraic-number utilities; checkpoint, memory, and trust-boundary reviews.
- **2026-11-25:** Math Agent tools and tutor-first direction; Grades 1–4, 5–8, 8–12 and university generator expansion; university topic registry work; model/training preflight and free-runtime review; exact identity verifier documentation.
- **2026-11-26:** Requested separate PRs for README consolidation, generator unification, SymPy differential testing, exact-verification status naming, and Lean readiness design.

See [docs/HISTORY.md](docs/HISTORY.md) for the preserved milestone detail and [docs/](docs/) for topic-specific specifications.
