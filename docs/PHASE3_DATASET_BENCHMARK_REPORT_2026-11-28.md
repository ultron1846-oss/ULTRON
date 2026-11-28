# Phase 3 dataset benchmark report — 2026-11-28

## Status and scope

This report records the read-only verified-dataset benchmark executed on implementation + regression-test revision `17a59284459f503adc4002b70af8d538c043c14d`, including SQLite main/temp page caps, the quality-audit journal-budget regression, writer-side identity checks, and independent parameter-based sample reconstruction.

- GitHub Actions run: [Python AI Core Tests #46154661483](https://github.com/ultron1846-oss/ULTRON/actions/runs/46154661483)
- Job: `python-core`, job ID `141008547123`
- Test command: `python -m unittest discover -s tests/python -v`
- Result: **722 tests passed in 67.686 seconds**
- Additional regressions: journal guards prove main/temp schemas disable journaling before audit writes; the independent checker reconstructs all eight supported topics, rejects tampered ingredients/prompts/answers/difficulty, and the writer rejects parameter tampering even when a content-derived identity is recomputed.
- The 12,000-row input was a temporary synthetic test fixture created within CI; it is not a production corpus and is not retained as project data.
- The benchmark itself reports `data_generated=false`, `dataset_modified=false`, `training_performed=false`, and `optimizer_steps=0`.

## Conditions

| Property | Measured / configured value |
|---|---:|
| Dataset rows | 12,000 |
| Selected split rows | 12,000 |
| Random-access samples | 64 |
| Python | 3.11.18 |
| SQLite | 3.46.1 |
| Runner OS | Ubuntu 26.04.1 hosted runner |
| Platform fingerprint | Linux 7.0.0-1020-azure x86_64, glibc 2.43 |

The benchmark verified the existing fixture and split manifest, built a private immutable snapshot and SQLite offset index, scanned each selected record in deterministic split order, and performed seeded random reads. The fixture and its source metadata were outside the measured dataset-generation work; no production data was created or downloaded.

## Results

| Metric | Result |
|---|---:|
| Verified snapshot copy size | 4,540,482 bytes |
| SQLite index size | 6,291,456 bytes |
| Index build time | 4.812796 seconds |
| Sequential scan duration | 0.500137 seconds |
| Sequential scan throughput | 23,993.42 rows/second |
| Random-read median latency | 0.075542 ms |
| Random-read p95 latency | 0.088531 ms |
| Traced peak Python allocations | 33,575,004 bytes |

These values are from one hosted CI run on the same code/test revision listed above. They are observations, not stable performance guarantees or cross-system comparisons. They are not a speedup comparison against an eager loader. The benchmark output is part of the Python AI Core job log and uses a temporary 12,000-row synthetic fixture.

## Memory and measurement limits

The `tracemalloc` value covers Python allocations traced by the benchmark. It does **not** include native SQLite allocations, all PyTorch tensor allocations, process RSS, operating-system page cache, or device/GPU memory. It must not be presented as total RAM usage.

The reported disk bytes are the private snapshot and SQLite index files at measurement time. They do not establish free-tier service quotas, long-running persistence, or disk behavior on an iPad or another owner device.

## CI validation on the implementation revision

All workflows passed on exact implementation + regression-test revision `17a59284459f503adc4002b70af8d538c043c14d`:

- [Tests / Node Tests — run #46154661494](https://github.com/ultron1846-oss/ULTRON/actions/runs/46154661494): success; command `npm test`.
- [Python AI Core Tests — run #46154661483](https://github.com/ultron1846-oss/ULTRON/actions/runs/46154661483): success; command `python -m unittest discover -s tests/python -v` (722 tests), followed by `python -m ultron_core.smoke --device cpu --batch 2 --sequence 8` (success; forward/backward only).
- [ULTRON Level 1 Math Tooling — run #46154661437](https://github.com/ultron1846-oss/ULTRON/actions/runs/46154661437): success; command `pytest -q`, including the workflow's 5,000 randomized cases.

The CPU smoke is a forward/backward validation only. It does not step an optimizer or update ULTRON weights.

## Acceptance and remaining limitations

The synthetic benchmark demonstrates bounded disk-backed behavior for a 12,000-row fixture, deterministic scans, seeded random access, and a bounded Python-allocation measurement. The resource-limit and stress tests exercise size/row/line boundaries, manifests, index limits, temporary disk limits, concurrency, corruption, interrupted snapshot/index writes, rebuild, and lifecycle cleanup. The read-only quality auditor's disposable SQLite main and temp schemas also disable journaling before writes and are independently page-capped, so rollback-journal growth cannot bypass the configured temporary-disk budget.

It does not demonstrate production-scale corpus performance, complete process/device memory use, or behavior under a specific cloud service's free-tier limits. A production benchmark remains blocked on an owner-supplied, already-existing dataset and an approved execution environment.

Sample schema v1 does not carry prerequisite IDs, explicit boundary/adversarial annotations, per-generator schema versions, source-commit/runtime provenance, or a standalone row-schema version. The quality auditor therefore reports prerequisite coverage and boundary coverage as not assessed, and semantic near-duplicate detection as not assessed. Split-manifest ID arrays and writer ID/index uniqueness sets remain bounded but O(N) in Python memory.

No production corpus was generated or downloaded. No real ULTRON training, optimizer step, remote job, checkpoint publishing, or model-weight publishing occurred. The separate parameter-based checker independently reconstructs the eight supported schema-v1 generator families, but it is not a formally verified proof kernel. PR #220 remains open pending independent review; this report is validation evidence, not production acceptance.
