import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

import torch
from torch import nn

from ultron_core.compress.report import (
    build_model_for_report,
    main,
    parameter_report,
    parameter_report_for_config,
)
from ultron_core.config import NeuroSparseConfig


class _TiedWeightsModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Embedding(3, 2)
        self.lm_head = nn.Linear(2, 3, bias=False)
        self.lm_head.weight = self.embedding.weight


class _DistinctParametersWithSharedStorage(nn.Module):
    def __init__(self):
        super().__init__()
        self.embedding = nn.Module()
        self.embedding.weight = nn.Parameter(torch.ones(4))
        self.position_embedding = nn.Module()
        # A new Parameter object sharing storage is still distinct for id-based
        # accounting, even though data_ptr() is identical.
        self.position_embedding.weight = nn.Parameter(self.embedding.weight.detach())


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

    def test_foundation_matches_existing_analytical_counts(self):
        config = NeuroSparseConfig.foundation()
        report = parameter_report_for_config(config)
        self.assertEqual(report["total_parameters"], 63_400_451)
        self.assertEqual(report["trainable_parameters"], 61_826_048)
        self.assertEqual(report["config_expected_total"], 63_400_451)
        self.assertEqual(report["config_expected_trainable"], 61_826_048)
        self.assertTrue(report["matches_config"])

    def test_real_foundation_categories_cover_total_and_other_is_allowlisted(self):
        config = NeuroSparseConfig.foundation()
        report = parameter_report(build_model_for_report(config))

        self.assertEqual(
            sum(values["total"] for values in report["by_type"].values()),
            report["total_parameters"],
        )
        self.assertEqual(
            sum(values["trainable"] for values in report["by_type"].values()),
            report["trainable_parameters"],
        )
        self.assertEqual(
            sum(values["frozen"] for values in report["by_type"].values()),
            report["frozen_parameters"],
        )
        self.assertEqual(report["total_parameters"], 63_400_451)
        self.assertEqual(report["trainable_parameters"], 61_826_048)

        expected_other_names = {"final_norm.weight", "final_norm.bias"}
        for layer_index in range(config.num_layers):
            for module_name in ("attention_norm", "norm"):
                for parameter_name in ("weight", "bias"):
                    expected_other_names.add(
                        f"blocks.{layer_index}.{module_name}.{parameter_name}"
                    )
        self.assertEqual(set(report["other_parameter_names"]), expected_other_names)

    def test_tied_weights_are_counted_once_by_parameter_identity(self):
        model = _TiedWeightsModel()
        self.assertIs(model.embedding.weight, model.lm_head.weight)

        report = parameter_report(model)
        self.assertEqual(report["total_parameters"], model.embedding.weight.numel())
        self.assertEqual(report["total_parameters"], 6)
        self.assertEqual(sum(item["total"] for item in report["by_type"].values()), 6)

    def test_distinct_parameter_objects_sharing_storage_are_both_counted(self):
        model = _DistinctParametersWithSharedStorage()
        first = model.embedding.weight
        second = model.position_embedding.weight
        self.assertIsNot(first, second)
        self.assertEqual(first.data_ptr(), second.data_ptr())

        report = parameter_report(model)
        self.assertEqual(report["total_parameters"], 8)

    def test_meta_construction_failure_uses_and_reports_existing_analytical_counts(self):
        with mock.patch(
            "ultron_core.compress.report.build_model_for_report",
            side_effect=RuntimeError("meta device unsupported"),
        ):
            report = parameter_report_for_config(NeuroSparseConfig.foundation())
            self.assertEqual(report["count_method"], "analytical_config_fallback")
            self.assertFalse(report["category_breakdown_available"])
            self.assertEqual(report["total_parameters"], 63_400_451)
            self.assertEqual(report["trainable_parameters"], 61_826_048)
            self.assertIn("meta device unsupported", report["fallback_reason"])

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main([])
        self.assertEqual(exit_code, 0)
        self.assertIn("analytical_config_fallback", output.getvalue())
        self.assertIn("meta-device model construction failed", output.getvalue())
        self.assertIn("63,400,451", output.getvalue())
        self.assertIn("61,826,048", output.getvalue())


if __name__ == "__main__":
    unittest.main()
