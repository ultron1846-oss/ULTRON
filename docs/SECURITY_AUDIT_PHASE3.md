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


## Follow-up live verification — 2026-11-26

A read-only follow-up was performed against the active `ultron-memory` project after the previous mitigation. No table rows were read or changed, and no schema or Auth settings were mutated.

### Database policy and privilege results

- All nine tables in the `public` schema inspected in this check have RLS enabled.
- The six owner-linked data tables (`experiences`, `knowledge`, `mistakes`, `checkpoints`, `backups`, and `memory_imports`) each have an `authenticated` owner policy with both `USING (auth.uid() = user_id)` and `WITH CHECK (auth.uid() = user_id)`.
- The `anon` role has no SELECT privilege on any of the nine inspected public tables.
- `authenticated` has no TRUNCATE privilege on any of the nine inspected public tables. This re-confirms the earlier six-table revocation.
- The only `SECURITY DEFINER` function found in the `public` schema is `rls_auto_enable`; the current privilege check returned no EXECUTE privilege for `anon` or `authenticated`.
- The three retired pairing/device tables remain RLS-enabled and inaccessible to `anon` and `authenticated`. They have no policies; the advisor finding is informational and should not be “fixed” by adding broad policies.

### Current deployed Edge Function review

- `training-control` is deployed as version 8. The public `public_status` action requires the publishable API key, accepts only the configured GitHub Pages Origin, limits the body to 4 KiB, and returns generic untrained/training-disabled/remote-execution-disabled status.
- Owner-only actions require a bearer token and API key, validate the token with Supabase Auth, and compare the verified user ID to the server-side owner secret. Its `start` action dispatches the configured CPU diagnostic workflow only; the reviewed workflow installs CPU PyTorch and does not start model training or touch checkpoints. The public static site exposes no owner controls.
- `device-control` is deployed as version 4 and returns HTTP 410 for all requests; it cannot create pairing credentials or accept heartbeats. Its CORS origin still references the retired Pages domain, but the endpoint is fail-closed and has no active action. Do not re-enable pairing.

### Current security advisor results

The 2026-11-26 security advisor returned:

- **WARN:** leaked-password protection is still disabled. This is an Auth dashboard setting, not a repository or SQL change. Owner action remains required: enable Supabase Auth leaked-password protection and verify it in the dashboard, then re-run security advisors.
- **INFO (3):** RLS enabled without policies on the three retired pairing/device tables listed above. These are intentionally inaccessible and should remain fail-closed.

Remediation reference: [Supabase leaked-password protection](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

The security advisor was re-run after the read-only policy review. No data or configuration changes were made during this follow-up.
