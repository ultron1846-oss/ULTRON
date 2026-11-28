# Verified indexed dataset benchmark

Run the benchmark only against a dataset and split manifest that already exist and have been verified:

```sh
python -m tools.benchmark_verified_dataset \
  --dataset /path/to/existing.jsonl \
  --split-manifest /path/to/existing.splits.json \
  --random-access-samples 100 \
  --seed 2026 \
  --output reports/indexed-loader-benchmark.json
```

The command validates and snapshots the source dataset, builds the SQLite offset index, scans each selected split with bounded record iteration, and performs deterministic random-access samples. It reports dataset and split digests, index build time, sequential rows/second, median and p95 random-access latency, snapshot/index disk bytes, and Python allocation peak traced by `tracemalloc`.

**Measurement limits:** `tracemalloc` does not capture native SQLite allocations, PyTorch tensors, total process RSS, GPU memory, or device allocator overhead. This benchmark does not compare against the eager loader and therefore cannot establish a speedup or a complete memory reduction ratio. To make a fair comparison, run both implementations against the same frozen dataset, device/runtime, process conditions, and commit; report all limitations.

The benchmark is read-only with respect to the input dataset. It does not generate or download corpus data, instantiate ULTRON weights, train, restore checkpoints, or dispatch remote jobs. A temporary verified snapshot and SQLite index are created and removed when the run ends.


**Output safety:** The CLI rejects output paths that resolve to the dataset or split manifest, including symlink and hard-link aliases, so writing the JSON report cannot overwrite either input. The benchmark only snapshots and reads the input data; the report is written to a separate path.


## Stress validation merged in PR #201

The proposed regression suite exercises a 3,500-row synthetic dataset across all filtered splits, incremental record iteration, first/last random access, and deterministic repeated reads. It also tests a 2,400-row benchmark smoke, tampered snapshot-record rejection, corrupted dataset/incomplete split-manifest rejection, idempotent close/removal, and temporary-directory cleanup after invalid manifest construction. These are correctness/resource-lifecycle tests, not a production memory profile. The benchmark's Python `tracemalloc` value excludes native SQLite, process RSS, PyTorch, and device memory. A production dataset must be supplied before reporting production throughput or memory.


## Explicit memory-boundary interpretation

The indexed path bounds record payload handling, but it is not fully constant-memory with respect to dataset size. The verified snapshot is copied in 1 MiB chunks; each JSONL record is limited to 8 MiB; the SQLite page cache is configured to about 2 MiB; index-build reads use batches of 1,024; and split iteration fetches 256 index rows at a time while decoding one record per yield. The selected row payloads are not accumulated as a full Python list. However, the split-manifest ID arrays are currently parsed into Python memory, bounded by the repository's 100,000-row preflight limit, so metadata memory grows with selected example count. A future manifest/index protocol would be needed to remove that O(N) ID-list component. This distinction must be included in any memory report.


## Phase 3 resource policy

The loader and semantic split path now accept a shared immutable DatasetResourceLimits policy. Defaults and hard ceilings are defined in ultron_core/dataset_resource_limits.py. The policy controls:

- source dataset bytes, row count, per-line bytes and dataset-sidecar manifest bytes;
- split-manifest byte size;
- snapshot copy chunk size;
- SQLite page-cache KiB;
- SQLite index-build batch size and iterator fetch batch size;
- SQLite index bytes and combined temporary-directory bytes.

The benchmark CLI exposes these values as --max-dataset-bytes, --max-rows, --max-line-bytes, --max-dataset-manifest-bytes, --max-split-manifest-bytes, --snapshot-copy-chunk-bytes, --sqlite-cache-kib, --index-build-batch-rows, --iterator-fetch-rows, --max-index-bytes and --max-temporary-bytes. It records the selected resource policy plus Python, platform and SQLite versions. The verified-loader and non-authorizing preflight APIs accept the same policy object.

The SQLite index configures PRAGMA max_page_count from the smaller of the index-byte cap and the temporary-disk remainder after the snapshot copy. Temporary-directory usage is inspected during snapshot copying and after index construction; configured caps reject an input rather than silently truncate. The split builder and quality audit also cap their temporary SQLite databases. These limits govern the paths explicitly measured and are not a guarantee about all OS-level filesystem accounting or unrelated processes.

## Additional synthetic stress coverage in the Phase 3 candidate

The candidate regression set adds:

- independent concurrent readers and deterministic per-split order;
- configured boundary rejection for dataset bytes, manifest bytes, rows, lines, SQLite index bytes and temporary bytes;
- missing and truncated input handling;
- duplicate split IDs with a recomputed manifest digest, plus manifest hash mismatch;
- failure injection during partial snapshot creation and during index insertion;
- corrupted ephemeral index detection followed by a clean rebuild from the original unchanged source;
- repeated open/iterate/close cycles with Linux file-descriptor accounting where /proc/self/fd exists;
- a 12,000-row synthetic dataset and a greater-than-500-KiB split manifest;
- deterministic quality-report replay, answer rechecking and dataset mutation detection during the audit read pass.

The 12,000-row test and fixture benchmarks are correctness/stress evidence only. No measured numbers are presented as production RSS, native SQLite memory, device-memory behavior or free-tier service capacity. The actual quality report and benchmark must be run against an owner-supplied, already-existing dataset before any production performance or distribution claim is made.
