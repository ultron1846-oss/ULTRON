"""Tests for the read-only indexed dataset benchmark on tiny fixtures."""
import tempfile
import unittest
from pathlib import Path

from test_dataset_split_manifest import fixture
from ultron_core.dataset_split_manifest import prepare_dataset_split_manifest
from tools.benchmark_verified_dataset import benchmark_indexed_dataset, _validate_output_path


class IndexedDatasetBenchmarkTests(unittest.TestCase):
    def test_benchmark_reports_reproducible_read_only_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "fixture.jsonl"
            split = root / "fixture.splits.json"
            fixture(dataset, 90, True)
            contract = prepare_dataset_split_manifest(dataset, split, split_seed=4)
            first = benchmark_indexed_dataset(
                dataset, split, random_access_samples=7, seed=123
            )
            second = benchmark_indexed_dataset(
                dataset, split, random_access_samples=7, seed=123
            )
            for report in (first, second):
                self.assertEqual(report["dataset_manifest_sha256"], contract.dataset_sha256)
                self.assertEqual(report["selected_example_count"], 90)
                self.assertEqual(report["sequential_scan"]["rows_scanned"], 90)
                self.assertEqual(report["random_access"]["samples"], 7)
                self.assertGreater(report["tracemalloc_peak_python_bytes"], 0)
                self.assertGreater(report["snapshot_bytes"], 0)
                self.assertGreater(report["sqlite_index_bytes"], 0)
                self.assertFalse(report["data_generated"])
                self.assertFalse(report["dataset_modified"])
                self.assertFalse(report["training_performed"])
                self.assertEqual(report["optimizer_steps"], 0)
            self.assertEqual(first["random_access"]["seed"], second["random_access"]["seed"])
            self.assertEqual(first["random_access"]["samples"], second["random_access"]["samples"])
            self.assertEqual(first["random_access"]["sampled_indices"], second["random_access"]["sampled_indices"])
            self.assertTrue(dataset.is_file())


    def test_output_path_cannot_overwrite_dataset_or_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "data.jsonl"
            split = root / "splits.json"
            dataset.write_text("fixture", encoding="utf-8")
            split.write_text("fixture", encoding="utf-8")
            for input_path in (dataset, split):
                with self.subTest(input_path=input_path):
                    with self.assertRaisesRegex(ValueError, "must not overwrite"):
                        _validate_output_path(input_path, dataset, split)
            alias = root / "alias.jsonl"
            alias.symlink_to(dataset)
            with self.assertRaisesRegex(ValueError, "must not overwrite"):
                _validate_output_path(alias, dataset, split)
            _validate_output_path(root / "report.json", dataset, split)

    def test_benchmark_bounds_random_access_sample_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "fixture.jsonl"
            split = root / "fixture.splits.json"
            # The manifest splitter requires all splits to be non-empty.
            fixture(dataset, 90, True)
            prepare_dataset_split_manifest(dataset, split, split_seed=4)
            for invalid in (True, -1, 10_001):
                with self.subTest(invalid=invalid):
                    with self.assertRaises(ValueError):
                        benchmark_indexed_dataset(
                            dataset, split, random_access_samples=invalid
                        )


if __name__ == "__main__":
    unittest.main()
