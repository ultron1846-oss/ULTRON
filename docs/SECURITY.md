# ULTRON focused website and runtime security review

**Review date:** 2026-11-28  
**Scope:** Static GitHub Pages frontend, browser runtime/configuration contract, public Supabase status integration, deployed Edge Function metadata/source available through the connected Supabase project, repository CI workflows, direct dependency declarations, and current tracked frontend source.

This is a focused engineering review, not a penetration test, complete source-history secret scan, formal dependency-license inventory, or security certification.

## Executive findings

- The website requires no login or sign-up. No public account-specific training history, checkpoint actions, pairing UI, or training job mutation controls are present.
- The browser calls the same-origin servers.json manifest and the fixed Supabase training-control public_status action. It does not invoke an external AI API or dispatch a model-training job.
- The RAM control is a requested workload memory budget saved in this browser. It does not reserve or limit physical RAM, GPU VRAM, or a hosted runner.
- Generic status has fresh, stale, offline, and unavailable states, retains the last successful response with an age, times out, and refreshes periodically only while a status page is active.
- Provider manifest values are schema-validated before rendering. Links must be HTTPS and directory entries must keep execution disabled.
- External Google Fonts import was removed. The site now uses system fonts.
- A pinned TypeScript development dependency, npm lockfile, pinned Python test dependencies, automated npm/pip advisory checks, Dependabot updates, and a focused static browser-source scan have been added.
- Supabase still has owner-side configuration findings (below). No production Supabase settings, Edge Functions, tables, or policies were modified during this review.

## Browser network and execution boundary

| Browser surface | Current behavior | Security boundary |
|---|---|---|
| servers.json | Same-origin GET with cache: no-store | Parsed with strict schema-v1 provider-directory validation; unknown fields, invalid HTTPS URLs, duplicate IDs, and execution-enabled providers are rejected. |
| Supabase training-control | POST to one fixed endpoint with a publishable key and the public_status action | Generic service flags only. No Authorization bearer token, owner ID, checkpoint, job history, or provider credentials are sent. |
| Provider site hyperlinks | Open only after the user activates an official provider link | No automatic OAuth flow, notebook connection, data upload, runtime creation, or training dispatch. |
| Math and graph tools | Local deterministic browser code | No dynamic evaluation or external AI inference endpoint. Graph labels are XML-escaped before SVG insertion. |
| Memory Vault | Browser IndexedDB and bounded JSON import/export | No automatic Supabase upload or cross-device sync. Treat exported memory files as private user data. |

The browser status integration contains a publishable key (the browser-safe key type). It does not contain a Supabase service-role key, Supabase secret key, GitHub token, or owner ID. The GitHub integration token and owner identity are read by the Edge Function from server-side environment secrets; their values were not inspected or exposed by this review.

The public status function is deployed with verify_jwt=false, but its public public_status branch is intentionally generic and requires the publishable API key and an allowed Origin. Other deployed health, status, start, and stop actions manually verify a signed-in user and compare the user ID with a server-side owner ID before proceeding. The static website calls none of those actions and has no UI for them. CORS and a publishable API key are not authentication; the server-side owner check remains the actual owner-action boundary.

## Runtime status and resource contract

- A successful status response is displayed with its timestamp and age.
- A failed refresh preserves the last successful response but changes its state to stale; it is not relabelled as current.
- Offline devices display offline/stale status and send no status request until network availability returns.
- Status polling is bounded to a 60-second interval while the Training or Backend page is active, and stops when navigating away or when the document is hidden.
- Status requests still have a 10-second timeout in the Supabase client.
- The slider value is exported to the runtime configuration as a requested preference only. No runtime currently enforces it; no physical-memory guarantee is made.
- Provider directory entries are informational and always have execution_enabled=false.

## Input, rendering, file and serialization review

- The static math parser constrains expression length and token count and accepts only a documented grammar. It does not use eval or new Function.
- The graph parser restricts tokens/functions and escapes expression text before it is placed in SVG title/aria attributes.
- Dynamic text fields in status, provider directory and error messages use text nodes or the existing HTML-escape helper before templated rendering.
- Memory import is JSON-only, has an explicit byte/record bound, validates store names and record shapes, and writes through IndexedDB transactions. It is not a general-purpose object or executable-code deserializer.
- Backend status request bodies are bounded by the deployed Edge Function before JSON parsing. Error details returned to public clients are intentionally generic.
- Python checkpoint code uses checksum validation and torch.load with weights_only=true; this is outside the browser path but is part of the wider project serialization boundary.

## Secrets and repository permissions

- Added .gitignore entries for environment files, common private-key extensions, local secrets directories, generated model/checkpoint files, and local data artifacts. Ignore rules prevent accidental addition of untracked files; they do not remove already committed secrets or scan Git history.
- Added a focused static scan for common token/private-key patterns, unsafe dynamic-code primitives, known AI-provider API hosts, remote CSS imports, and unexpected browser fetch surfaces. This scan checks selected current frontend source files only. It is heuristic and is not a substitute for GitHub secret scanning, full Git-history scanning, or incident response.
- Current GitHub Actions workflows declare permissions: contents: read. The seed-data workflow is workflow_dispatch only, and its job requires both the explicit confirmation input and repository variable ULTRON_SEED_IMPORT_ENABLED == 'true'. It does not run on every push or pull request.
- The frontend Node dependency is pinned and locked. Python runtime constraints remain range-based because PyTorch wheel selection varies by CPU/CUDA environment; CI-only test packages are pinned separately. Weekly Dependabot checks are enabled for npm, pip, and GitHub Actions.
- GitHub Actions currently use version tags such as actions/checkout@v4 and actions/setup-python@v5, not full commit-SHA pins. Dependabot is enabled, but an action immutability/SHA-pinning pass remains a separate hardening item.

## Dependency and license review boundary

| Group | Declared dependency treatment | Review status |
|---|---|---|
| Browser build | TypeScript 5.8.3, exact version in package.json and package-lock.json; npm audit workflow | Locked; TypeScript package metadata identifies Apache-2.0. |
| Python runtime | torch>=2.2,<3.0 in requirements-ai.txt and pyproject.toml | Range-based, not a full hash lock. Wheel selection depends on target runtime. Audited by pip-audit in CI. |
| Python tests | pytest==9.2.0, sympy==1.14.0 in requirements-test.txt | Exact CI pins; audited by pip-audit. |
| Optional seed tooling | datasets>=3,<5, huggingface_hub>=0.27,<2 | Explicit optional requirements; audited by pip-audit. No seed data is downloaded by the security workflow. |

A top-level project LICENSE file was not found during this review. The transitive Python dependency license inventory has not been generated or reviewed in full. The project owner must choose the project’s distribution license and complete a transitive license/SBOM review before making a release or distribution claim.

## Live Supabase findings — owner actions required

The connected project was inspected read-only on 2026-11-28:

1. Project ultron-memory was ACTIVE_HEALTHY in the ap-south-1 region. This is database availability status, not a statement that all security settings are clean.
2. The security advisor reports auth_leaked_password_protection disabled (WARN). The current Supabase password-security documentation says this breached-password check is available on Pro and above. The organization is currently on the Free plan. The owner must decide whether to upgrade to a supported plan and enable the setting, or explicitly accept this limitation. No plan change or Auth configuration change was made. See [Supabase password security](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).
3. The security advisor reports three retired tables with RLS enabled but no policies: public.ultron_devices, public.ultron_pairing_challenges, and public.ultron_pairing_rate_limits (INFO). RLS without policies denies ordinary client-role access, but the owner should verify no trusted function or service-role workflow still depends on these tables, back up any needed data, and then decide whether to remove them or add explicit deny policies. This review did not alter the database.
4. Deployed device-control reports ACTIVE in Supabase metadata, but its deployed handler always returns HTTP 410 and rejects pairing/heartbeat work. Its CORS allow-origin still points to the retired shayaanfarsheed-cmd.github.io site rather than the current ultrron1846-oss.github.io site. The handler is fail-closed; the owner should decide whether to decommission the function and its unused tables after dependency review.
5. Deployed training-control is version 8 with verify_jwt=false and manual user/owner validation for non-public actions. Its owner-only start action references .github/workflows/cpu-diagnostic.yml, which was not present in the current repository workflow directory at review time. The owner should decide whether to restore/replace that diagnostic workflow or retire those legacy actions. The public website does not call them.
6. Verify GitHub secret-scanning and push-protection settings in repository settings; their enablement could not be confirmed through the available repository interface.

## Owner acceptance still required

- Test the deployed site in actual iPad Safari in portrait and landscape, including mobile navigation, touch targets, status offline/reconnect behavior, and local export/import. Automated tests cannot substitute for real-device browser acceptance.
- Decide on Supabase Pro+ leaked-password protection or record acceptance of the Free-plan limitation.
- Review/retire the three RLS-protected pairing/device tables after checking dependencies and backups.
- Decommission or formally retain the HTTP-410 device-control function; reconcile its stale CORS origin if it remains deployed.
- Resolve the stale owner-only CPU diagnostic workflow reference.
- Choose a project license and complete transitive dependency license review.
- Review GitHub secret scanning/push protection and consider pinning GitHub Actions to full commit SHAs.

No training job, optimizer step, corpus generation, Supabase mutation, production deployment, or external AI API call was performed for this review.
