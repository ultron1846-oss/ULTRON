# ULTRON — Mathematics Intelligence Workspace

ULTRON is an independent, local-first mathematics workspace under development. Its long-term goal is an original mathematics intelligence system. The current website is a static frontend and deterministic foundation prototype—not a trained AI model.

## Frontend status

A follow-up startup/navigation hardening change keeps a complete static overview visible before JavaScript modules load, adds visible browser error reporting if a module fails, cache-busts the app entry and its imports, and replaces the intentionally empty overview telemetry placeholders with actionable project status and quick links. This is a resilience fallback; a successful render in the real iPad browser still needs device verification.

The frontend is being redesigned around the supplied ULTRON control-room reference: near-black surfaces, crimson accents, a compact top header, left navigation, bordered panels and responsive tablet/mobile layouts.

### Current pages
- **Supabase backend:** refreshable, bounded-time read-only status check with visible last-checked time, plus an audit of deployed Edge Function contracts and backend security findings. It never calls owner-only services from the public site.
- **Overview:** honest system status, model/training state, mathematical capability summary and local practice count.
- **How ULTRON learns:** explains the intended verified learning lifecycle and distinguishes learning exercises from neural-model training.
- **Math Agent:** browser interface to the existing deterministic arithmetic parser and limited linear-equation solver.
- **Learn & practice:** topic roadmap, four fixed foundation exercises, answer checking, hints and local practice counts.
- **Memory vault:** IndexedDB stores experiences and mistakes locally, with JSON export/import for device-to-device transfer. This is not cloud sync.
- **Servers:** reads optional `servers.json`, handles missing/malformed directory data and never starts remote jobs.
- **Settings:** stores a preferred future workload memory budget locally; it does not allocate device or remote memory.

The frontend intentionally does not claim a general AI assistant, general symbolic algebra, a proof checker, a trained neural model or active training.

## Architecture
- `index.html`: public application shell and navigation.
- `styles.css`: black/crimson control-room visual system and responsive layouts.
- `app.js`: frontend rendering, navigation, local preferences, Math Agent UI, provider directory and Supabase audit page.
- `supabase-integration.js`: public status client and non-secret audit metadata. It uses only the publishable API key and the read-only `public_status` action.
- `memory-store.js`: local IndexedDB memory database (`ULTRON_MEMORY`, version 1) with `experiences`, `knowledge`, `mistakes` and `checkpoints` stores.
- `servers.json`: informational provider directory; Google Colab is selected as the planned notebook environment, not connected.
- `math-engine.js`: deterministic arithmetic parser and limited one-variable linear equation solver. No `eval()` or `new Function()`.
- `tests/`: Node.js built-in regression tests.
- `.github/workflows/`: test and GitHub Pages workflows.

## Safety boundaries
- No external AI APIs or pretrained model weights.
- Public browsing requires no account. The optional owner sign-in uses the existing Supabase email/password account; public registration is not exposed.
- No provider job submission or background execution from the public frontend.
- **Actual model training remains disabled** until separate explicit user authorization.
- The RAM slider is a browser-local workload preference only; it does not control physical RAM, GPU VRAM or Colab runtime allocation.
- The Memory Vault is device/browser-local. JSON backup export/import is the supported manual transfer path; no cloud memory sync is currently implemented.
- Provider availability and free-tier terms are not guaranteed; verify directly with providers.

## Development and tests
Requires Node.js 18 or later. Run:

```sh
node --test
```

Automated tests do not replace live browser testing. iPad Safari testing must only be reported after it has actually been performed.

## GitHub Pages
Target URL: `https://ultron1846-oss.github.io/ULTRON/`. The Pages workflow must stage every runtime asset required by the frontend, including `math-engine.js`, `supabase-integration.js`, `memory-store.js` and `servers.json`. A successful Actions deployment is not by itself proof of every page interaction.

## Supabase integration audit

The connected Supabase project `ultron-memory` was inspected directly. It was `ACTIVE_HEALTHY` at inspection time. Its memory tables and `training_api` tables remain owner-linked and protected by row-level security; the public website does not query those records.

- `device-control` remains retired and returns HTTP 410.
- `training-control` is deployed at version 8. Its GitHub repository target is `ultron1846-oss/ULTRON`, and its allowed browser origin is `https://ultron1846-oss.github.io`.
- A `public_status` action is available without a user session. It returns only generic service state, model status, and explicit training/remote-execution disabled flags. It does not return owner IDs, run metadata, memory records, provider credentials, or secrets.
- The Edge Function platform JWT check is disabled so the public status action can be called from the account-free site. Every existing protected action still performs its own bearer-token verification and owner-ID check inside the function. The public site calls only `public_status`.
- The frontend uses the Supabase publishable key in the `apikey` header. No service-role key, secret key, GitHub token, or owner credential is included in the repository.
- No database schema, RLS policy, user record, or secret was changed. The Edge Function code was updated; training remains disabled and no training job was started.
- Security advisors also reported three RLS-enabled retired device/pairing tables with no policies, disabled leaked-password protection, and several unindexed foreign keys. These are separate database-hardening items; the public status endpoint does not expose those tables.

## Owner authentication — 2026-11-24

The frontend includes optional Supabase email/password sign-in for the existing owner account. No sign-up or account-creation flow is present. Public pages remain accessible while signed out. The browser stores only the Supabase access/refresh session, never the password; expiring access tokens are refreshed and sign-out clears the local session. Authentication alone does not grant owner privileges: the page calls the `training-control` `health` action with the bearer token, and the Edge Function verifies the authenticated user ID against the server-side `ULTRON_OWNER_USER_ID` secret. Non-owner users are rejected. The publishable key is the only key included in browser code. No Auth provider settings, user records, secrets, RLS policies or database data were changed. The owner sign-in page does not start training or remote jobs.

## Supabase frontend integration audit — 2026-11-24

The live project was re-inspected while aligning the backend page with the rebuilt frontend. The project is `ACTIVE_HEALTHY` in `ap-south-1`. The public page calls only `training-control` with the `public_status` action, the publishable key in the `apikey` header, no owner bearer token, and a 10-second request timeout. The response is validated to require an online control plane, training disabled, remote execution disabled, and an informational-only provider directory. The page exposes a manual refresh and last-checked timestamp.

The deployed `training-control` function is version 8 with platform JWT verification disabled so the no-login public status request can reach its handler. The handler returns only generic status for `public_status`; its other actions continue to validate a signed-in owner session and configured owner ID. The deployed `device-control` function is still listed as active/version 4, but its handler is fail-closed and returns HTTP 410 for every request. It is retired, not physically removed.

All nine inspected public tables had RLS enabled. The security advisor reported three RLS-enabled retired device/pairing tables with no policies, and warned that leaked-password protection is disabled. Those findings are documented for backend hardening; this frontend PR does not alter database schema, policies, Auth settings, Edge Functions, secrets, or records. The public website does not access any of those tables.

## Backend handoff / remaining work

The backend owner (Codex) should:
1. Maintain and test the deterministic math engine API without breaking the frontend imports.
2. Maintain the documented `servers.json` provider schema and verify Colab terms and quotas before any future runtime integration.
3. Keep all training entry points hard-disabled and add backend regression tests preventing accidental execution.
4. Keep cloud memory synchronization separate from the local Memory Vault. Do not expose owner-linked tables to the no-login website; propose an explicit anonymous-device identity and threat model before any cloud-sync change.
5. Keep provider metadata evidence-based and current; never invent free-tier availability.
6. Keep the Supabase public_status response read-only and separate from owner-only training controls; do not expose database rows or credentials.
7. Update this README at meaningful milestones so the next development session can resume accurately.

## Delivery history

- [PR #3](https://github.com/ultron1846-oss/ULTRON/pull/3): screenshot-inspired crimson control-room redesign and safe Supabase public status integration.
- The follow-up frontend completion milestone adds topic exploration, functional local practice, IndexedDB memory with backup/restore, and the informational Google Colab directory.

## Current frontend boundaries

- Google Colab is the selected future notebook environment. The website only links to the official Colab site; it does not authenticate, create notebooks, launch runtimes, submit jobs or start training.
- The Memory Vault uses browser IndexedDB because the existing Supabase memory tables are owner-authenticated. The no-login public website must not weaken RLS or expose those rows. Cross-device transfer currently requires a user-managed JSON backup.
- The memory database follows the requested store names, but browser quota and private-browsing behavior vary. “Unlimited history” cannot be guaranteed by browser storage.
- The Settings memory slider is a saved preference only. A future Colab notebook must independently translate approved settings into batch size and runtime-safe limits.

## Next verification steps
1. Run `node --test` and inspect all GitHub Actions checks on the frontend completion PR.
2. Confirm GitHub Pages deployment and verify that every runtime asset is staged.
3. Test navigation, topic selection, exercise checking, memory export/import and slider behavior on iPad Safari.
4. Confirm the live Supabase `public_status` request from the deployed Pages origin and use the backend page's refresh/last-checked indicator.
5. Keep actual model training and remote execution disabled until separately authorized.

## Project rule
A polished interface must not imply functionality that has not been implemented. Training remains disabled absent separate explicit authorization.


## Next-chat handoff — owner authentication

- Optional owner email/password sign-in is implemented; public pages remain anonymous-accessible and there is no sign-up UI.
- Verify the existing owner account can sign in from GitHub Pages and that a different Supabase account is rejected by server-side owner verification.
- Confirm Supabase Auth email/password provider is already enabled and the existing owner user is active; do not create another account or change Auth settings without explicit approval.
- Keep service-role keys and `ULTRON_OWNER_USER_ID` secret server-side.
- Do not launch the CPU diagnostic workflow, training, Colab, or any remote job.
- Update this README at the next meaningful milestone.


## Frontend completion hardening — 2026-11-24

This release pass closes several frontend reliability gaps while preserving the no-training/no-server-connection boundary:

- The GitHub Pages artifact now explicitly includes `owner-auth.js`, which is imported by the application entry module. This prevents the deployed site from omitting a required runtime module.
- Navigation exposes the active page to assistive technology. The mobile menu closes with Escape, after navigation, and when the user taps outside it. The contrast preference persists in the current browser.
- The Memory Vault separates recent experiences from incorrect attempts, provides an explicit confirmed clear-all action, and reports storage failures honestly. Export URL cleanup is delayed so mobile browsers have time to start the download.
- IndexedDB request helpers resolve only after the transaction commits. The local practice interface no longer hides a failed memory write behind a success message.
- Tablet/mobile styles account for safe areas and reduced-motion preferences.

Automated release checks cover the Pages runtime asset list, frontend module syntax, mobile navigation hooks, persisted contrast preference, and Memory Vault controls. These checks do not substitute for a live iPad Safari interaction test; that still requires a user-side browser test after deployment. Owner sign-in remains email/password for the existing owner account, with no public sign-up. No Supabase policies, secrets, Auth settings, provider connections, remote jobs or training behavior are changed.

## Next-chat handoff — frontend release

- Verify the deployed Pages build loads the owner sign-in page and all public pages. The Pages artifact must include `owner-auth.js` as well as the other imported modules.
- On iPad, test opening/closing navigation, switching pages, contrast preference persistence, practice answer checking, Memory Vault history/mistake lists, backup export/import and clear-all confirmation.
- If local memory is important, export a backup before testing clear-all; clear-all permanently deletes all four local IndexedDB stores in the current browser profile.
- Keep Google Colab disconnected. Do not create notebooks, connect runtimes, submit jobs, or start model training. Server connection is deferred until the AI model is ready.
- Do not change Supabase RLS, secrets, Auth provider settings or owner records as part of frontend verification.
- Update this README at the next meaningful milestone.


## Learning page simplification — 2026-11-24

- Removed the fixed local arithmetic exercise card (question, answer field, answer checking, hint and next-exercise controls) from Learn & Practice.
- Reframed that page as the mathematics topic roadmap: topic descriptions, prerequisites, representative examples and available/planned status remain.
- Updated the Overview quick-access card to lead to Mathematics Topics instead of the removed practice exercise.
- Removed the now-unused exercise fixtures, event handlers and practice-only imports from the browser entry module.
- Existing IndexedDB experience/mistake history and backup tools remain intact; this UI change does not delete browser data. Existing local practice counters are left untouched rather than destructively clearing user preferences.
- No backend, Supabase, owner authentication, Colab connection, remote execution or model-training behavior changed.
