"""Measure verified indexed-dataset construction and read throughput.

This tool operates only on a caller-supplied existing dataset and split
manifest. It never writes or generates dataset rows and never trains.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import time
import tracemalloc
from pathlib import Path

from ultron_core.indexed_verified_dataset import VerifiedIndexedSplitStore


def benchmark_indexed_dataset(
    dataset_path,
    split_manifest_path,
    *,
    random_access_samples: int = 100,
    seed: int = 0,
) -> dict:
    if (
        isinstance(random_access_samples, bool)
        or not isinstance(random_access_samples, int)
        or not 0 <= random_access_samples <= 10_000
    ):
        raise ValueError("random_access_samples must be in [0, 10000]")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
        raise ValueError("seed must be in [0, 2**63)")

    tracing_started_here = not tracemalloc.is_tracing()
    if tracing_started_here:
        tracemalloc.start()
    store = None
    try:
        build_start = time.perf_counter()
        store = VerifiedIndexedSplitStore(dataset_path, split_manifest_path)
        index_build_seconds = time.perf_counter() - build_start

        sequential_start = time.perf_counter()
        rows_scanned = 0
        for split_name in ("train", "validation", "test"):
            for _record in store.iter_records(split_name):
                rows_scanned += 1
        sequential_seconds = time.perf_counter() - sequential_start
        rows_per_second = (
            rows_scanned / sequential_seconds if sequential_seconds > 0 else None
        )

        total_selected = sum(store.split_counts.values())
        sample_count = min(random_access_samples, total_selected)
        rng = random.Random(seed)
        split_names = tuple(
            split_name
            for split_name in ("train", "validation", "test")
            if store.split_counts[split_name]
        )
        random_latencies_ms = []
        sampled_indices = []
        for _ in range(sample_count):
            global_index = rng.randrange(total_selected)
            split_name = split_names[0]
            index = global_index
            for candidate in split_names:
                candidate_count = store.split_counts[candidate]
                if index < candidate_count:
                    split_name = candidate
                    break
                index -= candidate_count
            sampled_indices.append([split_name, index])
            start = time.perf_counter()
            store.get_record(split_name, index)
            random_latencies_ms.append((time.perf_counter() - start) * 1000)

        median_ms = statistics.median(random_latencies_ms) if random_latencies_ms else None
        p95_ms = (
            sorted(random_latencies_ms)[max(0, math.ceil(0.95 * len(random_latencies_ms)) - 1)]
            if random_latencies_ms
            else None
        )
        _, peak_python_bytes = tracemalloc.get_traced_memory()
        snapshot_bytes = store._snapshot_path.stat().st_size
        sqlite_bytes = store._index_path.stat().st_size
        return {
            "schema_version": 1,
            "benchmark": "verified_indexed_dataset",
            "dataset_manifest_sha256": store.dataset_manifest_sha256,
            "split_manifest_sha256": store.split_manifest_sha256,
            "dataset_example_count": store.dataset_example_count,
            "selected_split_counts": dict(store.split_counts),
            "selected_example_count": total_selected,
            "snapshot_bytes": snapshot_bytes,
            "sqlite_index_bytes": sqlite_bytes,
            "index_build_seconds": index_build_seconds,
            "sequential_scan": {
                "rows_scanned": rows_scanned,
                "elapsed_seconds": sequential_seconds,
                "rows_per_second": rows_per_second,
            },
            "random_access": {
                "seed": seed,
                "samples": sample_count,
                "sampled_indices": sampled_indices,
                "median_latency_ms": median_ms,
                "p95_latency_ms": p95_ms,
            },
            "tracemalloc_peak_python_bytes": peak_python_bytes,
            "memory_measurement_scope": (
                "Python allocations traced by tracemalloc only; excludes native SQLite "
                "allocations, PyTorch tensors, process RSS, and device memory. Not a "
                "complete memory or speedup comparison against the eager loader."
            ),
            "data_generated": False,
            "dataset_modified": False,
            "training_performed": False,
            "optimizer_steps": 0,
            "remote_jobs_dispatched": False,
        }
    finally:
        if store is not None:
            store.close()
        if tracing_started_here:
            tracemalloc.stop()



def _validate_output_path(output_path, dataset_path, split_manifest_path):
    """Reject output paths that resolve to either benchmark input."""
    if output_path is None:
        return
    output = Path(output_path).expanduser().resolve()
    inputs = {
        Path(dataset_path).expanduser().resolve(),
        Path(split_manifest_path).expanduser().resolve(),
    }
    aliases_input = output in inputs
    if not aliases_input and output.exists():
        aliases_input = any(
            input_path.exists() and os.path.samefile(output, input_path)
            for input_path in inputs
        )
    if aliases_input:
        raise ValueError("benchmark output must not overwrite the dataset or split manifest")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--split-manifest", required=True, type=Path)
    parser.add_argument("--random-access-samples", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    _validate_output_path(args.output, args.dataset, args.split_manifest)
    report = benchmark_indexed_dataset(
        args.dataset,
        args.split_manifest,
        random_access_samples=args.random_access_samples,
        seed=args.seed,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        destination = args.output.expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
