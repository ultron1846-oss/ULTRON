"""Bounded semantic JSONL ingestion regressions; synthetic fixtures only."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_dataset_split_manifest import fixture
import ultron_core.dataset_split_manifest as split_module
from ultron_core.data_generation import verify_dataset
from ultron_core.dataset_split_manifest import (
    prepare_dataset_split_manifest,
    validate_dataset_split_manifest,
)


class StreamingSemanticDatasetTests(unittest.TestCase):
    def _paths(self, root):
        dataset = root / "synthetic.jsonl"
        split = root / "splits.json"
        fixture(dataset, count=90, duplicate=False)
        return dataset, split

    def _rewrite_manifest(self, dataset, *, count=None, duplicate_id=False):
        manifest_path = dataset.with_suffix(dataset.suffix + ".manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        content = dataset.read_bytes()
        if duplicate_id:
            first = content.splitlines(keepends=True)[0]
            content += first
            manifest["example_count"] += 1
            manifest["topic_counts"]["arithmetic"] += 1
        if count is not None:
            manifest["example_count"] = count
        dataset.write_bytes(content)
        manifest["sha256"] = hashlib.sha256(content).hexdigest()
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    def test_semantic_verifier_does_not_read_full_dataset_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, _ = self._paths(Path(directory))
            original = Path.read_bytes

            def guarded_read_bytes(path):
                if path == dataset:
                    raise AssertionError("dataset full-file read_bytes must not be used")
                return original(path)

            with patch.object(Path, "read_bytes", guarded_read_bytes):
                report = verify_dataset(dataset)
            self.assertEqual(report["example_count"], 90)

    def test_byte_row_and_line_limits_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, _ = self._paths(Path(directory))
            with self.assertRaisesRegex(ValueError, "byte limit"):
                verify_dataset(dataset, max_bytes=10)
            with self.assertRaisesRegex(ValueError, "row limit"):
                verify_dataset(dataset, max_rows=10)
            with self.assertRaisesRegex(ValueError, "line byte limit"):
                verify_dataset(dataset, max_line_bytes=20)

    def test_blank_malformed_and_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, _ = self._paths(Path(directory))
            original = dataset.read_bytes()
            blank_content = original + b"\n"
            dataset.write_bytes(blank_content)
            manifest_path = dataset.with_suffix(dataset.suffix + ".manifest.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["example_count"] += 1
            manifest["topic_counts"]["arithmetic"] += 1
            manifest["sha256"] = hashlib.sha256(blank_content).hexdigest()
            manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "blank rows"):
                verify_dataset(dataset)

            for malformed in (b"{not-json}\n", b'{"topic":"arithmetic","topic":"linear_equations"}\n'):
                dataset.write_bytes(malformed)
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["sha256"] = hashlib.sha256(malformed).hexdigest()
                manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "malformed|duplicate JSON key"):
                    verify_dataset(dataset)

    def test_duplicate_example_id_rejected_even_with_updated_manifest_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, _ = self._paths(Path(directory))
            self._rewrite_manifest(dataset, duplicate_id=True)
            with self.assertRaisesRegex(ValueError, "duplicate example IDs"):
                verify_dataset(dataset)

    def test_dataset_mutation_between_verify_and_split_row_pass_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._paths(Path(directory))
            original_verify = split_module.verify_dataset

            def verify_then_mutate(path):
                result = original_verify(path)
                dataset.write_bytes(dataset.read_bytes().replace(b"1 + 2", b"9 + 2", 1))
                return result

            with patch.object(split_module, "verify_dataset", side_effect=verify_then_mutate):
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    prepare_dataset_split_manifest(dataset, split, split_seed=7)

    def test_existing_split_manifest_roundtrip_remains_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._paths(Path(directory))
            prepared = prepare_dataset_split_manifest(
                dataset, split, split_seed=17, validation_fraction=0.1, test_fraction=0.1
            )
            validated = validate_dataset_split_manifest(dataset, split)
            self.assertEqual(prepared, validated)
            self.assertEqual(validated.dataset_example_count, 90)
            self.assertEqual(validated.selected_example_count, 90)


if __name__ == "__main__":
    unittest.main()
