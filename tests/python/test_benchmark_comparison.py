import unittest
from fractions import Fraction

from ultron_core.data_generation import generate_examples
from ultron_core.benchmark_comparison import (
    compare_predictions,
    exact_mcnemar_p_value,
)


class PairedMathBenchmarkTests(unittest.TestCase):
    def test_exact_mcnemar_is_symmetric_and_significant_for_clear_wins(self):
        self.assertAlmostEqual(exact_mcnemar_p_value(3, 3), 1.0)
        self.assertEqual(exact_mcnemar_p_value(24, 0), 2.0 ** -23)
        self.assertEqual(exact_mcnemar_p_value(0, 24), 2.0 ** -23)

    def test_rejects_invalid_mcnemar_counts(self):
        for args in ((-1, 0), (1, -1), (True, 0), (1.5, 0)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    exact_mcnemar_p_value(*args)

    def test_stage_a_topic_gate_passes_only_on_paired_validated_win(self):
        examples = generate_examples(20261125, 24, topics=("arithmetic",))
        ultron = {item.example_id: item.exact_answer for item in examples}
        baseline = {
            item.example_id: str(Fraction(item.exact_answer) + 1)
            for item in examples
        }

        report = compare_predictions(
            examples, ultron, baseline, minimum_examples=24,
        )
        topic = report["per_topic"]["arithmetic"]
        self.assertTrue(report["all_topics_passed"])
        self.assertTrue(topic["passed"])
        self.assertEqual(topic["paired_ultron_wins"], 24)
        self.assertEqual(topic["paired_baseline_wins"], 0)
        self.assertEqual(topic["accuracy_difference"], 1.0)
        self.assertTrue(topic["gate"]["paired_significance"])
        self.assertFalse(report["model_invoked"])
        self.assertFalse(report["training_performed"])
        self.assertFalse(report["data_generated"])

    def test_abstention_or_coverage_regression_blocks_gate(self):
        examples = generate_examples(20261126, 20, topics=("arithmetic",))
        baseline = {
            item.example_id: str(Fraction(item.exact_answer) + 1)
            for item in examples
        }
        ultron = {item.example_id: None for item in examples}
        ultron[examples[0].example_id] = examples[0].exact_answer

        report = compare_predictions(
            examples, ultron, baseline, minimum_examples=20,
        )
        topic = report["per_topic"]["arithmetic"]
        self.assertFalse(topic["passed"])
        self.assertFalse(topic["gate"]["coverage_noninferior"])
        self.assertEqual(topic["ultron_coverage"], 1 / 20)

    def test_rejects_prediction_ids_outside_frozen_benchmark(self):
        examples = generate_examples(17, 5, topics=("arithmetic",))
        with self.assertRaisesRegex(ValueError, "outside the benchmark"):
            compare_predictions(
                examples, {"extra": "1"}, {},
                minimum_examples=5,
            )

    def test_requires_valid_benchmark_and_predeclared_limits(self):
        examples = generate_examples(18, 5, topics=("arithmetic",))
        answers = {item.example_id: item.exact_answer for item in examples}
        with self.assertRaisesRegex(ValueError, "minimum_examples"):
            compare_predictions(examples, answers, answers, minimum_examples=0)
        with self.assertRaisesRegex(ValueError, "alpha"):
            compare_predictions(examples, answers, answers, alpha=1.0)
        with self.assertRaisesRegex(ValueError, "baseline_name"):
            compare_predictions(examples, answers, answers, baseline_name=" ")

if __name__ == "__main__":
    unittest.main()
