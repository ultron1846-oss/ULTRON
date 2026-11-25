import unittest
from ultron_core.data_generation import generate_examples
from ultron_core.evaluation import evaluate_predictions

class ExactAnswerEvaluationTests(unittest.TestCase):
    def test_reports_exact_accuracy_coverage_and_abstentions(self):
        examples = generate_examples(88, 30)
        predictions = {item.example_id: item.exact_answer for item in examples}
        predictions[examples[0].example_id] = "0" if examples[0].exact_answer != "0" else "1"
        predictions[examples[1].example_id] = None
        predictions[examples[2].example_id] = "not a rational"
        report = evaluate_predictions(examples, predictions)
        self.assertEqual(report["total_examples"], 30)
        self.assertEqual(report["attempted"], 29)
        self.assertEqual(report["answered"], 28)
        self.assertEqual(report["abstentions"], 1)
        self.assertEqual(report["invalid_predictions"], 1)
        self.assertEqual(report["incorrect_valid_predictions"], 1)
        self.assertEqual(report["correct"], 27)
        self.assertAlmostEqual(report["coverage"], 29 / 30)
        self.assertAlmostEqual(report["valid_answer_rate"], 28 / 30)
        self.assertAlmostEqual(report["exact_accuracy_all"], 27 / 30)
        self.assertAlmostEqual(report["exact_accuracy_answered"], 27 / 28)
        self.assertFalse(report["proof_verified"])
        self.assertFalse(report["model_evaluated"])
        self.assertFalse(report["training_performed"])
        self.assertEqual(report["schema_version"], 3)
        self.assertEqual(report["error_class_counts"], {
            "abstention": 1, "correct_answer": 27, "incorrect_answer": 1,
            "malformed_output": 1,
        })


    def test_invalid_predictions_are_not_abstentions(self):
        examples = generate_examples(93, 30)
        predictions = {item.example_id: item.exact_answer for item in examples}
        predictions[examples[0].example_id] = "invalid answer"
        predictions[examples[1].example_id] = None
        report = evaluate_predictions(examples, predictions)
        self.assertEqual(report["attempted"], 29)
        self.assertEqual(report["answered"], 28)
        self.assertEqual(report["invalid_predictions"], 1)
        self.assertEqual(report["abstentions"], 1)
        self.assertAlmostEqual(report["coverage"], 29 / 30)
        self.assertAlmostEqual(report["valid_answer_rate"], 28 / 30)


    def test_scores_exact_linear_system_answer_pairs(self):
        examples = generate_examples(724, 20, topics=("linear_system_2x2",))
        predictions = {item.example_id: item.exact_answer for item in examples}
        first = examples[0]
        predictions[first.example_id] = "x=999, y=-999"
        report = evaluate_predictions(examples, predictions)
        self.assertEqual(report["answered"], 20)
        self.assertEqual(report["correct"], 19)
        self.assertEqual(report["incorrect_valid_predictions"], 1)
        self.assertAlmostEqual(report["per_topic"]["linear_system_2x2"]["exact_accuracy_all"], 19 / 20)

    def test_scores_exact_polynomial_definite_integral_predictions(self):
        examples = generate_examples(39, 25, topics=("polynomial_definite_integral",))
        predictions = {item.example_id: item.exact_answer for item in examples}
        report = evaluate_predictions(examples, predictions)
        self.assertEqual(report["correct"], 25)
        self.assertEqual(report["exact_accuracy_all"], 1.0)
        self.assertEqual(report["per_topic"]["polynomial_definite_integral"]["exact_accuracy_all"], 1.0)


    def test_non_string_prediction_is_counted_as_invalid(self):
        examples = generate_examples(94, 5)
        predictions = {item.example_id: item.exact_answer for item in examples}
        predictions[examples[0].example_id] = 123
        report = evaluate_predictions(examples, predictions)
        self.assertEqual(report["attempted"], 5)
        self.assertEqual(report["answered"], 4)
        self.assertEqual(report["invalid_predictions"], 1)
        self.assertEqual(report["abstentions"], 0)

    def test_polynomial_answers_are_scored_by_exact_symbolic_equivalence(self):
        examples = generate_examples(29, 100, topics=("polynomial_derivative",))
        predictions = {item.example_id: item.exact_answer for item in examples}
        item = next(item for item in examples if " + " in item.exact_answer or " - " in item.exact_answer)
        target = item.exact_answer
        equivalent = target.replace(" ", "")
        self.assertNotEqual(equivalent, target)
        predictions[item.example_id] = equivalent
        report = evaluate_predictions(examples, predictions)
        self.assertEqual(report["correct"], 100)
        self.assertEqual(report["error_class_counts"]["correct_answer"], 100)

    def test_evaluator_scores_exact_matrix_inverse_predictions(self):
        examples = generate_examples(725, 30, topics=("matrix_inverse_2x2",))
        predictions = {item.example_id: item.exact_answer for item in examples}
        report = evaluate_predictions(examples, predictions)
        self.assertEqual(report["correct"], 30)
        self.assertEqual(report["error_class_counts"]["correct_answer"], 30)
        predictions[examples[0].example_id] = "not a matrix"
        report = evaluate_predictions(examples, predictions)
        self.assertEqual(report["invalid_predictions"], 1)
        self.assertEqual(report["correct"], 29)

    def test_scores_exact_polynomial_derivative_predictions(self):
        examples = generate_examples(29, 25, topics=("polynomial_derivative",))
        predictions = {item.example_id: item.exact_answer for item in examples}
        report = evaluate_predictions(examples, predictions)
        self.assertEqual(report["correct"], 25)
        self.assertEqual(report["exact_accuracy_all"], 1.0)
        self.assertEqual(report["per_topic"]["polynomial_derivative"]["exact_accuracy_all"], 1.0)


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
