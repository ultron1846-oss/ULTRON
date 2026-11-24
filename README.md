# ULTRON — Mathematics Intelligence Workspace

ULTRON is an independent, local-first mathematics workspace under development. Its long-term goal is an original mathematics intelligence system. The current website is a static frontend and deterministic foundation prototype—not a trained AI model.

## Frontend status

The frontend is being redesigned around the supplied ULTRON control-room reference: near-black surfaces, crimson accents, a compact top header, left navigation, bordered panels and responsive tablet/mobile layouts.

### Current pages
- **Supabase backend:** audited view of the existing Supabase project and deployed Edge Function contracts. It intentionally does not call owner-only services from the public site.
- **Overview:** honest system status, model/training state, mathematical capability summary and local practice count.
- **How ULTRON learns:** explains the intended verified learning lifecycle and distinguishes learning exercises from neural-model training.
- **Math Agent:** browser interface to the existing deterministic arithmetic parser and limited linear-equation solver.
- **Servers:** reads optional `servers.json`, handles missing/malformed directory data and never starts remote jobs.
- **Settings:** stores a preferred future workload memory budget locally; it does not allocate device or remote memory.

The frontend intentionally does not claim a general AI assistant, general symbolic algebra, a proof checker, a trained neural model or active training.

## Architecture
- `index.html`: public application shell and navigation.
- `styles.css`: black/crimson control-room visual system and responsive layouts.
- `app.js`: frontend rendering, navigation, local preferences, Math Agent UI, provider directory and Supabase audit page.
- `supabase-integration.js`: safe, non-secret snapshot of the inspected Supabase service contract; no network calls or credentials.
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

## Supabase integration audit

The existing Supabase project `ultron-memory` was inspected directly. Its project status was `ACTIVE_HEALTHY` at inspection time. The database contains owner-linked memory tables and a `training_api` schema; row-level security is enabled. The public site has no login, so it must not query owner-scoped records or attempt to use the owner-only training function.

- `device-control` is deployed but intentionally retired; it returns HTTP 410.
- `training-control` requires a valid owner JWT and currently contains an old GitHub repository target (`shayaanfarsheed-cmd/ULTRONAI`) and old Pages origin (`shayaanfarsheed-cmd.github.io`). The current website is `ultron1846-oss/ULTRON`; the backend allowlist/configuration therefore needs Codex-side alignment before any browser integration.
- The frontend exposes this audit as configuration information only. It does not claim live telemetry, read protected tables, send credentials, dispatch workflows, or start training.
- No Supabase schema, policies, secrets, or Edge Functions were changed during this frontend work.

### Required backend follow-up (Codex)
1. Align the server-side GitHub repository constant and allowed Pages origin with `ultron1846-oss/ULTRON` and its deployed Pages origin.
2. Add a public, read-only health endpoint that returns only service health/configuration booleans; do not expose owner data, run metadata, credentials, or start/stop actions.
3. Keep training start/stop inaccessible from the public website and retain the explicit training-disabled safeguard.
4. Document and test the response contract before the frontend adds live polling.

## Backend handoff / remaining work
The backend owner (Codex) should:
1. Maintain and test the deterministic math engine API without breaking the frontend imports.
2. Decide and document the `servers.json` schema; include it in the Pages staging step when it exists.
3. Keep all training entry points hard-disabled and add backend regression tests preventing accidental execution.
4. Implement knowledge, lesson, verification and memory services behind documented interfaces before the frontend advertises them as available.
5. Keep provider metadata evidence-based and current; never invent free-tier availability.
6. Keep the Supabase health-only public contract separate from owner-only training controls.
7. Update this README at meaningful milestones so the next development session can resume accurately.

## Delivery plan

The screenshot-inspired frontend redesign is delivered as one consolidated pull request: [PR #3](https://github.com/ultron1846-oss/ULTRON/pull/3). Do not split this frontend milestone into additional pull requests. Codex owns backend services and backend tests; this frontend branch must not duplicate backend implementation. Keep actual training disabled.

## Next frontend steps
1. Run the full Node test suite and inspect the PR checks.
2. Verify the deployed Pages URL and asset paths after merge.
3. Test touch navigation, forms, scrolling and layout on iPad Safari and mobile browsers.
4. Connect additional backend capabilities only after their interfaces and tests exist.

## Project rule
A polished interface must not imply functionality that has not been implemented. Training remains disabled absent separate explicit authorization.
