import unittest

from ultron_core.config import (
    MIN_FOUNDATION_TRAINABLE_PARAMETERS,
    NeuroSparseConfig,
    count_parameters,
    count_total_parameters,
)


class ModelCapacityTests(unittest.TestCase):
    def test_foundation_has_at_least_sixty_million_trainable_parameters(self):
        config = NeuroSparseConfig.foundation()
        self.assertGreaterEqual(
            count_parameters(config),
            MIN_FOUNDATION_TRAINABLE_PARAMETERS,
        )
        self.assertGreaterEqual(count_total_parameters(config), count_parameters(config))

    def test_expanded_configuration_exceeds_foundation(self):
        foundation = NeuroSparseConfig.foundation()
        expanded = NeuroSparseConfig.expanded()
        self.assertGreater(count_parameters(expanded), count_parameters(foundation))
        self.assertEqual(expanded.hidden_size, 768)
        self.assertEqual(expanded.num_layers, 4)
        self.assertEqual(expanded.num_experts, 12)

    def test_expanded_configuration_rejects_non_expansion(self):
        with self.assertRaisesRegex(ValueError, "must exceed foundation capacity"):
            NeuroSparseConfig.expanded(
                hidden_size=512,
                num_layers=3,
                num_experts=8,
                expert_multiplier=4,
                num_attention_heads=8,
            )

    def test_parameter_formula_matches_instantiated_small_model(self):
        from ultron_core.model import NeuroSparseModel

        config = NeuroSparseConfig(
            vocab_size=64,
            hidden_size=32,
            num_layers=1,
            num_experts=4,
            top_k=2,
            expert_multiplier=2,
            fast_memory_slots=8,
            num_attention_heads=4,
            max_sequence_length=32,
        )
        model = NeuroSparseModel(config)
        actual_total = sum(parameter.numel() for parameter in model.parameters())
        actual_trainable = sum(
            parameter.numel() for parameter in model.parameters()
            if parameter.requires_grad
        )
        self.assertEqual(count_total_parameters(config), actual_total)
        self.assertEqual(count_parameters(config), actual_trainable)


if __name__ == "__main__":
    unittest.main()
