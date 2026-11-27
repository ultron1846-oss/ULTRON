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
