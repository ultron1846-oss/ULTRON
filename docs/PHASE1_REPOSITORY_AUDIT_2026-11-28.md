# ULTRON Phase 1 — Repository code audit and optimization

**Assessment date:** 2026-11-28  
**Audit base:** PR #207 integrated readiness candidate, commit 4b9308bcbc8a96b24af4c67a0a9bb90fd63ece85  
**Audit branch:** audit/repository-quality-phase1-2026-11-28  
**Scope:** Repository inventory, risk-based source review, targeted correctness/resource fixes, regression tests, and reproducible engineering microbenchmarks.  
**Status:** Implementation and benchmark harness added; exact-head CI and benchmark artifact are pending. This is not a claim that the whole repository is bug-free.

## 1. Executive summary

The repository-wide inventory at the audit base contained 292 paths (271 files): 151 Python files, 32 JavaScript/MJS files, one TypeScript source file, 84 test files, six GitHub workflow files, and 53 documentation files. These counts include tests and documentation and do not imply that every file received a line-by-line manual audit.

The risk-based review concentrated on high-impact boundaries: tokenizer output allocation, dataset sequence enforcement, checkpoint-backed inference input handling, disk-backed dataset measurement, model attention/router hot paths, runtime-status state management, and repository CI/security boundaries.

Three confirmed issues were fixed:

1. Dataset and inference code checked maximum sequence length only after tokenization had already allocated the complete token sequence. An oversized but syntactically valid row or prompt could therefore allocate substantially more token objects than the configured sequence budget before rejection.
2. The indexed-dataset benchmark could report a process-global tracemalloc peak that included allocations made before the benchmark when the caller already had tracing active. The correction leaves an already-active caller-owned tracer untouched; in that case a benchmark-specific peak is reported as unavailable rather than resetting global state or misreporting prior allocations.
3. The compressed inference loader propagated a raw torch.device construction exception while the ordinary inference loader normalized invalid device inputs to a clear ValueError. The compressed path now uses the same public error contract.

A reproducible CPU benchmark harness and PR-targeted workflow have been added. The harness compares the current trie tokenizer with a reference implementation of the earlier longest-match scan, measures indexed fixture loading, small-model forward passes at multiple sequence lengths, attention/router component latency, checkpoint save/load, checkpoint-backed inference, and frontend raw/gzip transfer-size proxies. It does not profile the 60M+ foundation model, claim trained-model performance, or measure real browser page-load time.

## 2. Repository inventory and baseline

### Repository structure

| Area | Inventory |
| --- | ---: |
| Total paths | 292 |
| Files (blobs) | 271 |
| Python files | 151 |
| JavaScript/MJS files | 32 |
| TypeScript files | 1 |
| Test files | 84 |
| GitHub workflow files | 6 |
| Documentation files | 53 |

The project is split across:
- Browser application and static assets: HTML, CSS, JavaScript modules, browser-local memory, provider/status display, deterministic math tools, and runtime configuration handoff.
- Typed math-engine source: one TypeScript source module with a compiled JavaScript output used by the browser application.
- Python core: configuration and parameter accounting; tokenizer and model; attention, routing, memory and refinement; mathematical parsing/IR and exact arithmetic; generators and verification; dataset manifests, streaming/indexed loading and preflight; checkpoint/recovery; evaluation; inference; compression; resource monitoring and bounded training controller.
- Curriculum generators: grade-band packages and university generators/registries/prerequisite metadata.
- Tests: Node, Python unit/contract/integration tests, property/randomized math tests, and synthetic dataset/checkpoint fixtures.
- CI/security: Node tests, Python AI Core tests, Level 1 math tooling, security/dependency audit, optional seed-data workflow, and Dependabot configuration.
- Documentation: architecture, math engine, data, training/readiness, checkpoint/recovery, inference/compression, security, frontend/device acceptance, and project handoff.

### Dependencies and configuration

The audited candidate uses a locked TypeScript development dependency and npm lockfile. Python runtime dependency policy remains range-based for PyTorch (torch >=2.2,<3.0); test dependencies are separately pinned and audited; optional seed tooling is a distinct dependency group. GitHub Actions are version-tagged rather than pinned to immutable commit SHAs. These are known supply-chain limitations, not changed by this Phase 1 batch.

Important contracts reviewed include canonical tokenizer version/vocabulary/PAD ID; runtime configuration schema and non-authorizing flags; provider-directory schema; dataset and split manifest hashes; model configuration and 60M trainable-parameter floor; checkpoint format, checksum/metadata sidecars, model-state compatibility, RNG/sampler/scheduler metadata; and training-controller authorization/resource/step boundaries.

### Exact baseline before Phase 1 changes

PR #207 head 4b9308bcbc8a96b24af4c67a0a9bb90fd63ece85 had all four existing workflows completed successfully:

| Workflow | Run ID | Recorded result |
| --- | ---: | --- |
| Tests | 46115096949 | 128 Node tests passed, 0 failed |
| Python AI Core Tests | 46115096953 | 725 Python tests passed; CPU forward/backward smoke only |
| ULTRON Level 1 Math Tooling | 46115096965 | Workflow passed (five fixed tests plus the workflow's 5,000 randomized cases) |
| Security and dependency audit | 46115096956 | Passed; npm audit found 0 vulnerabilities; pip-audit reported no known vulnerabilities in the three declared dependency groups |

The Python smoke explicitly reported no optimizer step and no training run. These are baseline results for PR #207, not results for this Phase 1 branch. New exact-head results must be recorded separately below after the Phase 1 pull request checks complete.

## 3. Prioritized findings

Severity definitions: P1 means a resource or correctness boundary could be bypassed in ordinary use; P2 means a measurement/API-contract defect that could mislead callers or reviewers; P3 means an explicit coverage/performance acceptance gap.

| Severity | Evidence and location | Action |
| --- | --- | --- |
| P1 — unbounded token materialization before sequence rejection | The in-memory and indexed dataset adapters tokenized the complete Question/Answer string, then checked the token count. Checkpoint-backed inference did the same with prompts. The tokenizer had no max-token contract. | Fixed by adding max_tokens to tokenize/encode; the scanner now stops before creating token objects beyond the budget. Dataset adapters and inference pass their sequence budget into tokenization and preserve explicit no-truncation behavior. Regression tests cover tokenizer budget accounting, in-memory and indexed datasets, and inference prompts. |
| P2 — benchmark peak contaminated by prior tracing | tools/benchmark_verified_dataset.py called get_traced_memory when tracemalloc was already active and could report allocations made before the benchmark as its own peak. | Fixed. The benchmark only reports a peak when it owns the tracing session. When a caller already owns tracing, the function records the baseline, does not reset or stop the tracer, and returns null for the benchmark-specific peak. A regression test creates unrelated prior allocations and verifies that the caller's tracer remains intact. |
| P2 — inconsistent compressed inference device error | load_compressed_inference_engine constructed torch.device outside the normalization guard used by load_inference_engine. Invalid device input could expose a raw Torch exception rather than the documented ValueError contract. | Fixed with the same normalized error message and a negative regression test. |
| P2 — benchmark coverage incomplete | Existing benchmark tooling covered indexed dataset construction/scan/random access and a single-config inference smoke, but did not consolidate tokenizer comparison, multi-length forward latency, attention/router components, checkpoint save/load, inference latency by prompt size, and frontend transfer-size data into one reproducible report. | Added tools/benchmark_phase1.py and a dedicated PR-targeted GitHub workflow. The initial unsupported \\sin sample was corrected to use the existing tokenizer vocabulary. Corrected benchmark workflows pass and upload JSON artifacts. |
| P2 — unbounded browser memory-list materialization | memory-store.js listRecords used getAll(), sorted all IndexedDB rows in JavaScript, then sliced to the requested 100/500-row display limit. This allowed a bounded UI request to allocate and sort the entire growing store. | Fixed by adding a version-2 IndexedDB schema with a createdAt index on all four stores and a reverse cursor limited to the requested 1–500 records. The migration backfills missing timestamps with an empty string. The exported/imported backup contract remains version 1. New tests cover v1-to-v2 migration, legacy records without timestamps, backup-version compatibility, and exact cursor-visit limits. |
| P3 — full-size and real-device performance unmeasured | The small model and synthetic dataset cannot establish the 60M+ model's memory/latency on intended hardware. Static frontend transfer bytes do not establish browser load time. | No claim made. The benchmark report explicitly separates CPU CI measurements from CUDA, target-device, production dataset, and real-browser owner acceptance. |
| P3 — indexed manifest metadata has an O(N) component | The disk-backed store streams record payloads and stores row offsets in SQLite, but selected split-ID metadata is parsed into Python structures under an explicit dataset/preflight cap. | Retained and documented as a bounded design limitation. No unmeasured redesign was made. |
| P3 — no full learned capability evidence | The foundation architecture is formula-counted at 63,400,451 total / 61,826,048 trainable parameters, but has not been fully instantiated/profiled or trained. | No training or full-size allocation was attempted. Random initialized inference/benchmark results are software-pipeline measurements only. |

## 4. Changes and regression coverage

### Bounded tokenizer output

- Added TokenLimitExceeded and max_tokens validation.
- MathTokenizer.tokenize accepts an optional token budget and raises as soon as the next lexical token would exceed it.
- MathTokenizer.encode accounts for requested BOS/EOS IDs in the total budget, then passes only the remaining lexical budget into tokenization.
- Default behavior without max_tokens remains compatible with the previous tokenizer contract.
- Dataset adapters pass max_sequence_length before token-list materialization; oversized examples still fail without truncation.
- Inference reserves the BOS and at least one output position before scanning the prompt; prompts that cannot fit fail with a clear ValueError.

Regression coverage:
- Exact-fit lexical input and BOS/EOS budget accounting.
- Exceeding token budget stops early with TokenLimitExceeded.
- Invalid boolean/negative/non-integer budgets rejected.
- Both in-memory and indexed disk-backed dataset adapters pass their configured limit to the tokenizer and still reject oversized rows.
- Inference overlong prompt is rejected without truncation.

### Benchmark measurement ownership

- When the benchmark starts tracemalloc itself, it reports the peak allocation observed during its own run.
- When tracing is already active, it does not reset or stop the caller's tracer. Its benchmark-specific peak is null because the global tracer cannot isolate an independent peak without changing caller-owned state.
- Existing caveats remain: tracemalloc excludes native SQLite, PyTorch allocator memory, process RSS, and device memory.

Regression coverage uses a prior unrelated allocation to ensure the benchmark does not misattribute it or mutate the tracing session.

### Inference device error contract

- Compressed checkpoint inference now normalizes invalid torch.device values to the same ValueError contract as ordinary checkpoint inference.
- Regression test ensures invalid device input is rejected before attempting to open checkpoint/artifact files.

### Bounded IndexedDB memory listing

- Increased the IndexedDB schema version from 1 to 2 and added a non-unique createdAt index to all four object stores.
- Version upgrade backfills legacy rows without string createdAt values using an empty string. This keeps legacy records queryable and preserves the former sort convention in which missing timestamps appear last.
- listRecords now uses a reverse cursor on createdAt and stops after the bounded display limit (1–500); it no longer calls getAll() or sorts the full object store for list views.
- The portable JSON backup schema remains version 1 through a separate BACKUP_VERSION constant, so an internal database schema migration does not make existing exported backups incompatible.
- tests/memory-store-indexeddb.test.js now models indexes/cursors and checks: legacy v1 migration, all four index creations, legacy timestamp handling, backup schema compatibility, and a 1,500-record fixture where requesting 25 rows visits exactly 25 cursor entries and does not call getAll().
- The exportMemory backup path still intentionally materializes a complete bounded export (20 MB safety cap); this change only bounds list views, not full backup serialization.

### Reproducible performance harness

tools/benchmark_phase1.py reports:
- Tokenizer tokens/second and timing for the trie implementation compared with a same-process reference full-vocabulary longest-match scanner. Token IDs must match before timing is accepted.
- Synthetic 3,500-row verified indexed dataset benchmark with split counts, index-build time, sequential scan rate, random-access latency, disk bytes, and the benchmark's declared memory limits.
- Small randomly initialized CPU model forward latency at sequence lengths 16, 32 and 64, batch size 2.
- Separate attention and top-k router component latency.
- Checkpoint save/load latency and serialized byte size using a tiny model, no optimizer state and no RNG restoration.
- Checkpoint-backed inference latency for prompt sizes around 8, 24 and 48 tokens.
- Frontend asset raw and deterministic gzip transfer-size proxies.
- OS, CPU, Python, PyTorch, Node, thread, seed, warm-up and repetition metadata.
- Explicit flags proving this benchmark did not generate production corpus data, download external data, create an optimizer, update model weights, train, or dispatch remote jobs.

The workflow is restricted to pull requests targeting the integrated readiness branch. It publishes a JSON artifact for review and applies no hardware-dependent performance thresholds.

## 5. Validation commands and current evidence

The following commands define the local equivalents. This execution environment could read and update GitHub files and inspect Actions results but could not clone the GitHub repository over the container network; no claim of a local command run is made.

npm ci  
npm test

python -m unittest discover -s tests/python -v  
python -m ultron_core.smoke --device cpu --batch 2 --sequence 8

cd tools/level1_math  
python -m pip install -r ../../requirements-ai.txt -r ../../requirements-test.txt  
pytest -q

The Phase 1 benchmark workflow invokes:

python -m tools.benchmark_phase1 --output artifacts/phase1-benchmark.json

**Phase 1 implementation/test validation — commit 15a7d518fd4aeadcd4166b792282f306600e1e2e:**

| Workflow | Run ID | Result |
| --- | ---: | --- |
| Tests | [46116772850](https://github.com/ultron1846-oss/ULTRON/actions/runs/46116772850) | Success; 130 Node tests passed, 0 failed, including the v2 IndexedDB migration and cursor-bound tests |
| Python AI Core Tests | [46116772844](https://github.com/ultron1846-oss/ULTRON/actions/runs/46116772844) | Success; 734 tests passed; CPU forward/backward smoke passed with no optimizer step |
| ULTRON Level 1 Math Tooling | [46116772851](https://github.com/ultron1846-oss/ULTRON/actions/runs/46116772851) | Success; 5 tests passed; workflow covers 5,000 randomized cases |
| Security and dependency audit | [46116772867](https://github.com/ultron1846-oss/ULTRON/actions/runs/46116772867) | Success; npm audit 0 vulnerabilities; pip-audit reported no known vulnerabilities in all three declared groups |
| ULTRON Phase 1 performance benchmarks | [46116772901](https://github.com/ultron1846-oss/ULTRON/actions/runs/46116772901) | Success; uploaded JSON artifact |

Latest benchmark artifact: workflow run 46116772901, artifact name ultron-phase1-benchmark, artifact ID 15252171168 (4,559 bytes). The benchmark was rerun after the IndexedDB code change. The detailed numeric table below is the explicitly decoded measurement set from successful run 46116204496; the repeated run above confirms the harness still completes on the later code head.

### Measured Phase 1 benchmark results

Environment: GitHub-hosted Linux runner, CPU AMD EPYC 9V74, 4 logical CPUs exposed to the job, Python 3.11.18, PyTorch 2.15.0+cpu, Node 22.23.5, one PyTorch CPU thread. Seed 20261128; three warm-ups and 12 measured repetitions for tokenizer/model/dataset throughput timing. Model batch size 2; forward sequence lengths 16, 32 and 64. The model contained 42,593 randomly initialized parameters; it was not the 60M+ foundation model.

| Area | Measured result | Conditions / limit |
| --- | --- | --- |
| Tokenizer | Reference scanner 129,231 tokens/s; trie 1,098,192 tokens/s; ratio 8.50x | Five fixed supported math inputs; 112 characters and 91 tokens per iteration. Token ID equivalence checked first. One CI CPU runner; not a device guarantee. |
| Indexed dataset | 3,500 rows; build 1.292 s; full scan 0.146 s (23,958 rows/s); random access median 0.071 ms, p95 0.083 ms | Temporary synthetic fixture; 100 random accesses. Snapshot 1,380,474 bytes; SQLite index 1,859,584 bytes; tracemalloc peak 33,575,212 bytes. Native SQLite/Torch/RSS/device memory are excluded from tracemalloc. |
| Small-model forward | Median 0.758 ms at sequence 16; 0.810 ms at 32; 0.963 ms at 64 | Batch 2; CPU, random weights, 12 repetitions after warm-up. |
| Attention / router components | Attention median 0.054 ms; top-k router median 0.024 ms | Isolated component microbenchmarks on the same tiny configuration; not full model FLOPs. |
| Checkpoint | Save median 318.5 ms; load median 6.24 ms; serialized file 201,747 bytes | Three save/load iterations, tiny model, no optimizer state, RNG not restored. |
| Checkpoint-backed inference | Median 1.819 ms for an 8-token prompt; 1.921 ms at 24; 2.021 ms at 48; two generated tokens | Eight measured repetitions per prompt size; random-initialized small model; no quality claim. |
| Frontend assets | 127,907 raw bytes; 40,620 deterministic gzip bytes across 13 assets | Static transfer-size proxy only; no browser/network waterfall or page-load time measurement. |
| Process memory | 341,680,128 bytes process high-water RSS | Run-wide high-water mark, not per-component peak memory. No CUDA available. |

The first attempt of the new benchmark workflow (run 46116108239) correctly failed because one selected sample used the unsupported tokenizer command \\sin. The fixture was replaced with a supported expression using only commands and symbols in the canonical vocabulary; tokenizer scope was not expanded. The corrected benchmark workflow passed as run 46116204496. This failed first attempt is retained in the history, not counted as a successful measurement.

These values are reproducible CI observations under the listed conditions, not stable performance thresholds or predictions for iPad, a free cloud runtime, production data, CUDA or the foundation model.

## 6. Scope limits and unresolved audit areas

This is a risk-based engineering pass, not proof of absence of bugs. The inventory is repository-wide, but the source review prioritizes high-risk execution and data boundaries and is not a formal line-by-line verification of all 151 Python files and all JavaScript/TypeScript modules.

Still outstanding:
- Full line-by-line review of remaining math generators, parser/verifier edge cases, checkpoint restore and rollback paths, training controller/resource enforcement, compression transforms, and all frontend event/state paths.
- CUDA/target-device profiling, full 60M+ model memory measurements, and attention/router measurements on representative hardware.
- Production dataset benchmarking with owner-provided existing and verified data; the CI fixture is synthetic.
- Actual iPad Safari and real browser network/paint/page-load measurement.
- Eager versus indexed loader comparison under identical conditions; no speedup claim is made.
- Full static dependency/license inventory, immutable GitHub Action SHA pinning, and owner-side GitHub/Supabase security decisions remain outside this Phase 1 code fix batch.
- Exact interrupted-versus-uninterrupted optimizer-step equivalence remains untested and still gated by separate authorization.

No training, optimizer step on ULTRON weights, production corpus generation/download, external AI API call, Supabase mutation, Pages deployment, or remote training job was performed.

## 7. Phase status and next task

**Phase 1 status: five confirmed fixes/improvements and their regression coverage passed on implementation/test head 15a7d518fd4aeadcd4166b792282f306600e1e2e; all five workflows and the repeated benchmark artifact passed. Repository-wide audit remains risk-based and incomplete. The PR is unmerged pending independent review; a documentation-only follow-up commit still requires exact-head workflow confirmation.**

The next task after this audit batch is to resolve review feedback, verify all exact-head checks and benchmark artifact, and have an independent reviewer assess the Phase 1 PR. Do not merge while independent review is absent. PR #207 also remains open and unmerged because its own independent-review gate is still unsatisfied.

After the integration/review gates are cleared, proceed to the bounded exact-rational Green's theorem generator for the university catalog entry Green_stokes_divergence_theorems. Stokes' theorem and the divergence theorem must remain incomplete until separately implemented and validated.
