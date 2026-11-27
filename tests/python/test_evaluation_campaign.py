"""Deterministic evaluation suites, frozen split isolation, and scoring taxonomy."""
import dataclasses
import hashlib
import re
import unittest

from ultron_core.data_generation import generate_examples
from ultron_core.evaluation import (
    build_deterministic_math_task_suite,
    evaluate_predictions,
)
from ultron_core.frozen_evaluation import (
    build_frozen_evaluation_manifest,
    verify_frozen_evaluation_manifest,
)


class DeterministicMathSuiteTests(unittest.TestCase):
    def test_suite_covers_all_supported_topics_and_replays_identically(self):
        first = build_deterministic_math_task_suite(seed=20261127, examples_per_topic=3)
        second = build_deterministic_math_task_suite(seed=20261127, examples_per_topic=3)
        manifest = first["manifest"]
        self.assertEqual(manifest["manifest_sha256"], second["manifest"]["manifest_sha256"])
        self.assertEqual(manifest["topics"], sorted(manifest["topics"]))
        self.assertEqual(len(manifest["topics"]), 8)
        self.assertEqual(len(first["examples"]), 24)
        self.assertTrue(manifest["evaluation_only"])
        self.assertTrue(manifest["independent_reference_validation"])
        self.assertFalse(manifest["training_performed"])
        self.assertFalse(manifest["corpus_written"])

        predictions = {item.example_id: item.exact_answer for item in first["examples"]}
        report = evaluate_predictions(first["examples"], predictions)
        self.assertEqual(report["exact_accuracy_all"], 1.0)
        self.assertEqual(report["correct"], 24)
        self.assertFalse(report["model_evaluated"])
        self.assertFalse(report["training_performed"])

    def test_suite_rejects_unbounded_or_invalid_requests(self):
        for kwargs in (
            {"seed": True},
            {"seed": 1, "examples_per_topic": 0},
            {"seed": 1, "examples_per_topic": 101},
            {"seed": 1, "topics": ()},
            {"seed": 1, "topics": ("arithmetic", "arithmetic")},
            {"seed": 1, "topics": ("not-a-topic",)},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises((TypeError, ValueError)):
                build_deterministic_math_task_suite(**kwargs)


class NumericToleranceAndErrorTaxonomyTests(unittest.TestCase):
    def test_numeric_tolerance_is_opt_in_and_reported_separately(self):
        example = generate_examples(20261127, 1, topics=("arithmetic",))[0]
        from fractions import Fraction
        from decimal import Decimal

        expected = Fraction(example.exact_answer)
        approx = Decimal(expected.numerator) / Decimal(expected.denominator) + Decimal("0.0000001")
        prediction = format(approx, "f")

        exact_report = evaluate_predictions([example], {example.example_id: prediction})
        self.assertEqual(exact_report["exact_correct"], 0)
        self.assertEqual(exact_report["correct"], 0)
        self.assertEqual(exact_report["error_class_counts"]["incorrect_answer"], 1)

        tolerant_report = evaluate_predictions(
            [example],
            {example.example_id: prediction},
            absolute_tolerance=0.000001,
        )
        self.assertEqual(tolerant_report["exact_correct"], 0)
        self.assertEqual(tolerant_report["within_numeric_tolerance"], 1)
        self.assertEqual(tolerant_report["correct"], 1)
        self.assertEqual(tolerant_report["exact_accuracy_all"], 0.0)
        self.assertEqual(tolerant_report["accepted_accuracy_all"], 1.0)
        self.assertEqual(
            tolerant_report["detailed_error_class_counts"],
            {"within_numeric_tolerance": 1},
        )

    def test_relative_tolerance_is_supported_for_scalar_topics_only(self):
        from fractions import Fraction
        from decimal import Decimal

        example = next(
            item
            for seed in range(20261128, 20261160)
            for item in generate_examples(seed, 1, topics=("matrix_determinant_2x2",))
            if Fraction(item.exact_answer) != 0
        )
        expected = Fraction(example.exact_answer)
        approx = (
            Decimal(expected.numerator) / Decimal(expected.denominator)
            * Decimal("1.0000001")
        )
        prediction = format(approx, "f")
        report = evaluate_predictions(
            [example],
            {example.example_id: prediction},
            relative_tolerance=0.000001,
        )
        self.assertEqual(report["within_numeric_tolerance"], 1)

    def test_error_taxonomy_distinguishes_domain_invalid_malformed_wrong_and_abstention(self):
        examples = generate_examples(20261129, 4, topics=("arithmetic",))
        predictions = {
            examples[0].example_id: "1/0",
            examples[1].example_id: "not a number",
            examples[2].example_id: "987654321",
            examples[3].example_id: None,
        }
        report = evaluate_predictions(examples, predictions)
        self.assertEqual(report["invalid_predictions"], 2)
        self.assertEqual(report["abstentions"], 1)
        self.assertEqual(report["incorrect_valid_predictions"], 1)
        self.assertEqual(report["detailed_error_class_counts"], {
            "abstention": 1,
            "domain_invalid_output": 1,
            "malformed_output": 1,
            "mathematically_incorrect_answer": 1,
        })
        self.assertFalse(report["reasoning_trace_scored"])

    def test_tolerance_values_reject_nan_infinity_negative_and_boolean(self):
        example = generate_examples(20261130, 1, topics=("arithmetic",))[0]
        for field, value, error in (
            ("absolute_tolerance", float("nan"), ValueError),
            ("absolute_tolerance", float("inf"), ValueError),
            ("relative_tolerance", -1.0, ValueError),
            ("absolute_tolerance", True, TypeError),
        ):
            with self.subTest(field=field, value=value), self.assertRaises(error):
                evaluate_predictions([example], {}, **{field: value})


class FrozenEvaluationManifestTests(unittest.TestCase):
    def setUp(self):
        self.train = generate_examples(7101, 3, topics=("arithmetic",))
        self.validation = generate_examples(7102, 3, topics=("rational_arithmetic",))
        self.evaluation = generate_examples(7103, 3, topics=("matrix_inverse_2x2",))
        self.categories = {
            item.example_id: "unseen_concept" for item in self.evaluation
        }
        self.revision = "a" * 40

    def build(self, train=None, validation=None, evaluation=None, categories=None, revision=None):
        return build_frozen_evaluation_manifest(
            self.train if train is None else train,
            self.validation if validation is None else validation,
            self.evaluation if evaluation is None else evaluation,
            evaluation_categories=self.categories if categories is None else categories,
            benchmark_revision=self.revision if revision is None else revision,
        )

    def test_manifest_is_stable_and_verifiable_across_input_order(self):
        manifest = self.build()
        report = verify_frozen_evaluation_manifest(
            manifest,
            reversed(self.train),
            reversed(self.validation),
            reversed(self.evaluation),
            evaluation_categories=dict(reversed(list(self.categories.items()))),
            benchmark_revision=self.revision,
        )
        self.assertTrue(report["valid"])
        self.assertEqual(report["split_counts"], {
            "train": 3, "validation": 3, "evaluation": 3,
        })
        self.assertFalse(manifest["training_performed"])
        self.assertFalse(manifest["model_evaluated"])
        self.assertFalse(manifest["corpus_written"])
        for split in ("train", "validation", "evaluation"):
            self.assertEqual(len(manifest["splits"][split]), 3)
            self.assertNotIn("input_text", manifest["splits"][split][0])
            self.assertNotIn("exact_answer", manifest["splits"][split][0])

    def test_manifest_fingerprint_binds_revision_and_reference_content(self):
        original = self.build()
        changed_revision = self.build(revision="b" * 40)
        self.assertNotEqual(original["manifest_sha256"], changed_revision["manifest_sha256"])
        changed_answer = list(self.evaluation)
        changed_answer[0] = dataclasses.replace(
            changed_answer[0],
            exact_answer="123456789",
            target_text="123456789",
        )
        with self.assertRaisesRegex(ValueError, "invalid reference answer"):
            self.build(evaluation=changed_answer)

    def test_rejects_prompt_leakage_between_training_and_validation(self):
        duplicate_validation = generate_examples(
            7101, 3, topics=("arithmetic",)
        )
        categories = {
            item.example_id: "unseen_concept" for item in self.evaluation
        }
        with self.assertRaisesRegex(ValueError, "normalized prompt leakage"):
            self.build(validation=duplicate_validation, categories=categories)

    def test_rejects_duplicate_generation_ingredients_even_if_surface_form_changes(self):
        original = self.train[0]
        match = re.search(r"(?<![A-Za-z0-9_+\-])(\d+)(?![A-Za-z0-9_])", original.input_text)
        self.assertIsNotNone(match)
        altered_prompt = (
            original.input_text[:match.start()]
            + "+"
            + original.input_text[match.start():match.end()]
            + original.input_text[match.end():]
        )
        altered = dataclasses.replace(
            original,
            example_id=hashlib.sha256(b"different-id").hexdigest(),
            input_text=altered_prompt,
        )
        self.assertNotEqual(" ".join(original.input_text.split()), " ".join(altered.input_text.split()))
        with self.assertRaisesRegex(ValueError, "generation ingredient leakage"):
            self.build(validation=(altered,) + tuple(self.validation[1:]))

    def test_rejects_example_id_overlap_across_splits(self):
        duplicate_id = dataclasses.replace(
            self.evaluation[0], example_id=self.train[0].example_id
        )
        with self.assertRaisesRegex(ValueError, "example IDs overlap"):
            self.build(evaluation=(duplicate_id,) + tuple(self.evaluation[1:]))

    def test_validation_concepts_count_as_seen_for_unseen_concept_claims(self):
        evaluation = generate_examples(7104, 1, topics=("rational_arithmetic",))
        categories = {evaluation[0].example_id: "unseen_concept"}
        with self.assertRaisesRegex(ValueError, "concept present in training"):
            self.build(evaluation=evaluation, categories=categories)

    def test_rejects_missing_or_extra_evaluation_category_labels(self):
        with self.assertRaisesRegex(ValueError, "exactly one transfer category"):
            self.build(categories={})


if __name__ == "__main__":
    unittest.main()
