# ULTRON pre-training readiness plan

**Status:** planning and implementation checklist; not a training authorization.
**Model size:** minimum **40,000,000 trainable parameters**. The earlier 3–5M target is retired.
**Budget:** $0 planned compute; free-tier capacity must be verified at time of use.
**Workflow:** website-first, iPad-compatible; no actual training until the final gate is approved.

## Phase 1 — Project specification

- [ ] Define first-release mathematical capabilities and unsupported scope.
- [ ] Distinguish deterministic math operations, learned outputs, conjectures, and verified proofs.
- [ ] Preserve from-scratch constraints: no pretrained weights, pretrained models, external AI APIs, or externally generated training corpus.
- [ ] Document the initial curriculum and evaluation tasks.
- [ ] Specify model architecture before implementation; calculate the exact trainable parameter count and verify it is at least 40M.
- [ ] Estimate weights, gradients, optimizer state, activations, batch memory, checkpoint size, and runtime requirements.
- [ ] Specify data-generation, validation, checkpoint, and recovery interfaces.
- [ ] Keep actual training and remote execution disabled until separate authorization.

**Exit criteria:** a reviewed specification, architecture document, parameter-count calculation, resource estimate, and explicitly bounded capability list.

## Phase 2 — Website completion and acceptance

### Functional acceptance
- [ ] Verify all navigation routes and fallback/error states.
- [ ] Verify overview status is truthful and does not imply a trained model.
- [ ] Test supported and unsupported Math Agent inputs, invalid expressions, zero division, and equation edge cases.
- [ ] Verify user-triggered Save to memory, retry, Memory Vault display, JSON export/import, and local-only persistence.
- [ ] Verify server directory failure states do not invent provider availability.
- [ ] Verify settings persist and accurately describe the workload slider as a preference—not actual RAM allocation.
- [ ] Verify owner sign-in, refresh, sign-out, and server-side owner rejection for non-owners.
- [ ] Verify no public signup and no public training/remote execution controls.

### iPad/browser acceptance
- [ ] Test Safari on iPad in portrait and landscape.
- [ ] Test touch navigation, on-screen keyboard, focus, scrolling, and long math input.
- [ ] Test page refresh, tab close/reopen, IndexedDB persistence, and backup/restore.
- [ ] Test responsive layout, contrast control, and accessible status/error announcements.
- [ ] Record manual test date, browser/device, pass/fail, and unresolved defects; do not mark untested items as passed.

**Exit criteria:** automated tests pass, manual iPad acceptance is recorded, and no critical frontend defect remains. GitHub Pages CI alone is not evidence of manual Safari acceptance.

## Phase 3 — Security audit

- [ ] Review exposed Supabase tables, RLS policies, grants, and access paths.
- [ ] Review every Edge Function's authentication, owner authorization, input validation, rate limits, timeouts, and error handling.
- [ ] Verify owner identity is checked server-side; never trust a client flag or local storage as authorization.
- [ ] Verify no service-role/secret key is shipped in static frontend assets or committed.
- [ ] Verify public status endpoints are read-only and cannot invoke owner actions.
- [ ] Test unauthenticated, non-owner, expired-session, malformed-input, oversized-request, and network-failure cases.
- [ ] Review logs and responses for secret or personal-data leakage.
- [ ] Ensure training endpoints/jobs remain disabled and cannot be started by page load, public users, or UI-only state.
- [ ] Record findings by severity, fix blocking findings, and add regression tests.

**Exit criteria:** no unresolved critical/high severity finding; authorization and fail-closed tests pass; security review is documented. This checklist does not replace a live review of deployed Supabase policies/functions.

## Training-readiness gate (not yet approved)

Training remains blocked until Phases 1–3 are completed and reviewed, then the model, independent data generator, training loop, benchmarks, checkpoint/recovery, and approved free runtime are separately implemented and validated. A 40M parameter count alone does not establish readiness. Start training only after an explicit authorization step.

## Next-chat handoff

1. Complete Phase 1 specification and update the README whenever a milestone changes.
2. Work on Phase 2 website issues in a dedicated PR; preserve owner sign-in and account-free public browsing.
3. Perform Phase 3 security review without exposing secrets or changing production Supabase settings without a verified need.
4. Run Node tests and Python core tests appropriate to changed files; report actual CI outcomes.
5. Do not start training, optimizer steps, corpus generation, or remote jobs.
