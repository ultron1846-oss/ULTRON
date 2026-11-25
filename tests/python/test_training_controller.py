import unittest
import torch

from ultron_core.config import NeuroSparseConfig, count_parameters
from ultron_core.training import TrainingSettings, run_training_steps


class MockModel(torch.nn.Module):
    def __init__(self, non_finite=False):
        super().__init__()
        self.config = NeuroSparseConfig.foundation()
        self.reset_calls = 0
        self.non_finite = non_finite

    def reset_memory(self):
        self.reset_calls += 1

    def forward(self, input_ids, write_memory=False, attention_mask=None):
        shape = (*input_ids.shape, self.config.vocab_size)
        logits = torch.zeros(shape, requires_grad=True)
        if self.non_finite:
            logits = logits + torch.tensor(float("nan"))
        auxiliary = logits.sum() * 0.0
        return {"logits": logits, "load_balance_loss": auxiliary,
                "prediction_error": auxiliary}


class MockOptimizer:
    def __init__(self):
        self.steps = 0
        self.zero_calls = 0

    def zero_grad(self, set_to_none=True):
        self.zero_calls += 1

    def step(self):
        # Mock only: records controller behavior, never mutates model weights.
        self.steps += 1


class BoundedTrainingControllerTests(unittest.TestCase):
    def setUp(self):
        self.model = MockModel()
        self.optimizer = MockOptimizer()
        self.report = {"validated": True, "parameter_count": count_parameters(self.model.config)}
        self.settings = TrainingSettings(max_steps=2, gradient_accumulation_steps=2,
                                        max_seconds=60, write_memory=True)
        self.batches = [{"input_ids": torch.tensor([[1, 2, 3]], dtype=torch.long)}
                        for _ in range(4)]

    def test_authorization_gate_does_not_consume_batches(self):
        consumed = []
        def batches():
            consumed.append(True)
            yield self.batches[0]
        with self.assertRaisesRegex(PermissionError, "explicit training authorization"):
            run_training_steps(self.model, batches(), self.optimizer, self.report,
                               settings=self.settings, training_authorized=False)
        self.assertEqual(consumed, [])
        self.assertEqual(self.optimizer.steps, 0)

    def test_mock_controller_respects_step_cap_and_resets_memory(self):
        saved = []
        result = run_training_steps(
            self.model, self.batches, self.optimizer, self.report,
            settings=self.settings, training_authorized=True,
            checkpoint_callback=lambda step, metrics: saved.append((step, metrics)),
        )
        self.assertEqual(result["steps_completed"], 2)
        self.assertEqual(result["microbatches_seen"], 4)
        self.assertEqual(result["stop_reason"], "step_limit")
        self.assertEqual(self.optimizer.steps, 2)
        self.assertEqual(len(saved), 2)
        self.assertGreaterEqual(self.model.reset_calls, 9)

    def test_memory_writes_reject_multi_example_batches(self):
        batch = {"input_ids": torch.tensor([[1, 2, 3], [1, 2, 3]], dtype=torch.long)}
        with self.assertRaisesRegex(ValueError, "batch_size=1"):
            run_training_steps(self.model, [batch], self.optimizer, self.report,
                               settings=self.settings, training_authorized=True)
        self.assertEqual(self.optimizer.steps, 0)

    def test_non_finite_loss_stops_before_optimizer_step(self):
        model = MockModel(non_finite=True)
        with self.assertRaisesRegex(FloatingPointError, "loss is non-finite"):
            run_training_steps(model, self.batches, self.optimizer, self.report,
                              settings=self.settings, training_authorized=True)
        self.assertEqual(self.optimizer.steps, 0)

    def test_settings_enforce_step_and_time_caps(self):
        with self.assertRaisesRegex(ValueError, "max_steps"):
            TrainingSettings(max_steps=1001)
        with self.assertRaisesRegex(ValueError, "max_seconds"):
            TrainingSettings(max_seconds=3601)


if __name__ == "__main__":
    unittest.main()
