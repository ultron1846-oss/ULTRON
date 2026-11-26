import unittest

from ultron_core.compress.report import build_model_for_report, parameter_report
from ultron_core.config import NeuroSparseConfig


class CompressionParameterReportTests(unittest.TestCase):
    def small_config(self):
        return NeuroSparseConfig(
            vocab_size=64, hidden_size=32, num_layers=1, num_experts=4,
            top_k=2, expert_multiplier=2, fast_memory_slots=8,
            num_attention_heads=4, max_sequence_length=32,
        )

    def test_module_and_type_counts_sum_to_total(self):
        report = parameter_report(build_model_for_report(self.small_config()))
        self.assertEqual(sum(v["total"] for v in report["by_module"].values()), report["total_parameters"])
        self.assertEqual(sum(v["total"] for v in report["by_type"].values()), report["total_parameters"])
        self.assertEqual(sum(v["trainable"] for v in report["by_type"].values()), report["trainable_parameters"])
        self.assertEqual(sum(v["frozen"] for v in report["by_type"].values()), report["frozen_parameters"])

    def test_required_category_buckets_are_present(self):
        report = parameter_report(build_model_for_report(self.small_config()))
        for name in ("embedding", "attention", "expert", "router", "refinement", "memory"):
            self.assertGreater(report["by_type"][name]["total"], 0)

    def test_foundation_matches_exact_existing_counts_without_allocating_weights(self):
        report = parameter_report(build_model_for_report(NeuroSparseConfig.foundation()))
        self.assertEqual(report["total_parameters"], 63_400_451)
        self.assertEqual(report["trainable_parameters"], 61_826_048)
        self.assertTrue(report["matches_config"])

    def test_tied_embedding_is_counted_once(self):
        model = build_model_for_report(self.small_config())
        report = parameter_report(model)
        self.assertEqual(report["total_parameters"], sum(p.numel() for p in model.parameters()))


if __name__ == "__main__":
    unittest.main()
