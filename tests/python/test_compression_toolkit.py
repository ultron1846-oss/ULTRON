import unittest

import torch

from ultron_core.compress import ExpertUsageCounter, prune_experts
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


if __name__ == "__main__":
    unittest.main()
