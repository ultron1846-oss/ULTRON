"""Deterministic read-only quality-report tests; fixtures only."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_dataset_split_manifest import fixture
from ultron_core.dataset_split_manifest import prepare_dataset_split_manifest
from ultron_core.data_generation import SUPPORTED_TOPICS, generate_examples
import ultron_core.dataset_quality as quality_module
from ultron_core.dataset_quality import audit_dataset_quality, _reject_output_aliases
from ultron_core.dataset_resource_limits import DatasetResourceLimits


class DatasetQualityAuditTests(unittest.TestCase):
    def _prepare(self, root, count=180):
        dataset = root / "quality-fixture.jsonl"
        split = root / "quality-fixture.splits.json"
        fixture(dataset, count, duplicate=False)
        prepare_dataset_split_manifest(dataset, split, split_seed=20261128)
        return dataset, split

    def test_quality_report_is_reproducible_read_only_and_manifest_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory))
            dataset_before = dataset.read_bytes()
            split_before = split.read_bytes()

            first = audit_dataset_quality(dataset, split)
            second = audit_dataset_quality(dataset, split)

            self.assertEqual(first, second)
            self.assertEqual(first["report_sha256"], second["report_sha256"])
            self.assertEqual(first["dataset_manifest_sha256"], hashlib.sha256(dataset_before).hexdigest())
            self.assertEqual(first["source_dataset_example_count"], 180)
            self.assertEqual(first["reference_answer_recheck"]["rows_rechecked"], 180)
            self.assertEqual(first["reference_answer_recheck"]["invalid_reference_answers"], 0)
            self.assertEqual(first["prerequisite_coverage"]["status"], "not_assessed")
            self.assertTrue(first["quality_gate_summary"]["manifest_and_split_verified"])
            self.assertTrue(first["quality_gate_summary"]["all_reference_answers_rechecked"])
            self.assertTrue(first["quality_gate_summary"]["prompt_group_split_separation"])
            self.assertFalse(first["quality_gate_summary"]["production_readiness"])
            self.assertEqual(first["semantic_near_duplicates"]["status"], "not_assessed")
            self.assertEqual(first["boundary_sample_coverage"]["status"], "not_annotated_in_schema_v1")
            self.assertFalse(first["reproducibility"]["input_data_modified"])
            self.assertEqual(dataset.read_bytes(), dataset_before)
            self.assertEqual(split.read_bytes(), split_before)

            for split_name in ("train", "validation", "test"):
                self.assertEqual(
                    first["per_split"][split_name]["manifest_selected_count"],
                    first["selected_split_counts"][split_name],
                )
                self.assertEqual(
                    first["per_split"][split_name]["audited_selected_count"],
                    first["selected_split_counts"][split_name],
                )
                self.assertGreater(first["per_split"][split_name]["topic_coverage_count"], 0)
                self.assertEqual(first["per_split"][split_name]["seed_use_counts"], {"31": first["selected_split_counts"][split_name]})

            for pair in first["split_pairwise_leakage_diagnostics"].values():
                self.assertEqual(pair["normalized_prompt_groups"], 0)
                self.assertEqual(pair["generation_ingredients_shared"], 0)
                self.assertEqual(pair["generation_seed_values_shared"], 1)

    def test_corrupted_dataset_or_split_manifest_fails_before_report(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            dataset.write_bytes(dataset.read_bytes() + b" ")
            with self.assertRaises(ValueError):
                audit_dataset_quality(dataset, split)

        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            payload = json.loads(split.read_text(encoding="utf-8"))
            payload["dataset_sha256"] = "0" * 64
            split.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            with self.assertRaises(ValueError):
                audit_dataset_quality(dataset, split)

    def test_quality_report_output_cannot_alias_any_input(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            sidecar = dataset.with_suffix(dataset.suffix + ".manifest.json")
            for input_path in (dataset, split, sidecar):
                with self.subTest(input_path=input_path):
                    with self.assertRaisesRegex(ValueError, "must not overwrite"):
                        _reject_output_aliases(input_path, (dataset, split, sidecar))
            alias = Path(directory) / "dataset-hardlink.jsonl"
            alias.hardlink_to(dataset)
            with self.assertRaisesRegex(ValueError, "must not overwrite"):
                _reject_output_aliases(alias, (dataset, split, sidecar))

    def test_current_sample_schema_and_seed_contract_are_deterministic(self):
        first = tuple(
            example
            for topic_index, topic in enumerate(SUPPORTED_TOPICS)
            for example in generate_examples(
                seed=1846 + topic_index, count=9, topics=(topic,)
            )
        )
        second = tuple(
            example
            for topic_index, topic in enumerate(SUPPORTED_TOPICS)
            for example in generate_examples(
                seed=1846 + topic_index, count=9, topics=(topic,)
            )
        )
        expected_fields = {
            "example_id", "generator_version", "topic", "difficulty",
            "input_text", "target_text", "exact_answer", "seed", "index",
            "generation_parameters", "validation_status", "provenance",
        }
        first_rows = [example.to_dict() for example in first]
        second_rows = [example.to_dict() for example in second]
        self.assertEqual(first_rows, second_rows)
        self.assertEqual({row["topic"] for row in first_rows}, set(SUPPORTED_TOPICS))
        for row in first_rows:
            self.assertEqual(set(row), expected_fields)
            self.assertEqual(row["seed"], 1846 + SUPPORTED_TOPICS.index(row["topic"]))
            self.assertEqual(row["validation_status"], "semantically_checked")
            self.assertEqual(
                row["example_id"],
                hashlib.sha256(
                    json.dumps(
                        {
                            "generator_version": row["generator_version"],
                            "seed": row["seed"],
                            "index": row["index"],
                            "topic": row["topic"],
                            "input_text": row["input_text"],
                            "target_text": row["target_text"],
                            "generation_parameters": row["generation_parameters"],
                        },
                        sort_keys=True,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest(),
            )

    def test_prompt_duplicate_diagnostics_do_not_claim_semantic_deduplication(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            report = audit_dataset_quality(dataset, split)
            self.assertIn("normalized_prompt_duplicate_rows_after_first", report)
            self.assertIn("normalized_prompt_duplicate_groups", report)
            self.assertEqual(report["semantic_near_duplicates"]["owner_review_required"], True)
            self.assertIn("diagnostic only", report["answer_leakage"]["interpretation"].lower())
            self.assertIn("not semantic equivalence", report["template_leakage"]["interpretation"].lower())


    def test_audit_rejects_dataset_mutation_after_manifest_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            real_validate = quality_module.validate_dataset_split_manifest

            def verify_then_mutate(*args, **kwargs):
                verified = real_validate(*args, **kwargs)
                original = dataset.read_bytes()
                dataset.write_bytes(original.replace(b"1 + 2", b"9 + 2", 1))
                return verified

            with patch.object(
                quality_module, "validate_dataset_split_manifest",
                side_effect=verify_then_mutate,
            ):
                with self.assertRaisesRegex(ValueError, "dataset changed during quality audit"):
                    audit_dataset_quality(dataset, split)

    def test_quality_audit_obeys_caller_resource_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split = self._prepare(Path(directory), count=90)
            with self.assertRaisesRegex(ValueError, "line byte limit"):
                audit_dataset_quality(
                    dataset, split,
                    resource_limits=DatasetResourceLimits(max_line_bytes=32),
                )



    def test_duplicate_prompt_group_is_counted_and_unselected_row_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / "duplicate-fixture.jsonl"
            split = Path(directory) / "duplicate-fixture.splits.json"
            fixture(dataset, 90, duplicate=True)
            prepare_dataset_split_manifest(dataset, split, split_seed=41)
            report = audit_dataset_quality(dataset, split)
            self.assertEqual(report["source_dataset_example_count"], 91)
            self.assertEqual(report["audited_selected_example_count"], 90)
            self.assertEqual(report["unassigned_source_rows"], 1)
            self.assertEqual(report["normalized_prompt_duplicate_groups"], 1)
            self.assertEqual(report["normalized_prompt_duplicate_rows_after_first"], 1)
            for pair in report["split_pairwise_leakage_diagnostics"].values():
                self.assertEqual(pair["normalized_prompt_groups"], 0)



    def test_copied_dataset_pair_and_split_reverify_before_use(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            destination = root / "transferred"
            source.mkdir()
            destination.mkdir()
            dataset, split = self._prepare(source, count=90)
            report = audit_dataset_quality(dataset, split)

            copied_dataset = destination / dataset.name
            copied_split = destination / split.name
            copied_sidecar = dataset.with_suffix(dataset.suffix + ".manifest.json")
            copied_dataset_sidecar = copied_dataset.with_suffix(
                copied_dataset.suffix + ".manifest.json"
            )
            shutil.copy2(dataset, copied_dataset)
            shutil.copy2(copied_sidecar, copied_dataset_sidecar)
            shutil.copy2(split, copied_split)

            copied_report = audit_dataset_quality(copied_dataset, copied_split)
            self.assertEqual(copied_report["dataset_manifest_sha256"], report["dataset_manifest_sha256"])
            self.assertEqual(copied_report["split_manifest_sha256"], report["split_manifest_sha256"])
            self.assertEqual(copied_report["report_sha256"], report["report_sha256"])

            with copied_dataset.open("ab") as stream:
                stream.write(b"tampered-transfer\n")
            with self.assertRaises(ValueError):
                audit_dataset_quality(copied_dataset, copied_split)



if __name__ == "__main__":
    unittest.main()
