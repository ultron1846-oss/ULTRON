import unittest

import torch

from ultron_core.precision import training_autocast, validate_training_precision
from ultron_core.training import TrainingSettings, causal_language_model_loss


class TrainingPrecisionTests(unittest.TestCase):
    def test_fp32_is_default_and_preserves_dtype(self):
        value = torch.ones(2, 2, dtype=torch.float32)
        with training_autocast("cpu", "fp32"):
            result = value @ value
        self.assertEqual(result.dtype, torch.float32)

    def test_bf16_cpu_autocast_is_scoped_and_differentiable(self):
        value = torch.ones(2, 2, dtype=torch.float32, requires_grad=True)
        with training_autocast("cpu", "bf16"):
            result = value @ value
        self.assertEqual(result.dtype, torch.bfloat16)
        result.float().sum().backward()
        self.assertIsNotNone(value.grad)
        self.assertTrue(torch.isfinite(value.grad).all())

    def test_training_settings_precision_defaults_to_fp32_and_accepts_bf16(self):
        self.assertEqual(TrainingSettings().precision, "fp32")
        self.assertEqual(TrainingSettings(precision="bf16").precision, "bf16")
        with self.assertRaisesRegex(ValueError, "precision must"):
            TrainingSettings(precision="fp16")

    def test_precision_rejects_unknown_values(self):
        for value in ("fp16", "auto", "BF16", "", None, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_training_precision(value)

    def test_language_model_loss_accumulates_logits_in_fp32(self):
        logits = torch.randn(1, 4, 8, dtype=torch.bfloat16, requires_grad=True)
        input_ids = torch.tensor([[1, 2, 3, 4]], dtype=torch.long)
        loss = causal_language_model_loss(logits, input_ids, ignore_index=None)
        self.assertEqual(loss.dtype, torch.float32)
        self.assertTrue(torch.isfinite(loss))
        loss.backward()
        self.assertIsNotNone(logits.grad)
        self.assertTrue(torch.isfinite(logits.grad).all())


if __name__ == "__main__":
    unittest.main()
