import unittest
from collections import Counter
from types import SimpleNamespace

from ultron_core.data_generation import SUPPORTED_TOPICS
from ultron_core.concepts import (
    CONCEPTS,
    CONCEPT_TRANSFER_CATEGORIES,
    TOPIC_TO_CONCEPT,
    concept_coverage_report,
    concept_id_for_topic,
    sample_concept_balanced,
    validate_concept_registry,
    validate_concept_transfer_split,
)


class ConceptTaxonomyTests(unittest.TestCase):
    def test_registry_covers_supported_topics_and_is_acyclic(self):
        self.assertTrue(validate_concept_registry())
        self.assertEqual(set(TOPIC_TO_CONCEPT), set(SUPPORTED_TOPICS))
        self.assertTrue(all(value in CONCEPTS for value in TOPIC_TO_CONCEPT.values()))
        self.assertTrue(all(concept.principle for concept in CONCEPTS.values()))

    def test_topic_lookup_rejects_unknown_topic(self):
        with self.assertRaisesRegex(ValueError, "unsupported concept topic"):
            concept_id_for_topic("not-a-math-topic")

    def test_concept_balanced_sampling_is_deterministic_and_bounded(self):
        examples = [
            SimpleNamespace(example_id=f"arith-{i}", topic="arithmetic", input_text=f"{i} + 1")
            for i in range(5)
        ] + [
            SimpleNamespace(example_id=f"rat-{i}", topic="rational_arithmetic", input_text=f"{i}/2")
            for i in range(3)
        ]
        sampled = sample_concept_balanced(examples, max_per_concept=2, seed=17)
        sampled_again = sample_concept_balanced(reversed(examples), max_per_concept=2, seed=17)
        self.assertEqual([item.example_id for item in sampled], [item.example_id for item in sampled_again])
        counts = Counter(concept_id_for_topic(item.topic) for item in sampled)
        self.assertEqual(len(sampled), 4)
        self.assertTrue(all(count <= 2 for count in counts.values()))

    def test_sampler_rejects_duplicate_ids_and_bad_limit(self):
        item = SimpleNamespace(example_id="same", topic="arithmetic", input_text="1+1")
        with self.assertRaisesRegex(ValueError, "duplicate IDs"):
            sample_concept_balanced([item, item], max_per_concept=2)
        with self.assertRaisesRegex(ValueError, "max_per_concept"):
            sample_concept_balanced([item], max_per_concept=0)

    def test_coverage_report_is_metadata_only(self):
        examples = [
            SimpleNamespace(example_id="a", topic="arithmetic", input_text="1 + 2"),
            SimpleNamespace(example_id="b", topic="arithmetic", input_text="3 + 4"),
        ]
        report = concept_coverage_report(examples)
        self.assertEqual(report["concept_counts"], {"concept.integer_operations": 2})
        self.assertFalse(report["data_generated"])
        self.assertFalse(report["training_performed"])


class ConceptTransferProtocolTests(unittest.TestCase):
    def setUp(self):
        self.train = [
            SimpleNamespace(example_id="train-a", topic="arithmetic", input_text="3 + 4"),
            SimpleNamespace(example_id="train-b", topic="linear_equations", input_text="2*x + 1 = 5"),
            SimpleNamespace(example_id="train-c", topic="polynomial_derivative", input_text="differentiate x^2"),
        ]
        self.test = [
            SimpleNamespace(example_id="test-values", topic="arithmetic", input_text="7 + 9"),
            SimpleNamespace(
                example_id="test-composition",
                topic="arithmetic",
                input_text="5/7 + 2/3",
                concept_ids=("concept.integer_operations", "concept.rational_operations"),
            ),
            SimpleNamespace(example_id="test-prereq", topic="linear_equations", input_text="8*x - 4 = 20"),
            SimpleNamespace(
                example_id="test-unseen-concept",
                topic="matrix_determinant_2x2",
                input_text="determinant [[1, 2], [3, 4]]",
            ),
            SimpleNamespace(example_id="test-surface", topic="arithmetic", input_text="Add seven and nine"),
        ]
        self.categories = {
            "test-values": "unseen_numeric_values",
            "test-composition": "multi_concept_composition",
            "test-prereq": "prerequisite_sensitive",
            "test-unseen-concept": "unseen_concept",
            "test-surface": "unseen_surface_form",
        }

    def test_validates_held_out_transfer_categories(self):
        report = validate_concept_transfer_split(
            self.train, self.test, test_categories=self.categories
        )
        self.assertTrue(report["split_valid"])
        self.assertEqual(report["normalized_prompt_overlap_count"], 0)
        self.assertEqual(report["test_category_counts"], {
            "multi_concept_composition": 1,
            "prerequisite_sensitive": 1,
            "unseen_concept": 1,
            "unseen_numeric_values": 1,
            "unseen_surface_form": 1,
        })
        self.assertFalse(report["training_performed"])
        self.assertFalse(report["data_generated"])

    def test_rejects_prompt_leakage(self):
        leaked = SimpleNamespace(example_id="test-leak", topic="arithmetic", input_text="3 + 4")
        with self.assertRaisesRegex(ValueError, "prompts overlap"):
            validate_concept_transfer_split(
                self.train, [leaked], test_categories={"test-leak": "unseen_surface_form"}
            )

    def test_rejects_reused_numeric_values_for_unseen_value_claim(self):
        reused = SimpleNamespace(example_id="test-reused", topic="arithmetic", input_text="3 + 9")
        with self.assertRaisesRegex(ValueError, "reuses a training numeric value"):
            validate_concept_transfer_split(
                self.train, [reused], test_categories={"test-reused": "unseen_numeric_values"}
            )

    def test_rejects_unseen_concept_claim_when_concept_was_trained(self):
        known = SimpleNamespace(example_id="test-known", topic="arithmetic", input_text="8 + 9")
        with self.assertRaisesRegex(ValueError, "concept present in training"):
            validate_concept_transfer_split(
                self.train, [known], test_categories={"test-known": "unseen_concept"}
            )

    def test_rejects_multi_concept_label_without_multiple_concepts(self):
        single = SimpleNamespace(example_id="test-single", topic="arithmetic", input_text="8 + 9")
        with self.assertRaisesRegex(ValueError, "at least two concepts"):
            validate_concept_transfer_split(
                self.train, [single], test_categories={"test-single": "multi_concept_composition"}
            )


if __name__ == "__main__":
    unittest.main()
