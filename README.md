# ULTRON — Mathematics Workspace

ULTRON is an independent, local-first mathematics workspace under development. Its long-term goal is an original mathematics intelligence system. The current work is a prototype foundation, not a complete AI system. It uses no external AI APIs, pretrained models, pretrained weights, or paid services. Model training remains disabled unless separately authorized.

## Repository status

- Default branch: `main`.
- Current milestone branch: `feat/math-website-foundation`.
- Open pull request: [#1 — Build ULTRON mathematics website foundation](https://github.com/ultron1846-oss/ULTRON/pull/1).
- Assessment/deployment milestone branch: `milestone-2-assessment-pages` (stacked on PR #1).
- Latest local test run including assessment/deployment checks: `node --test` — 6 passed, 0 failed.
- GitHub Actions workflow checks: no run yet. Pages is not merged, enabled, or publicly verified.

The repository's initial `main` snapshot contained only a placeholder README. The feature branch in PR #1 adds the first application, arithmetic parser, limited linear equation solver, and tests. GitHub currently reports no workflow runs for the repository.

## Architecture

- `index.html` is the static application shell.
- `styles.css` provides responsive desktop, tablet, and mobile styles.
- `app.js` renders the dashboard and the Mathematics, Learning, Engine, Knowledge, Training, Settings, and System Information sections.
- `math-engine.js` is a small deterministic arithmetic parser and limited one-variable linear equation solver. It does not use `eval()` or `new Function()`.
- `tests/` contains Node.js built-in tests; no third-party packages are required.
- `docs/` records assessment, architecture, research, testing, deployment, limitations, and next steps.
- `.github/workflows/` will contain the static Pages deployment and test workflows after the assessment milestone is proposed.

## Current implementation

- Responsive navigation and dashboard with explicit prototype labels.
- Arithmetic expressions with parentheses, signs, decimals, and exponentiation.
- A limited solver for one-variable linear equations.
- One arithmetic practice problem with local progress tracking.
- A resource preference control that is explicitly not physical RAM allocation.
- Training controls that remain disabled and state that no model exists.
- A hand-authored starter glossary and planned-domain labels.

These features are in an open PR until merged. Planned cards are not implemented functionality.

## Tests

With Node.js 18 or later, run `node --test` (or `npm test` where npm is installed). Tests cover arithmetic parsing, unsafe and malformed expression rejection, linear equations, navigation entry points, persistence hooks, and the responsive viewport declaration. They do not replace browser interaction tests. iPad Safari and live deployment have not been verified.

## GitHub Pages

ULTRON is intended for GitHub Pages at `https://ultron1846-oss.github.io/ULTRON/`. The static website has no build step. The proposed workflow packages the root page and its required assets and deploys only from `main`. After the workflow is merged, repository Pages settings must use **GitHub Actions** as the publishing source. Do not claim that the site is live until the public URL has been opened and checked.

## Known limitations

- The engine supports numeric arithmetic and a narrow linear equation format only; it is not a computer algebra system.
- Most mathematics topics are planned and do not yet have lessons, verified exercises, or formulas.
- Learning contains one exercise; progress and preferences use browser local storage, not IndexedDB or cloud storage.
- The resource control records workload preference and cannot allocate or measure physical memory.
- There is no model, generated training data, durable model checkpoint, backend, or authentication system.
- The current assessment found no Subspace code, dependency, configuration, documentation, or tests in the inspected repository snapshot.

## Five-PR development plan

1. **PR #1 — Website foundation:** responsive shell, prototype sections, safe arithmetic foundation, initial tests. Open.
2. **PR #2 — Repository assessment and delivery groundwork:** evidence-based architecture and issue documentation, research notes, tests workflow, GitHub Pages workflow, and deployment instructions. Stacked milestone branch prepared.
3. **PR #3 — Mathematical engine and knowledge:** expand mathematical operations and verification, define structured knowledge entries, and add regression tests for supported operations.
4. **PR #4 — Learning and browser memory:** verified lesson/exercise flows, learner mistake history, IndexedDB-backed local progress, and safe export/import.
5. **PR #5 — Original intelligence research and integration:** document and test an original model/data-generation/training design, integrate only components supported by evidence, and add evaluation/checkpoint foundations. Training must remain disabled absent separate authorization.

The PR plan is staged. Later PRs depend on earlier work and should be opened only when their milestone is implemented, tested, and documented. The repository safety policy limits new PRs to two per 24 hours.

## Exact next steps

1. Review PR #1 and the stacked assessment/deployment milestone.
2. Once the foundation is on `main`, confirm GitHub Pages settings and verify the published site.
3. Start PR #3 by specifying the mathematical grammar and verification invariants before adding operations.
4. Add browser-based checks on desktop, mobile, and iPad Safari when an available browser test environment supports them.
5. Keep actual model training disabled unless the user separately authorizes it.
