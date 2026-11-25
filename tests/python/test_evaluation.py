import unittest
from ultron_core.data_generation import generate_examples
from ultron_core.evaluation import evaluate_predictions

class ExactAnswerEvaluationTests(unittest.TestCase):
    def test_reports_exact_accuracy_coverage_and_abstentions(self):
        examples = generate_examples(88, 30)
        predictions = {item.example_id: item.exact_answer for item in examples}
        predictions[examples[0].example_id] = "999/1"
        predictions[examples[1].example_id] = None
        predictions[examples[2].example_id] = "not a rational"
        report = evaluate_predictions(examples, predictions)
        self.assertEqual(report["total_examples"], 30)
        self.assertEqual(report["answered"], 28)
        self.assertEqual(report["abstentions"], 2)
        self.assertEqual(report["invalid_predictions"], 1)
        self.assertEqual(report["correct"], 27)
        self.assertAlmostEqual(report["coverage"], 28 / 30)
        self.assertAlmostEqual(report["exact_accuracy_all"], 27 / 30)
        self.assertAlmostEqual(report["exact_accuracy_answered"], 27 / 28)
        self.assertFalse(report["proof_verified"])
        self.assertFalse(report["model_evaluated"])
        self.assertFalse(report["training_performed"])

    def test_rejects_prediction_ids_outside_evaluation_set(self):
        examples = generate_examples(4, 5)
        with self.assertRaisesRegex(ValueError, "IDs not present"):
            evaluate_predictions(examples, {"unknown-id": "1"})

    def test_rejects_duplicate_reference_ids(self):
        examples = generate_examples(4, 5)
        with self.assertRaisesRegex(ValueError, "duplicate IDs"):
            evaluate_predictions((examples[0], examples[0]), {})

if __name__ == "__main__":
    unittest.main()
