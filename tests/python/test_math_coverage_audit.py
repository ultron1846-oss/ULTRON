"""Tests for deterministic, evidence-backed curriculum coverage audit."""
import unittest

from tools.math_generators.coverage_audit import build_coverage_audit


class MathCoverageAuditTests(unittest.TestCase):
    def test_audit_is_deterministic_and_non_authorizing(self):
        first = build_coverage_audit()
        second = build_coverage_audit()
        self.assertEqual(first, second)
        self.assertTrue(first["registry_sync_valid"])
        self.assertFalse(first["data_generated"])
        self.assertFalse(first["training_performed"])
        self.assertFalse(first["model_mastery_claimed"])

    def test_catalogued_generated_validated_benchmarked_and_mastered_are_separate(self):
        report = build_coverage_audit()
        self.assertEqual(report["catalogued_topic_count"], 266)
        self.assertEqual(report["generator_available_topic_count"], 119)
        self.assertEqual(report["independently_validated_topic_count"], 68)
        self.assertEqual(report["benchmarked_topic_count"], 0)
        self.assertEqual(report["mastered_topic_count"], 0)
        self.assertEqual(report["unique_catalog_id_count"], 266)
        self.assertEqual(report["unique_raw_topic_id_count"], 264)
        self.assertEqual(report["scope_qualified_identifier_collision_count"], 0)
        self.assertEqual(report["raw_topic_identifier_collision_count"], 1)
        self.assertEqual(report["raw_topic_identifier_collisions"], {"linear_equations": 3})

    def test_university_topic_split_and_prerequisite_graph(self):
        report = build_coverage_audit()
        self.assertEqual(report["university_curriculum_topic_count"], 213)
        self.assertEqual(report["university_generator_available_count"], 66)
        self.assertEqual(report["university_catalogued_not_implemented_count"], 147)
        self.assertEqual(report["university_prerequisite_mapped_topic_count"], 213)
        self.assertEqual(report["university_prerequisite_edge_count"], 401)
        self.assertTrue(report["university_prerequisite_graph_acyclic"])

    def test_scope_qualified_registry_entries_are_unique(self):
        report = build_coverage_audit()
        self.assertEqual(
            report["unique_source_topic_entry_count"],
            report["combined_registry_entry_count"],
        )
        self.assertEqual(report["unique_catalog_id_count"], report["combined_registry_entry_count"])


if __name__ == "__main__":
    unittest.main()
