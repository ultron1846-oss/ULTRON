"""Tests for deterministic curriculum coverage audit; no examples are generated."""
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

    def test_current_university_catalog_and_generator_status_are_explicit(self):
        report = build_coverage_audit()
        self.assertEqual(report["university_curriculum_topic_count"], 197)
        self.assertEqual(report["university_generator_available_count"], 59)
        self.assertEqual(report["university_catalogued_not_implemented_count"], 138)
        self.assertEqual(
            report["university_prerequisite_mapped_topic_count"],
            report["university_curriculum_topic_count"],
        )
        self.assertTrue(report["university_prerequisite_graph_acyclic"])
        self.assertGreater(report["university_prerequisite_edge_count"], 0)

    def test_registry_source_topic_pairs_are_unique(self):
        report = build_coverage_audit()
        self.assertEqual(
            report["unique_source_topic_entry_count"],
            report["combined_registry_entry_count"],
        )
        self.assertGreater(report["unique_topic_id_count"], 0)


if __name__ == "__main__":
    unittest.main()
