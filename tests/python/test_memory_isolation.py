import unittest

import torch

from ultron_core import NeuroSparseConfig, NeuroSparseModel


class MemoryIsolationTests(unittest.TestCase):
    def model(self):
        return NeuroSparseModel(NeuroSparseConfig(
            vocab_size=64,
            hidden_size=32,
            num_layers=1,
            num_experts=4,
            top_k=2,
            max_refinements=1,
            fast_memory_slots=6,
            num_attention_heads=4,
            max_sequence_length=16,
        ))

    def test_training_memory_write_rejects_multiple_independent_examples(self):
        model = self.model().train()
        ids = torch.randint(1, 64, (2, 4))
        with self.assertRaisesRegex(ValueError, "batch_size=1"):
            model(ids, write_memory=True)

    def test_reset_memory_clears_all_blocks(self):
        model = self.model().train()
        ids = torch.randint(1, 64, (1, 4))
        model(ids, write_memory=True)
        memory = model.blocks[0].memory
        self.assertTrue(bool(memory.valid.any()))
        self.assertNotEqual(int(memory.cursor), 0)

        model.reset_memory()

        self.assertFalse(bool(memory.valid.any()))
        self.assertEqual(int(memory.cursor), 0)
        self.assertEqual(float(memory.fast_weights.abs().sum()), 0.0)
        self.assertEqual(float(memory.episodic_keys.abs().sum()), 0.0)
        self.assertEqual(float(memory.episodic_values.abs().sum()), 0.0)

    def test_eval_mode_never_mutates_memory_even_when_write_requested(self):
        model = self.model().eval()
        ids = torch.randint(1, 64, (2, 4))
        model(ids, write_memory=True)
        for block in model.blocks:
            self.assertFalse(bool(block.memory.valid.any()))


if __name__ == "__main__":
    unittest.main()
