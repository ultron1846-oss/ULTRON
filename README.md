# ULTRON — Mathematics Intelligence Workspace

**Status snapshot: 2026-11-26**

ULTRON is an independent mathematics-learning and reasoning project. Its deterministic tools, generators, and model architecture are development infrastructure—not evidence of a trained general-purpose mathematics model.

## Current status

- **From-scratch model:** The foundation configuration enforces at least 60 million trainable parameters. The current allocation is 63,400,451 total parameters, including 61,826,048 trainable parameters. The model remains untrained.
- **Mathematics core:** The repository includes a bounded parser and expression representation, exact rational and polynomial operations, rational and polynomial identity checking, algebraic-number utilities, and deterministic math tools.
- **Generators:** Core, Grades 1–4, 5–8, 8–12, and university generators are present. The shared `Problem` contract and verifier interface normalize source records; a code-generated combined registry tracks declared coverage. Generator availability does not mean a topic is mastered.
- **Train/benchmark separation:** Reserved seed ranges, normalized-prompt checks, and generation-ingredient hashes guard against benchmark overlap with training examples.
- **Exact checking:** Exact engine results use `EXACT_CHECKED`. This is not formal proof. Trusted-knowledge admission remains fail-closed; `FORMALLY_VERIFIED` is reserved for a future independently validated proof-kernel receipt.
- **SymPy differential tests:** Fixed-seed tests cover eight exact-engine areas with 1,000 cases per area. SymPy is test-only and is not part of runtime math code.
- **Level 1 tooling:** Arithmetic and linear-equation generators have exact regression coverage and a separate 500-item held-out benchmark. The benchmark is opt-in; it is not training data and has not been used for training.
- **Lean:** The integration plan and abstract interface stub exist. No Lean toolchain, proof execution, receipt validator, or theorem-proving capability is claimed.
- **Compression:** PR #166 added non-destructive expert pruning/representative merging, SVD factorization, simulated int8 sensitivity reporting, and versioned artifacts. Int8 remains a floating-point simulation; there are no trained-checkpoint quality, speed, or memory-reduction results. Compressed deployment artifacts do not count toward the foundation parameter floor.
- **Website:** The static website is account-free. The local memory and memory-preference UI do not provide a connected training runtime or a physical RAM allocation guarantee. Manual iPad Safari acceptance remains pending.

## Architecture

- `ultron_core/`: model/configuration, parser and math IR, exact math, verification, data generation, benchmark/split guards, memory, agent tools, training and checkpoint infrastructure, and compression.
- `tools/math_generators/`: curriculum generators, metadata, replay verifiers, per-band registries, and the combined registry builder.
- `tools/level1_math/`: bounded Level 1 arithmetic and linear-equation generators, exact verifier, and opt-in held-out benchmark.
- `tests/`: Python and Node regression, differential, contract, and integration tests.
- `docs/`: architecture, mathematical engine, security, evaluation, compression, runtime constraints, historical milestones, and staged Lean integration documentation.
- `index.html` and frontend assets: the static browser workspace.

## Verification and limitations

The most recent post-merge checks verified on `main` after PR #166 are:

- [Python AI Core run #45811463595](https://github.com/ultron1846-oss/ULTRON/actions/runs/45811463595): success, including the Python regression suite and CPU forward/backward smoke.
- [Level 1 Math Tooling run #45811463693](https://github.com/ultron1846-oss/ULTRON/actions/runs/45811463693): success, including the regression job with 5,000 randomized cases.

These results establish the tested code and workflow behavior only. They do not establish trained model capability, benchmark mastery, successful deployment to a physical device, or compression quality on trained weights.

## Safety and trust boundaries

- No external AI APIs or pretrained weights are used for the from-scratch model plan.
- No training, optimizer steps, training-corpus generation, calibration-data generation, or cloud/remote training execution is authorized by this status.
- A deterministic generator, command result, exact-check result, or tool-assisted answer must not be presented as learned model capability.
- SymPy is restricted to tests; runtime math code must not depend on it.
- Do not modify the website, Supabase, authentication, GitHub Pages, secrets, or deployment configuration as part of core math work without separate scope and authorization.
- Do not start training without separate explicit authorization.

## Current handoff

- Repository: [ultron1846-oss/ULTRON](https://github.com/ultron1846-oss/ULTRON), default branch `main`.
- Latest merged engineering change: [PR #166 — compression toolkit](https://github.com/ultron1846-oss/ULTRON/pull/166). The post-merge Python AI Core and Level 1 Math Tooling runs listed above both succeeded.
- The requested pre-training engineering checklist A–G has been reviewed. Its implemented math-engine, generator, verification, Lean-stub, Level 1, and word-problem coverage is summarized above; detailed dated milestones are archived in docs/HISTORY.md.
- Remaining owner-side acceptance includes manual iPad Safari testing. Automated responsive checks are not a substitute for testing on an actual iPad.
- Continue with small, independently reviewable math-engine or readiness tasks. Preserve the no-training authorization boundary.

For prior implementation details and dated engineering milestones, see [docs/HISTORY.md](docs/HISTORY.md). For current feature-specific requirements, use the relevant documents under [docs/](docs/).
