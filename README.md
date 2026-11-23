# ULTRON — Mathematics Workspace

ULTRON is an independent, local-first mathematics workspace under development. Its long-term goal is an original mathematics intelligence system. The current work is a prototype foundation, not a complete AI system. It uses no external AI APIs, pretrained models, pretrained weights, or paid services. Model training remains disabled unless separately authorized.

## Repository status

- Default and current branch: `main`.
- Open pull requests: none. Milestone PRs [#1](https://github.com/ultron1846-oss/ULTRON/pull/1) and [#2](https://github.com/ultron1846-oss/ULTRON/pull/2) are merged.
- Latest local test result: `node --test` — 6 passed, 0 failed.
- Latest main-branch test workflow: passed.
- Public site: verified at the target URL after GitHub's Pages build/deployment workflow succeeded. The separate custom Pages action workflow failed on its first run at `Configure Pages`, so that deployment path still needs validation.

The initial repository contained only a placeholder README. PR #1 added the first application and math foundation. PR #2 added the repository assessment, documentation, and delivery workflows.

## Architecture

- `index.html` is the static application shell.
- `styles.css` provides responsive desktop, tablet, and mobile styles.
- `app.js` renders the dashboard and the Mathematics, Learning, Engine, Knowledge, Training, Settings, and System Information sections.
- `math-engine.js` is a deterministic arithmetic parser and limited one-variable linear equation solver. It accepts `×` and `÷` and does not use `eval()` or `new Function()`.
- `tests/` contains Node.js built-in tests; no third-party packages are required.
- `docs/` records assessment, architecture, research, testing, deployment, limitations, and next steps.
- `.github/workflows/` contains the Node test workflow and static Pages deployment workflow.

## Current implementation

- Responsive navigation and dashboard with explicit prototype labels.
- Arithmetic expressions with parentheses, signs, decimals, exponentiation, and standard multiplication/division symbols.
- A limited solver for one-variable linear equations.
- One arithmetic practice problem with local progress tracking.
- A resource preference control that is explicitly not physical RAM allocation.
- Training controls that remain disabled and state that no model exists.
- A hand-authored starter glossary and planned-domain labels.

Planned cards are not implemented functionality.

## Tests

With Node.js 18 or later, run `node --test` (or `npm test` where npm is installed). The current suite covers arithmetic parsing, unsafe and malformed expression rejection, linear equations, navigation entry points, persistence hooks, responsive viewport declaration, and workflow guardrails. It does not replace browser interaction tests. iPad Safari and live deployment have not been verified.

## GitHub Pages

Target URL: `https://ultron1846-oss.github.io/ULTRON/`.

The custom static workflow stages the required site files and has no build step. It deploys only from `main`. Its first run stopped at `Configure Pages` with a “Get Pages site failed” error. A GitHub-generated Pages build/deployment run later succeeded, and the public dashboard loaded at the target URL. Confirm the repository **Settings → Pages** source before relying on the custom workflow; validate that workflow separately after the setting is confirmed.

## Known limitations

- The engine supports numeric arithmetic and a narrow linear equation format only; it is not a computer algebra system.
- Most mathematics topics are planned and do not yet have lessons, verified exercises, or formulas.
- Learning contains one exercise; progress and preferences use browser local storage, not IndexedDB or cloud storage.
- The resource control records workload preference and cannot allocate or measure physical memory.
- There is no model, generated training data, durable model checkpoint, backend, or authentication system.
- The repository contains no Subspace code or reference; its intended meaning is unresolved.
- The custom Actions deployment path has not yet passed; the public site itself is live and browser-verified.

## Five-PR development plan

1. **PR #1 — Website foundation:** responsive shell, prototype sections, safe arithmetic foundation, and initial tests. Merged.
2. **PR #2 — Repository assessment and delivery groundwork:** architecture and issue documentation, research notes, test workflow, Pages workflow, and deployment instructions. Merged.
3. **PR #3 — Mathematical engine and knowledge:** expand mathematical operations and verification, define structured knowledge entries, and add regression tests for supported operations.
4. **PR #4 — Learning and browser memory:** verified lesson/exercise flows, learner mistake history, IndexedDB-backed local progress, and safe export/import.
5. **PR #5 — Original intelligence research and integration:** document and test an original model/data-generation/training design, integrate only evidence-backed components, and add evaluation/checkpoint foundations. Training must remain disabled absent separate authorization.

Later milestones should be implemented, tested, and documented before their PRs are opened. The repository safety policy limits new PRs to two per 24 hours.

## Next steps

1. Confirm the GitHub Pages publishing source, then validate the custom deployment workflow without creating repeated runs.
2. Begin PR #3 by specifying the supported mathematical grammar and verification invariants before adding operations.
3. Add browser checks on desktop, mobile, and iPad Safari when an available test environment supports them.
4. Keep actual model training disabled unless the user separately authorizes it.

