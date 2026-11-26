import tempfile
import unittest
from pathlib import Path

import torch
from torch import nn

from ultron_core.compress import (
    ExpertUsageCounter,
    LowRankLinear,
    factorize_linear,
    factorize_model,
    merge_experts,
    prune_experts,
    simulate_int8_quantization,
    load_compression_artifact,
    run_compression_pipeline,
    save_compression_artifact,
)
from ultron_core.config import NeuroSparseConfig
from ultron_core.model import NeuroSparseModel


def small_model():
    torch.manual_seed(314159)
    config = NeuroSparseConfig(
        vocab_size=64,
        hidden_size=32,
        num_layers=2,
        num_experts=4,
        top_k=2,
        expert_multiplier=2,
        fast_memory_slots=8,
        num_attention_heads=4,
        max_sequence_length=32,
    )
    return NeuroSparseModel(config)


class ExpertUsageCounterTests(unittest.TestCase):
    def test_counts_expert_token_rows_per_layer_without_training(self):
        model = small_model().eval()
        counter = ExpertUsageCounter(model)
        input_ids = torch.tensor([[1, 2, 3, 4, 5]], dtype=torch.long)

        with counter:
            with torch.inference_mode():
                model(input_ids)

        report = counter.snapshot()
        self.assertEqual(report["layer_count"], 2)
        self.assertEqual(report["expert_count"], 4)
        self.assertEqual(report["total_assignments"], 2 * 5 * 2)
        for layer_counts in report["layers"].values():
            self.assertEqual(sum(layer_counts), 5 * 2)
        self.assertEqual(report["measurement"], "expert_forward_input_token_rows")

        before = counter.snapshot()
        with torch.inference_mode():
            model(input_ids)
        self.assertEqual(counter.snapshot(), before)

    def test_reset_and_close_are_idempotent(self):
        model = small_model().eval()
        counter = ExpertUsageCounter(model)
        with torch.inference_mode():
            model(torch.tensor([[1, 2]], dtype=torch.long))
        self.assertGreater(counter.snapshot()["total_assignments"], 0)
        counter.reset()
        self.assertEqual(counter.snapshot()["total_assignments"], 0)
        counter.close()
        counter.close()
        with torch.inference_mode():
            model(torch.tensor([[1, 2]], dtype=torch.long))
        self.assertEqual(counter.snapshot()["total_assignments"], 0)


class ExpertPruningTests(unittest.TestCase):
    def test_prunes_low_usage_experts_in_a_new_model_and_preserves_weights(self):
        model = small_model().eval()
        original_state = {name: value.clone() for name, value in model.state_dict().items()}
        usage = {"layers": {"0": [1, 20, 5, 2], "1": [1, 20, 5, 2]}}
        result, report = prune_experts(model, usage, keep_experts=2)

        self.assertIsNot(result, model)
        self.assertEqual(result.config.num_experts, 2)
        self.assertEqual(report["kept_expert_indices"], [1, 2])
        self.assertEqual(report["pruned_expert_indices"], [0, 3])
        for layer_index in range(2):
            self.assertTrue(torch.equal(
                result.blocks[layer_index].experts[0].net[0].weight,
                model.blocks[layer_index].experts[1].net[0].weight,
            ))
            self.assertTrue(torch.equal(
                result.blocks[layer_index].router.proj.weight,
                model.blocks[layer_index].router.proj.weight[[1, 2]],
            ))
        for name, value in model.state_dict().items():
            self.assertTrue(torch.equal(value, original_state[name]))

        with torch.inference_mode():
            output = result(torch.tensor([[1, 2, 3]], dtype=torch.long))
        self.assertEqual(tuple(output["logits"].shape), (1, 3, 64))

    def test_rejects_pruning_below_router_top_k(self):
        model = small_model()
        before = {name: value.clone() for name, value in model.state_dict().items()}
        with self.assertRaisesRegex(ValueError, "at least top_k"):
            prune_experts(model, {"layers": {"0": [1, 1, 1, 1], "1": [1, 1, 1, 1]}}, keep_experts=1)
        for name, value in model.state_dict().items():
            self.assertTrue(torch.equal(value, before[name]))


class ExpertMergeTests(unittest.TestCase):
    def test_keeps_layer_specific_real_representatives_without_averaging(self):
        model = small_model().eval()
        original_state = {name: value.clone() for name, value in model.state_dict().items()}
        usage = {"layers": {"0": [1, 20, 7, 2], "1": [9, 2, 3, 30]}}
        result, report = merge_experts(model, [[0, 1], [2, 3]], usage)

        self.assertEqual(result.config.num_experts, 2)
        self.assertEqual(report["representatives_by_layer"], {"0": [1, 2], "1": [0, 3]})
        for layer_index, representatives in enumerate(([1, 2], [0, 3])):
            for new_index, old_index in enumerate(representatives):
                self.assertTrue(torch.equal(
                    result.blocks[layer_index].experts[new_index].net[0].weight,
                    model.blocks[layer_index].experts[old_index].net[0].weight,
                ))
                self.assertTrue(torch.equal(
                    result.blocks[layer_index].router.proj.weight[new_index],
                    model.blocks[layer_index].router.proj.weight[old_index],
                ))
        self.assertFalse(report["ridge_refit"])
        for name, value in model.state_dict().items():
            self.assertTrue(torch.equal(value, original_state[name]))
        with torch.inference_mode():
            output = result(torch.tensor([[1, 2, 3]], dtype=torch.long))
        self.assertEqual(tuple(output["logits"].shape), (1, 3, 64))

    def test_rejects_groups_that_do_not_partition_all_experts(self):
        model = small_model()
        with self.assertRaisesRegex(ValueError, "partition every"):
            merge_experts(model, [[0, 1], [1, 2]])

class LowRankFactorizationTests(unittest.TestCase):
    def test_svd_selects_rank_within_relative_frobenius_error_limit(self):
        torch.manual_seed(2718)
        linear = nn.Linear(13, 10, bias=True)
        original_weight = linear.weight.detach().clone()
        result, report = factorize_linear(linear, max_relative_error=0.25)
        self.assertIsInstance(result, LowRankLinear)
        self.assertLessEqual(report["relative_frobenius_error"], 0.25 + 1e-6)
        self.assertTrue(torch.equal(linear.weight, original_weight))
        reconstructed = result.up.weight @ result.down.weight
        actual_error = torch.linalg.vector_norm(original_weight - reconstructed) / torch.linalg.vector_norm(original_weight)
        self.assertAlmostEqual(float(actual_error), report["relative_frobenius_error"], places=5)

    def test_zero_matrix_is_handled_without_nan(self):
        layer = nn.Linear(5, 4, bias=False)
        with torch.no_grad():
            layer.weight.zero_()
        factor, report = factorize_linear(layer, max_relative_error=0.0)
        self.assertEqual(factor.rank, 1)
        self.assertEqual(report["relative_frobenius_error"], 0.0)

    def test_model_factorization_is_copy_only_and_keeps_forward_contract(self):
        model = small_model().eval()
        original = model.blocks[0].experts[0].net[0].weight.detach().clone()
        result, report = factorize_model(
            model,
            max_relative_error=0.1,
            target_modules=["blocks.0.experts.0.net.0"],
        )
        self.assertIsNot(result, model)
        self.assertIsInstance(result.blocks[0].experts[0].net[0], LowRankLinear)
        self.assertTrue(torch.equal(model.blocks[0].experts[0].net[0].weight, original))
        self.assertEqual(report["factorized_layer_count"], 1)
        with torch.inference_mode():
            output = result(torch.tensor([[1, 2]], dtype=torch.long))
        self.assertEqual(tuple(output["logits"].shape), (1, 2, 64))

    def test_rejects_unknown_target_module(self):
        with self.assertRaisesRegex(ValueError, "unknown target"):
            factorize_model(small_model(), target_modules=["missing.layer"])


class SimulatedInt8QuantizationTests(unittest.TestCase):
    def test_quantizes_copy_and_reports_per_layer_sensitivity(self):
        model = small_model().eval()
        path = "blocks.0.experts.0.net.0"
        original_weight = model.get_submodule(path).weight.detach().clone()
        torch.manual_seed(99)
        sample = torch.randn(5, model.get_submodule(path).in_features)
        result, report = simulate_int8_quantization(
            model,
            sensitivity_inputs={path: sample},
        )
        self.assertIsNot(result, model)
        self.assertTrue(torch.equal(model.get_submodule(path).weight, original_weight))
        self.assertFalse(torch.equal(result.get_submodule(path).weight, original_weight))
        self.assertIn(path, report["layers"])
        layer_report = report["layers"][path]
        self.assertEqual(layer_report["quantization"], "symmetric_per_layer_int8_simulation")
        self.assertGreater(layer_report["scale"], 0.0)
        self.assertIsNotNone(layer_report["relative_output_error"])
        self.assertIn("lm_head", report["skipped_tied_modules"])
        with torch.inference_mode():
            output = result(torch.tensor([[1, 2, 3]], dtype=torch.long))
        self.assertEqual(tuple(output["logits"].shape), (1, 3, 64))

    def test_zero_weight_layer_has_finite_scale_and_zero_error(self):
        model = nn.Sequential(nn.Linear(4, 3, bias=False))
        with torch.no_grad():
            model[0].weight.zero_()
        result, report = simulate_int8_quantization(model)
        self.assertEqual(report["layers"]["0"]["scale"], 1.0)
        self.assertEqual(report["layers"]["0"]["relative_weight_error"], 0.0)
        self.assertTrue(torch.equal(result[0].weight, model[0].weight))


class CompressionArtifactAndPipelineTests(unittest.TestCase):
    def test_pipeline_writes_versioned_artifact_and_loads_it(self):
        model = small_model().eval()
        path = "blocks.0.experts.0.net.0"
        torch.manual_seed(41)
        sample = torch.randn(4, 32)
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "ultron-compressed.pt"
            result, report = run_compression_pipeline(
                model,
                [
                    {
                        "name": "factorize",
                        "options": {
                            "max_relative_error": 0.15,
                            "target_modules": [path],
                        },
                    },
                    {
                        "name": "quantize_int8",
                        "options": {
                            "sensitivity_inputs": {path + ".down": sample},
                        },
                    },
                ],
                parent_checkpoint_id="seeded-foundation-checkpoint",
                artifact_version="0.1.0",
                artifact_path=artifact_path,
            )
            self.assertTrue(report["success"], report.get("error", report))
            self.assertFalse(report["rolled_back"])
            self.assertEqual(len(report["steps"]), 2)
            self.assertTrue(artifact_path.is_file())
            self.assertIsNot(result, model)

            artifact = load_compression_artifact(artifact_path)
            self.assertEqual(artifact["format"], "ultron.compressed-model")
            self.assertEqual(artifact["format_version"], 1)
            self.assertEqual(artifact["artifact_version"], "0.1.0")
            self.assertEqual(artifact["parent_checkpoint_id"], "seeded-foundation-checkpoint")
            self.assertFalse(artifact["foundation_parameter_floor_applies"])
            self.assertEqual(len(artifact["compression_steps"]), 2)
            self.assertIn(path + ".down.weight", artifact["model_state"])

    def test_pipeline_rolls_back_all_steps_on_failure(self):
        model = small_model().eval()
        before = {name: value.clone() for name, value in model.state_dict().items()}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "must-not-exist.pt"
            result, report = run_compression_pipeline(
                model,
                [
                    {"name": "quantize_int8", "options": {}},
                    {"name": "not-a-real-compression-step", "options": {}},
                ],
                parent_checkpoint_id="seeded-parent",
                artifact_path=target,
            )
            self.assertFalse(report["success"])
            self.assertTrue(report["rolled_back"])
            self.assertEqual(report["failed_step"], "not-a-real-compression-step")
            self.assertFalse(target.exists())
            self.assertIsNot(result, model)
            for name, value in result.state_dict().items():
                self.assertTrue(torch.equal(value, before[name]))
            for name, value in model.state_dict().items():
                self.assertTrue(torch.equal(value, before[name]))

    def test_artifact_paths_are_immutable(self):
        model = small_model().eval()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "artifact.pt"
            save_compression_artifact(
                target,
                model,
                parent_checkpoint_id="parent-immutable",
                artifact_version="1.0.0",
                compression_steps=[{"name": "test-only", "options": {}}],
            )
            original_bytes = target.read_bytes()
            with self.assertRaisesRegex(FileExistsError, "cannot be overwritten"):
                save_compression_artifact(
                    target,
                    model,
                    parent_checkpoint_id="different-parent",
                    artifact_version="1.0.1",
                    compression_steps=[{"name": "test-only", "options": {}}],
                )
            self.assertEqual(target.read_bytes(), original_bytes)

    def test_artifact_state_hash_detects_tampering(self):
        model = small_model().eval()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "artifact.pt"
            save_compression_artifact(
                target,
                model,
                parent_checkpoint_id="parent-123",
                artifact_version="1.2.3",
                compression_steps=[{"name": "test-only", "options": {}}],
            )
            payload = torch.load(target, map_location="cpu", weights_only=True)
            key = next(iter(payload["model_state"]))
            payload["model_state"][key].view(-1)[0] += 1
            torch.save(payload, target)
            with self.assertRaisesRegex(ValueError, "hash"):
                load_compression_artifact(target)


if __name__ == "__main__":
    unittest.main()
