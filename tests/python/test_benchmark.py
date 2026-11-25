import unittest

from ultron_core.benchmark import bootstrap_median_ci, percentile


class BenchmarkStatisticsTests(unittest.TestCase):
    def test_parameter_accounting_separates_trainable_and_fixed_weights(self):
        from ultron_core import NeuroSparseConfig, NeuroSparseModel
        from ultron_core.model import SparseExpert
        from ultron_core.benchmark import parameter_accounting
        config = NeuroSparseConfig(vocab_size=64, hidden_size=32, num_layers=1,
            num_experts=4, top_k=2, max_refinements=2, fast_memory_slots=8,
            num_attention_heads=4)
        model = NeuroSparseModel(config)
        report = parameter_accounting(model)
        total = sum(p.numel() for p in model.parameters())
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        expert = sum(p.numel() for module in model.modules()
                     if isinstance(module, SparseExpert)
                     for p in module.parameters() if p.requires_grad)
        self.assertEqual(report["parameters_total"], total)
        self.assertEqual(report["parameters_trainable"], trainable)
        self.assertEqual(report["parameters_fixed"], total - trainable)
        self.assertEqual(report["parameters_expert_trainable"], expert)
        self.assertEqual(report["estimated_structurally_active_trainable_parameters_per_token"],
                         report["parameters_shared_trainable"] + report["estimated_selected_expert_parameters_per_token"])


    def test_cpu_inference_benchmark_smoke_is_non_training(self):
        import math
        from ultron_core.benchmark import run_benchmark
        report = run_benchmark(device="cpu", batch=1, sequence=4,
                              warmup=0, iterations=2, seed=19, num_threads=1)
        self.assertEqual(report["benchmark_kind"], "inference_only_synthetic_token_timing")
        self.assertEqual(report["model_config_name"], "smoke")
        self.assertEqual(report["parameter_count_formula"]["total"], report["parameter_accounting"]["parameters_total"])
        self.assertEqual(report["parameter_count_formula"]["trainable"], report["parameter_accounting"]["parameters_trainable"])
        self.assertFalse(report["training_performed"])
        self.assertEqual(report["optimizer_steps"], 0)
        self.assertEqual(report["measured_iterations"], 2)
        self.assertEqual(len(report["latency_seconds"]["samples"]), 2)
        self.assertTrue(math.isfinite(report["latency_seconds"]["median"]))
        self.assertGreater(report["latency_seconds"]["median"], 0.0)
        self.assertGreater(report["parameter_accounting"]["parameters_total"], 0)

    def test_foundation_parameter_floor_and_cap_rejects_before_allocation(self):
        from unittest.mock import patch
        from ultron_core.config import NeuroSparseConfig, count_parameters, count_total_parameters
        from ultron_core.benchmark import run_benchmark

        config = NeuroSparseConfig.foundation()
        self.assertGreater(count_parameters(config), 60_000_000)
        self.assertEqual(count_total_parameters(config), 63_400_451)
        self.assertEqual(count_parameters(config), 61_826_048)
        with patch("ultron_core.benchmark.NeuroSparseModel") as model_constructor:
            with self.assertRaisesRegex(ValueError, "exceeding the configured max_parameters cap"):
                run_benchmark(model_config="foundation", max_parameters=1, iterations=2)
            model_constructor.assert_not_called()

    def test_benchmark_rejects_invalid_model_config_and_parameter_cap(self):
        from ultron_core.benchmark import run_benchmark

        with self.assertRaisesRegex(ValueError, "model_config"):
            run_benchmark(model_config="unknown", iterations=2)
        with self.assertRaisesRegex(ValueError, "max_parameters"):
            run_benchmark(max_parameters=0, iterations=2)

    def test_benchmark_runtime_restores_rng_and_thread_count(self)
        import torch
        from ultron_core.benchmark import _preserve_benchmark_runtime
        state_before = torch.random.get_rng_state().clone()
        threads_before = torch.get_num_threads()
        with _preserve_benchmark_runtime(123, 1, torch.device("cpu")):
            _ = torch.rand(4)
            self.assertEqual(torch.get_num_threads(), 1)
        self.assertTrue(torch.equal(torch.random.get_rng_state(), state_before))
        self.assertEqual(torch.get_num_threads(), threads_before)

    def test_benchmark_rejects_non_positive_thread_count(self):
        import torch
        from ultron_core.benchmark import _preserve_benchmark_runtime
        with self.assertRaisesRegex(ValueError, "num_threads"):
            with _preserve_benchmark_runtime(1, 0, torch.device("cpu")):
                pass

    def test_bootstrap_interval_is_deterministic(self):
        values = [1.0, 2.0, 2.0, 3.0, 4.0]
        first = bootstrap_median_ci(values, seed=17, resamples=500)
        second = bootstrap_median_ci(values, seed=17, resamples=500)
        self.assertEqual(first, second)
        self.assertLessEqual(first[0], 2.0)
        self.assertGreaterEqual(first[1], 2.0)

    def test_percentile_interpolates_and_validates(self):
        self.assertEqual(percentile([1.0, 2.0, 3.0, 4.0], 0.5), 2.5)
        self.assertAlmostEqual(percentile([1.0, 2.0, 3.0, 4.0], 0.95), 3.85, places=12)
        with self.assertRaisesRegex(ValueError, "q must"):
            percentile([1.0, 2.0], 1.1)
        with self.assertRaisesRegex(ValueError, "at least one"):
            percentile([], 0.5)

    def test_statistics_reject_non_finite_samples(self):
        with self.assertRaisesRegex(ValueError, 'finite'):
            percentile([1.0, float('nan')], 0.5)
        with self.assertRaisesRegex(ValueError, 'finite'):
            bootstrap_median_ci([1.0, float('inf')])

    def test_bootstrap_rejects_single_sample(self):
        with self.assertRaisesRegex(ValueError, "at least two"):
            bootstrap_median_ci([1.0])

    def test_bootstrap_rejects_invalid_resamples(self):
        with self.assertRaisesRegex(ValueError, "at least 100"):
            bootstrap_median_ci([1.0, 2.0], resamples=10)

    def test_bootstrap_rejects_invalid_confidence(self):
        with self.assertRaisesRegex(ValueError, "confidence"):
            bootstrap_median_ci([1.0, 2.0], confidence=1.0)


if __name__ == "__main__":
    unittest.main()
