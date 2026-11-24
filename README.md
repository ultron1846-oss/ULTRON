# ULTRON — Mathematics Intelligence Workspace

ULTRON is an independent, local-first mathematics workspace under development. Its long-term goal is an original mathematics intelligence system. The current website is a static frontend and deterministic foundation prototype—not a trained AI model.

## Frontend status

The frontend is being redesigned around the supplied ULTRON control-room reference: near-black surfaces, crimson accents, a compact top header, left navigation, bordered panels and responsive tablet/mobile layouts.

### Current pages
- **Overview:** honest system status, model/training state, mathematical capability summary and local practice count.
- **How ULTRON learns:** explains the intended verified learning lifecycle and distinguishes learning exercises from neural-model training.
- **Math Agent:** browser interface to the existing deterministic arithmetic parser and limited linear-equation solver.
- **Servers:** reads optional `servers.json`, handles missing/malformed directory data and never starts remote jobs.
- **Settings:** stores a preferred future workload memory budget locally; it does not allocate device or remote memory.

The frontend intentionally does not claim a general AI assistant, general symbolic algebra, a proof checker, a trained neural model or active training.

## Architecture
- `index.html`: public application shell and navigation.
- `styles.css`: black/crimson control-room visual system and responsive layouts.
- `app.js`: frontend rendering, navigation, local preferences, Math Agent UI and provider-directory presentation.
- `math-engine.js`: deterministic arithmetic parser and limited one-variable linear equation solver. No `eval()` or `new Function()`.
- `tests/`: Node.js built-in regression tests.
- `.github/workflows/`: test and GitHub Pages workflows.

## Safety boundaries
- No external AI APIs or pretrained model weights.
- No login or registration required.
- No provider job submission or background execution from the public frontend.
- **Actual model training remains disabled** until separate explicit user authorization.
- The RAM slider is a browser-local preference only; it does not control physical RAM or GPU VRAM.
- Provider availability and free-tier terms are not guaranteed; verify directly with providers.

## Development and tests
Requires Node.js 18 or later. Run:

```sh
node --test
```

Automated tests do not replace live browser testing. iPad Safari testing must only be reported after it has actually been performed.

## GitHub Pages
Target URL: `https://ultron1846-oss.github.io/ULTRON/`. The Pages workflow must stage every runtime asset required by the frontend, including `math-engine.js` and (when added by backend work) `servers.json`. A successful Actions deployment is not by itself proof of every page interaction.

## Backend handoff / remaining work
The backend owner (Codex) should:
1. Maintain and test the deterministic math engine API without breaking the frontend imports.
2. Decide and document the `servers.json` schema; include it in the Pages staging step when it exists.
3. Keep all training entry points hard-disabled and add backend regression tests preventing accidental execution.
4. Implement knowledge, lesson, verification and memory services behind documented interfaces before the frontend advertises them as available.
5. Keep provider metadata evidence-based and current; never invent free-tier availability.
6. Update this README at meaningful milestones so the next development session can resume accurately.

## Next frontend steps
1. Run the full Node test suite and inspect the PR checks.
2. Verify the deployed Pages URL and asset paths after merge.
3. Test touch navigation, forms, scrolling and layout on iPad Safari and mobile browsers.
4. Connect additional backend capabilities only after their interfaces and tests exist.

## Project rule
A polished interface must not imply functionality that has not been implemented. Training remains disabled absent separate explicit authorization.
