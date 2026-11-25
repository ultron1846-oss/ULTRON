import unittest
from unittest.mock import patch
import torch

from ultron_core.config import NeuroSparseConfig, count_parameters, count_total_parameters
from ultron_core.training import (TrainingSettings, run_training_steps, seed_training_rng, make_seeded_generator)
import random


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
    def tearDown(self):
        seed_training_rng(0, deterministic=False)

    def setUp(self):
        self.model = MockModel()
        self.optimizer = MockOptimizer()
        trainable = count_parameters(self.model.config)
        self.report = {
            "status": "PREFLIGHT_ONLY",
            "validated": True,
            "training_authorized": False,
            "optimizer_steps": 0,
            "remote_execution_enabled": False,
            "parameter_count": trainable,
            "trainable_parameter_count": trainable,
            "total_parameter_count": count_total_parameters(self.model.config),
            "batch_size": 1,
            "sequence_length": 3,
            "gradient_accumulation_steps": 2,
            "memory_budget_bytes": 2 * 1024 ** 3,
            "budget_covers_persistent_state": True,
            "dataset_manifest_sha256": "a" * 64,
        }
        self.settings = TrainingSettings(max_steps=2, gradient_accumulation_steps=2,
                                        max_seconds=60, write_memory=False)
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
        self.assertEqual(saved[0][0], 1)
        self.assertEqual(saved[0][1]["data_state"]["next_batch_index"], 2)
        self.assertEqual(saved[1][0], 2)
        self.assertEqual(saved[1][1]["data_state"]["next_batch_index"], 4)
        self.assertEqual(saved[1][1]["dataset_manifest_sha256"], "a" * 64)
        self.assertEqual(result["global_step"], 2)
        self.assertEqual(result["data_state"]["next_batch_index"], 4)
        self.assertGreaterEqual(self.model.reset_calls, 9)

    def test_memory_writing_training_is_blocked_until_chunk_semantics_exist(self):
        settings = TrainingSettings(max_steps=1, gradient_accumulation_steps=1,
                                   max_seconds=60, write_memory=True)
        with self.assertRaisesRegex(NotImplementedError, "sequential chunk semantics"):
            run_training_steps(self.model, self.batches, self.optimizer, self.report,
                               settings=settings, training_authorized=True)
        self.assertEqual(self.optimizer.steps, 0)

    def test_preflight_report_must_be_non_authorizing_and_local(self):
        for field, value in (("training_authorized", True), ("remote_execution_enabled", True)):
            report = dict(self.report)
            report[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "non-authorizing"):
                run_training_steps(self.model, self.batches, self.optimizer, report,
                                   settings=self.settings, training_authorized=True)
        self.assertEqual(self.optimizer.steps, 0)

    def test_batch_cannot_exceed_preflight_resource_plan(self):
        oversized = {"input_ids": torch.tensor([[1, 2, 3, 4]], dtype=torch.long)}
        with self.assertRaisesRegex(ValueError, "exceeds the preflight"):
            run_training_steps(self.model, [oversized], self.optimizer, self.report,
                               settings=self.settings, training_authorized=True)
        self.assertEqual(self.optimizer.steps, 0)

    def test_training_memory_writes_default_off(self):
        self.assertFalse(TrainingSettings().write_memory)

    def test_controller_restores_previous_model_mode(self):
        self.model.eval()
        run_training_steps(self.model, self.batches, self.optimizer, self.report,
                           settings=self.settings, training_authorized=True)
        self.assertFalse(self.model.training)

    def test_non_finite_loss_stops_before_optimizer_step(self):
        model = MockModel(non_finite=True)
        with self.assertRaisesRegex(FloatingPointError, "loss is non-finite"):
            run_training_steps(model, self.batches, self.optimizer, self.report,
                              settings=self.settings, training_authorized=True)
        self.assertEqual(self.optimizer.steps, 0)


    def test_python_torch_and_dataloader_rng_are_reproducible(self):
        seed_training_rng(1846, deterministic=True)
        python_first = random.random()
        torch_first = torch.rand(5)
        generator_first = torch.rand(5, generator=make_seeded_generator(1846))
        seed_training_rng(1846, deterministic=True)
        self.assertEqual(random.random(), python_first)
        torch.testing.assert_close(torch.rand(5), torch_first)
        torch.testing.assert_close(torch.rand(5, generator=make_seeded_generator(1846)), generator_first)
        seed_training_rng(1846, deterministic=False)

    def test_seed_helpers_reject_boolean_and_negative_seed(self):
        with self.assertRaisesRegex(ValueError, "seed must be"):
            seed_training_rng(True)
        with self.assertRaisesRegex(ValueError, "seed must be"):
            make_seeded_generator(-1)



    def test_resume_uses_restored_rng_without_reseeding(self):
        metadata = {"format_version": 4, "rng_restored": True, "dataset_hash_verified": True,
                    "step": 12,
                    "data_state": {"epoch": 2, "next_batch_index": 3, "next_sample_index": 3, "seed": 0, "gradient_accumulation_steps": 2},
                    "dataset_manifest_sha256": "a" * 64}
        settings = TrainingSettings(max_steps=1, gradient_accumulation_steps=2,
                                   max_seconds=60, write_memory=False)
        with patch("ultron_core.training.seed_training_rng") as seed:
            result = run_training_steps(self.model, self.batches[:2], self.optimizer,
                self.report, settings=settings, training_authorized=True,
                resume_metadata=metadata)
            seed.assert_not_called()
        self.assertTrue(result["resumed_from_checkpoint"])
        self.assertEqual(self.optimizer.steps, 1)
        self.assertEqual(result["steps_completed"], 1)
        self.assertEqual(result["global_step"], 13)
        self.assertEqual(result["data_state"]["epoch"], 2)
        self.assertEqual(result["data_state"]["next_batch_index"], 5)


    def test_resume_rejects_changed_seed_or_accumulation(self):
        metadata = {"format_version": 4, "rng_restored": True, "step": 4,
                    "data_state": {"epoch": 0, "next_batch_index": 2, "next_sample_index": 2, "seed": 0,
                                   "gradient_accumulation_steps": 2},
                    "dataset_manifest_sha256": "a" * 64}
        with self.assertRaisesRegex(ValueError, "seed does not match"):
            run_training_steps(self.model, self.batches, self.optimizer, self.report,
                settings=TrainingSettings(max_steps=1, gradient_accumulation_steps=2,
                                         seed=1, max_seconds=60, write_memory=False),
                training_authorized=True, resume_metadata=metadata)
        altered_report = dict(self.report)
        altered_report["gradient_accumulation_steps"] = 1
        with self.assertRaisesRegex(ValueError, "accumulation does not match"):
            run_training_steps(self.model, self.batches, self.optimizer, altered_report,
                settings=TrainingSettings(max_steps=1, gradient_accumulation_steps=1,
                                         max_seconds=60, write_memory=False),
                training_authorized=True, resume_metadata=metadata)
        self.assertEqual(self.optimizer.steps, 0)


    def test_resume_requires_next_batch_cursor(self):
        metadata = {"format_version": 4, "step": 8, "rng_restored": True,
                    "data_state": {"epoch": 1, "batch": 3},
                    "dataset_manifest_sha256": "a" * 64}
        with self.assertRaisesRegex(ValueError, "epoch and next_batch_index"):
            run_training_steps(self.model, self.batches, self.optimizer, self.report,
                settings=self.settings, training_authorized=True, resume_metadata=metadata)
        self.assertEqual(self.optimizer.steps, 0)

    def test_incomplete_accumulation_cursor_rewinds_to_last_committed_step(self):
        result = run_training_steps(self.model, self.batches[:3], self.optimizer,
            self.report, settings=TrainingSettings(max_steps=2, gradient_accumulation_steps=2,
            max_seconds=60), training_authorized=True)
        self.assertEqual(result["steps_completed"], 1)
        self.assertEqual(result["microbatches_seen"], 3)
        self.assertEqual(result["discarded_microbatches"], 1)
        self.assertEqual(result["global_step"], 1)
        self.assertEqual(result["data_state"]["next_batch_index"], 2)

    def test_initial_cursor_is_preserved_and_advanced(self):
        result = run_training_steps(self.model, self.batches[:2], self.optimizer,
            self.report, settings=TrainingSettings(max_steps=1, gradient_accumulation_steps=2,
            max_seconds=60), training_authorized=True,
            initial_data_state={"epoch": 5, "next_batch_index": 10})
        self.assertEqual(result["data_state"]["epoch"], 5)
        self.assertEqual(result["data_state"]["next_batch_index"], 12)
        self.assertEqual(result["global_step"], 1)

    def test_checkpoint_callback_metadata_can_be_persisted_and_restored(self):
        import tempfile
        from pathlib import Path
        from ultron_core.checkpoint import save_checkpoint, load_checkpoint
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mock-resume.pt"
            def save_callback(step, metrics):
                save_checkpoint(path, self.model, self.model.config, step=step,
                    data_state=metrics["data_state"],
                    dataset_manifest_sha256=metrics["dataset_manifest_sha256"])
            settings = TrainingSettings(max_steps=1, gradient_accumulation_steps=2,
                                       max_seconds=60)
            run_training_steps(self.model, self.batches, self.optimizer, self.report,
                settings=settings, training_authorized=True, checkpoint_callback=save_callback)
            restored = MockModel()
            metadata = load_checkpoint(path, restored,
                expected_dataset_manifest_sha256="a" * 64)
            self.assertEqual(metadata["step"], 1)
            self.assertEqual(metadata["data_state"]["next_batch_index"], 2)
            self.assertEqual(metadata["dataset_manifest_sha256"], "a" * 64)

    def test_resume_rejects_unrestored_rng_or_wrong_dataset_hash(self):
        base = {"format_version": 4, "rng_restored": True,
                "data_state": {"epoch": 0, "next_batch_index": 1}, "dataset_manifest_sha256": "b" * 64}
        with self.assertRaisesRegex(ValueError, "does not match preflight"):
            run_training_steps(self.model, self.batches, self.optimizer, self.report,
                settings=self.settings, training_authorized=True, resume_metadata=base)
        base["dataset_manifest_sha256"] = "a" * 64
        base["rng_restored"] = False
        with self.assertRaisesRegex(ValueError, "restored RNG"):
            run_training_steps(self.model, self.batches, self.optimizer, self.report,
                settings=self.settings, training_authorized=True, resume_metadata=base)
        self.assertEqual(self.optimizer.steps, 0)


    def test_settings_enforce_step_and_time_caps(self):
        with self.assertRaisesRegex(ValueError, "max_steps"):
            TrainingSettings(max_steps=1001)
        with self.assertRaisesRegex(ValueError, "max_seconds"):
            TrainingSettings(max_seconds=3601)


if __name__ == "__main__":
    unittest.main()
