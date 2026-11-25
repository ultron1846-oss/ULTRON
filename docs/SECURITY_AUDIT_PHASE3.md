# Phase 3 — Supabase and frontend security audit

**Review date:** 2026-11-25 (live read-only inspection plus one privilege-revocation mitigation)
**Project:** `ultron-memory` (`euhmejpaswmdpsutbtse`)
**Scope:** exposed public tables, RLS policies/grants, Supabase security advisors, deployed Edge Function contracts, and the public static frontend. No row data was read or changed. No secrets or owner identifiers are recorded here.

## Findings and disposition

### HIGH — authenticated role had TRUNCATE on six owner-linked tables

The live privilege check showed `authenticated_can_truncate=true` for `experiences`, `knowledge`, `mistakes`, `checkpoints`, `backups`, and `memory_imports`. RLS does not apply to `TRUNCATE`, so row ownership policies cannot prevent a signed-in role from truncating a whole table.

**Mitigation applied:** revoked `TRUNCATE` from `authenticated` on those six tables. A separate post-change query confirmed `authenticated_can_truncate=false` and `anon_can_truncate=false` for all six. No rows were deleted, no tables were dropped, and no data migration was run. The SQL is retained in [the repeatable safeguard](security/revoke_authenticated_truncate.sql).

### INFO — three retired device/pairing tables have RLS enabled without policies

`ultron_devices`, `ultron_pairing_challenges`, and `ultron_pairing_rate_limits` have RLS enabled and no policies. The inspected role grants did not show anon/authenticated TRUNCATE access. This is fail-closed for ordinary Data API row access and is consistent with retired pairing functionality; do not add broad policies just to silence the advisor. The deployed `device-control` Edge Function returns HTTP 410 and states pairing is retired.

### WARN — Supabase Auth leaked-password protection is disabled

The live security advisor reported leaked-password protection disabled. This cannot be changed through a repository PR. Owner action required in Supabase Dashboard: Authentication → Settings / Password security (label may vary) → enable leaked-password protection, then save and verify the setting. No password or user records were accessed.

## Edge Function review

### `training-control`

- Supabase JWT gateway verification is configured off, but the function manually requires a bearer token and API key, validates the token with Supabase Auth's user endpoint, and compares the returned user ID with the server-side `ULTRON_OWNER_USER_ID` secret.
- The function restricts browser Origin to the GitHub Pages origin, accepts POST/OPTIONS, caps request bodies at 4 KiB, parses JSON fail-closed, and returns generic errors.
- Public `public_status` returns generic prototype/untrained/training-disabled/remote-execution-disabled status and no owner telemetry or credentials.
- Owner-only `start` dispatches the configured CPU diagnostic workflow only; the reviewed branch states it installs CPU PyTorch and does not start model training or touch checkpoints. It checks for an active run before dispatch. This is a diagnostic remote job, not model training.
- The GitHub token is read from Edge Function secrets and is not returned to the browser.

### `device-control`

- Deployed function is retired and returns HTTP 410; no pairing, credential creation, or heartbeat path remains active.

## Frontend review

- Static frontend uses a publishable Supabase key only; no service-role or secret key was found in the inspected client files.
- Owner sign-in verifies identity through the protected Edge Function; browser session storage is not treated as authorization.
- Public frontend does not directly invoke owner-only control actions.
- Public signup remains absent.
- Training remains disabled in the public UI and no training implementation was added.

## Regression and verification

- SQL mitigation was applied once and verified with `has_table_privilege(..., 'TRUNCATE')`: six of six target tables returned false for authenticated and anon.
- Existing owner-linked tables retained RLS and `auth.uid() = user_id` policies with both `USING` and `WITH CHECK`.
- Node tests in this PR cover the public frontend security contract and the repeatable SQL safeguard. They do not replace live database checks or a manual dashboard confirmation.

## Remaining action

Enable Supabase Auth leaked-password protection in the dashboard and verify it is active. Re-run security advisors after that change. Do not enable device pairing or training as part of this audit.
