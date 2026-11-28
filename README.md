# ULTRON — Mathematics Intelligence Workspace

**Status snapshot: 2026-11-28 — integrated readiness documented in PR #207; not merged.**

ULTRON is an independent mathematics-learning and reasoning project. Its deterministic tools, generators, and model architecture are development infrastructure—not evidence of a trained general-purpose mathematics model.

## Implemented

- **From-scratch model architecture:** The foundation configuration enforces at least 60 million trainable parameters. The configured allocation is 63,400,451 total parameters, including 61,826,048 trainable parameters. The model remains untrained.
- **Mathematics core:** Bounded parser and expression representation, exact rational and polynomial operations, rational and polynomial identity checking, algebraic-number utilities, and deterministic math tools.
- **Curriculum generators:** Core, Grades 1–4, 5–8, 8–12, and university packages. A shared `Problem` contract and verifier interface normalize source records; a code-generated combined registry tracks declared coverage.
- **Train/benchmark guards:** Shared split helpers reserve disjoint seed ranges and reject benchmark overlap by normalized prompt or generation-ingredient hash.
- **Exact checking:** Exact engine results use `EXACT_CHECKED`. Trusted-knowledge admission remains fail-closed; `FORMALLY_VERIFIED` is reserved for a future independently validated proof-kernel receipt.
- **Level 1 math tooling:** Deterministic arithmetic and linear-equation generators, exact verifier, and a separate 500-item held-out benchmark.
- **Lean integration stub:** An integration plan and abstract checker interface exist.
- **Compression toolkit:** PR #166 added non-destructive expert pruning/representative merging, SVD factorization, simulated int8 sensitivity reporting, and versioned artifacts.
- **Static website:** Account-free browser workspace with local memory and a browser-local memory preference.
- **Runtime configuration handoff:** Versioned schema-v1 JSON export for the 2–10 GiB preference, bounded workload defaults, and explicit non-authorizing flags; JavaScript and Python validate it independently, with a Python preflight adapter. This is a file handoff only, not a connected runtime.
- **Streaming dataset verification:** semantic dataset validation now reads bounded JSONL lines incrementally, enforcing explicit byte/row/line limits while preserving exact-answer checks, content-derived IDs, duplicate ID/index detection, topic counts, and SHA-256. Split-row loading also avoids full-file byte/string copies and rechecks the digest between passes.
- **Owner notebook:** validates runtime config and formula-based capacity, verifies an existing dataset/split manifest, tokenizes every selected prompt/answer against the runtime sequence limit, builds a non-authorizing readiness report, and constructs all three read-only split DataLoaders from one verified snapshot. It does not consume batches, allocate model weights, create an optimizer, or train.

## Tested

- [Python AI Core run #45811463595](https://github.com/ultron1846-oss/ULTRON/actions/runs/45811463595): success on the PR #166 merge commit, including Python regression tests and CPU forward/backward smoke.
- [Level 1 Math Tooling run #45811463693](https://github.com/ultron1846-oss/ULTRON/actions/runs/45811463693): success on the PR #166 merge commit, including the regression job with 5,000 randomized cases.
- Fixed-seed SymPy differential suite: eight exact-engine areas with 1,000 cases per area; SymPy is test-only.
- Generator registry consistency and shared Problem/verifier contract tests.
- Train/benchmark split tests for disjoint seed ranges and overlap rejection.
- Level 1 arithmetic and linear-equation exact regression tests.

These checks validate the covered implementation and workflow behavior only. They do not demonstrate learned mathematical ability or generalization.

## Not done / not claimed

- **Model training:** No training run, optimizer step, trained weights, or demonstrated grade/university-level competence.
- **Benchmark evaluation:** The 500-item Level 1 holdout is opt-in and is not training data. Generator availability and test correctness do not establish model mastery.
- **Lean proof checking:** No Lean toolchain, kernel run, proof receipt validator, or theorem-proving capability.
- **Compression quality:** No trained-checkpoint quality, speed, or memory-reduction results. Int8 is currently a floating-point quantize/dequantize simulation. Compressed deployment artifacts do not count toward the foundation parameter floor.
- **Runtime/device acceptance:** No connected training runtime. The bounded trainer samples process RSS plus CUDA allocator-reserved memory and stops at safe controller boundaries when its preflight budget is exceeded; it cannot interrupt a single tensor operation. The browser can export a validated schema-v1 config file, but that file is not consumed by a runtime yet and the website memory preference does not allocate physical RAM. Manual iPad Safari acceptance remains pending.
- **External data:** No seed dataset has been downloaded or uploaded as part of this work.

## Architecture

- `ultron_core/`: model/configuration, parser and math IR, exact math, verification, data generation, benchmark/split guards, memory, agent tools, training/checkpoint infrastructure, and compression.
- `tools/math_generators/`: curriculum generators, metadata, replay verifiers, per-band registries, and the combined registry builder.
- `tools/level1_math/`: bounded Level 1 generators, exact verifier, and opt-in held-out benchmark.
- `tests/`: Python and Node regression, differential, contract, and integration tests.
- `docs/`: architecture, mathematical engine, security, evaluation, compression, runtime constraints, historical milestones, and Lean integration documentation.
- `index.html` and frontend assets: the static browser workspace.

## Safety and trust boundaries

- No external AI APIs or pretrained weights are used for the from-scratch model plan.
- Training, optimizer steps, corpus generation, calibration-data generation, and cloud/remote training execution are not authorized.
- A deterministic generator, command result, exact-check result, or tool-assisted answer must not be presented as learned model capability.
- SymPy is restricted to tests; runtime math code must not depend on it.
- Do not modify the website, Supabase, authentication, GitHub Pages, secrets, or deployment configuration as part of core math work without separate scope and authorization.
- Do not start training without separate explicit authorization.

## Current handoff

- Repository: [ultron1846-oss/ULTRON](https://github.com/ultron1846-oss/ULTRON), default branch `main`.
- Earlier runtime-memory milestone: [PR #181 — record PR #180 runtime memory guard merge](https://github.com/ultron1846-oss/ULTRON/pull/181), squash-merged as `0baab32502a17d50de6f33e57be3e394cd91d72a`. PR #180’s runtime RSS/CUDA memory guard remains merged as `a5b3a4d39d86e12eb1255c06fb050b10a477bc39`; all six post-merge checks passed (Python `45923177570`, Node `45923177573`, Level 1 `45923177527`, Pages build/report/deploy `45923176814`).
- Checkpoint-resume safeguard (merged PR #176): checkpoint load metadata distinguishes optimizer/scheduler state present from state actually restored. The bounded trainer rejects resume unless optimizer state was restored and any saved scheduler state was restored, preventing a model-only load from being accepted as a complete training resume. Exact uninterrupted-versus-resumed numerical equivalence remains unproven and is still a separate acceptance item; no actual optimizer step or model training was performed.
- Merged checkpoint-cursor integrity guard (PR #178): `save_checkpoint` and `load_checkpoint` reject cursor and nested sampler dataset hashes that differ from the checkpoint's top-level manifest hash. Load-time checks occur before model, optimizer, scheduler, or RNG state restoration; regression tests cover checksum-valid tampering and model-state immutability. PR checks and all six post-merge checks passed. No training or optimizer step was performed.
- Merged runtime memory guard (PR #180): an injectable monitor checks before training, at batch boundaries, after backward, before/after optimizer steps, and after checkpoint callbacks. It reports sampled peak and measurement limitations; no training or optimizer step on ULTRON weights was performed.
- The requested pre-training engineering checklist A–G has been reviewed. The implemented math-engine, generator, verification, Lean-stub, Level 1, and word-problem coverage is summarized above; detailed dated milestones are archived in [docs/HISTORY.md](docs/HISTORY.md).
- Remaining owner-side acceptance includes manual iPad Safari testing. Automated responsive checks are not a substitute for testing on an actual iPad.

- Current math-engine hardening: [PR #169 — enforce polynomial operand limits](https://github.com/ultron1846-oss/ULTRON/pull/169) adds input-budget checks to polynomial addition, scaling, multiplication, and powers, with regression tests for degree, term-count, and exponent limits plus cancellation/zero-operation bypasses. The code/test revision passed Node Tests run `45824836936`, Python AI Core run `45824836974` (full Python regression suite and CPU forward/backward smoke), and Level 1 Math Tooling run `45824837375` (including 5,000 randomized cases). The final merged revision also passed post-merge Node Tests run `45825511165`, Python AI Core run `45825511264`, Level 1 Math Tooling run `45825511167`, and Pages build/deployment run `45825510334`.
- Recent validation change: [PR #168 — rational-function division differential coverage](https://github.com/ultron1846-oss/ULTRON/pull/168) adds 1,000 fixed-seed SymPy comparison cases for exact rational-function division and a regression for divisor-domain preservation. See [docs/HISTORY.md](docs/HISTORY.md) for the validation scope and recorded CI runs.
- Continue with small, independently reviewable math-engine or readiness tasks. Preserve the no-training authorization boundary.

- **Current engineering handoff (2026-11-27):** PR #192 (`9adb26790e581ab4feb419724563aa741d42c669`) and PR #193 (`53f925627891885e6363c9f512fe6c27b1c075ac`) are merged; post-merge checks passed. PR #194 — [lazy disk-backed verified dataset loaders](https://github.com/ultron1846-oss/ULTRON/pull/194) — merged as `ec55abd99e10adc1430c56de7c764f4f63476a4c`; exact-head Node, Python AI Core, Level 1, and post-merge checks passed. PR #195 — [stream indexed preflight and curriculum audit](https://github.com/ultron1846-oss/ULTRON/pull/195) — merged as `fdb8b640ea8ad4cb884aafcbe9e6961b338afc4f`; exact-head Node (`45994243531`), Python (`45994243605`), and Level 1 (`45994243669`) passed. It streams preflight token checks from the verified snapshot, explicitly closes temporary storage, audits generator/curriculum status, and adds tokenizer contract tests. PR #196 — [read-only indexed dataset benchmark](https://github.com/ultron1846-oss/ULTRON/pull/196) — is being rebased onto post-#195 main so its diff contains only benchmark additions: index build time, scan throughput, random-access latency, disk bytes, and Python allocation peak. It does not claim complete RSS/device measurement or an eager-loader speedup. The 14-stage campaign is tracked in [docs/ENGINEERING_CAMPAIGN_STATUS.md](docs/ENGINEERING_CAMPAIGN_STATUS.md). No training, optimizer step, corpus generation/download, or remote compute was performed. Owner acceptance still required: actual iPad Safari, clean-process checkpoint transfer/resume, free runtime quotas/persistence, and Supabase Auth leaked-password protection.

- Merged training-controller hardening: [PR #172 — validate actual model parameter counts](https://github.com/ultron1846-oss/ULTRON/pull/172) compares the model's enumerated trainable and total parameters with the preflight report before iterating batches. It was squash-merged as `80185f0730fa4aafd7d47f417ba96362f27096ee`. Final PR checks passed on `0d3b0e8be2d4a1cba4ad6dd07cde510bf3744a6d` (Node `45832090241`, Python `45832090388`, Level 1 `45832090161`); all six post-merge checks passed on `main` (Node `45832389890`, Python `45832390292`, Level 1 `45832390114`, Pages build/report/deploy run `45832389411`). Regression tests use exact-count meta-device parameters and reject mismatched/frozen parameters before batch consumption. No real training or optimizer step was run.

- Current optimizer hardening: [PR #173 — verify optimizer parameter coverage](https://github.com/ultron1846-oss/ULTRON/pull/173) requires optimizer parameter groups to match the model's trainable parameters exactly: no missing, unrelated, frozen, or duplicate parameters. New tests verify rejection before input batches are consumed. The first Python CI attempt exposed and fixed a test fixture that reused an optimizer from another model. The corrected final code/test revision `1a0e6868a8b9b189709c4ae804fc2245644169b0` passed Node Tests run `45834204104`, Python AI Core run `45834203997`, and Level 1 Math Tooling run `45834204069`. The final README/history revision also passed Node Tests `45834360621`, Python AI Core `45834360563`, and Level 1 Math Tooling `45834360523`. No training or optimizer step was run.

- Merged canonical task serialization: [PR #174](https://github.com/ultron1846-oss/ULTRON/pull/174) adds strict schema-v1 problem restore, content-bound verifier receipts with explicit scope, canonical JSON, and an allowlisted prompt/derivation/answer projection. The code/test revision `e5f1f86a7852e2422a89828774728d27d66fc6a9` passed Node `45837819889`, Python AI Core `45837819908`, and Level 1 `45837819890`; final PR revision `3ad08e527dac9be298313222d3dea95b80f52f19` passed Node `45838266304`, Python `45838266301`, and Level 1 `45838266463`. Merged as `d62e54e1fd663cbd7c865d26a59faddb6f908b25`; all six post-merge checks passed on `main` (Node `45838672166`, Python `45838672328`, Level 1 `45838672111`, Pages build/report/deploy `45838671242`). This is serialization/readiness work only; it does not generate a corpus or authorize training. See [docs/TASK_SERIALIZATION.md](docs/TASK_SERIALIZATION.md).

For current feature-specific requirements, use the relevant documents under [docs/](docs/).

- Foundation training-gate hardening: [PR #170 — align the foundation parameter floor](https://github.com/ultron1846-oss/ULTRON/pull/170) merged as `ea1e1851a42a2334369bcf26b8bc74037ec98191`. Preflight and the bounded training controller now use the shared inclusive 60,000,000-trainable-parameter floor; regression tests cover exact-floor acceptance and rejection below the floor before batch consumption or optimizer steps. Final PR checks passed on `8d9a0dd9d42f21ac7cb86ccac87a67ebbce4f14c`: Node Tests run `45830279539`, Python AI Core run `45830279637`, and Level 1 Math Tooling run `45830279788`. All six post-merge checks passed on `main`: Node Tests `45830648511`, Python AI Core `45830648531`, Level 1 Math Tooling `45830648456`, Pages build `45830648135`, build-status report, and Pages deployment (both jobs in run `45830648135`). No model training, optimizer steps, or corpus/dataset generation were performed.

- Earlier runtime-config milestone: [PR #182 — versioned runtime-config handoff](https://github.com/ultron1846-oss/ULTRON/pull/182), squash-merged as `87db245d7147690d986535fa6b80f60015634d5e`. Final PR CI passed on head `05775faf460ea6bba69ecb995858ddd7d63b56c8`: Node `45924574433`, Python AI Core `45924574430`, Level 1 Math Tooling `45924574420`. All six post-merge checks passed on `main`: Python AI Core `45924733525`, Level 1 Math Tooling `45924733537`, Node Tests `45924733492`, and Pages build/report/deploy run `45924733234`.


- PR #183 — documentation handoff for PR #182 — merged as `0f456b4c92c1381e19cd259d79413df74d053548`; latest-head Node, Python AI Core, and Level 1 checks passed.
- Current owner notebook (PR #187): builds a non-authorizing report from an existing verified dataset, split manifest, canonical tokenizer, model-capacity formulas, and exported runtime configuration. It checks every selected sequence against the runtime length limit and creates all three DataLoaders from one verified split snapshot. The train sampler seed is distinct from the split seed and must match `TrainingSettings.seed` later. No batches are consumed, no weights/optimizer/checkpoint are allocated or restored, and no training occurs. See [docs/OWNER_NOTEBOOK.md](docs/OWNER_NOTEBOOK.md).

- PR #184 — owner notebook preflight scaffold — merged as `041c39d2b37f68a21e45f149c3ef6412c64641bf`; latest-head Python AI Core, Level 1 Math Tooling, and Node checks passed.
- PR #185 — manifest-bound split preflight — merged as `f189de4d53c56ed7162eebe9a6256d2d899ca2e6`. Final PR checks passed: Node run `45940051111`, Python AI Core `45940051105`, Level 1 Math Tooling `45940051151`. All six post-merge main checks passed: Python `45940271270`, Level 1 `45940271193`, Node `45940271206`, and Pages build/report/deploy `45940270667`. It writes split-ID metadata only; no production dataset rows were generated or downloaded.


- Latest merged engineering change: PR #186 — verified split DataLoaders — squash-merged as `eea774a71100fc7b1aabd67e526090885be9e0d6`. Latest-head checks passed on `88ea8ad40aef051aa3101ae65a96742796042c99`: Node `45967507758`, Python AI Core `45967507636` (regression suite and CPU forward/backward smoke), and Level 1 `45967507654`. All six post-merge checks passed: Python AI Core `45967755444`, Node `45967755446`, Level 1 `45967755414`, and Pages build/report/deploy run `45967754542`. No model training, optimizer step on ULTRON weights, production corpus generation/download, checkpoint restore, batch consumption, or remote execution occurred.

- PR #187 — [verified dataset preflight report](https://github.com/ultron1846-oss/ULTRON/pull/187) — squash-merged as `d817ef9a96a874db5092900f88b8099b317a8876`. Exact PR-head checks passed: Node `45970193704`, Python AI Core `45970193657` (589 tests and CPU forward/backward smoke), Level 1 Math Tooling `45970193750` (5,000 randomized cases). All six post-merge main/Pages checks passed: Node `45970513782`, Python AI Core `45970513600`, Level 1 `45970513508`, and Pages build/report/deploy workflow `45970512991`. No batches were consumed by the preflight notebook, and no training or optimizer step on ULTRON weights, checkpoint restore, production corpus generation/download, or remote execution occurred.

- PR #188 — canonical resumable data-cursor contract — merged as `7adf369549206eec139bc3fdb1a390631113e662`. Adds pure validation binding dataset/sampler hashes, split size, batch size, epoch, batch/sample cursor alignment, seed, and accumulation settings; malformed metadata is rejected before batch access. Exact-head Node, Python AI Core, and Level 1 checks passed, as did post-merge checks. No production training run or real ULTRON weight update was performed.

- PR #189 — [checkpoint metadata-only resume compatibility](https://github.com/ultron1846-oss/ULTRON/pull/189) — merged as `582533c7267babf3035f1d4126e96fde4429592e`. Python AI Core run `45973713970`, Level 1 run `45973713967`, and Node run `45973714005` passed on the exact PR head. Added cursor validation at checkpoint boundaries, a SHA-256-bound JSON sidecar, and a metadata-only compatibility inspector that does not deserialize weights; updated the owner notebook. No training, optimizer steps, production data generation/download, or remote jobs.


- PR #190 — [resume-cursor equivalence and restore hash gate](https://github.com/ultron1846-oss/ULTRON/pull/190) — squash-merged as `ab8e08ff9e482fca52cdc801e376212d42a8eb80`. Exact-head Node `45976015317`, Python AI Core `45976015089` (regression suite and CPU forward/backward smoke), and Level 1 Math Tooling `45976015246` passed. Added mock-only sampler sequence equivalence and a dataset-hash rejection test that proves model/optimizer/scheduler state is untouched before the gate. No ULTRON training, optimizer step, corpus generation/download, or remote job.


- PR #191 — [checkpoint portability recovery and bounded JSONL scan](https://github.com/ultron1846-oss/ULTRON/pull/191) — squash-merged as `ac10b09cb281547e47a2ec82ecd84ae9543a011a`; exact-head Node, Python AI Core, and Level 1 checks passed. Adds fresh-object model/optimizer/scheduler and sampler-cursor restore; checkpoint bundle copy/restore integrity; interrupted-save recovery; and a bounded structural JSONL scan. Restore coverage includes synthetic momentum-buffer and scheduler-state assertions without an optimizer step. The scanner does not generate data or validate mathematical answers. No ULTRON training or optimizer step was performed.


## Current engineering handoff — 2026-11-27

- PR #196 merged as `faa4b8ea31415598355afa36414092482b1a8e00`: read-only indexed-dataset benchmark, deterministic scan/random-access metrics, 2,000-row synthetic integrity stress, and direct/symlink/hard-link output collision protection. Post-merge Node, Python AI Core, Level 1, and GitHub Pages build/deploy checks passed (runs 45999719213, 45999719007, 45999719034, and 45999718336).
- PR #197 merged as `be318623fc4919bee4848cdc7f7bf6ae155e65fe`: independent mathematical invariant checks across all 20 existing extended university templates, 2,000 deterministic seed/difficulty cases. This adds validator coverage; it does not add generators for the 138 catalog topics still missing implementation.
- Batch 2 tokenizer/model audit is underway in branch `audit/tokenizer-model-architecture-v2-2026-11-27`: model config now carries tokenizer version; explicit config/vocabulary compatibility checks and checkpoint legacy-v1 normalization are being tested; deterministic model shape, mask, gradient, and numerical tests are added.
- No ULTRON training, optimizer step, full corpus generation/download, or remote compute was performed. Continue the tokenizer/model audit, then proceed to training-engine recovery and evaluation work only after the relevant PRs are verified.


## Batch 1 engineering handoff — PR #201 merged

PR #201 was squash-merged as `15bac227ca4335a3b8cd3f43c63601830b495956`. It adds synthetic stress coverage for the indexed verified dataset path: 3,500-row filtered split streaming and boundary random access, a 2,400-row read-only benchmark exercise, snapshot-record corruption detection, corrupted/incomplete manifest rejection, idempotent cleanup, and failed-construction cleanup. It also adds an exact Euclidean-algorithm university generator with independent 500-seed Bézout/gcd/quotient-trace tests and registry synchronization. Exact-head Node, Python AI Core, and Level 1 checks passed (runs 46003076411, 46003076428, and 46003076581). Post-merge `main` checks also passed: Node `46003403936`, Python AI Core `46003403876`, Level 1 `46003404073`, and Pages build/deploy `46003403018`. PR #196's benchmark implementation and PR #197's extended-template validators were already merged. No production dataset was supplied, so no production RSS, native SQLite memory, device-memory, or throughput result is claimed. No corpus generation or training was performed.


**Dataset memory boundary:** The indexed loader bounds snapshot copying and record iteration, but it is not constant-memory: split-manifest ID arrays are parsed in Python memory up to the 100,000-row preflight cap. The benchmark's `tracemalloc` measurement excludes native SQLite allocations and process RSS/device memory. A production dataset benchmark remains owner-dependent.


## Full-system readiness — 2026-11-28

**Current verdict: automated engineering validation passed; not ready for training.** The integrated candidate is [PR #207](https://github.com/ultron1846-oss/ULTRON/pull/207), based on main `2ba3340dbc841699ad98e651c86f2e227be8cac0`. Exact implementation/test revision `bfb48af944c9dfba8e387d9c39f9a1b39a31145f` passed:

- Node Tests [run 46107031153](https://github.com/ultron1846-oss/ULTRON/actions/runs/46107031153): 127 passed, 0 failed.
- Python AI Core [run 46107031165](https://github.com/ultron1846-oss/ULTRON/actions/runs/46107031165): 722 tests passed; CPU forward/backward smoke explicitly performed no optimizer step or training run.
- Level 1 Math Tooling [run 46107031224](https://github.com/ultron1846-oss/ULTRON/actions/runs/46107031224): 5 tests passed, including 5,000 randomized cases.
- Security and dependency audit [run 46107031196](https://github.com/ultron1846-oss/ULTRON/actions/runs/46107031196): passed; npm audit found 0 vulnerabilities and pip-audit found no known vulnerabilities in the declared runtime/test/seed dependency sets.

The documentation-only follow-up pass also passed on the PR handoff revision: Node [46107500105] (127/127), Python [46107500109] (722), Level 1 [46107500160] (5 tests plus 5,000 randomized cases), and security/dependency [46107500169] (npm audit 0 vulnerabilities; pip-audit no known vulnerabilities). No executable source or test changes were made between the two passes.

The target configuration is 63,400,451 total / 61,826,048 trainable parameters, but the full model has not been instantiated or profiled. The university curriculum lists 197 topics; 60 currently have generators and 137 do not. The evaluation fixtures are synthetic, there is no trained checkpoint or model-accuracy result, inference/compression tests use small initialized weights, and simulated int8 is not a packed deployment runtime.

The website/runtime contracts pass mocked and static tests. The 2–10 GiB slider and exported runtime config are preferences only; no live resource enforcement or website-to-runtime connection exists. Manual iPad Safari acceptance and provider-session/persistence checks remain owner tasks. Supabase leaked-password protection, retired tables/functions, secret-scanning settings, project license and full dependency-license inventory also require owner decisions. See [docs/FULL_SYSTEM_READINESS_2026-11-28.md](docs/FULL_SYSTEM_READINESS_2026-11-28.md) for the complete status table, limitations and owner actions.

**No training, optimizer step on ULTRON weights, production corpus generation/download, Supabase mutation, production deployment, external AI API call or remote training execution was performed. Do not start training without separate explicit authorization.**

### Code audit follow-up — 2026-11-28

A targeted review of the integrated PR #207 code found and addressed three issues/improvements:

- **Tokenizer performance:** replaced a full vocabulary scan at every input offset with a trie-based longest-match lexer. The test compares token IDs, values and source offsets against the prior reference-scanner behavior over deterministic mixed-token inputs.
- **Profiler accuracy:** training throughput metrics now count only causal next-token targets that the loss actually scores. Padding targets and positions whose predictor/target pair is masked are excluded. Added padded/unpadded and malformed-mask regression tests.
- **Security scan coverage:** added `runtime-status.js`, `preferences.js` and `word-problems.js` to the frontend static scan. A new guard checks that every local module imported by `app.js` appears in the audited-source list. This remains a focused heuristic scan, not a security certification.

**Validation on code revision `50b3e03705943a047640ca70faacce7ef4dae172`:**

- Node Tests [run 46109015334](https://github.com/ultron1846-oss/ULTRON/actions/runs/46109015334): **128 passed, 0 failed**.
- Python AI Core [run 46109015315](https://github.com/ultron1846-oss/ULTRON/actions/runs/46109015315): **725 tests passed**; CPU forward/backward smoke explicitly reports no optimizer step or training run.
- Level 1 Math Tooling [run 46109015308](https://github.com/ultron1846-oss/ULTRON/actions/runs/46109015308): **5 passed**, including the workflow's 5,000 randomized cases.
- Security/dependency audit [run 46109015366](https://github.com/ultron1846-oss/ULTRON/actions/runs/46109015366): passed; npm audit reported **0 vulnerabilities**, and pip-audit reported no known vulnerabilities in each declared dependency group.

These validations ran on GitHub-hosted Linux CI. They do not constitute target-device profiling, a trained-model evaluation, or a full independent security audit. PR #207 remains open and unmerged pending independent review. No ULTRON weight update, optimizer step, corpus generation/download, external AI API call or remote training job was run.

### Exact next engineering task

After independent review of PR #207, implement a bounded exact-rational **Green's theorem** generator tranche for the existing `Green_stokes_divergence_theorems` university catalog entry. Use polynomial vector fields over axis-aligned rational rectangles; independently verify the counter-clockwise boundary line integral against the double integral of the curl; add deterministic, tamper, orientation and resource-bound tests; update the registry and coverage audit without claiming Stokes/divergence coverage. Use fixtures only—no production corpus, training, optimizer step or remote compute.


## Phase 0 review-gate audit — 2026-11-28

**Outcome: BLOCKED — do not merge PR #207 until an independent review is recorded.**

This audit checked the live GitHub state before making this README-only handoff update.

- Repository: ultron1846-oss/ULTRON; default branch: main.
- Base main SHA at audit: 2ba3340dbc841699ad98e651c86f2e227be8cac0.
- Integration PR: [#207 — Run integrated full-system readiness validation](https://github.com/ultron1846-oss/ULTRON/pull/207).
- PR branch: full-system-readiness-batch-7-2026-11-28.
- Exact code/documentation head audited before this README update: 8a49eb5ef120f1edebdeaaaedb7dc62479f6ac86.
- PR #207 targeted main at the same base SHA, was 18 commits ahead and 0 behind, had 70 changed paths, and GitHub reported it mergeable at audit time.
- PR #207 was open and unmerged. GitHub reported **zero submitted reviews** and **zero inline review threads**. The visible conversation comments were authored by the PR author; none is an independent review. Independent review is therefore unavailable in the recorded PR state.

### Exact-head workflow evidence

All four workflows fetched for audited commit 8a49eb5ef120f1edebdeaaaedb7dc62479f6ac86 were completed with conclusion success:

| Workflow | Run ID | Result |
| --- | ---: | --- |
| Tests | [46109232702](https://github.com/ultron1846-oss/ULTRON/actions/runs/46109232702) | Success |
| Security and dependency audit | [46109232711](https://github.com/ultron1846-oss/ULTRON/actions/runs/46109232711) | Success |
| Python AI Core Tests | [46109232698](https://github.com/ultron1846-oss/ULTRON/actions/runs/46109232698) | Success |
| ULTRON Level 1 Math Tooling | [46109232715](https://github.com/ultron1846-oss/ULTRON/actions/runs/46109232715) | Success |

The connector's legacy combined-status endpoint returned no separate status entries; the four completed Actions workflow runs above are the available CI evidence. No failed workflow was present in that exact-head run listing.

### Open-PR overlap and duplicate-work warning

The live open-PR inventory contained #207, #206, #205, #204, #203 and #199. Comparing changed-path lists showed:

| Open PR | Changed paths | Paths also changed by #207 | Note |
| --- | ---: | ---: | --- |
| #206 | 32 | 32 | All changed paths overlap #207. |
| #205 | 15 | 14 | One additional path is outside #207. |
| #204 | 14 | 13 | One additional path is outside #207. |
| #203 | 17 | 16 | One additional path is outside #207; GitHub reported it non-mergeable. |
| #199 | 8 | 6 | Two additional paths are outside #207; its base is older and GitHub reported it non-mergeable. |

These are **changed-path overlaps**, not a claim that every file's patch or resulting content is identical. PR #207's description says it integrates #203–#206 and retains the newer #204 clean-process recovery test rather than #199's older duplicate recovery test. Do not merge the component PRs independently while #207 is the integration candidate. After the integration decision, reconcile or close superseded PRs deliberately; check their unique documentation/tests first.

### Phase decision and next action

- **Phase 0 remains blocked.** CI is green on the audited head, and the branch is current with main, but the independent-review requirement is not met.
- Do not self-approve, fabricate a review, resolve nonexistent threads, or merge around this gate.
- Required owner/reviewer action: arrange an independent review of PR #207, triage any findings, and rerun all required workflows if code changes.
- Immediately before any future merge, re-fetch the PR and main, verify the latest head/base SHAs, changed files, review state, unresolved threads, and exact-head checks. Merge only if every gate is then satisfied.
- Once PR #207 is reviewed and safely integrated, the next planned engineering task is the bounded exact-rational Green's theorem generator described above. Stokes' theorem and the divergence theorem must remain marked incomplete until separately implemented and validated.

This Phase 0 audit did not modify executable source or tests. It did not run model training, step an optimizer on ULTRON weights, generate or download a production corpus, deploy Pages, mutate Supabase, call an external AI API, or launch remote compute. Training remains blocked pending separate explicit authorization.


## Phase 1 repository audit — 2026-11-28

**Status: implementation submitted for CI and independent review; not merged.** Phase 1 is tracked in [PR #208 — Audit repository correctness and add bounded performance benchmarks](https://github.com/ultron1846-oss/ULTRON/pull/208), stacked on the integrated readiness candidate PR #207 rather than directly on main.

- Branch: audit/repository-quality-phase1-2026-11-28
- Base branch: full-system-readiness-batch-7-2026-11-28 at 4b9308bcbc8a96b24af4c67a0a9bb90fd63ece85
- Latest code/test head with all five workflows passing: 15a7d518fd4aeadcd4166b792282f306600e1e2e.
- Latest audit-report update before this README edit: b0a81f6bc0139f4ff6c7b48de8f65e605d6c9e2c.
- PR #208 stacks on the PR #207 integration branch; 16 changed paths, open and unmerged. Current exact head must be refreshed after this README commit.
- Audit report: docs/PHASE1_REPOSITORY_AUDIT_2026-11-28.md.

### Confirmed fixes

1. Tokenizer resource budget: added max_tokens to MathTokenizer.tokenize/encode. Tokenization stops before materializing token objects beyond the budget. Both in-memory and indexed dataset adapters enforce max_sequence_length during tokenization, and inference bounds prompt encoding while reserving generation space. Added tokenizer, dataset and inference regression coverage.
2. Indexed dataset benchmark isolation: when this process owns tracemalloc, the benchmark measures its own peak. When a caller already owns the process-global tracer, it does not reset or stop that tracer and reports the benchmark-specific peak as unavailable. Added a regression proving prior caller allocations are not misreported and tracer state remains intact.
3. Inference API contract: compressed inference now normalizes invalid device input to the same clear ValueError used by ordinary inference. Added a negative test.
4. Browser memory listing: listRecords previously read every IndexedDB record using getAll(), sorted the full store in JavaScript, and only then applied the 100/500-row UI limit. IndexedDB v2 now creates a createdAt index on all four stores and listRecords reads a reverse cursor only until the requested limit. Migration backfills legacy missing timestamps with an empty sort key. Exported/imported backups remain schema version 1. Regression tests verify v1-to-v2 migration, legacy row retention, backup-version compatibility, and that requesting 25 records from a 1,500-record store visits exactly 25 cursor entries with no getAll() call.

### Benchmark harness

Added tools/benchmark_phase1.py and .github/workflows/phase1-benchmarks.yml. The PR-targeted job measures the trie tokenizer against a reference full-vocabulary scanner, a temporary synthetic disk-backed dataset fixture, small random-initialized CPU forward latency at sequence lengths 16/32/64, separate attention/router latency, checkpoint save/load, checkpoint-backed inference at several prompt sizes, and raw/gzip frontend asset transfer-size proxies. It uploads a JSON artifact. No device-dependent performance thresholds are added.

### Validation boundary and measured results

Latest code/test head 15a7d518fd4aeadcd4166b792282f306600e1e2e passed all five workflows:

| Workflow | Run ID | Result |
| --- | ---: | --- |
| Tests | [46116772850](https://github.com/ultron1846-oss/ULTRON/actions/runs/46116772850) | 130 passed, 0 failed |
| Python AI Core | [46116772844](https://github.com/ultron1846-oss/ULTRON/actions/runs/46116772844) | 734 tests passed; CPU forward/backward only, no optimizer step |
| Level 1 Math Tooling | [46116772851](https://github.com/ultron1846-oss/ULTRON/actions/runs/46116772851) | 5 passed, including the workflow's 5,000 randomized cases |
| Security/dependency audit | [46116772867](https://github.com/ultron1846-oss/ULTRON/actions/runs/46116772867) | Passed; npm audit 0 vulnerabilities; pip-audit no known vulnerabilities in the three declared groups |
| Phase 1 performance benchmarks | [46116772901](https://github.com/ultron1846-oss/ULTRON/actions/runs/46116772901) | Passed; JSON artifact uploaded as ultron-phase1-benchmark (artifact ID 15252171168) |

Benchmark conditions: GitHub-hosted Linux CPU runner, AMD EPYC 9V74, 4 logical CPUs exposed, Python 3.11.18, PyTorch 2.15.0+cpu, Node 22.23.5, one Torch CPU thread, seed 20261128, three warmups and 12 repetitions. The model was a 42,593-parameter random-initialized smoke model, batch 2, sequence lengths 16/32/64—not the 60M+ foundation model.

Measured results:
- Tokenizer: reference scanner about 129k tokens/s; trie about 1.10M tokens/s; observed 8.50x ratio on five fixed supported expressions (91 tokens/iteration).
- 3,500-row temporary indexed dataset: 1.292s index build, 23,958 rows/s sequential scan, random-access median 0.071ms and p95 0.083ms.
- Small model forward median: 0.758ms / 0.810ms / 0.963ms for sequence lengths 16 / 32 / 64. Attention component median 0.054ms; top-k router 0.024ms.
- Tiny checkpoint: 201,747 bytes. In the first successful measurement run, median save was 318.5ms and load 6.24ms; timings vary substantially between hosted CI runs. The later successful run measured about 6.14ms median save and 5.39ms load. Inference with two generated tokens: median 1.819ms / 1.921ms / 2.021ms for nominal 8 / 24 / 48 token prompts.
- Frontend assets: 127,907 raw bytes and 40,620 deterministic gzip bytes across 13 files.

The initial benchmark attempt failed because a test expression used unsupported tokenizer command \sin; the benchmark correctly rejected it. The fixture was changed to an expression composed only of supported vocabulary tokens. The corrected benchmark run above passed. The tokenizer scope itself was not expanded.

These are CI observations, not device-independent performance guarantees. The dataset is synthetic. The RSS figure is a process high-water mark, and tracemalloc excludes native SQLite/Torch/device allocations. No CUDA or full-size model profile was performed. Frontend byte counts are transfer-size proxies, not browser page-load measurements.

No local test commands were run because this environment could not clone the repository over its network. The audit is risk-based, not a line-by-line verification of every file. Full-size 60M+ memory/CUDA profiling, production dataset results, browser load timing and real iPad acceptance remain outstanding. PR #208 has not received independent review and remains unmerged. PR #207 itself also remains open pending its own independent review.

The audit report also records the second successful benchmark artifact and the browser-memory store fix. This README update itself creates a new PR head; exact-head workflows are being rechecked. Do not merge until those checks pass on the latest head and an independent review is recorded.

No ULTRON training, optimizer steps, model weight updates, production corpus generation/download, external AI API call, Supabase mutation, Pages deployment or remote training job occurred.


## Phase 2 mathematics curriculum and Green's theorem

**Status:** bounded Green's theorem family implemented; curriculum audit and evidence-backed registry updated; exact-head CI passed. PR #209 remains open and unmerged pending independent review and the upstream review gates.

### Repository state

- Repository: ultron1846-oss/ULTRON
- Branch: phase2/green-theorem-curriculum-batch-2026-11-28
- Latest source commit validated: 8bed24b56430413db2bef4703265bedc7178417a
- PR: [#209 — bounded exact-rational Green's theorem and curriculum evidence audit](https://github.com/ultron1846-oss/ULTRON/pull/209)
- Base: audit/repository-quality-phase1-2026-11-28, head 26d0d940b8f3a62edb5a682169049a0094b6a1c1 (PR #208). PR #208 is itself stacked on PR #207. Preserve the chain; do not merge the child PR independently.

### Coverage counts

Counts are computed from the scope-qualified combined registry and the validation evidence manifest—not from catalogue presence alone.

| State | Current candidate |
| --- | ---: |
| Catalogued scope entries | 255 |
| Generator available | 114 |
| Independently validated exercise topics | 63 |
| Benchmarked on a compatible trained checkpoint | 0 |
| Mastered on a compatible trained checkpoint | 0 |

University curriculum: **202 topics**, **61 generator-available**, **141 catalogued but not implemented**. The former Green_stokes_divergence_theorems umbrella is split into greens_theorem_rectangles, stokes_theorem, and divergence_theorem. Only the bounded Green rectangle family has a generator. Stokes and divergence remain incomplete.

The prerequisite graph covers all 202 university topics and 378 edges. The combined registry has 255 unique scoped IDs; raw linear_equations labels occur in Core, G7–8, and G8–9, but scoped ID collisions are zero.

### Green's theorem contract

tools/math_generators/university/green_theorem.py supports exact rational sparse polynomial vector fields P(x,y), Q(x,y) over non-degenerate axis-aligned rectangles with rational bounds.

- Total degree at most 5; at most 8 terms in each polynomial; at most 12 combined terms (the conservative operation budget may reject some lower-term cases).
- Coefficient numerator absolute value at most 1,000; denominator at most 100.
- Rectangle-bound numerator absolute value at most 100; denominator at most 20.
- Conservative estimated exact-operation budget at most 256.
- Counter-clockwise boundary integration is evaluated separately over all four rectangle edges. The area side separately computes dQ/dx-dP/dy and integrates over the rectangle.
- All arithmetic is exact Fraction; exact equality is required. Clockwise orientation reverses both signs.
- Invalid input, unsupported expressions, duplicate monomials, zero coefficients, booleans/floats in integer fields, excessive degree/terms/budgets, malformed rationals, unsupported orientation, and degenerate/reversed rectangles are rejected.
- verify_green_problem recomputes the integrals and reconstructs the entire expected generated object; changed answer, prompt, steps, metadata, ingredients, or extra fields fail verification.

This does not support arbitrary regions, curved boundaries, non-polynomial fields, general Green-theorem automation, Stokes' theorem, or the divergence theorem.

### Exact-head CI results

All five required workflows passed on exact code/docs candidate head 8bed24b56430413db2bef4703265bedc7178417a on 2026-11-28.

| Validation | Exact command / workflow | Result |
| --- | --- | --- |
| Python AI Core | python -m unittest discover -s tests/python -v | **742 tests passed** |
| CPU model smoke | python -m ultron_core.smoke --device cpu --batch 2 --sequence 8 | Forward/backward smoke passed; **no optimizer step or training** |
| Level 1 Math Tooling | pytest -q | **5 passed**, workflow includes 5,000 randomized cases |
| Node/frontend tests | npm ci then npm test | **130 tests passed** |
| Frontend/security checks | frontend workflow | Passed |
| Python dependency audit | pip-audit -r requirements-ai.txt; pip-audit -r requirements-test.txt; pip-audit -r requirements-seed.txt | No known vulnerabilities in all three declared groups |

Workflow run IDs:
- Python AI Core: [46119241376](https://github.com/ultron1846-oss/ULTRON/actions/runs/46119241376)
- Level 1 Math: [46119241434](https://github.com/ultron1846-oss/ULTRON/actions/runs/46119241434)
- Node tests: [46119241419](https://github.com/ultron1846-oss/ULTRON/actions/runs/46119241419)
- Frontend and dependency audit: [46119241429](https://github.com/ultron1846-oss/ULTRON/actions/runs/46119241429)

The repository was validated by GitHub Actions; no local clone or local test execution was available in this session. The successful runs do not establish performance on full-size ULTRON or a trained checkpoint. No generator throughput benchmark or trained-model math benchmark was run for this Phase 2 batch.

### Files changed in PR #209

- README.md
- docs/MATH_CURRICULUM_AUDIT_2026-11-28.md
- docs/PRETRAINING_READINESS.md
- docs/UNIVERSITY_PREREQUISITES.md
- tests/python/test_grade8_12_generators.py
- tests/python/test_greens_theorem_generator.py
- tests/python/test_math_coverage_audit.py
- tests/python/test_math_foundation.py
- tests/python/test_university_math_generators.py
- tests/python/test_university_prerequisites.py
- tools/math_generators/build_registry.py
- tools/math_generators/coverage_audit.py
- tools/math_generators/grade1_4/registry.json
- tools/math_generators/grade5_8/registry.json
- tools/math_generators/grade8_12/registry.json
- tools/math_generators/registry.json
- tools/math_generators/university/curriculum.json
- tools/math_generators/university/generators.py
- tools/math_generators/university/green_theorem.py
- tools/math_generators/university/prerequisites.json
- tools/math_generators/university/registry.json
- tools/math_generators/validation_manifest.json

### Review status, remaining risks, and next task

PR #209 has no independent submitted review or inline review threads, and must remain open. PR #208 and PR #207 also remain open pending their own independent reviews and exact-head checks. No merge has been performed.

Remaining work:
- 138 university topics still have no registered generator.
- Zero topics are benchmarked on a compatible trained model; zero are mastered.
- Broad compound curriculum entries complex_numbers_and_topology and Taylor_and_Laurent_series need syllabus-level scope review before splitting.
- Global difficulty progression is not defined consistently across topic families. Green now defines difficulty levels 1–5 by maximum polynomial total degree; other families need explicit per-level progression.
- Grade-band prerequisite dependencies remain to be mapped separately.
- Existing first_order_ODEs is broader than its current generator, which only generates homogeneous constant-coefficient equations y'=ky with an initial value. This is the next focused scope-correction and independent-validator task; do not claim general first-order ODE support.

**Next concrete task:** implement one additional bounded ODE family, beginning with separable first-order equations, using an independent exact validator and deterministic/tamper/boundary/invariant tests. Keep variable-coefficient linear and exact equations separate until implemented.


### Phase 2 follow-up — first-order ODE scope correction

- Branch: phase2/ode-scope-and-validator-2026-11-28
- Scope: replace the broad first_order_ODEs catalog label with four bounded families. Only homogeneous_constant_coefficient_first_order_ODEs is implemented (y'=k y, y(0)=y0). Separable, variable-coefficient linear, and exact first-order ODE families remain incomplete.
- A new independent analytic validator checks the canonical exponential solution, derivative identity, initial value, difficulty-scaled parameter bounds, and the full generated problem object.
- Candidate counts after the split: 255 combined catalogue entries; 114 generator-available; 63 independently validated; zero trained-model benchmarks; zero mastered topics. University: 202 total, 61 generator-available, 141 not implemented; prerequisite graph 202/378.
- Tests and latest-head CI are still pending for this follow-up branch. Do not interpret this entry as validated until the exact branch head passes all required checks.

No training, optimizer step, production corpus generation/download, external AI API call, remote training job, model-weight publication, Supabase mutation, or Pages deployment occurred.
