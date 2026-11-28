"""Focused contracts for Phase 1 engineering benchmark helpers."""
import tempfile
import unittest
from pathlib import Path

from tools.benchmark_phase1 import (
    frontend_report,
    measure,
    reference_scan,
    tokenizer_report,
    tiny_config,
    write_fixture,
)
from ultron_core.dataset_split_manifest import prepare_dataset_split_manifest
from ultron_core.math_tokenizer import MathTokenizer


class Phase1BenchmarkTests(unittest.TestCase):
    def test_measure_reports_only_requested_repetitions(self):
        calls = []
        report = measure(lambda: calls.append(1), warmup=1, repetitions=2)
        self.assertEqual(len(calls), 3)
        self.assertEqual(report["warmup_iterations"], 1)
        self.assertEqual(report["measured_iterations"], 2)
        self.assertEqual(len(report["samples_seconds"]), 2)
        self.assertGreaterEqual(report["median_seconds"], 0)

    def test_reference_tokenizer_matches_current_trie_on_curated_math_inputs(self):
        tokenizer = MathTokenizer()
        for source in (
            "12345 + 67890 = 80235",
            r"\frac{1}{2} + \frac{1}{3} = \frac{5}{6}",
            "∀x∈ℝ: x²≥0",
            "∫₀¹ x² dx = 1/3",
            r"\lim_{x\to0}\frac{x^2}{x}=0",
        ):
            self.assertEqual(reference_scan(tokenizer, source), tokenizer.encode(source))

    def test_tokenizer_benchmark_reports_equivalence_and_measurement_conditions(self):
        report = tokenizer_report()
        self.assertTrue(report["token_ids_equivalent"])
        self.assertGreater(report["tokens_per_iteration"], 0)
        self.assertEqual(report["reference_full_vocabulary_scan"]["measured_iterations"], 12)
        self.assertEqual(report["current_trie_tokenizer"]["measured_iterations"], 12)
        self.assertGreater(report["reference_full_vocabulary_scan"]["median_seconds"], 0)
        self.assertGreater(report["current_trie_tokenizer"]["median_seconds"], 0)

    def test_fixture_writer_produces_manifest_verifiable_temporary_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "phase1.jsonl"
            split = root / "phase1.splits.json"
            write_fixture(dataset, rows=90)
            verified = prepare_dataset_split_manifest(dataset, split, split_seed=29)
            self.assertEqual(verified.dataset_example_count, 90)
            self.assertEqual(verified.selected_example_count, 90)
            self.assertEqual(sum(verified.split_counts.values()), 90)
            self.assertTrue(dataset.is_file())
            self.assertTrue(split.is_file())

    def test_small_benchmark_configuration_is_not_foundation_configuration(self):
        config = tiny_config()
        self.assertLess(config.hidden_size, 512)
        self.assertEqual(config.max_sequence_length, 64)

    def test_frontend_report_is_a_transfer_size_proxy(self):
        root = Path(__file__).resolve().parents[2]
        report = frontend_report(root)
        self.assertGreater(report["raw_total_bytes"], 0)
        self.assertGreater(report["gzip_total_bytes"], 0)
        self.assertTrue(report["assets"])
        self.assertFalse(report["browser_load_time_measured"])
        self.assertIn("Transfer-size proxy", report["limitation"])


if __name__ == "__main__":
    unittest.main()
