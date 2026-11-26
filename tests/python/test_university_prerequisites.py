import json
import unittest
from pathlib import Path

from ultron_core.curriculum_prerequisites import (
    load_curriculum_prerequisites,
    validate_prerequisite_data,
)


CURRICULUM_PATH = Path("tools/math_generators/university/curriculum.json")
PREREQUISITES_PATH = Path("tools/math_generators/university/prerequisites.json")


class UniversityPrerequisiteTests(unittest.TestCase):
    def test_curated_map_covers_declared_fields_and_reports_partial_scope(self):
        curriculum = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
        data = json.loads(PREREQUISITES_PATH.read_text(encoding="utf-8"))
        mapping = load_curriculum_prerequisites()

        expected = {
            item["topic"] for item in curriculum["topics"]
            if item["field"] in data["coverage_fields"]
        }
        self.assertEqual(set(mapping.prerequisites), expected)
        self.assertEqual(mapping.mapped_topic_count, 89)
        self.assertEqual(mapping.source_topic_count, 197)
        self.assertEqual(mapping.source_topic_count - mapping.mapped_topic_count, 108)

    def test_prerequisite_edges_are_ordered_and_queryable(self):
        mapping = load_curriculum_prerequisites()
        self.assertTrue(mapping.is_prerequisite("eigenvalues_and_eigenvectors", "spectral_theorem"))
        self.assertTrue(mapping.is_prerequisite("inner_product_spaces", "spectral_theorem"))
        self.assertFalse(mapping.is_prerequisite("sets_and_functions", "spectral_theorem"))
        positions = {topic: index for index, topic in enumerate(mapping.topological_order)}
        for topic, parents in mapping.prerequisites.items():
            for parent in parents:
                self.assertLess(positions[parent], positions[topic])


    def test_calculus_and_real_analysis_edges_are_present(self):
        mapping = load_curriculum_prerequisites()
        self.assertTrue(mapping.is_prerequisite("power_series", "Taylor_series"))
        self.assertTrue(mapping.is_prerequisite("derivative_theory", "Taylor_series"))
        self.assertTrue(mapping.is_prerequisite("Cauchy_sequences", "pointwise_and_uniform_convergence"))
        self.assertTrue(mapping.is_prerequisite("Lebesgue_measure", "Lebesgue_integral"))


    def test_complex_algebra_and_number_theory_edges_are_present(self):
        mapping = load_curriculum_prerequisites()
        self.assertTrue(mapping.is_prerequisite("Cauchy_integral_formula", "residues"))
        self.assertTrue(mapping.is_prerequisite("groups_and_subgroups", "cyclic_groups"))
        self.assertTrue(mapping.is_prerequisite("fields_and_extensions", "Galois_theory_intro"))
        self.assertTrue(mapping.is_prerequisite("congruences", "Chinese_remainder_theorem"))

    def test_unmapped_curriculum_topic_is_not_assumed_to_have_prerequisites(self):
        mapping = load_curriculum_prerequisites()
        with self.assertRaisesRegex(ValueError, "no curated prerequisite mapping"):
            mapping.prerequisites_for("holomorphic_functions")

    def test_validator_rejects_cycles(self):
        curriculum = {"topics": [{"topic": "a", "field": "F"}, {"topic": "b", "field": "F"}]}
        data = {
            "schema_version": 1,
            "source_topic_count": 2,
            "mapped_topic_count": 2,
            "coverage_fields": ["F"],
            "prerequisites": {"a": ["b"], "b": ["a"]},
        }
        with self.assertRaisesRegex(ValueError, "contains a cycle"):
            validate_prerequisite_data(data, curriculum)

    def test_validator_rejects_unknown_prerequisite(self):
        curriculum = {"topics": [{"topic": "a", "field": "F"}]}
        data = {
            "schema_version": 1,
            "source_topic_count": 1,
            "mapped_topic_count": 1,
            "coverage_fields": ["F"],
            "prerequisites": {"a": ["missing"]},
        }
        with self.assertRaisesRegex(ValueError, "unmapped topic"):
            validate_prerequisite_data(data, curriculum)


if __name__ == "__main__":
    unittest.main()
