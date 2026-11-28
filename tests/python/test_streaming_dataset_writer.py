"""Streaming generation-writer tests; small deterministic fixtures only."""
from dataclasses import replace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ultron_core.data_generation import (
    SUPPORTED_TOPICS,
    generate_examples,
    verify_dataset,
    write_dataset,
)
from ultron_core.dataset_resource_limits import DatasetResourceLimits


class StreamingDatasetWriterTests(unittest.TestCase):
    def _examples(self, count=12):
        return generate_examples(
            101, count,
            topics=("arithmetic", "rational_arithmetic", "linear_equations"),
        )

    def test_iterator_writer_is_deterministic_and_verifiable(self):
        examples = self._examples()

        def row_iterator():
            for item in examples:
                yield item

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_path = root / "streamed.jsonl"
            second_path = root / "tuple.jsonl"
            manifest = write_dataset(
                first_path, row_iterator(), seed=101,
                topics=("arithmetic", "rational_arithmetic", "linear_equations"),
            )
            second_manifest = write_dataset(
                second_path, examples, seed=101,
                topics=("arithmetic", "rational_arithmetic", "linear_equations"),
            )
            self.assertEqual(first_path.read_bytes(), second_path.read_bytes())
            self.assertEqual(manifest, second_manifest)
            self.assertEqual(verify_dataset(first_path), manifest)
            self.assertEqual(manifest["example_count"], 12)

    def test_all_writer_resource_limits_fail_before_replacing_existing_pair(self):
        examples = self._examples()
        topics = ("arithmetic", "rational_arithmetic", "linear_equations")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bounded.jsonl"
            write_dataset(path, examples, seed=101, topics=topics)
            original_dataset = path.read_bytes()
            manifest_path = path.with_suffix(path.suffix + ".manifest.json")
            original_manifest = manifest_path.read_bytes()

            policies = (
                DatasetResourceLimits(max_rows=3),
                DatasetResourceLimits(max_dataset_bytes=10),
                DatasetResourceLimits(max_line_bytes=10),
                DatasetResourceLimits(max_dataset_manifest_bytes=10),
                DatasetResourceLimits(max_temporary_bytes=1),
            )
            expected = (
                "max_rows", "max_dataset_bytes", "max_line_bytes",
                "max_dataset_manifest_bytes", "max_temporary_bytes",
            )
            for policy, message in zip(policies, expected):
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValueError, message):
                        write_dataset(path, iter(examples), seed=101, topics=topics, resource_limits=policy)
                    self.assertEqual(path.read_bytes(), original_dataset)
                    self.assertEqual(manifest_path.read_bytes(), original_manifest)

            with self.assertRaisesRegex(ValueError, "max_manifest_bytes|byte limit"):
                verify_dataset(path, max_manifest_bytes=10)


    def test_combined_temporary_budget_includes_manifest_before_replacement(self):
        examples = self._examples()
        topics = ("arithmetic", "rational_arithmetic", "linear_equations")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "combined-budget.jsonl"
            write_dataset(path, examples, seed=101, topics=topics)
            original_dataset = path.read_bytes()
            manifest_path = path.with_suffix(path.suffix + ".manifest.json")
            original_manifest = manifest_path.read_bytes()

            # The staged JSONL fits exactly; adding its sidecar must exceed the cap.
            with self.assertRaisesRegex(
                ValueError, "dataset and sidecar temporary outputs exceed configured max_temporary_bytes"
            ):
                write_dataset(
                    path,
                    iter(examples),
                    seed=101,
                    topics=topics,
                    resource_limits=DatasetResourceLimits(
                        max_temporary_bytes=len(original_dataset)
                    ),
                )

            self.assertEqual(path.read_bytes(), original_dataset)
            self.assertEqual(manifest_path.read_bytes(), original_manifest)
            self.assertEqual(list(Path(directory).glob(".*.tmp")), [])

    def test_writer_rejects_content_identity_mismatch_before_replacing_existing_pair(self):
        example = generate_examples(101, 1, topics=("arithmetic",))[0]
        params = dict(example.generation_parameters)
        params["a"] += 1
        tampered = replace(
            example,
            generation_parameters=tuple(sorted(params.items())),
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "identity-bound.jsonl"
            topics = ("arithmetic",)
            original_manifest = write_dataset(
                path, (example,), seed=101, topics=topics
            )
            original_dataset_bytes = path.read_bytes()
            manifest_path = path.with_suffix(path.suffix + ".manifest.json")
            original_manifest_bytes = manifest_path.read_bytes()

            with self.assertRaisesRegex(ValueError, "example ID does not match"):
                write_dataset(path, (tampered,), seed=101, topics=topics)

            self.assertEqual(path.read_bytes(), original_dataset_bytes)
            self.assertEqual(manifest_path.read_bytes(), original_manifest_bytes)
            self.assertEqual(verify_dataset(path), original_manifest)

    def test_math_example_rejects_duplicate_generation_parameter_names(self):
        example = generate_examples(101, 1, topics=("arithmetic",))[0]
        with self.assertRaisesRegex(ValueError, "keys must be unique"):
            replace(
                example,
                generation_parameters=example.generation_parameters
                + (example.generation_parameters[0],),
            )

    def test_writer_rejects_duplicate_ids_indices_and_unknown_topic_sequence(self):
        examples = self._examples()
        topics = ("arithmetic", "rational_arithmetic", "linear_equations")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "duplicate example IDs"):
                write_dataset(root / "duplicate-id.jsonl", (examples[0], examples[0]), seed=101, topics=topics)
            duplicate_index = replace(examples[1], index=examples[0].index)
            with self.assertRaisesRegex(ValueError, "duplicate example indices"):
                write_dataset(root / "duplicate-index.jsonl", (examples[0], duplicate_index), seed=101, topics=topics)
            with self.assertRaisesRegex(ValueError, "unique supported-topic"):
                write_dataset(root / "bad-topics.jsonl", examples, seed=101, topics=("arithmetic", "arithmetic"))

    def test_interrupted_two_file_replacement_fails_verification(self):
        examples = self._examples()
        topics = ("arithmetic", "rational_arithmetic", "linear_equations")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "interrupt.jsonl"
            write_dataset(path, examples, seed=101, topics=topics)
            original_dataset = path.read_bytes()
            changed = generate_examples(202, 12, topics=topics)
            real_replace = __import__("os").replace
            state = {"calls": 0}

            def fail_sidecar_replace(source, destination):
                state["calls"] += 1
                if state["calls"] == 2:
                    raise OSError("injected sidecar-replacement interruption")
                return real_replace(source, destination)

            with patch("ultron_core.data_generation.os.replace", side_effect=fail_sidecar_replace):
                with self.assertRaisesRegex(OSError, "injected sidecar-replacement interruption"):
                    write_dataset(path, changed, seed=202, topics=topics)

            self.assertNotEqual(path.read_bytes(), original_dataset)
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify_dataset(path)
            self.assertEqual(list(Path(directory).glob(".*.tmp")), [])

    def test_generator_obeys_shared_row_cap(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 3"):
            generate_examples(
                9, 4, topics=("arithmetic",),
                resource_limits=DatasetResourceLimits(max_rows=3),
            )


if __name__ == "__main__":
    unittest.main()
