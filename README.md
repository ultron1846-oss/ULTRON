# ULTRON — Mathematics Intelligence Workspace

ULTRON is an independent, local-first mathematics workspace under development. Its long-term goal is an original mathematics intelligence system. The current website is a static frontend and deterministic foundation prototype—not a trained AI model.

## Frontend status

The frontend includes startup/navigation resilience, visible render-error recovery, cache-busted modules, actionable overview status and quick links. A successful automated build does not replace full iPad browser verification.

The frontend is being redesigned around the supplied ULTRON control-room reference: near-black surfaces, crimson accents, a compact top header, left navigation, bordered panels and responsive tablet/mobile layouts.

### Current pages
- **Supabase backend:** refreshable, bounded-time read-only status check with visible last-checked time, plus an audit of deployed Edge Function contracts and backend security findings. It never calls owner-only services from the public site.
- **Overview:** honest system status, model/training state, capability summary, roadmap and quick links to current pages.
- **Mathematics topics:** curriculum roadmap with descriptions, prerequisites, representative examples and explicit available/planned status. The former fixed exercise card and its answer/hint/next controls have been removed.
- **Math Agent:** browser interface to the deterministic arithmetic parser and limited linear-equation solver; unsupported requests are rejected rather than guessed.
- **Memory vault:** IndexedDB stores existing experiences and mistakes locally, with JSON export/import for manual device-to-device transfer. This is not cloud sync.
- **Servers & Colab:** reads `servers.json`, handles missing/malformed directory data and never starts remote jobs.
- **Supabase backend:** checks only the public read-only status endpoint; private owner records remain protected.
- **Owner sign in:** optional email/password sign-in for the existing owner account; there is no public sign-up.
- **Settings:** stores a preferred future workload memory budget locally; it does not allocate device or remote memory.

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
1. Confirm the latest `main` commit is the deployed GitHub Pages version.
2. On iPad Safari, test navigation and every page: Overview, Mathematics Topics, Math Agent, Memory Vault, Servers & Colab, Supabase Backend, Settings and Owner Sign-in.
3. Test supported Math Agent inputs and unsupported-input handling; the removed fixed exercise card must not reappear.
4. Test Memory Vault history, JSON export/import and clear-all only after exporting any data you want to keep.
5. Test the workload preference slider and verify it is clearly described as a saved preference, not actual memory allocation.
6. Verify the public Supabase status refresh and owner sign-in/sign-out without exposing private data.
7. Keep actual model training, Colab connection and remote execution disabled until separately authorized.

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


## GitHub Pages deployment verification — 2026-11-24

The latest frontend commit `932fcf005d414fdd1338d4d58265afd9b8ed64c4` was checked against both Pages workflows. The repository's custom `Deploy static site to GitHub Pages` workflow successfully staged and uploaded the `github-pages` artifact, but its deploy step failed because GitHub could not resolve the artifact for that concurrent deployment. The built-in `pages build and deployment` workflow then completed its build, artifact upload and deploy jobs successfully for the same commit. Therefore the latest commit has a successful Pages deployment through the built-in workflow; do not interpret the custom workflow's failed run as proof that the site is offline.

The repository currently has two deployment paths targeting the same Pages environment. This is a workflow-coordination issue to monitor; avoid changing the Pages source or deleting either workflow without validating the repository's Pages configuration and confirming the replacement deploy path. The custom workflow's artifact contains the explicitly staged runtime files, while the built-in Jekyll workflow independently built and deployed the repository content.

## Next-chat handoff — post-removal release

- Latest merged change: PR #9, removing the fixed exercise interface and retaining the Mathematics Topics roadmap and existing local Memory Vault records.
- The latest commit's built-in GitHub Pages deployment completed successfully. Custom deployment run failed at its deploy step after artifact upload; see the deployment verification section above.
- README content has been aligned to the current page structure and the removal of the fixed exercise interface.
- Perform the real iPad Safari page-by-page interaction test before declaring frontend completion.
- Do not connect Google Colab, start a server, submit remote jobs or train the model. The user explicitly deferred server connection until the AI is ready.
- Preserve Supabase RLS, owner-only checks, credentials and private records. Do not change Auth settings or secrets during frontend QA.
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
- The model still has no tokenizer, original deterministic training-data generator, curriculum, tested ablation controls, dense-expert reference path, or formal proof kernel.
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
- The method now fails closed for all candidates because this repository does not yet contain a formal proof kernel or verifiable proof-receipt type. A status label and free-form evidence text are not proof.
- Added a regression test showing that a caller-supplied FORMALLY_VERIFIED label cannot promote a candidate into trusted knowledge.
- Future trusted admission requires a structured proof receipt from an implemented backend and independent validation of that receipt; do not restore status-only trust.


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
4. Keep formal proof status fail-closed until a proof kernel and verifiable receipt exist.
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
- Every denominator contributes a preserved non-zero constraint. Dividing by a rational expression also requires its numerator to be non-zero. Zero powers require the base numerator to be non-zero, matching the evaluator's undefined (0^0) rule.
- No polynomial GCD cancellation is performed. For example, (x/x) evaluates to 1 where defined but remains undefined at (x=0). The same applies to ((x^2-1)/(x-1)) at (x=1).
- Denominators are normalized by a rational scalar for deterministic representation; non-zero constraints are normalized and deduplicated. Structural representation equality is not advertised as general rational-function equivalence.
- The layer inherits polynomial degree, term and exponent limits, and caps preserved domain constraints at 256.
- Function calls, comparisons, assumption-bearing expressions and non-integer powers remain unsupported.

This is exact arithmetic over a restricted rational-function representation with explicit domain tracking. It does not implement polynomial GCD, factor cancellation, multivariate polynomial division, equation solving, calculus, algebraic numbers or a proof kernel. It is not a general CAS. No training, optimizer step, corpus generation, cloud job, remote execution, website, Supabase or authentication change was performed.
