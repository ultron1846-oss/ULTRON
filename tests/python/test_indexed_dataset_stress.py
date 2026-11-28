"""Stress tests for the verified disk-backed dataset path.

Fixtures are temporary and synthetic. These tests do not generate a training
corpus, instantiate ULTRON weights, or train.
"""
import json
import os
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless
import unittest
from pathlib import Path
from unittest.mock import patch

from test_dataset_split_manifest import fixture
from ultron_core.dataset_split_manifest import prepare_dataset_split_manifest
import ultron_core.indexed_verified_dataset as indexed_module
from ultron_core.indexed_verified_dataset import IndexedDatasetResourceLimits, VerifiedIndexedSplitStore
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

    def test_corrupt_dataset_and_incomplete_split_manifests_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset, split = self._prepare(root, count=90)
            dataset_manifest = dataset.with_suffix(dataset.suffix + ".manifest.json")
            dataset_manifest.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                VerifiedIndexedSplitStore(dataset, split)

            # Recreate a valid source/sidecar, then remove required split data.
            fixture(dataset, 90, duplicate=False)
            prepare_dataset_split_manifest(dataset, split, split_seed=29)
            incomplete = json.loads(split.read_text(encoding="utf-8"))
            incomplete.pop("split_ids")
            split.write_text(json.dumps(incomplete), encoding="utf-8")
            with self.assertRaises(ValueError):
                VerifiedIndexedSplitStore(dataset, split)

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


    def test_configurable_resource_limits_are_enforced_and_tunables_applied(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset, split = self._prepare(root, count=90)
            limits = IndexedDatasetResourceLimits(
                snapshot_copy_chunk_bytes=4096,
                sqlite_cache_kib=1,
                index_build_batch_rows=7,
                iterator_fetch_rows=5,
            )
            with VerifiedIndexedSplitStore(dataset, split, resource_limits=limits) as store:
                self.assertEqual(store.resource_limits, limits)
                self.assertEqual(len(list(store.iter_records("train"))), store.split_counts["train"])
                self.assertFalse(os.stat(store._snapshot_path).st_mode & 0o222)

            cases = (
                (IndexedDatasetResourceLimits(max_dataset_bytes=dataset.stat().st_size - 1),
                 "max_dataset_bytes"),
                (IndexedDatasetResourceLimits(max_rows=10), "row limit"),
                (IndexedDatasetResourceLimits(max_line_bytes=10), "line byte limit"),
                (IndexedDatasetResourceLimits(max_split_manifest_bytes=10),
                 "max_split_manifest_bytes"),
                (IndexedDatasetResourceLimits(max_dataset_manifest_bytes=10),
                 "max_dataset_manifest_bytes"),
                (IndexedDatasetResourceLimits(max_index_bytes=4096), "SQLite index"),
                (IndexedDatasetResourceLimits(max_temporary_bytes=1), "max_temporary_bytes"),
            )
            for resource_limits, message in cases:
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValueError, message):
                        VerifiedIndexedSplitStore(dataset, split, resource_limits=resource_limits)

            for kwargs in (
                {"max_rows": 0},
                {"max_line_bytes": True},
                {"sqlite_cache_kib": 0},
                {"iterator_fetch_rows": 4097},
            ):
                with self.subTest(kwargs=kwargs):
                    with self.assertRaises((TypeError, ValueError)):
                        IndexedDatasetResourceLimits(**kwargs)

    def test_concurrent_readers_have_stable_order_and_independent_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=180)

            def read_train(_):
                with VerifiedIndexedSplitStore(dataset, split) as store:
                    records = list(store.iter_records("train"))
                    ids = [record[0] for record in records]
                    self.assertEqual(ids, sorted(ids))
                    self.assertEqual(len(ids), store.split_counts["train"])
                    return records

            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(read_train, range(4)))
            self.assertTrue(all(result == results[0] for result in results[1:]))
            self.assertTrue(dataset.is_file())
            self.assertTrue(split.is_file())

    def test_missing_and_truncated_source_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            dataset.unlink()
            with self.assertRaisesRegex(ValueError, "not a file"):
                VerifiedIndexedSplitStore(dataset, split)

        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            original = dataset.read_bytes()
            dataset.write_bytes(original[:-7])
            with self.assertRaises(ValueError):
                VerifiedIndexedSplitStore(dataset, split)

    def test_interrupted_index_build_rolls_back_and_removes_temporary_files(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            real_connect = sqlite3.connect
            real_temporary_directory = tempfile.TemporaryDirectory
            created_paths = []
            state = {"record_inserts": 0}

            class FaultingConnection:
                def __init__(self, connection):
                    self.connection = connection

                def execute(self, sql, parameters=()):
                    if sql.lstrip().upper().startswith("INSERT INTO RECORDS"):
                        state["record_inserts"] += 1
                        if state["record_inserts"] == 4:
                            raise RuntimeError("injected interrupted index update")
                    return self.connection.execute(sql, parameters)

                def executemany(self, sql, parameters):
                    return self.connection.executemany(sql, parameters)

                def commit(self):
                    return self.connection.commit()

                def rollback(self):
                    return self.connection.rollback()

                def close(self):
                    return self.connection.close()

            def tracked_temporary_directory(*args, **kwargs):
                temporary = real_temporary_directory(*args, **kwargs)
                if kwargs.get("prefix") == "ultron-indexed-dataset-":
                    created_paths.append(Path(temporary.name))
                return temporary

            with patch.object(
                indexed_module.sqlite3, "connect",
                side_effect=lambda *args, **kwargs: FaultingConnection(real_connect(*args, **kwargs)),
            ), patch.object(
                indexed_module.tempfile, "TemporaryDirectory",
                side_effect=tracked_temporary_directory,
            ):
                with self.assertRaisesRegex(RuntimeError, "injected interrupted"):
                    VerifiedIndexedSplitStore(dataset, split)

            self.assertEqual(state["record_inserts"], 4)
            self.assertEqual(len(created_paths), 1)
            self.assertFalse(created_paths[0].exists())

    def test_duplicate_manifest_ids_and_manifest_hash_mismatch_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            payload = json.loads(split.read_text(encoding="utf-8"))
            payload["split_ids"]["train"].append(payload["split_ids"]["train"][0])
            payload["split_ids"]["train"].sort()
            unsigned = {key: value for key, value in payload.items() if key != "sha256"}
            payload["sha256"] = __import__("hashlib").sha256(
                json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest()
            split.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
            with self.assertRaises(ValueError):
                VerifiedIndexedSplitStore(dataset, split)

        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            payload = json.loads(split.read_text(encoding="utf-8"))
            payload["split_seed"] += 1
            split.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                VerifiedIndexedSplitStore(dataset, split)


    def test_interrupted_snapshot_copy_cleans_partial_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            created_paths = []
            real_temporary_directory = tempfile.TemporaryDirectory

            def tracked_temporary_directory(*args, **kwargs):
                temporary = real_temporary_directory(*args, **kwargs)
                if kwargs.get("prefix") == "ultron-indexed-dataset-":
                    created_paths.append(Path(temporary.name))
                return temporary

            def write_partial_then_fail(store):
                store._snapshot_path.write_bytes(b"partial verified snapshot")
                raise OSError("injected snapshot-copy interruption")

            with patch.object(
                indexed_module.tempfile, "TemporaryDirectory",
                side_effect=tracked_temporary_directory,
            ), patch.object(
                VerifiedIndexedSplitStore, "_copy_verified_snapshot",
                write_partial_then_fail,
            ):
                with self.assertRaisesRegex(OSError, "injected snapshot-copy interruption"):
                    VerifiedIndexedSplitStore(dataset, split)

            self.assertEqual(len(created_paths), 1)
            self.assertFalse(created_paths[0].exists())

    def test_corrupted_ephemeral_index_is_recovered_by_fresh_rebuild(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=180)
            with VerifiedIndexedSplitStore(dataset, split) as store:
                expected = store.get_record("train", 0)
                index_path = store._index_path
                with index_path.open("r+b") as index_file:
                    index_file.seek(0)
                    index_file.write(b"CORRUPTED")
                    index_file.flush()
                    os.fsync(index_file.fileno())
                with self.assertRaises(sqlite3.DatabaseError):
                    store.get_record("train", 0)

            with VerifiedIndexedSplitStore(dataset, split) as rebuilt:
                self.assertEqual(rebuilt.get_record("train", 0), expected)
                self.assertEqual(len(list(rebuilt.iter_records("train"))), rebuilt.split_counts["train"])

    @skipUnless(Path("/proc/self/fd").is_dir(), "file descriptor accounting requires /proc/self/fd")
    def test_repeated_store_lifecycle_does_not_leak_file_descriptors(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            baseline = len(list(Path("/proc/self/fd").iterdir()))
            for _ in range(8):
                store = VerifiedIndexedSplitStore(dataset, split)
                list(store.iter_records("train"))
                store.close()
            after = len(list(Path("/proc/self/fd").iterdir()))
            self.assertLessEqual(after, baseline + 1)

    def test_large_manifest_and_record_count_are_bounded_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=12000)
            manifest_bytes = split.stat().st_size
            self.assertGreater(manifest_bytes, 500_000)
            with VerifiedIndexedSplitStore(dataset, split) as store:
                self.assertEqual(sum(store.split_counts.values()), 12000)
                first_pass = {
                    split_name: [example_id for example_id, _prompt, _answer in store.iter_records(split_name)]
                    for split_name in ("train", "validation", "test")
                }
                second_pass = {
                    split_name: [example_id for example_id, _prompt, _answer in store.iter_records(split_name)]
                    for split_name in ("train", "validation", "test")
                }
                self.assertEqual(first_pass, second_pass)
                for ids in first_pass.values():
                    self.assertEqual(ids, sorted(ids))
                self.assertGreater(store._index_path.stat().st_size, 0)



if __name__ == "__main__":
    unittest.main()
