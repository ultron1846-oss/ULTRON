# ULTRON — Mathematics Workspace

ULTRON is an independent, local-first mathematics learning and calculation workspace. This repository currently contains an early static website prototype and a small mathematical engine. It uses no external AI APIs, pretrained models, or paid services.

## Architecture

- `index.html` is the accessible static application shell.
- `styles.css` provides responsive desktop, tablet, and mobile layouts.
- `app.js` renders the dashboard and the Mathematics, Learning, Engine, Knowledge, Training, Settings, and System Information sections.
- `math-engine.js` is an independent safe arithmetic parser and limited linear equation solver. It never uses `eval()` or `new Function()`.
- `tests/` contains Node.js built-in tests; no third-party packages are needed.

## Current features

- Responsive navigation and dashboard with explicit prototype status.
- Arithmetic expression evaluation with parentheses, signs, decimals, and exponentiation.
- One-variable linear equation solving for basic numeric coefficients.
- One arithmetic practice problem with local progress tracking.
- Local resource preference slider, clearly described as a preference rather than RAM allocation.
- Training control page that keeps training disabled and does not claim a model exists.
- Hand-authored starter glossary and planned-domain status labels.

## Milestone and outstanding work

The first website foundation prototype is in place. This does not complete ULTRON or constitute a mathematical intelligence system. Planned work includes broader parser validation, symbolic operations, equation families, domain-specific lessons and practice, a structured knowledge base, a model architecture, and training infrastructure. Training must remain disabled until separately authorized. No model or generated training data is included.

## Tests

Run `npm test` with Node.js 18 or later. Tests cover arithmetic parsing, unsafe and malformed input rejection, linear equations, navigation entry points, persistence hooks, and the responsive viewport declaration. Automated source checks do not replace real-device visual testing; iPad Safari and deployed hosting have not been verified in this environment.

## Netlify deployment

This is a static site with no build step. In Netlify, connect the repository, set the publish directory to `.` and leave the build command empty. The root `index.html` is the entry point. A live deployment has not been created or verified.

## Known limitations

- The engine supports numeric arithmetic and a narrow linear equation format only. It is not a computer algebra system.
- Domain cards marked planned do not implement those subjects.
- Learning has one arithmetic practice item; progress is stored only in the current browser.
- The resource control expresses future workload preference and cannot control physical memory.
- The interface uses system fonts and has no external runtime dependencies.
- No login, backend, model, training, or live Netlify site exists.

## Exact next steps

1. Review this foundation in the proposed GitHub pull request.
2. Add parser and solver cases with explicit supported grammar, then broaden mathematical engine modules.
3. Build learning content and validate accessible behavior on desktop, mobile, and iPad Safari.
4. Design the local knowledge schema and tests before populating it.
5. Propose a model design and data-generation approach separately; do not start training without separate authorization.
