# ULTRON — Mathematics Intelligence Workspace

**Status snapshot: 2026-11-27**

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
