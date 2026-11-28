"""Shared dataset resource-policy regressions; temporary synthetic fixtures only."""
import tempfile
import unittest
from pathlib import Path

from test_dataset_split_manifest import fixture
from ultron_core.dataset_resource_limits import DatasetResourceLimits
from ultron_core.dataset_split_manifest import (
    prepare_dataset_split_manifest,
    validate_dataset_split_manifest,
)
from ultron_core.indexed_verified_dataset import VerifiedIndexedSplitStore
from ultron_core.verified_dataset import (
    build_verified_split_loaders,
    close_verified_split_loaders,
)


class DatasetResourceLimitTests(unittest.TestCase):
    def _prepare(self, root):
        dataset = root / "bounded.jsonl"
        split = root / "bounded.splits.json"
        fixture(dataset, 90, duplicate=False)
        prepare_dataset_split_manifest(dataset, split, split_seed=41)
        return dataset, split

    def test_manifest_verifier_obeys_configured_byte_row_and_line_caps(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory))
            size = dataset.stat().st_size
            for limits, message in (
                (DatasetResourceLimits(max_dataset_bytes=size - 1), "max_dataset_bytes"),
                (DatasetResourceLimits(max_rows=10), "row limit"),
                (DatasetResourceLimits(max_line_bytes=32), "line byte limit"),
                (DatasetResourceLimits(max_split_manifest_bytes=10), "max_split_manifest_bytes"),
            ):
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValueError, message):
                        validate_dataset_split_manifest(dataset, split, resource_limits=limits)

    def test_split_writer_obeys_manifest_and_dataset_limits_before_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "bounded.jsonl"
            fixture(dataset, 90, duplicate=False)
            output = root / "too-large.splits.json"
            limits = DatasetResourceLimits(max_split_manifest_bytes=128)
            with self.assertRaisesRegex(ValueError, "max_split_manifest_bytes"):
                prepare_dataset_split_manifest(
                    dataset, output, split_seed=41, resource_limits=limits
                )
            self.assertFalse(output.exists())
            with self.assertRaisesRegex(ValueError, "max_dataset_bytes"):
                prepare_dataset_split_manifest(
                    dataset, root / "too-small.splits.json", split_seed=41,
                    resource_limits=DatasetResourceLimits(max_dataset_bytes=dataset.stat().st_size - 1),
                )

    def test_loader_api_accepts_policy_and_cleans_store_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory))
            with self.assertRaisesRegex(ValueError, "max_dataset_bytes"):
                build_verified_split_loaders(
                    dataset, split, batch_size=4, seed=3,
                    resource_limits=DatasetResourceLimits(max_dataset_bytes=dataset.stat().st_size - 1),
                )

            loaders = build_verified_split_loaders(
                dataset, split, batch_size=4, seed=3,
                resource_limits=DatasetResourceLimits(
                    snapshot_copy_chunk_bytes=4096,
                    sqlite_cache_kib=1024,
                    iterator_fetch_rows=8,
                    index_build_batch_rows=16,
                ),
            )
            try:
                stores = {id(loader.dataset._store): loader.dataset._store for loader in loaders.values()}
                self.assertEqual(len(stores), 1)
                store = next(iter(stores.values()))
                self.assertEqual(store.resource_limits.iterator_fetch_rows, 8)
                self.assertEqual(sum(store.split_counts.values()), 90)
            finally:
                close_verified_split_loaders(loaders)

    def test_policy_rejects_invalid_and_over_ceiling_values(self):
        for kwargs in (
            {"max_dataset_bytes": 0},
            {"max_rows": True},
            {"max_line_bytes": 8 * 1024 * 1024 + 1},
            {"max_index_bytes": 4095},
            {"max_temporary_bytes": 2 * 1024 * 1024 * 1024 + 1},
            {"sqlite_cache_kib": -1},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises((TypeError, ValueError)):
                    DatasetResourceLimits(**kwargs)

    def test_index_constructor_rejects_wrong_policy_type(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory))
            with self.assertRaisesRegex(TypeError, "DatasetResourceLimits"):
                VerifiedIndexedSplitStore(dataset, split, resource_limits=object())


if __name__ == "__main__":
    unittest.main()
