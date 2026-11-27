"""Stress tests for the verified disk-backed dataset path.

Fixtures are temporary and synthetic. These tests do not generate a training
corpus, instantiate ULTRON weights, or train.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_dataset_split_manifest import fixture
from ultron_core.dataset_split_manifest import prepare_dataset_split_manifest
from ultron_core.indexed_verified_dataset import VerifiedIndexedSplitStore
from tools.benchmark_verified_dataset import benchmark_indexed_dataset


class IndexedDatasetStressTests(unittest.TestCase):
    def _prepare(self, root, count=3500):
        dataset = root / "stress.jsonl"
        split = root / "stress.splits.json"
        fixture(dataset, count, duplicate=False)
        prepare_dataset_split_manifest(dataset, split, split_seed=29)
        return dataset, split

    def test_large_filtered_stream_and_boundary_random_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset, split = self._prepare(root)
            payload = json.loads(split.read_text(encoding="utf-8"))
            with VerifiedIndexedSplitStore(dataset, split) as store:
                self.assertEqual(sum(store.split_counts.values()), 3500)
                self.assertGreater(store._index_path.stat().st_size, 0)
                for split_name in ("train", "validation", "test"):
                    expected_ids = set(payload["split_ids"][split_name])
                    iterator = store.iter_records(split_name)
                    self.assertIn(next(iterator)[0], expected_ids)
                    count = 1 + sum(1 for _ in iterator)
                    self.assertEqual(count, store.split_counts[split_name])
                    self.assertEqual(len(expected_ids), count)
                    first = store.get_record(split_name, 0)
                    last = store.get_record(split_name, count - 1)
                    self.assertEqual(first, store.get_record(split_name, 0))
                    self.assertEqual(last, store.get_record(split_name, count - 1))
                self.assertFalse(store._closed)

    def test_benchmark_reports_measured_metrics_without_overclaiming(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset, split = self._prepare(root, count=2400)
            report = benchmark_indexed_dataset(
                dataset, split, random_access_samples=32, seed=20261127
            )
            self.assertEqual(report["dataset_example_count"], 2400)
            self.assertEqual(report["sequential_scan"]["rows_scanned"], 2400)
            self.assertGreaterEqual(report["index_build_seconds"], 0)
            self.assertGreaterEqual(report["sequential_scan"]["elapsed_seconds"], 0)
            self.assertGreater(report["sequential_scan"]["rows_per_second"], 0)
            self.assertEqual(report["random_access"]["samples"], 32)
            self.assertIsNotNone(report["random_access"]["median_latency_ms"])
            self.assertIsNotNone(report["random_access"]["p95_latency_ms"])
            self.assertIn("tracemalloc", report["memory_measurement_scope"])
            self.assertIn("excludes native SQLite", report["memory_measurement_scope"])
            self.assertFalse(report["dataset_modified"])
            self.assertFalse(report["training_performed"])
            self.assertTrue(dataset.is_file())

    def test_snapshot_record_corruption_fails_integrity_check(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            store = VerifiedIndexedSplitStore(dataset, split)
            try:
                record = store._connection.execute(
                    "SELECT byte_offset FROM ordered_records WHERE split_name='train' AND seq=0"
                ).fetchone()
                offset = record[0]
                store._snapshot_path.chmod(0o600)
                with store._snapshot_path.open("r+b") as stream:
                    stream.seek(offset)
                    original = stream.read(1)
                    stream.seek(offset)
                    stream.write(b"!" if original != b"!" else b"?")
                with self.assertRaisesRegex(ValueError, "integrity check failed"):
                    store.get_record("train", 0)
            finally:
                store.close()

    def test_close_is_idempotent_and_removes_snapshot_and_index(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            store = VerifiedIndexedSplitStore(dataset, split)
            temporary_root = Path(store._temporary.name)
            self.assertTrue(temporary_root.exists())
            store.close()
            store.close()
            self.assertFalse(temporary_root.exists())
            with self.assertRaisesRegex(RuntimeError, "closed"):
                store.get_record("train", 0)

    def test_invalid_manifest_construction_cleans_temporary_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            split.write_text("{", encoding="utf-8")
            real_temporary_directory = tempfile.TemporaryDirectory
            created_paths = []

            def tracked_temporary_directory(*args, **kwargs):
                temporary = real_temporary_directory(*args, **kwargs)
                created_paths.append(Path(temporary.name))
                return temporary

            with patch(
                "ultron_core.indexed_verified_dataset.tempfile.TemporaryDirectory",
                side_effect=tracked_temporary_directory,
            ):
                with self.assertRaises(ValueError):
                    VerifiedIndexedSplitStore(dataset, split)
            self.assertEqual(len(created_paths), 1)
            self.assertFalse(created_paths[0].exists())


if __name__ == "__main__":
    unittest.main()
