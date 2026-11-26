# ULTRON — Mathematics Intelligence Workspace

> **Current access model (2026-11-25):** Public browsing does not require an account. Optional Owner Sign-in is retained for the existing Supabase email/password account; there is no public sign-up. Owner privileges are verified by the Edge Function against the configured owner identity. No pairing UI or account-specific training history/checkpoints are exposed. Training and remote execution remain disabled.

ULTRON is an independent, local-first mathematics workspace under development. Its long-term goal is an original mathematics intelligence system. The current website is a static frontend and deterministic foundation prototype—not a trained AI model.


## Optimization milestone — causal SDPA mask memory (PR in review)

ULTRON's causal attention now uses PyTorch scaled-dot-product attention with the existing fused Q/K/V and output projection weights. Unpadded sequences use the built-in causal flag rather than materializing a quadratic boolean mask; padded sequences preserve the combined causal and key-validity mask. Checkpoint parameter naming is retained. Output and input-gradient parity tests are included. This removes one explicit O(sequence_length²) mask allocation on the unpadded path; no target-hardware speed or peak-memory result has been measured. No training or dataset generation was performed.

## Current continuation handoff — pre-training readiness

The latest code review fixed shared fast-memory contamination risk: training-time writes reject batches containing multiple independent examples, and the model exposes `reset_memory()`. The bounded trainer resets memory at batch boundaries and rejects memory-writing mode until sequential chunk semantics exist. Its checkpoint callback now carries global step and the next-batch cursor; the caller must restore the sampler/iterator from that cursor. CI uses only a mock optimizer; no real weights were updated.

Phase 9 provider research is updated with current official Colab, Lightning AI, and Hugging Face ZeroGPU limits. Actual Colab access and checkpoint-transfer acceptance still require the owner on iPad. The bounded local controller is implemented but only tested with a mock optimizer; PR #60 hardens preflight/resource checks and disables unsupported memory-write training. Next: expand the restricted exact polynomial identity verifier and broader independently validated university-math tasks; complete owner-side sampler restoration/clean-runtime resume acceptance and iPad/Colab checks. The CPU benchmark is only a small-model harness smoke, not a foundation baseline. The Phase 5 corpus coverage report is complete, but current generator coverage remains narrow. Keep real-weight training and remote execution disabled.

## Pre-training readiness — Phase 1 specification

The current model specification sets a **minimum of 60,000,001 trainable parameters (strictly greater than 60 million)**. The previous 3–5M prototype target is superseded. Architecture, parameter count, and resource estimates must be documented and verified before training. See [the phased pre-training readiness plan](docs/PRETRAINING_READINESS.md).

## Foundation model sizing — Phase 4

The repository now defines a proposed foundation configuration of **63,400,451 total parameters, of which 61,826,048 are trainable**, exceeding the >60M trainable minimum. The exact count is computed without allocating the large model and cross-checked against a small instantiated model in tests. The configuration has not been trained. See [foundation architecture and resource budget](docs/FOUNDATION_MODEL_SPEC.md).

Source review: ULTRON has an untrained model prototype, a narrow deterministic generator, loss/optimizer helpers, checkpoint utilities, and a bounded local training controller. The controller has only been tested with a mock model/optimizer; no real weights have been updated and the full resume controller remains incomplete. Training remains disabled.

## Phase 5 — data integrity hardening

The deterministic generator now covers arithmetic, rational arithmetic, simple linear equations, polynomial derivatives (degree 2–5), definite polynomial integrals (degree 1–4), 2x2 determinants, and unique 2x2 linear systems. It still does not cover university mathematics broadly. Phase 5 adds deterministic prompt-disjoint train/validation/test splitting, duplicate-prompt collapse, strict manifest schema checks, and recomputation of each example ID from its content. This is dataset infrastructure only; no training corpus was generated or training started.

The foundation config now binds to the canonical 240-token math vocabulary instead of the initial 256-token placeholder. The revised exact count is **63,400,451 total / 61,826,048 trainable**. Fast-memory key/value/gate projections are frozen because their updates are detached and they receive no gradients.

## Phase 6 — training preflight (validation only)

Added `ultron_core/preflight.py` and a bounded training controller. The controller requires explicit authorization, a complete non-authorizing preflight report, a budget covering persistent state, matching batch/sequence/accumulation limits, the >60M trainable floor, memory reset, finite loss/gradient checks, gradient accumulation/clipping, cancellation, and step/time caps. Memory writing defaults off. CI exercises only a mock model/optimizer; no real weights were updated. Live resource monitoring remains pending.

## Model review — fast-memory isolation

The code review identified that fast/episodic memory is mutable and shared by the model. Training-time memory writes now reject batches containing multiple independent examples, and `NeuroSparseModel.reset_memory()` clears every block's memory between examples. This prevents accidental cross-example contamination when the future trainer uses memory writes. The trainer is not implemented yet and must call the reset boundary explicitly; no training was run.

## Phase 8 — checkpoint recovery hardening

Checkpoint format v4 records Python/Torch RNG state and optional data cursor bound to a dataset manifest SHA-256, retains the last verified backup, and rolls back model/optimizer/scheduler/RNG state on restore failure. The loader rejects a mismatched expected dataset hash before mutation. The trainer carries global step and next-batch cursor through checkpoint callback metadata; `ResumableRandomSampler` now provides a deterministic epoch/sample cursor bound to the dataset manifest, with exact permutation-tail restore tests. The public Training Control page displays generic public status and readiness blockers, with all job controls disabled and no execution handlers. The bounded trainer accepts the DataLoader's `ResumableRandomSampler`, restores its checkpoint state before iterator creation, and includes sampler state in checkpoint callback/final metadata. It validates dataset hash/size, preflight batch size, sample-vs-batch cursor alignment, `num_workers=0`, and `drop_last=False`; it rewinds sampler state when partial accumulation is discarded. The notebook caller still must construct the sampler/DataLoader and save callback `data_state`. This is infrastructure validation only; no real-weight optimizer step or training run occurred.

## Phase 7 — exact-answer evaluation

Added schema-v3 exact-answer evaluation for caller-supplied predictions on the current generated topics. It reports attempted coverage, valid-answer rate, abstentions, malformed outputs, incorrect valid answers, and mutually exclusive error classes globally and per topic. Rational/integral/determinant outputs use exact fractions; polynomial derivatives use exact coefficient-map equivalence; 2x2 system outputs use exact rational-pair parsing. It does not run a model or validate proofs. See [math evaluation protocol](docs/MATH_EVALUATION_PROTOCOL.md).

## Phase 9 — free runtime review

Official provider terms have been reviewed and documented. Colab remains the planned primary notebook with dynamic, unguaranteed free resources; Lightning AI is excluded under the current phone-verification constraint; Hugging Face ZeroGPU offers only short shared free quota and is auxiliary for brief checks, not dependable training. Actual iPad account/runtime acceptance remains owner-side and incomplete. See [free runtime review](docs/FREE_RUNTIME_REVIEW.md).

Phase 6 also now provides explicit Python/Torch/CUDA seeding and a dedicated seeded DataLoader generator. Reproducibility is tested independently; deterministic algorithms may still depend on supported hardware/operators and must be recorded.

Phase 8 binds resumable data cursors to a validated dataset-manifest SHA-256 in checkpoint format v4. The restore guard rejects a mismatched expected dataset hash before mutating model/optimizer/RNG state; older checkpoint formats remain loadable but cannot satisfy a dataset-bound resume.

Checkpoint resume now returns whether RNG restoration succeeded. The trainer refuses resume without restored RNG, data cursor, and a matching dataset-manifest SHA-256; it skips initial reseeding on resume so checkpoint RNG is preserved.

Generator v0.4.0 adds independently validated 2x2 matrix determinants and unique 2x2 linear systems with exact rational solutions. The complete current generator has seven narrow exact-synthetic topics; these additions are introductory linear algebra exercises, not broad university-math capability.

## Frontend status

The frontend retains the optional Owner Sign-in page. Public browsing still loads without an account; there is no public sign-up or public/private access-mode toggle. The Supabase page provides generic service status, while protected owner actions remain server-verified.

The frontend includes startup/navigation resilience, visible render-error recovery, cache-busted modules, actionable overview status and quick links. A successful automated build does not replace full iPad browser verification.

## Frontend hardening milestone — workload preference validation

The settings and overview now normalize the stored workload preference to the supported 2–10 GB range and fall back to 6 GB when browser storage contains an invalid, non-finite, or empty value. This remains a local preference only, not a RAM allocator. Unit tests cover valid, fractional, out-of-range, and malformed values. Manual iPad Safari acceptance is still required before declaring the frontend fully complete.

## Phase 3 security audit — 2026-11-25

A live Supabase review found authenticated-role `TRUNCATE` privileges on six owner-linked tables, which bypass RLS. The privilege was revoked and verified false for authenticated/anon on all six tables; no data was changed. The audit and repeatable safeguard are documented in [Phase 3 security audit](docs/SECURITY_AUDIT_PHASE3.md). Supabase Auth leaked-password protection remains disabled and requires an owner dashboard setting change.

## Frontend release gate

The public frontend, optional owner sign-in, required root assets and deployment-path cleanup are covered by automated regression tests. Before calling the frontend fully complete, perform the real iPad Safari acceptance pass: open every page, test owner sign-in/sign-out and server-side owner verification, exercise mobile navigation and contrast, run supported/unsupported Math Agent inputs, verify IndexedDB history and backup/restore, and check the workload slider. Do not start training or connect a cloud runtime during this pass.

The frontend uses the supplied ULTRON control-room reference: near-black surfaces, crimson accents, a compact top header, left navigation, bordered panels and responsive tablet/mobile layouts.

### Current pages
- **Supabase backend:** refreshable, bounded-time read-only status check with visible last-checked time, plus an audit of deployed Edge Function contracts and backend security findings. It never calls owner-only services from the public site.
- **Overview:** honest system status, model/training state, capability summary, roadmap and quick links to current pages.
- **Mathematics topics:** curriculum roadmap with descriptions, prerequisites, representative examples and explicit available/planned status. The former fixed exercise card and its answer/hint/next controls have been removed.
- **Math Agent:** browser interface to the deterministic arithmetic parser and limited linear-equation solver; supported answers have an explicit Save to memory action, and unsupported requests are rejected rather than guessed.
- **Memory vault:** IndexedDB stores saved Math Agent answers and existing experiences/mistakes locally, with JSON export/import for manual device-to-device transfer. Saves are user-triggered; this is not cloud sync.
- **Servers & Colab:** reads `servers.json`, handles missing/malformed directory data and never starts remote jobs.
- **Settings:** stores a preferred future workload memory budget locally; it does not allocate device or remote memory.
- **Owner sign in:** optional email/password sign-in for the existing owner account; no public registration.

The frontend intentionally does not claim a general AI assistant, general symbolic algebra, a proof checker, a trained neural model or active training. The Math Agent currently supports only its documented deterministic arithmetic and limited linear-equation operations.

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
- Public browsing requires no account. The optional owner sign-in uses the existing Supabase email/password account; public registration is not exposed. Owner-only actions are revalidated server-side.
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

Target URL: `https://ultron1846-oss.github.io/ULTRON/`. The repository uses GitHub's built-in Pages branch deployment, which successfully published the frontend with optional owner sign-in. The redundant custom `.github/workflows/pages.yml` workflow was removed because it repeatedly uploaded an artifact that the subsequent deploy step could not find, while the built-in `pages build and deployment` workflow succeeded for the same main commit.

Keep the required runtime assets in the repository root: `index.html`, `styles.css`, `app.js`, `math-engine.js`, `supabase-integration.js`, `memory-store.js` and `servers.json`. Regression tests verify they exist and are non-empty. Do not reintroduce a second deployment workflow unless its artifact handoff is independently validated.


## Supabase integration audit

The connected Supabase project `ultron-memory` was inspected directly. It was `ACTIVE_HEALTHY` at inspection time. Its memory tables and `training_api` tables remain owner-linked and protected by row-level security; the public website does not query those records.

- `device-control` remains retired and returns HTTP 410.
- `training-control` is deployed at version 8. Its GitHub repository target is `ultron1846-oss/ULTRON`, and its allowed browser origin is `https://ultron1846-oss.github.io`.
- A `public_status` action is available without a user session. It returns only generic service state, model status, and explicit training/remote-execution disabled flags. It does not return owner IDs, run metadata, memory records, provider credentials, or secrets.
- The Edge Function platform JWT check is disabled so the public status action can be called from the public site. Every existing protected action still performs its own bearer-token verification and owner-ID check inside the function. The public status page calls only `public_status`; owner sign-in remains separate.
- The frontend uses the Supabase publishable key in the `apikey` header. No service-role key, secret key, GitHub token, or owner credential is included in the repository.
- No database schema, RLS policy, user record, or secret was changed. The Edge Function code was updated; training remains disabled and no training job was started.
- Security advisors also reported three RLS-enabled retired device/pairing tables with no policies, disabled leaked-password protection, and several unindexed foreign keys. These are separate database-hardening items; the public status endpoint does not expose those tables.

## Owner authentication — retained

The optional owner sign-in is retained in the frontend. It uses the existing Supabase email/password account, supports session refresh and sign-out, and does not expose public registration. Authentication alone does not grant owner privileges: the page calls the `training-control` `health` action with the bearer token, and the Edge Function verifies the authenticated user ID against the server-side `ULTRON_OWNER_USER_ID` secret. Non-owner users are rejected. The publishable key is the only key included in browser code. No Auth provider settings, user records, secrets, RLS policies or database data were changed. Owner sign-in does not start training or remote jobs.

## Supabase frontend integration audit — 2026-11-24

The live project was re-inspected while aligning the backend page with the rebuilt frontend. The project is `ACTIVE_HEALTHY` in `ap-south-1`. The public page calls only `training-control` with the `public_status` action, the publishable key in the `apikey` header, no owner bearer token, and a 10-second request timeout. The response is validated to require an online control plane, training disabled, remote execution disabled, and an informational-only provider directory. The page exposes a manual refresh and last-checked timestamp.

The deployed `training-control` function is version 8 with platform JWT verification disabled so the unauthenticated public status request can reach its handler. The handler returns only generic status for `public_status`; its other actions continue to validate a signed-in owner session and configured owner ID. The deployed `device-control` function is still listed as active/version 4, but its handler is fail-closed and returns HTTP 410 for every request. It is retired, not physically removed.

All nine inspected public tables had RLS enabled. The security advisor reported three RLS-enabled retired device/pairing tables with no policies, and warned that leaked-password protection is disabled. Those findings are documented for backend hardening; this frontend PR does not alter database schema, policies, Auth settings, Edge Functions, secrets, or records. The website does not access any of those tables.

## Backend handoff / remaining work

Next implementation work should:
1. Maintain and test the deterministic math engine API without breaking the frontend imports.
2. Maintain the documented `servers.json` provider schema and verify Colab terms and quotas before any future runtime integration.
3. Keep all training entry points hard-disabled and add backend regression tests preventing accidental execution.
4. Keep cloud memory synchronization separate from the local Memory Vault. Do not expose owner-linked tables to the public website; propose an explicit anonymous-device identity and threat model before any cloud-sync change.
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
1. Confirm the latest `main` commit is the deployed GitHub Pages version.
2. On iPad Safari, test navigation and every page: Overview, Mathematics Topics, Math Agent, Memory Vault, Servers & Colab, Supabase Backend and Settings.
3. Test supported Math Agent inputs and unsupported-input handling; the removed fixed exercise card must not reappear.
4. Test Memory Vault history, JSON export/import and clear-all only after exporting any data you want to keep.
5. Test the workload preference slider and verify it is clearly described as a saved preference, not actual memory allocation.
6. Verify the public Supabase status refresh; test owner sign-in/sign-out and confirm non-owner accounts are rejected by server-side verification. Confirm there is no public sign-up or pairing UI.
7. Keep actual model training, Colab connection and remote execution disabled until separately authorized.

## Project rule
A polished interface must not imply functionality that has not been implemented. Training remains disabled absent separate explicit authorization.


## Owner sign-in correction — 2026-11-25

Owner sign-in remains an optional existing-account feature. The public access-mode badge is removed, but the Owner Sign-in navigation and `owner-auth.js` module are present. Do not add public sign-up, pairing, or account-specific training history/checkpoint UI. Keep owner identity verification on the Edge Function; do not treat a successful Supabase login alone as owner authorization.


## Frontend completion hardening — 2026-11-24

This release pass closes several frontend reliability gaps while preserving the no-training/no-server-connection boundary:

- The built-in GitHub Pages deployment serves the root runtime assets, including `owner-auth.js` for the optional Owner Sign-in page.
- Navigation exposes the active page to assistive technology. The mobile menu closes with Escape, after navigation, and when the user taps outside it. The contrast preference persists in the current browser.
- The Memory Vault separates recent experiences from incorrect attempts, provides an explicit confirmed clear-all action, and reports storage failures honestly. Export URL cleanup is delayed so mobile browsers have time to start the download.
- IndexedDB request helpers resolve only after the transaction commits. The local practice interface no longer hides a failed memory write behind a success message.
- Tablet/mobile styles account for safe areas and reduced-motion preferences.

Automated release checks cover the Pages runtime asset list, frontend module syntax, mobile navigation hooks, persisted contrast preference, and Memory Vault controls. These checks do not substitute for a live iPad Safari interaction test; that still requires a user-side browser test after deployment. The website has optional owner sign-in but no public sign-up. The browser auth module stores the session locally and never stores the password. No Supabase policies, secrets, Auth settings, provider connections, remote jobs or training behavior are changed.

## Next-chat handoff — frontend release

- Verify the deployed Pages build loads all pages, including Owner Sign-in. Confirm `owner-auth.js` is served from the repository root.
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
- No backend, Supabase, Colab connection, remote execution or model-training behavior changed; optional owner authentication remains available in the frontend.


## GitHub Pages deployment verification — 2026-11-24

The latest frontend commit `932fcf005d414fdd1338d4d58265afd9b8ed64c4` was checked against both Pages workflows. The repository's custom `Deploy static site to GitHub Pages` workflow successfully staged and uploaded the `github-pages` artifact, but its deploy step failed because GitHub could not resolve the artifact for that concurrent deployment. The built-in `pages build and deployment` workflow then completed its build, artifact upload and deploy jobs successfully for the same commit. Therefore the latest commit has a successful Pages deployment through the built-in workflow; do not interpret the custom workflow's failed run as proof that the site is offline.

The redundant custom deployment workflow has been removed in the frontend release PR. The built-in GitHub Pages deployment remains the single deployment path and has completed successfully for the merged frontend.

## Next-chat handoff — owner sign-in retention

- Latest merged change: PR #9, removing the fixed exercise interface and retaining the Mathematics Topics roadmap and existing local Memory Vault records.
- The latest main commit's GitHub Pages retry completed successfully. A first custom workflow attempt had a transient artifact lookup failure; the retry succeeded
- README content has been aligned to the current page structure and the removal of the fixed exercise interface.
- Perform the real iPad Safari page-by-page interaction test before declaring frontend completion. Automated checks do not simulate Safari's UI or IndexedDB behavior. Include owner sign-in/sign-out and server-side owner rejection of non-owner accounts.
- Do not connect Google Colab, start a server, submit remote jobs or train the model. The user explicitly deferred server connection until the AI is ready.
- Preserve Supabase RLS, server-side authorization, credentials and private records. Do not change Auth settings or secrets during frontend QA.
- Update this README at every meaningful milestone and leave a precise next-chat handoff.


## Original mathematical AI core — Section C prototype (2026-11-24)

An isolated Python/PyTorch research scaffold now lives in `ultron_core/`; it does not alter the JavaScript website, GitHub Pages runtime, Supabase, authentication, or existing browser memory. See [NeuroSparse implementation notes](docs/NEUROSPARSE_IMPLEMENTATION.md).

The prototype includes sparse top-k expert dispatch, bounded predictive latent refinement, fast-weight plus bounded episodic memory, a typed mathematical expression representation, seed formula candidates, finite-domain counterexample probing, checkpoint integrity helpers, and CPU/GPU smoke/profiling tools. These are experimental components, not a trained model, formal theorem prover, or demonstrated mathematical discovery system. The default expert selection ratio is 25%, not the proposed 2% target.

### Install and validate

Install a PyTorch wheel appropriate for the target CPU/CUDA device, then run:

```sh
python -m unittest discover -s tests/python -v
python -m ultron_core.smoke --device cpu --batch 2 --sequence 8
python -m ultron_core.smoke --device cuda --profile
```

GitHub Actions now runs the Python regression suite and a CPU forward/backward smoke check on pull requests and pushes to `main`. Smoke validation does not execute an optimizer step or start training. No training corpus, pretrained weights, external AI API, cloud job, or remote execution is used.

### Next-chat handoff — after Section C

1. Review the Section C pull request and inspect its Python CI result; run the same tests in a supported local CPU environment before making performance claims.
2. Review expert dispatch overhead, load-balancing behavior, fast/episodic memory semantics, checkpoint recovery, and profiler output. The current reference paths are not optimized GPU kernels.
3. Continue with deterministic original mathematical data generation, richer symbolic operations, and formal-verifier interfaces only after the user authorizes the next stage.
4. Keep the website, Supabase, authentication, Pages deployment, and provider integrations unchanged.
5. Do not start actual model training, cloud execution, or remote jobs without separate explicit authorization.
6. Continue only when the user says: `Continue to Section D`.


## Section D — benchmark and ablation protocol (2026-11-24)

Section D adds an inference-only benchmark harness and a controlled-experiment protocol. See [Section D benchmark protocol](docs/SECTION_D_BENCHMARK_PROTOCOL.md).

- Run `python -m ultron_core.benchmark --device cpu --batch 2 --sequence 16 --warmup 10 --iterations 50` for a repeatable CPU inference timing report. CUDA is optional and requires a compatible CUDA-enabled PyTorch installation.
- The JSON report includes raw latency samples, median/mean/standard deviation, a seeded bootstrap 95% interval for the median, throughput, parameter accounting, environment metadata and CUDA peak allocated memory when applicable.
- The benchmark is synthetic-input inference only. It does not train, perform optimizer steps, use external datasets or call external AI APIs.
- The default expert selection remains 2/8 = 25%. The reported active-parameter estimate is structural accounting, not measured FLOPs, hardware activity, latency or energy.
- Section D specifies a future ablation matrix, mathematical evaluation suite, paired statistical design, multiple-comparison correction and acceptance gates. The current Section C model does not yet expose the switches needed to execute those ablations.
- No performance improvement, quality result, energy reduction or mathematical capability is claimed from this harness.

### Next-chat handoff — after Section D

1. Review PR for the inference benchmark, its statistics tests, and the protocol document; inspect CI before merging.
2. Do not describe synthetic-token timing as a math capability benchmark. Do not report structural parameter estimates as measured FLOPs or energy.
3. Next engineering prerequisite is tested feature switches and a dense all-expert reference path, followed by per-token routing/refinement/memory instrumentation and the approved deterministic math-task generator.
4. Keep website, Supabase, authentication, GitHub Pages and provider integrations unchanged.
5. Do not start model training, connect Colab, launch remote jobs or use cloud compute without separate explicit authorization.
6. Update this README and retain a precise next-chat handoff at every meaningful milestone.


## Core code review and correctness hardening — 2026-11-24

A focused review of the merged Section C/D Python core identified and corrected these correctness issues in the follow-up code-review branch:

- The finite-domain probe now rejects empty sample sets, duplicate/invalid variable names, and candidates whose domain/assumption metadata it cannot interpret. It also refuses to return experimental support if every attempted point is undefined and zero valid points were evaluated.
- Predictive refinement now calculates its reported prediction error against the final latent representation actually returned, rather than the pre-update state from the last iteration.
- Benchmark percentile and bootstrap helpers now reject non-finite samples. Bootstrap interval endpoints use interpolated percentile estimates.
- Expert parameter accounting now identifies expert modules by type rather than a fragile class-name string.
- The causal next-token loss masks padding targets by default using `ignore_index=0`, supports an explicit alternate ignore index or `None`, and raises a clear error if every target is ignored.
- Regression tests cover these cases; the implementation notes document the limits of finite probing and padding-mask behavior.

### Remaining architectural blockers (not silently represented as fixed)

- Causal self-attention and learned positional embeddings are now implemented in the Python core. Remaining sequence-model gaps include padding key masks, tokenizer semantics, efficient decoding/KV caching, and long-context evaluation.
- The model still has no tested ablation controls or dense-expert reference path. A bounded exact polynomial-identity verifier has been added separately; ULTRON still has no general formal proof kernel.
- Memory writes are opt-in and sequential; ordinary forward calls do not update the memory. A future training controller must define safe, deterministic memory lifecycle semantics before relying on it.
- The finite-domain evaluator supports only its explicitly implemented rational arithmetic operations. It does not interpret domains/assumptions, and it cannot establish a theorem or mathematical novelty.

### Next code-review handoff

1. Review the correctness-hardening pull request and require Python CI plus existing Node CI to pass before merge.
2. Continue architecture work with an explicit tokenizer/math-aware token contract, padding/key-mask semantics, and deterministic original mathematical data generation; keep causal past/future regression tests.
3. Add property-based tests for symbolic expression evaluation, domain edge cases, checkpoint recovery, memory isolation and router load balancing.
4. Do not call this prototype an LLM or claim university-level math capability until causal sequence modelling, training, and independent mathematical evaluation have actually been implemented and validated.
5. No model training, optimizer steps, cloud jobs, Colab sessions, or remote execution are authorized by this review.


## Core performance optimization — 2026-11-24

- The memory module now skips key and value linear projections during read-only calls. Those projections are only required to update fast weights and episodic slots during a training-mode write.
- The optimization preserves the query projection and existing recall calculations; it does not change memory contents or checkpoint tensor shapes.
- Regression tests verify that read-only calls do not execute key/value projections, both before memory is populated and after a write has populated it. A write request in evaluation mode is also treated as read-only.
- No Rust/C++ rewrite was introduced. PyTorch already executes the tensor kernels in compiled native code; replacing Python orchestration with another language without a measured bottleneck would add complexity without a demonstrated speedup.
- No performance gain is claimed until the before/after benchmark is run on the intended CPU/GPU hardware. No training, optimizer steps, external data, cloud compute or remote jobs were run.

### Next optimization handoff

1. Run Python regression tests and CPU forward/backward smoke; run the inference benchmark before and after on the same device and environment to quantify impact.
2. Add profiler ranges for router dispatch, expert execution, predictive refinement and memory read/write; optimize only the dominant measured stages.
3. Compare eager PyTorch with optional torch.compile on representative batch/sequence sizes before considering custom C++/CUDA kernels or Rust orchestration.
4. Preserve model outputs, checkpoint compatibility and deterministic tests. Do not claim a speedup from fewer operations alone.
5. The major architecture prerequisite remains causal sequence mixing and positional information; performance work must not disguise the current prototype's lack of context-aware language modelling.
6. Keep frontend, Supabase and authentication untouched. Do not train or launch remote jobs without separate explicit authorization.


## Broader Python-core review — 2026-11-24

A second review pass hardened API boundaries and benchmark reproducibility:

- Configuration now requires true integer dimensions/token IDs (booleans and fractional numbers are rejected) and finite floating-point thresholds/dropout values.
- Router balance validation now rejects empty/oversized top-k dimensions, non-integer indices, device mismatches, out-of-range indices and duplicate expert assignments.
- Predictive refinement rejects malformed rank, empty batch/sequence dimensions and hidden-size mismatches with clear errors.
- The symbolic expression IR now validates node kinds, tuple structure, child node types, integer atoms without truncation, rational literals and symbol identifiers.
- Loss and optimizer helpers reject non-finite or malformed scalar hyperparameters.
- The inference benchmark now isolates its CPU random seed and restores the caller's CPU thread count, avoiding persistent global runtime side effects.
- New regression tests cover these invalid-input and state-restoration cases.

### Next-chat handoff — after core hardening

1. Review the open core-hardening PR and require both Python AI Core Tests and Node Tests to pass.
2. Re-run the CPU inference benchmark before/after on the same hardware if measuring performance; this change makes the harness less intrusive but does not itself claim a speedup.
3. Causal sequence mixing and learned positional information are now implemented on the architecture branch; review PR #16 and retain the context-influence and future-token-isolation tests.
4. Keep the symbolic evaluator's supported operations explicit; finite probes remain counterexample searches, never proofs.
5. No model training, optimizer steps, external datasets, cloud jobs, Colab sessions or remote execution are authorized by this review.
6. Keep website, Supabase, authentication and GitHub Pages unchanged. Update this README at every meaningful milestone.


## Checkpoint integrity review — 2026-11-24

- Checkpoint save now rejects fractional/negative/bool step values and mismatched model/config metadata instead of silently truncating or writing misleading metadata.
- Checkpoint load validates checksum-manifest syntax, payload mapping structure, non-negative step metadata, target-model configuration compatibility and optimizer-state presence before applying state.
- The checksum manifest is now written to a temporary file, flushed and fsynced, then atomically replaced. The checkpoint and manifest are still two separate files, so a process interruption between their replacements can leave a detectable mismatch; keep periodic independent backups.
- The SHA-256 sidecar detects accidental corruption only. It is not a digital signature and does not make untrusted checkpoints safe.
- Regression tests cover invalid steps and configuration mismatch.


## GPU execution-path optimization — 2026-11-24

- Removed two host-visible CUDA scalar checks per model forward: accelerator token IDs now rely on the embedding operator for index validation, while CPU inputs retain explicit min/max validation and the same clear error.
- The model's internal load-balance loss call now skips range/duplicate scans for router-produced top-k indices. The public helper defaults to full validation; its fast path is opt-in and used only where index provenance is known.
- Predictive refinement keeps CPU early exit but avoids converting CUDA activity masks to Python booleans each iteration, preventing repeated device synchronization. Accelerator execution uses the configured fixed refinement budget and masks inactive token states.
- Episodic memory writes now read the ring cursor once per forward and update it once after the sequential write loop, instead of reading/updating the scalar cursor for every token.
- Regression tests cover the routing fast-path contract; the existing memory ring-wrap test covers cursor correctness.
- These are synchronization/launch-overhead reductions, not measured speed claims. GPU benchmarks are still required on target hardware.


## Mathematical trust-boundary review — 2026-11-24

- Closed a trust-boundary gap: a caller could previously construct a candidate with FORMALLY_VERIFIED status and have can_enter_trusted_knowledge() return true without any proof checker.
- The method remains fail-closed for all candidates. A bounded exact polynomial-identity verifier now checks a narrow rational-polynomial grammar, but there is still no general proof kernel or trusted-knowledge receipt pathway. A status label or verifier result alone does not promote a candidate into trusted knowledge.
- Added a regression test showing that a caller-supplied FORMALLY_VERIFIED label cannot promote a candidate into trusted knowledge.
- Future trusted admission requires a structured proof receipt bound to the candidate and independently validated by the trust layer; do not restore status-only trust.


## Causal sequence architecture — 2026-11-24

The isolated Python research core now has causal sequence mixing and explicit token positions:

- Added pre-normalized multi-head causal self-attention to each NeuroSparse block, before sparse expert routing.
- Added learned absolute positional embeddings and a configurable maximum sequence length.
- Added configuration validation for attention-head divisibility and positive sequence/head dimensions.
- Added regression tests proving earlier context can influence later-token logits and future tokens cannot influence earlier-token logits.
- The model remains an untrained research prototype. This architectural milestone does not establish language competence, university-level mathematics, formula discovery, theorem proving, or performance superiority.
- No training loop, optimizer step, external dataset, pretrained weights, external AI API, cloud job, Colab runtime, or remote execution was used.

### Next-chat handoff — after causal sequence foundation

1. Review the causal architecture PR and require Python regression tests, CPU forward/backward smoke, and the existing Node.js test suite to pass.
2. Inspect the causal mask semantics and position-limit behavior. Preserve the tests that enforce past-context influence and future-token isolation.
3. Next architecture work should add a tokenizer/math-aware token contract and deterministic original math-data generation design, with exact schemas and tests before any training is authorized.
4. Add explicit padding/key-mask semantics before supporting variable-length padded batches; the current causal mask alone does not suppress padded key positions.
5. Do not claim long-context support, streaming inference, KV caching, FlashAttention, mathematical discovery, formal proof, or university-level math capability.
6. Keep frontend, Supabase, authentication, Pages deployment and provider integrations unchanged.
7. Do not start actual training, optimizer steps, Colab sessions, cloud jobs or remote execution without separate explicit authorization.
8. Update this README at every meaningful milestone.


### Checkpoint compatibility

The causal architecture changes model parameters and configuration metadata. Checkpoint serialization now uses format version 2. Older version 1 feed-forward-only checkpoints are rejected; there is no automatic migration. No trained checkpoint existed for this prototype at the time of the change.


## Checkpoint and verifier boundary review — 2026-11-24

A further Python-core review tightened two correctness boundaries:

- Checkpoint loading validates the entire model state dictionary—keys, tensor types, shapes and dtypes—before applying any parameter updates. A malformed checkpoint now fails before the target model can be partially changed.
- Finite-domain probes accept exact integer, rational-string and Fraction sample values only. Floating-point and boolean samples are rejected; equivalent rational values are normalized and duplicates rejected.
- Regression coverage verifies unchanged target weights after malformed checkpoint rejection and exact finite-domain sample behavior.
- No training, optimizer step, external dataset, pretrained model, external AI API, cloud execution or remote job was used.

### Next-chat handoff — after checkpoint/verifier hardening

1. Review PR for the checkpoint state preflight and exact rational-domain validation; require Python AI Core Tests, CPU forward/backward smoke and Node Tests to pass.
2. Preserve the fail-before-mutation checkpoint test and exact-domain verifier tests.
3. Continue the architecture roadmap with tokenizer/math-token semantics and deterministic original mathematical data generation. Specify formats and test generation determinism before considering training.
4. Keep the finite-domain evaluator explicitly limited; it searches finite points and cannot prove an identity or novelty.
5. Keep website, Supabase, authentication, Pages deployment and provider integrations unchanged.
6. Do not start training, optimizer steps, Colab, cloud jobs or remote execution without separate explicit authorization.
7. Update this README at every meaningful milestone.


- FormulaCandidate construction now validates expression/status types and requires immutable tuple-based metadata, closing another malformed-input path at the mathematical IR boundary.

- Checkpoint preflight also rejects tensor-layout mismatches, and its key-difference diagnostics safely handle malformed non-string keys.

- Finite-domain probing now has a configurable positive max_samples budget (default 100,000) and rejects Cartesian domains that would exceed it before evaluation.

- Exact exponent evaluation is also bounded (default absolute exponent 1,024) so finite probes cannot allocate unbounded rational integers from extreme powers.


## Mathematical tokenization and deterministic data foundation — 2026-11-24

The isolated Python core now has an initial, deliberately bounded mathematical input/data foundation. This is infrastructure only; it does not train the model or establish mathematical competence.

### Implemented
- `ultron_core/math_tokenizer.py` provides a deterministic version-1 lexical vocabulary with reserved PAD/BOS/EOS IDs, longest-match mathematical operator tokens, digit-level exact numeric spelling, Latin/Greek symbols, common superscript/subscript glyphs, delimiters and preserved whitespace.
- Tokenization is lossless for the explicitly supported lexical subset. Unknown characters fail with an offset; they are not silently mapped to an unknown token.
- Numeric values do not create per-literal vocabulary entries. For example, `2x`, `2*x` and `2 × x` remain distinct token sequences. The tokenizer preserves the source minus sign and does not infer whether it is unary or binary.
- Vocabulary serialization is deterministic JSON with a schema version and strict duplicate/reserved-token checks. The default vocabulary IDs are fixed by the source-defined canonical token order.
- `ultron_core/data_generation.py` creates original deterministic arithmetic, exact-rational arithmetic and one-variable linear-equation examples using a local seeded PRNG and Python `Fraction`.
- Each example carries a SHA-256-derived stable identifier, generator version, topic, difficulty, source/target text, exact answer, seed/index, generation parameters, validation status and provenance.
- The emitted text is checked by a separate strict regular-expression parser and exact-rational calculation path. This is an independent implementation path from the generator's arithmetic expression construction, but it is not a formal proof system.
- JSONL output and a deterministic manifest include schema/generator versions, seed, topic counts, example count and SHA-256 content hash. The writer uses temporary files and atomic replacement for each output file.
- The existing model now accepts an optional boolean `attention_mask` (`True` means a real token). Padding keys are blocked in every causal-attention layer; padded query outputs are zeroed after attention, and padded positions are excluded from optional episodic-memory writes. Entirely padded batch rows are rejected.
- The mathematical IR and exact evaluator now include binary subtraction and division, including explicit division-by-zero rejection.
- Mathematical expressions now have strict recursive dictionary serialization, canonical structural JSON and SHA-256 structural hashes. These hashes identify structure; they do not prove algebraic equivalence or canonicalize equivalent formulas.

### Explicit coverage limits
The tokenizer is a lexer, not a parser: it does not construct expression trees, infer implicit multiplication, resolve function names, interpret domains/assumptions, or validate mathematical meaning. Its current fixed vocabulary is a documented subset, not complete LaTeX or complete mathematical notation. Some calculus, linear-algebra, set, logic and proof symbols are lexically recognized, but this does not mean their semantics or operations are implemented. Unsupported characters fail closed.

The initial generator supports only integer arithmetic, exact rational arithmetic and simple one-variable linear equations. It does not yet generate calculus, matrices, eigenvalue problems, graph theory, proof derivations, conjectures or counterexamples. Those topics remain planned work. No large corpus was generated or committed.

The model consumes the tokenizer's integer IDs when configured with `vocab_size=len(MathVocabulary.default())`; no tokenizer is automatically attached to model construction. The attention mask is explicit and must be passed for padded batches. Right-padding is the intended common layout, but left-padding is guarded against all-masked query NaNs. No training, optimizer step, checkpoint creation, cloud execution or remote job was performed.

### Validation status
The new Python regression module covers token round trips, stable vocabulary serialization, lexical errors, exact rational checking, deterministic seeds/IDs, JSONL/manifest reproducibility, tokenizer-to-model input compatibility, variable-length batches, padding isolation, memory-write masking and structural IR serialization. GitHub Actions for PR #18 passed all 88 Python regression tests, the CPU forward/backward smoke check, and the Node.js test suite. The smoke check did not perform an optimizer step or training run. The repository was inspected through GitHub's repository interface; this environment could not clone GitHub for local execution, so local test execution has not been claimed.

### Merged delivery
- [PR #18](https://github.com/ultron1846-oss/ULTRON/pull/18) merged successfully. Main commit: `38a4b30c28f90998ac5f092fe340df512963fdfc`.
- PR checks: 88 Python tests passed; CPU forward/backward smoke passed; Node tests passed. No training, optimizer step, external dataset/API, cloud job or remote execution was used.

### Next engineering handoff
1. Review this branch and require the Python AI Core Tests, CPU forward/backward smoke and Node Tests to pass in GitHub Actions.
2. If a CI failure occurs, inspect the exact failing job and fix it before merge; do not claim unexecuted local tests.
3. Expand the existing math IR and parser only with explicit grammar, exact semantics and independent tests; do not create a competing expression system.
4. Extend generation one mathematical family at a time, with independent exact validation and provenance. Keep calculus, linear algebra, discrete mathematics and proof-oriented data marked unsupported until implemented.
5. Preserve padding-aware causal attention and tests proving future-token isolation and padded-key isolation.
6. Do not start training, optimizer steps, download datasets/weights, call external AI APIs, use Colab/cloud, or change the website, Pages, Supabase or authentication without separate authorization.
7. Update this README and the implementation notes at the next meaningful milestone.


## Mathematical parser and conservative symbolic foundation — 2026-11-24

This AI-core stage adds a bounded recursive-descent parser that converts supported tokenizer output into the existing `Expr` IR. It does not introduce a competing expression representation.

### Implemented grammar
- Exact integer and finite decimal literals; decimals are converted directly to exact rational IR atoms using `Fraction`, never binary floating point.
- Identifiers made of contiguous letters/digits, including simple indexed names such as `x_1` and `x_{12}`.
- Parentheses, unary plus/minus, addition, subtraction, multiplication, division, integer/general power syntax, and one top-level equality.
- Explicit and Unicode multiplication/division symbols (`*`, `×`, `·`, `/`, `÷`), implicit multiplication such as `2x` and `2(x+1)`, supported Greek LaTeX aliases, and Unicode superscript integer powers.
- Standard precedence: powers bind more tightly than unary minus; powers are right-associative. Contiguous letters form one identifier (`velocity`), not a product of single-letter symbols.
- Source-offset parse errors and explicit limits of 100,000 source characters, 512 lexer tokens and 128 recursive nesting levels.
- No Python `eval` or `exec`.

### Conservative symbolic transformations
- Exact bounded constant folding using rational arithmetic.
- Flattening associative addition/multiplication nodes, combining numeric constants, removing additive zero and multiplicative one, simplifying subtraction by zero and division/power by one, and removing double negation.
- Does not distribute, factor, reorder symbolic terms, infer domains, cancel common factors, or reduce a zero product if another factor may be undefined.
- Constant folding uses an exponent magnitude cap of 64. Division-by-zero and over-budget expressions remain explicit.
- Finite sample comparisons in tests are regression evidence, not a formal proof of equivalence.

### Validation status
- GitHub Actions on implementation commit `e5fe00a6cc1afc2f3a9345f9469ba951009d6b53`: 104 Python regression tests passed; CPU forward/backward smoke passed; Node.js tests passed.
- The CPU smoke is architecture validation only. It performs no optimizer step or training run.
- Local execution was not claimed; CI is the execution evidence for this milestone.

### Explicit unsupported scope
The parser does not yet support function calls (including `sin(x)`), general LaTeX fractions, inequalities, set membership, matrices, calculus operators, summations, limits, complex numbers, assumptions/domains, or proof syntax. Such input is rejected rather than silently assigned a guessed meaning. The evaluator remains exact scalar arithmetic only; it does not solve equations or provide general symbolic semantics. The model remains untrained.

### Next handoff
1. Expand the typed IR and parser one feature family at a time (function-call nodes and typed comparisons are likely next), with explicit domain semantics and independent tests.
2. Build exact polynomial/rational normalization only after defining a grammar and preserving undefined-domain conditions.
3. Add equation-solving algorithms only with derivation traces and independently checkable exact results; do not label finite probing as proof.
4. Keep trusted-knowledge admission fail-closed. Restricted polynomial identity results must not bypass candidate-bound receipt validation.
5. No training, optimizer steps, external datasets/APIs, pretrained weights, cloud jobs, or website/frontend changes without separate authorization.
6. Update this README and implementation notes at the next milestone.


## Typed comparison and function-call IR — 2026-11-24

The expression IR and parser now represent one top-level comparison using distinct node kinds for equality, inequality, and ordered comparisons. ASCII `!=`, `<=`, `>=` and Unicode `≠`, `≤`, `≥` map to explicit typed nodes. Chained comparisons are rejected rather than assigned an implicit associativity.

A bounded unary-call grammar recognizes `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `exp`, `ln`, `log`, `sqrt`, and `abs`. Calls are stored as `CALL` nodes with a validated function name and one argument. This is syntax and IR support only: the exact rational evaluator deliberately rejects all function calls because transcendental values and their domains/branches need a separate semantic design. No numerical approximation or domain assumption is silently introduced.

The exact evaluator can evaluate comparisons only when both operands are exact scalar rational expressions. Comparisons nested inside comparisons are rejected. Finite-domain candidate probing remains equality-only and therefore does not treat inequalities as proof candidates. The symbolic simplifier preserves comparison and function-call nodes without rewriting them.

Tests cover ASCII and Unicode comparisons, chained-comparison rejection, function-name allowlisting, nested function-call parsing, and explicit evaluator rejection. This stage does not add trigonometric simplification, numerical function evaluation, domain inference, equation solving, or formal proof.


## Exact sparse-polynomial algebra — 2026-11-24

The mathematical core now includes a bounded sparse-polynomial engine in ultron_core/polynomial.py, operating on the existing typed Expr IR.

- Canonical monomials use lexicographically ordered symbol/exponent pairs; coefficients are exact Fraction values.
- Supports exact polynomial conversion, addition, subtraction through IR conversion, multiplication, non-negative integer powers, exact rational constant scaling/division and rational-point evaluation.
- Collects like terms, removes zero coefficients and deterministically exports back to the existing expression IR.
- Enforces configurable maximum total degree, term count and individual exponent. Defaults: 64, 4,096 and 64; absolute constructor ceilings are 256, 16,384 and 256.
- Rejects variable denominators, zero denominators, negative/fractional/non-literal powers, function calls, comparisons and assumption-bearing expressions to avoid silently losing domain restrictions.
- Polynomial canonical equality applies only to expressions converted into this supported rational-coefficient polynomial domain. It is not a general symbolic-equivalence or proof engine.

Regression coverage was added to tests/python/test_math_foundation.py. The parser's stale function-call comment was corrected. This stage does not add rational functions, equation solving, calculus, a formal proof kernel or demonstrated university-level capability. No training, optimizer step, corpus generation, remote execution, website, Supabase or authentication behavior changed.

### Next-chat handoff — exact polynomial foundation

1. Review canonical ordering, exact Fraction arithmetic and resource-budget enforcement.
2. Run the full Python AI-core test workflow, CPU forward/backward smoke and Node.js test suite; fix failures before merge.
3. Next math-engine stage: design rational expressions that preserve denominator non-zero constraints, then add exact polynomial division only where divisibility is proven by an implemented algorithm.
4. Add derivation traces only after every operation has a deterministic, independently checkable verifier.
5. Keep function-call evaluation unsupported until function-specific domains, branches and exact/approximate semantics are specified.
6. Do not start training, optimizer steps, generate a corpus, connect Colab/cloud, or change the frontend, Supabase or authentication without separate authorization.
7. Update this README at every meaningful milestone.


## Domain-preserving exact rational expressions — 2026-11-24

The mathematical core now has an exact rational-expression layer in `ultron_core/rational.py`. It represents a rational expression as exact sparse-polynomial numerator and denominator plus an explicit set of polynomial non-zero domain constraints.

- Supports exact conversion from the existing Expr IR, addition, subtraction through IR conversion, multiplication, division, integer powers (including negative powers), rational scaling and exact evaluation at integer/Fraction points.
- Every nonconstant denominator contributes a preserved non-zero constraint; non-zero constant denominators are omitted as vacuous. Dividing by a rational expression also requires its numerator to be non-zero. Zero powers require the base numerator to be non-zero, matching the evaluator's undefined (0^0) rule.
- No polynomial GCD cancellation is performed. For example, (x/x) evaluates to 1 where defined but remains undefined at (x=0). The same applies to ((x^2-1)/(x-1)) at (x=1).
- Denominators are normalized by a rational scalar for deterministic representation; non-zero constraints are normalized and deduplicated. Structural representation equality is not advertised as general rational-function equivalence.
- The layer inherits polynomial degree, term and exponent limits, and caps preserved domain constraints at 256.
- Function calls, comparisons, assumption-bearing expressions and non-integer powers remain unsupported.

This is exact arithmetic over a restricted rational-function representation with explicit domain tracking. It does not implement polynomial GCD, factor cancellation, multivariate polynomial division, equation solving, calculus, algebraic numbers or a proof kernel. It is not a general CAS. No training, optimizer step, corpus generation, cloud job, remote execution, website, Supabase or authentication change was performed.


## Exact univariate polynomial division and GCD — 2026-11-24

The sparse-polynomial engine now implements exact Euclidean division over rational coefficients for univariate inputs.

- `divide_univariate` returns quotient and remainder satisfying (A=QB+R), with (R=0) or (deg R<deg B).
- `exact_divide_univariate` returns the quotient only when the remainder is zero.
- `gcd_univariate` uses the Euclidean algorithm and returns the monic GCD over (mathbb{Q}[x]).
- Inputs with multivariate monomials or multiple distinct variables are rejected. No multivariate monomial order or multivariate division is inferred.
- Configured polynomial degree, term and exponent limits are checked on inputs and intermediate quotient/remainder states.

This is a univariate exact-algebra operation only. It does not yet cancel factors in RationalFunction, because rational cancellation must preserve the original non-zero domain restrictions. No training or optimizer step is involved.


## Domain-safe univariate rational reduction — 2026-11-24

RationalFunction now exposes `cancel_common_univariate_factors()`. It computes the exact univariate polynomial GCD of numerator and denominator, divides both exactly, and returns the reduced pair.

Crucially, the method carries forward the complete original non-zero constraint set. Thus `x/x` can reduce structurally to (1/1) while still rejecting (x=0); ((x^2-1)/(x-1)) can reduce to (x+1) while still rejecting (x=1). It rejects multivariate numerator/denominator inputs instead of guessing a multivariate GCD. Reduction is structural simplification, not proof of arbitrary expression equivalence.


## Exact real-root counting with Sturm sequences — 2026-11-24

The univariate polynomial engine now supports exact differentiation, Sturm-sequence construction and distinct-real-root counts over rational intervals.

- `derivative_univariate` differentiates with exact integer/Fraction coefficients.
- `sturm_sequence_univariate` builds the signed Euclidean remainder sequence using the exact univariate division implementation.
- `real_root_count_univariate(a, b)` returns the number of distinct real roots in the open interval ((a,b)), using exact sign-variation counts. Endpoints must be exact integers/Fractions and must not themselves be roots.
- Repeated roots are counted once. The zero polynomial is rejected because it does not have a finite root count; nonzero constants return zero.
- Multivariate inputs and work exceeding configured polynomial limits are rejected.

This computes root counts, not decimal approximations or isolating intervals. It does not yet solve for algebraic root representations, construct minimal polynomials, or provide a formally verified proof receipt. The implementation is an exact algorithm based on Sturm's theorem, not a formal proof-kernel implementation.


## Exact real-root isolation — 2026-11-24

The univariate polynomial engine now provides `isolate_real_roots_univariate(lower, upper)`. It first removes repeated factors using the exact polynomial GCD, then recursively bisects rational intervals using exact Sturm root counts.

- Returns disjoint rational intervals, each containing exactly one distinct real root.
- Returns ((r,r)) for a rational root detected exactly at a bisection midpoint.
- All non-degenerate interval endpoints are checked against the original polynomial, including when an exact rational root was removed from the square-free polynomial during bisection.
- Uses a caller-selected exact rational maximum width, with explicit maximum-depth and interval-count budgets.
- Uses only integer/Fraction arithmetic; no floating-point root approximations.

The input interval must have non-root endpoints. The zero polynomial, multivariate polynomials, invalid bounds and exhausted budgets are rejected. This is bounded root isolation for univariate rational-coefficient polynomials; it is not a general equation solver, algebraic-number system, or formal proof kernel.


## Exact real algebraic number representation — 2026-11-24

ULTRON now exposes `RealAlgebraicNumber`, a bounded exact representation of one real root of a univariate rational-coefficient polynomial.

- A non-degenerate rational interval must have non-root endpoints and contain exactly one distinct real root, verified with the exact Sturm counter.
- Exact rational roots can be represented as degenerate intervals `(r, r)`.
- `refine()` bisects with rational arithmetic and detects an exact rational midpoint.
- `same_value_as()` decides equality using exact rational evaluation or the polynomial GCD over the overlap of isolating intervals.
- `compare_to()` orders distinct represented roots by exact interval refinement, with a caller-controlled refinement budget.

The defining polynomial is **not asserted to be minimal or irreducible**. The representation supports exact affine transforms and, as documented below, bounded arithmetic via resultants. It does not provide minimal-polynomial computation, multivariate algebraic numbers, or formal proof receipts. Comparisons currently require both values to use the same variable name. No floating-point arithmetic is used.


A further regression covers an exact rational root encountered during the inward endpoint-adjustment search itself. The isolator now emits that root as a degenerate rational interval instead of passing a root endpoint into the Sturm counter.

## Exact algebraic affine transforms — 2026-11-24

The exact real-algebraic-number representation now supports rational affine transformations \(\beta=a\alpha+b\), where \(a\ne0\) and \(a,b\in\mathbb{Q}\). It constructs the transformed defining polynomial \(q(y)=a^n p((y-b)/a)\) using exact rational polynomial arithmetic, maps the isolating interval exactly, and reverses interval endpoints for negative multipliers. Rational inputs remain exact rational values.

- API: `RealAlgebraicNumber.affine_transform(multiplier, offset=0)`.
- Inputs reject booleans, floating-point values and zero multipliers.
- The operation enforces the existing polynomial resource limits.
- The resulting polynomial is not claimed to be minimal or irreducible.
- This does not implement arithmetic between two unrelated algebraic numbers, resultants, multivariate algebraic numbers or a proof kernel.
- Regression tests cover positive, negative and fractional transforms, rational inputs, invalid arguments, exact root counts and resource limits. See [affine transform notes](docs/ALGEBRAIC_AFFINE_TRANSFORMS.md).

No training, optimizer step, external data, remote execution, website, Supabase or authentication changes were made.

### Next mathematical-core step

That next step is implemented in the exact algebraic arithmetic milestone below. The resultant engine keeps the operand variable label so results can be chained, intersects both operands' resource budgets, and uses only certified rational intervals.



## Exact arithmetic between real algebraic numbers — 2026-11-24

ULTRON now provides bounded exact addition, subtraction, multiplication, division and reciprocal operations for represented real algebraic numbers.

- `RealAlgebraicNumber.add`, `.subtract`, `.multiply`, `.divide` and `.reciprocal` are the explicit APIs; `+`, `-`, `*` and `/` are also supported between two algebraic-number instances.
- Addition/subtraction and multiplication construct exact resultants over rational polynomial coefficients.
- Division first certifies that the selected divisor is non-zero, constructs its exact reciprocal polynomial and then uses the product resultant.
- Rational interval arithmetic bounds the intended result. The implementation refines operand intervals until the resultant has exactly one distinct real root in the candidate interval, with non-root endpoints.
- Resultant multiplicities and extraneous factors are retained. The output polynomial is **not claimed to be minimal or irreducible**.
- The subset-dynamic-programming determinant is capped at a Sylvester matrix dimension of 10. Existing polynomial term/degree/exponent budgets also apply. A computation that cannot be certified within its refinement budget fails explicitly.
- No floating-point approximation is used. The engine does not implement general multivariate algebraic numbers or a formal proof kernel.

Regression coverage includes sums and differences of square roots, products with repeated conjugate roots, reciprocals, quotients, rational operands, exact cancellation, division by zero and resource limits. Run:

`python -m unittest tests.python.test_algebraic_arithmetic -v`

No model training, optimizer step, external dataset, remote execution, website, Supabase or authentication changes were made.


## Exact algebraic normalization

The math core includes bounded exact real-algebraic arithmetic and square-free normalization. `ultron_core/squarefree.py` separates repeated polynomial factors over rational coefficients and identifies the square-free component containing a selected real root using exact rational evaluation or Sturm counts. This is **not** irreducible factorization and does not establish a minimal polynomial. See [square-free normalization](docs/SQUARE_FREE_NORMALIZATION.md) for scope and regression coverage.

No model training, optimizer step, external dataset ingestion, or remote execution was performed for this math-core milestone.


## Exact polynomial evaluation at algebraic numbers

The exact math core now includes bounded evaluation of a univariate rational polynomial at a selected real algebraic number using Horner's rule and the existing exact resultant arithmetic. It enforces the algebraic value's resource limits, rejects multivariate or mismatched-variable inputs, evaluates rational inputs directly, and normalizes exact cancellation to zero. The result is not claimed to have a minimal or irreducible defining polynomial. See [polynomial evaluation](docs/ALGEBRAIC_POLYNOMIAL_EVALUATION.md).

No model training, optimizer step, dataset generation, or remote execution was performed for this milestone.


## Pre-training readiness update — 2026-11-25

### Current verified engineering state
- Foundation architecture: **63,400,451 total parameters / 61,826,048 trainable parameters**, meeting the user's >60M trainable-parameter target. This is a configuration/counting result, not a trained model.
- The deterministic original-data generator currently covers eight narrow families: arithmetic, rational arithmetic, one-variable linear equations, polynomial derivatives, polynomial definite integrals, 2×2 determinants, 2×2 linear systems, and exact 2×2 matrix inverses (generator v0.5.0). Coverage is not university-math breadth.
- Phase 5 has a corpus coverage report for topic/difficulty balance, duplicate IDs/prompts, exact validation counts, split membership, and prompt leakage.
- Phase 7 evaluator schema v3 reports mutually exclusive answer classes and exact equivalence for the currently supported grammar. It does not evaluate ULTRON itself or verify derivations/proofs.
- Phase 8 now binds resumable sampler state to dataset SHA-256, checks dataset/sampler/batch cursor alignment, restores sampler before DataLoader iteration, rewinds to the last committed step on interruption, and requires a verified dataset hash before checkpoint cursor restore. Exact-resume DataLoader constraints: num_workers=0, drop_last=False.
- PR #91 passed Node tests, Python regression tests, and the CPU forward/backward smoke check. PR #93 added exact matrix inverse generation/validation and passed Node/Python tests plus CPU smoke. No real ULTRON weights were updated; no corpus was generated or training/remote job run.

### Remaining pre-training blockers
1. Owner notebook must create the train-split DataLoader with ResumableRandomSampler, save callback data_state in save_checkpoint, and pass expected_dataset_manifest_sha256 to load_checkpoint.
2. Verify a clean-runtime checkpoint restore/resume against an uninterrupted run. This requires separate explicit authorization for a tiny training/optimizer-step test; it has not been performed.
3. Implement measured live RAM/VRAM enforcement; the current controller relies on preflight budget checks.
4. Complete owner-side iPad Safari acceptance, enable Supabase leaked-password protection, and validate the free-cloud runtime/session workflow.
5. Continue broader independently validated university-math tasks, general symbolic equivalence, and proof-checker metrics.

Keep real-weight training and remote execution disabled until separate explicit authorization.



## Bounded exact polynomial identity verifier — 2026-11-25

ULTRON now includes `ultron_core/polynomial_verifier.py`, a bounded exact checker for identities in the supported multivariate rational-polynomial grammar.

- Converts both sides of an equality to canonical sparse polynomials over \(\mathbb{Q}\), then computes the exact difference.
- Returns `FORMALLY_VERIFIED` only when the canonical difference is exactly zero; returns `REJECTED` for a non-zero polynomial difference; unsupported syntax or resource exhaustion returns `UNRESOLVED`.
- Emits canonical JSON containing the expression hash, hard-capped resource limits, normalized sides and difference, plus a SHA-256 integrity digest.
- Certificate validation re-runs the checker using the certificate's validated limits. Limits above the polynomial engine's hard caps are rejected.
- Variable denominators, candidate domains/assumptions, function calls, inequalities and non-polynomial identities remain unresolved. This prevents silently discarding domain restrictions.
- The public API is exported from `ultron_core`. `FormulaCandidate.can_enter_trusted_knowledge()` remains fail-closed; a verifier result does not grant trusted-knowledge admission.

See [bounded polynomial identity verification](docs/POLYNOMIAL_IDENTITY_VERIFICATION.md). This is a restricted exact algebraic checker, not a universal theorem prover or proof of autonomous formula discovery. No training, optimizer step, dataset generation, remote execution, website, Supabase or authentication behavior changed.

### Next implementation handoff

1. Continue exact rational/algebraic verification only with preserved domain conditions, canonical certificates, and independent regression tests.
2. Keep the next release gate as manual iPad Safari frontend acceptance. Record the actual device/browser results; CI cannot substitute for this owner-side pass.
3. Do not connect a cloud runtime or perform optimizer steps until the frontend release gate is complete and training is separately authorized.
4. Update this README at every meaningful milestone.


## Domain-preserving rational identity verifier — 2026-11-25

ULTRON now includes `ultron_core/rational_verifier.py`, extending exact identity checking to supported rational functions without dropping definedness constraints.

- Converts each equality side into a normalized `RationalFunction`, including the preserved non-zero constraints generated by division and negative powers.
- Cross-multiplies exactly and checks the resulting polynomial difference using `Fraction` arithmetic.
- `FORMALLY_VERIFIED` means the rational functions are equal wherever both expressions are defined; it does **not** claim identical domains.
- Example: `x/x = 1` verifies with the explicit condition `x != 0`; the verifier does not make the original expression defined at zero.
- Candidate-supplied domain strings, assumptions, function calls, inequalities, and unsupported grammar remain `UNRESOLVED`.
- Canonical certificates include both sides' domain constraints, cross-difference, expression hash, and hard-capped limits. Validation re-runs the checker.
- The API is exported from `ultron_core`; trusted-knowledge admission remains fail-closed.

See [rational identity verification](docs/RATIONAL_IDENTITY_VERIFICATION.md). No training, optimizer step, dataset generation, remote execution, website, Supabase or authentication behavior changed.

### Next implementation handoff

1. After this PR merges, continue expanding exact math with independently validated university-level task families; do not broaden either verifier by silently dropping domains.
2. Complete manual iPad Safari frontend acceptance before training work, and record actual device/browser results.
3. Keep actual training and remote execution disabled until the frontend release gate is complete and separate explicit authorization is given.
4. Update this README at each meaningful milestone.



## First callable agent tool: exact math solver — 2026-11-25

Added a local allow-listed function tool named `math_solver` in `ultron_core/agent_tools.py`, backed by `ultron_core/math_solver_tool.py`.

- **Evaluate:** exact integer/rational scalar arithmetic with exact variable bindings.
- **Simplify:** conservative exact simplification using ULTRON's typed expression IR.
- **Solve:** bounded linear equations in one variable, returning exact rational answers and a short algebraic trace.
- **Agent interface:** `get_tool_specs()` returns the function-call schema; `execute_tool(name, arguments)` dispatches only registered local tools. Unknown tool names and extra arguments are rejected.
- **Safety:** uses the existing parser and exact evaluator; no `eval`, `exec`, shell, network, or arbitrary code execution. Input size, token count, nesting, variable count, and exponent magnitude are bounded.
- **Limitations:** nonlinear equations, calculus, and exact evaluation of transcendental functions are not supported by this tool. Unsupported inputs fail explicitly. This is a deterministic symbolic/exact tool, not proof that the untrained neural model can solve these tasks unaided.

Regression tests: `python -m unittest tests.python.test_math_solver_tool -v`.

### Next handoff

1. Run the new solver tests plus the full Python/Node CI and CPU model smoke checks.
2. Review the tool schema and ensure the future inference orchestrator can call `execute_tool` from model-generated structured tool calls without permitting arbitrary names or code.
3. Add domain-aware equation solving and more mathematical operation families only with exact validation and explicit limits.
4. Keep training and remote execution disabled; finish frontend/iPad acceptance before training, and update this README at every milestone.


## Agent knowledge bank — 2026-11-25

Added `ultron_core/data/knowledge_bank.json` with **169 curated starter entries** across mathematics, science, computer science, language arts, social studies, and university-level foundations. Grade bands are approximate; this is not an exhaustive curriculum.

- Entries have stable IDs, subject, approximate level, knowledge type, statement, prerequisites, and verification-status metadata.
- The bank distinguishes mathematical axioms from definitions, facts, formulas, and principles; entries are not all axioms.
- Added `ultron_core/knowledge_bank.py` for schema/ID validation and bounded ranked retrieval, plus the allow-listed `knowledge_search` agent tool.
- Retrieval supplies context; it does not automatically make an entry a proof premise.

Validation: `python -m unittest tests.python.test_knowledge_bank -v`.

### Next handoff

1. Run dedicated knowledge-bank tests, all Python tests, Node tests, and CPU model smoke CI.
2. Add source-level citations and formal axiom-system metadata before using entries as proof premises.
3. Expand subjects in reviewed, curriculum-aligned batches; test for duplicates, conflicts, and incorrect statements.
4. Connect retrieval to the agent planning/answer loop with evidence tracking and uncertainty.
5. Do not start training or remote execution. Finish and verify the frontend/iPad release gate first; update README at each milestone.


## Training optimization implementation — 2026-11-25

The first research-guided training optimization is implemented as an **opt-in BF16 autocast path** in `ultron_core/precision.py` and the bounded controller.

- FP32 remains the default (`TrainingSettings.precision="fp32"`).
- BF16 is selectable with `TrainingSettings(precision="bf16")`; CPU and supported CUDA devices are accepted, and unsupported device/dtype combinations fail clearly.
- The causal language-model loss converts logits to FP32 before cross-entropy accumulation to improve numerical stability.
- FP16 is intentionally not enabled yet: the controller must first save and restore GradScaler state as part of the checkpoint/resume contract.
- This change adds no training command, dataset generation, optimizer step, remote execution, or frontend behavior. Tests exercise precision utilities only; CI validates integration.
- Speed and memory improvements are hardware-dependent and remain unclaimed until measured against the same model, batch, sequence, and device.

Next: run CI, review BF16 support on the intended runtime, then implement optional profiling/AMP measurements and checkpoint-safe scaler handling before considering FP16.


## Opt-in training performance telemetry — 2026-11-25

Added optional measurements to the bounded training controller:

- Set `TrainingSettings(profile_performance=True)` to report optimizer-step elapsed time, target-token throughput, median/p95 step time, and peak allocated CUDA memory when running on CUDA.
- Profiling is disabled by default. It synchronizes CUDA only when explicitly enabled, because synchronization changes runtime behavior and can affect measured throughput.
- Metrics are returned in the controller's `performance` object. They are descriptive measurements, not a comparative benchmark or model-quality result.
- CPU runs report elapsed time and token throughput; CUDA memory is reported only on CUDA.
- No model benchmark, training run, or remote job was started as part of this change.

Validation: added mock-controller tests for the disabled default, validation, CPU timing, and target-token counts.


## Precision-aware checkpoint/resume — 2026-11-25

Checkpoint format version 5 now stores optional validated training settings, including precision, seed, gradient accumulation, deterministic mode, and profiling flag.

- The bounded controller writes the active training settings into its checkpoint cursor/callback metadata.
- Loading returns the saved training settings and rejects disagreement between top-level and cursor metadata.
- Resuming BF16 requires a checkpoint with explicit precision metadata; older checkpoints without it cannot silently resume in BF16.
- FP32 remains compatible with legacy checkpoint metadata. Existing dataset-hash, RNG, optimizer, and scheduler integrity checks remain in place.
- The checkpoint format accepts versions 2, 3, 4, and 5 for backwards compatibility.

No training run or remote job was started. Tests cover metadata persistence, validation, and precision mismatch/legacy BF16 resume rejection.


## Opt-in activation checkpointing — 2026-11-25

Added block-level activation recomputation for the transformer model.

- `NeuroSparseModel.set_activation_checkpointing(True)` enables checkpointed block execution during gradient-enabled training.
- The bounded controller exposes `TrainingSettings(activation_checkpointing=True)`, scopes the setting to the session, and restores the model's previous value.
- Activation checkpointing is disabled by default. It trades recomputation for lower saved-activation memory; no speed or memory improvement is claimed until measured on the target hardware.
- It is disabled for memory-writing forwards to avoid repeating mutable memory side effects.
- Checkpoint metadata validation now accepts the activation-checkpointing setting.
- Tests compare forward outputs and gradients against the ordinary path on a small deterministic CPU model.

No full-model training or remote job was started.


## Math Agent topic commands — 2026-11-25

The browser Math Agent now exposes slash commands for the ten mathematics roadmap topics:

- `/arithmetic`
- `/algebra`
- `/geometry`
- `/trigonometry`
- `/calculus`
- `/linear-algebra`
- `/probability`
- `/statistics`
- `/number-theory`
- `/logic-proofs`

Use `/help` to display the command directory or `/topics` to list topics with their current status. Topic commands return the topic's scope, core idea/formula, example and prerequisite. The Math Agent page also displays tappable command chips.

These commands are **curriculum references**, not new mathematical solvers. Only the existing deterministic arithmetic and limited linear-equation operations are supported; roadmap topics remain marked planned. No model training, data generation, remote execution, or backend/authentication behavior was changed.


## English word-problem understanding — Phase 1

The Math Agent now includes a bounded English word-problem parser (`word-problems.js`). It recognizes tested templates for addition (altogether/total), subtraction (left/remaining), multiplication (equal groups/each), division (shared equally/per person), and direct operation phrases. It accepts common number words (including compound forms such as twenty-one), returns a structured operation/expression/result, and explains the operation choice. Ambiguous or unsupported wording is rejected rather than guessed. This is a deterministic template parser—not general English comprehension or a trained language model. Unit conversion, multi-step stories, pronoun/coreference resolution, complex number phrases, and broad vocabulary remain future work. Regression tests are in `tests/word-problems.test.js`. No training data was generated and no model training was started.


## Training and AI optimization — Phase 1

The training loss now computes next-token cross-entropy in bounded per-row token chunks, avoiding a full flattened FP32 logits copy for mixed-precision outputs while preserving the global valid-token mean. The AdamW factory automatically selects fused AdamW on a single CUDA device when supported and falls back to the portable implementation in automatic mode; `fused=False` forces the reference path. CPU parity tests compare loss and gradients against full-batch cross-entropy. These are memory/optimizer implementation improvements, not evidence of improved model intelligence or measured training speed. No training was launched.


## Training-loop synchronization optimization — 2026-11-25

The bounded training controller now keeps detached loss scalars on-device while processing microbatches. It validates accumulated losses and the global gradient norm together at the optimizer boundary, reducing metric-related device-to-host synchronization from once per microbatch to once per optimizer step. Checkpoint loss metrics are transferred only when a checkpoint callback needs them; the session mean is transferred once at finalization.

This preserves loss values and fail-closed behavior for non-finite loss/gradients. It does not remove the synchronization required to decide whether an optimizer step is safe. Regression coverage checks that four microbatches with accumulation=2 cause two explicit CPU transfers for controller validation, and confirms the returned mean loss remains finite. This is a code-path optimization; no device benchmark has been run and no speedup is claimed.


## CUDA expert dispatch optimization — 2026-11-25

ULTRON's sparse-expert block now uses a CUDA-specific grouped dispatch path: flatten the top-k routes, stably sort by expert, count assignments, and transfer the compact count vector once per block. It avoids one dynamic `torch.where`/nonzero selection per expert. CPU keeps the original loop. Regression tests compare outputs and gradients against the reference dispatch. This reduces a known synchronization source by design; no target-GPU throughput benchmark has been run and no speedup is claimed. See [NeuroSparse implementation notes](docs/NEUROSPARSE_IMPLEMENTATION.md).



## Benchmark milestone — foundation configuration support (2026-11-25)

The inference-only benchmark now accepts `--model-config smoke|foundation`. The default remains the small CI model. The explicit foundation option selects the proposed **63,400,451 total / 61,826,048 trainable** configuration, allowing a future baseline measurement at the intended model size.

Before allocating model weights, the harness computes the exact parameter count and enforces `--max-parameters` (default 100,000,000). After construction, it checks actual total/trainable counts against the configuration formula. The cap is a parameter-count guard—not a complete RAM/VRAM estimate or guarantee against out-of-memory.

Example (run only on a device with adequate memory):

```bash
python -m ultron_core.benchmark --device cuda --model-config foundation --batch 1 --sequence 32 --warmup 10 --iterations 50
```

The benchmark still uses synthetic random token IDs solely for tensor-shape timing. It is not a math-quality test, and this code change does not report measured speed or memory gains. No training, optimizer step, corpus generation, cloud execution, or remote job was started. Next: CI validation, then a foundation-model inference baseline on suitable hardware before claiming any performance improvement.


## Hybrid language architecture — 2026-11-25

ULTRON will use a **measured hybrid stack** rather than force every language into the core. Python/PyTorch remains the canonical model and training implementation; JavaScript powers the current browser frontend; C++/CUDA is reserved for profiled native hot paths with a tested Python fallback. Rust may be considered for a safe inference/runtime service once interfaces stabilize. Java/C# and Julia/R remain optional integrations or research tools, not duplicate model implementations. See [hybrid language architecture](docs/MULTI_LANGUAGE_ARCHITECTURE.md) for responsibilities, interoperability boundaries and the performance decision gate.

No training, dataset generation, cloud execution or remote job was started for this documentation milestone.


## Typed browser math engine — 2026-11-25

The deterministic browser math engine now has a strict TypeScript source at `src/math-engine.ts`. Type contracts define token output and the discriminated linear-equation result (`unique`, `all-real`, or `none`). The static GitHub Pages runtime continues to load the compiled `math-engine.js`, so no browser compiler or server is required. CI compiles the TypeScript source before running Node regression tests, including expression precedence, equation outcomes and division-by-zero handling. This is a maintainability/type-safety change; no performance or AI-capability improvement is claimed. No training, data generation or remote execution was performed.


## Bounded training loss metrics — 2026-11-25

The training controller now retains only the current gradient-accumulation group's detached losses for validation/checkpoint metrics. A running scalar sum and count produce the session mean at finalization, avoiding per-microbatch GPU scalar retention and a full-session tensor stack. The mean still includes all processed microbatches, including an incomplete final group that is discarded from optimizer updates. Regression coverage simulates 20 microbatches and checks bounded stack size. No training or device benchmark was run.


## Path to Fable 5.2 — staged math capability plan

ULTRON's current capability roadmap is [Path to Fable 5.2](docs/PATH_TO_FABLE_5_2.md). Stage A is the active $0 target: arithmetic, algebra and basic calculus with independently checked answers. Stage A is **in progress**, not passed: the browser Math Agent currently supports deterministic arithmetic and limited linear equations, and calculus coverage plus a matched benchmark against Fable 5.2 are not yet established.

Progression is gated by measured topic-level results: Stage B broadens to geometry, trigonometry, probability, statistics, linear algebra and number theory; Stage C adds multi-step and competition-style reasoning, considering 1B+ parameters only when justified by results and resource estimates. Merged PR #122 adds a bounded exact-rational step verifier; natural-language decomposition and measured Stage C capability remain unimplemented; Stage D adds formal proof checking with Lean. Merged PR #124 adds an opt-in local Lean type-checking adapter and preflight only; formal proof benchmarks and measured proof-search capability remain unimplemented. Each topic requires its own verifier, validated data generator, leakage-resistant benchmark and regression tests. Parameter count alone is not evidence of capability. Merged PR #119 adds only a Stage B readiness-manifest contract; topic generators, verifiers, held-out datasets and measured baselines remain unimplemented.

This plan does not authorize data generation, training, optimizer steps or remote jobs. Training remains disabled until separate explicit authorization, and frontend/device acceptance remains a prerequisite.


## Stage A implementation — paired benchmark gate (merged PR #118)

Stage A now adds `ultron_core/benchmark_comparison.py`, a paired exact-answer comparison tool for caller-supplied ULTRON and baseline prediction files. It compares both systems on the same independently validated references, reports topic-level accuracy/coverage/valid-answer rate, paired wins/losses/ties, exact McNemar p-values, Holm correction, and explicit pass/fail gate conditions. Defaults require 200 examples per topic, a significant corrected paired win, and no more than a 2-percentage-point coverage or validity regression.

This is evaluation infrastructure—not a measured ULTRON-vs-Fable result. It does not invoke either model, create training data, run training, or call an external AI API. Stage A remains in progress until actual matched prediction files are scored and every required topic passes. See [Math evaluation protocol](docs/MATH_EVALUATION_PROTOCOL.md).

**Next handoff:** PR #118 was merged after the PR-branch Node and Python AI Core checks passed. Verify the final main-branch Node, Python AI Core and Pages workflows for the merge/handoff commits. Then freeze the Stage A arithmetic/algebra/basic-calculus benchmark specification, task serialization and held-out split. Stage A remains in progress until actual matched ULTRON and Fable 5.2 prediction files are scored and every required topic passes. No training or training-data generation is authorized by this milestone; Stage B–D must not be marked complete or started as empirical capability stages before Stage A's gate.


## Grade 1–4 question generator package — 2026-11-25

The merged `tools/math_generators/grade1_4/` package adds ten deterministic original-template generators for counting, addition, subtraction, place value, multiplication, division, fraction basics, simple word problems, time and money, and perimeter/area. Each generated problem is checked before return; `verify()` replays the seed and applies an arithmetic or inverse check. The topic/grade-band registry and deterministic train/held-out split script are included. The randomized regression suite checks 1,000 generated problems per topic. Difficulty is heuristic and requires curriculum calibration; these generators do not establish ULTRON model capability. Dataset files are not generated and no training was started. See the package README for usage and split commands.

**Next handoff:** Continue with Grades 5–8 generators and contextual word problems using the same generator/verifier/test contract. Continue to update this README at each milestone.


## Grade 5–8 generator batch — 2026-11-25

The `tools/math_generators/grade5_8/` package adds thirteen deterministic, original-template generators: decimal operations, fraction operations, ratios, percentages, integers, exponents, order of operations, linear equations, inequalities, basic geometry, angles, statistics, and simple probability. Contextual word problems are included across ratio, percent, integer, order-of-operations, equation, inequality, geometry, angle, statistics, and probability tasks. Every generated item is checked before return; the verifier replays the seed and checks the exact result. The registry flags word-problem coverage, and the split script uses separate seed ranges plus content fingerprints for train/benchmark separation. Tests exercise 1,000 seeds per topic. Difficulty remains heuristic and needs curriculum calibration. No training or dataset generation was started.

**Next handoff:** Run Python CI and review PR for Grade 5–8. After merge, continue Batch 3 (Grades 9–12), retaining contextual word problems in applicable topics and exact answer verification. The combined topic registry is at `tools/math_generators/registry.json`.


## Grade 5–8 generator validation update — 2026-11-25

PR #127 now includes generator-declared contextual metadata and `tools/math_generators/build_registry.py`. Run `python -m tools.math_generators.build_registry` to regenerate the Grade 5–8 and combined registries. Regression tests require the committed JSON to match generated output and assert the complete Grade 5–8 word-problem topic set, including integers and order of operations.

The percentage generator now distinguishes count and continuous quantities. Count totals are multiples of `100 / gcd(percent, 100)`; continuous results are limited to two decimal places with appropriate rounding language. A shared semantic-validation hook is applied after each topic's exact arithmetic verifier.

The contextual-generator audit also corrected potentially invalid quiz scores, ticket totals, cost-variable domains, and checked ratio counts, geometry dimensions, angle bounds, statistics values, and probability bounds. Tests include 2,500 percentage seeds across all five difficulty levels.

**Validation and merge:** PR #127 was reviewed and merged (merge commit `f5ee61050ef564d9b63997e2fe1ebbbc2ad4f3d6`). Python AI Core Tests passed, including the full Python regression suite and CPU forward/backward smoke; Node Tests passed on PR head `bbe79c5225cd74d52efbd05e7d652eedc713a026`. Separate post-merge workflow runs were not yet reported by the Actions query. No training, dataset generation, or remote execution was started. Next: proceed to Batch 3 (Grades 9–12) only as generator/verifier/test infrastructure, retaining exact checks and updating this README at the next milestone.


## Grade 1–4 hardening and Grade 8–12 generator batch — 2026-11-25

Grade 1–4 already had 10 topic generators; this update adds an explicit semantic-validation hook for non-negative counts, currency formatting, time conversion, and positive rectangle measures, plus complete contextual-topic and registry-parity regression tests.

Batch 3 adds 22 deterministic Grade 8–12 topics: linear equations, systems, quadratics, polynomial operations/factoring, functions, coordinate geometry, triangle geometry, trigonometry, sequences, logarithms, limits, derivatives, definite integrals, matrices, combinatorics, number theory, complex numbers, vectors, statistics, probability, and a narrow divisibility proof template. Each item is seed-replay verified and includes ingredients and solution steps. Contextual coverage is declared in generator metadata and the registry builder now regenerates Grade 1–4, Grade 5–8, Grade 8–12, and combined registries.

**Validation and merge:** PR #128 merged successfully as `07cc149358c55b4b7a3702a470a00d4ef27449a9`. Final PR head `fb8a7978186952e631f9cfe8b0fe5f60383bf572` passed Python AI Core Tests (run #406; 392 tests, Python 3.11 regression suite, and CPU forward/backward smoke) and Node Tests (run #455). The initial CI attempt found over-escaped Grade 1–4 semantic regexes and insufficient coordinate seed variation; both were corrected and the complete workflows passed again.

**Important limits:** These are original deterministic practice-item generators, not trained-model capability. Difficulty is heuristic. The proof topic is a narrow divisibility proof template, not a general proof checker. No training, corpus generation, or remote execution was started.

**Next handoff:** Grade 1–4 semantic validation is hardened, and Grade 8–12 Batch 3 has 22 topics. Continue expanding topic coverage and curriculum-calibrated difficulty while keeping training disabled. Always update this README at the next milestone.


## University mathematics foundation batch — 2026-11-25 (PR in review)

The new `tools/math_generators/university/` package adds nine deterministic university-foundation exercise templates: 2×2 linear algebra, partial derivatives of quadratic functions, first-order separable differential equations, modular exponentiation, a sequence-limit proof for c/n, element order in cyclic groups, quadratic optimization, one Newton iteration, and a count-based Bayes calculation. Items include a problem, exact/recomputable answer, worked steps, ingredients, seed replay, and tamper-resistant verification. The university registry is generated alongside the combined registry.

The scope is intentionally a **foundation starter batch**, not full university mathematics and not general natural-language solving. The Bayes generator constrains positive-event counts to valid population counts. Tests cover 300 seeds per topic, determinism, variation, registry parity, and tampering. CI must still run before merge. No training corpus was generated and no model training or remote execution was started.

**Next:** Review CI and correct failures before merge. After this batch, add proof-oriented foundations and broader university topics (vector spaces, eigenvalues, multivariable integration, ODE systems, combinatorics/probability, and rigorous analysis) with exact verifiers and benchmark gates. Keep training disabled.


## Expanded university curriculum map — 2026-11-25

The university topic catalog now lists 197 topics across foundations and logic, linear algebra, calculus, real and complex analysis, abstract algebra, number theory, topology, discrete mathematics/combinatorics, probability, statistics, differential equations, optimization, numerical/computational mathematics, geometry, applied mathematics/mathematical physics, and advanced/interdisciplinary topics.

**Status is explicit:** nine topics currently have deterministic generator implementations; the remaining catalog entries are marked `catalogued_not_implemented`. This is a broad undergraduate curriculum map, not literally every university course or specialty. Do not present catalog entries as trained capability. The earlier CI failure in multivariable calculus (six values unpacked into five variables) has been fixed; the full suite must pass on the updated head before PR #129 can merge.

No training, corpus generation, or remote execution has started. Continue by implementing catalogued topics in tested batches with exact verifiers and benchmark gates. README updated for this handoff.


### University generator registry correction — 2026-11-25

CI exposed a mismatch between nine implemented university generator identifiers and the curriculum topic IDs. The curriculum now maps each generator to a canonical topic (`determinants`, `partial_derivatives`, `first_order_ODEs`, `congruences`, `convergence_of_sequences`, `cyclic_groups`, `unconstrained_optimization`, `Newton_and_secant_methods`, and `Bayes_theorem`). Registry generation reports these as `generator_available_not_mastered`; this means a deterministic exercise template exists, not that ULTRON has learned or mastered the topic. The remaining catalog entries stay `catalogued_not_implemented`. Regression tests now verify all nine mappings. Training remains disabled.


### University foundation generator batch 2 — 2026-11-25 (PR in review)

Added nine more deterministic, seed-replayable university exercise templates: finite-set inclusion/exclusion, propositional truth evaluation, a summation induction proof template, vector linear combinations, nonsingular 2×2 linear systems, diagonal-matrix eigenvalues, quadratic Taylor polynomials, count-based conditional probability, and the multiplication principle. Each is registered against its curriculum topic with status `generator_available_not_mastered`; exact verification and randomized regression tests are required. The catalog remains 197 topics, with 18 generator implementations and 179 topics not yet implemented. This is template coverage only, not learned or benchmark-mastered ability. No training or corpus generation was performed.

**Next:** validate this batch on CI, fix any failures, then continue with additional topics in prerequisite order. Training remains disabled.


### University foundation generator batch 3 — 2026-11-25
Added eight deterministic, seed-replayable university exercise templates: bounded predicate logic, modular equivalence classes, standard-basis span coordinates, vector independence, basis/dimension in R², rank of 2×2 matrices, limits of linear expressions, and derivatives of quadratic polynomials. Curriculum and combined registries mark these as \`generator_available_not_mastered\`. Regression tests independently check 250 seeds per topic (2,000 generated cases across this batch), in addition to existing replay, verifier, and registry tests. This increases implemented university generator topics from 18 to 26; 171 of the 197 catalog topics remain without generators. Templates are narrow, exact synthetic tasks—not general proof, calculus, or university-level solving. No training or corpus generation was started.


### University generator expansion — Batch 3 (PR in progress)

- Added 22 deterministic, seed-replayable university-foundation exercise templates across logic, linear algebra, and calculus.
- New topics include quantifiers, cardinality, linear transformations, diagonalization, inner products, projections, least squares, mean value theorem, definite/improper integrals, geometric series, power-series convergence, gradient/directional derivatives, and multivariable chain rule, alongside the first eight batch topics.
- Curriculum and generated coverage registries now mark these as `generator_available_not_mastered`; generator availability is not evidence of model training or mastery.
- Added randomized regression checks for the mathematical formulas. CI must run before this batch is considered validated or merged.
- This work only expands deterministic exercise generation and verification. No training was started and no model weights were changed.


### Math Agent graph tool — PR #132 (2026-11-25)

- Added the local `/graph` command. Examples: `/graph y=x^2`, `/graph sin(x)`, `/graph sqrt(abs(x))`.
- Supported functions: sin, cos, tan, sqrt, abs, ln, log, exp. Constants: pi and e. Operators: +, -, *, /, ^, and parentheses. Use explicit multiplication, such as `2*x`.
- Graphs render as responsive SVG in the browser. No API, training, generated training corpus, or model weights are involved.
- Parser, domain, dimensions, and sample count are bounded. Tests cover polynomial/trig functions, constants, malformed input, and resource limits.
- PR: https://github.com/ultron1846-oss/ULTRON/pull/132 — CI pending; do not merge until tests pass and review is clean.

Next: validate PR #132, then add practical Math Agent tools (table of values, improved equation solving, and calculator utilities) one at a time with tests. Keep README updated. Training remains disabled.
\n\n## Math Agent calculator and numerical tools — merged PR #133 (2026-11-25)\n\nAdded a registered local tool set: `/calc`, `/gcd`, `/lcm`, `/factor`, `/table`, `/derivative`, `/integral`, `/solve`, `/quadratic`, and `/system`. The table, derivative and integral tools use the safe graph-expression parser. Derivatives use a 5-point central-difference estimate; definite integrals use composite Simpson quadrature (1,000 intervals). Quadratic equations support real and complex roots; 2×2 systems classify unique, dependent and inconsistent cases. Command help is generated from the registry.\n\nThis is deterministic tool functionality, not neural-model capability. Numerical outputs are approximations where explicitly stated. Tests cover command registration, expression safety, table limits, numerical reference values, equation edge cases and system classifications. CI is required before merge. No training, training-data generation or remote execution was performed.\n

## University generator expansion — 20-topic batch (merged PR #133, 2026-11-25)

Added 20 exact, deterministic, seed-replayable university templates: proof methods, countable-set mapping, finite choice functions, the spectral theorem for a symmetric 2×2 family, Jordan blocks, quadratic forms, elementary multivariable limits, rectangular double integrals, Jacobian scaling, constant-field line/surface integrals, divergence, Euclidean metric distance, geometric sequence convergence, Cauchy sequences with an explicit epsilon bound, uniform convergence of x/n, compactness and connectedness of intervals, Lipschitz continuity, and interval measure. Each topic is registered as `generator_available_not_mastered`; the university curriculum remains 197 topics and the registry continues to mark uncovered topics explicitly.

The batch is tested through the existing 300-seed replay/verifier suite plus new 100–150 seed tests and independent formula checks. These are narrow templates, not general solvers or trained ability. No dataset was generated and no training or remote execution was started.

**PR #133 scope:** calculator/numerical commands, command directory/help, equation tools, and this 20-topic university generator batch. CI must pass on the final PR head before merge. The next work is to inspect any CI failures, fix them, then merge only after checks pass and review is clean. Stage 6 is a broad batch, not complete coverage of the full 197-topic university catalog.


## Roadmap handoff — PR #132 and PR #133 merged (2026-11-25)

- PR #132 merged as `2cd3db5711008cba306989e1882a699c9bcc143d`: local `/graph` SVG tool.
- PR #133 merged as `9444f3e1883068ebde09a04d442a4a5bb030bc42`: calculator command registry, numerical table/derivative/integral tools, quadratic and 2×2 equation solvers, plus 20 university generator templates and updated curriculum/coverage registries.
- PR #133 head `75e4f006f8a36ab1a75775b21a65a09288fb0a2d` passed Node Tests and Python AI Core Tests, including the full Python regression suite and CPU forward/backward smoke. Main-branch Node Tests passed after merge; main build and Python AI Core checks were still running at handoff.
- Important: 20 university templates were added in this batch. The university catalog still has topics marked `catalogued_not_implemented`; generator availability is not model mastery.
- No training, training-corpus generation, model-weight update or remote execution was performed.

**Next work:** verify the post-merge main workflows and deployed GitHub Pages. Then expand the remaining university and Grade 1–12 generator gaps in a single planned batch with registry parity and independent mathematical checks. Continue adding real tools only with tests. Training remains disabled pending separate authorization.


## Guided learning: no automatic final answers (2026-11-26)

The Math Agent's ordinary learner-input path is now tutor-first. For word problems, arithmetic questions and supported linear equations, it gives a setup hint or first-step strategy and asks the learner to attempt the next step. It does not automatically evaluate the parsed word-problem result, arithmetic expression or equation to reveal the final answer. Unsupported questions receive a prompt to show work or ask for a hint.

Slash commands are opt-in tools: the learner must type a command explicitly. Graphing is a visualization tool; numerical/calculator commands operate on the specific expression or operation requested. They are not automatically called by normal question text. This distinction keeps the conversational tutor from acting as an answer key, while explicit calculator commands can still return the requested calculation. Regression tests assert the normal-answer handler does not call the final-answer arithmetic or equation solvers.
