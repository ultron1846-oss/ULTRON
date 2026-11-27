import unittest
from unittest.mock import patch
import torch

from ultron_core.config import (MIN_FOUNDATION_TRAINABLE_PARAMETERS, NeuroSparseConfig,
                                count_parameters, count_total_parameters)
from ultron_core.training import (TrainingSettings, run_training_steps, seed_training_rng, make_seeded_generator)
from ultron_core.resource_monitor import MemoryUsage, RuntimeMemoryMonitor
import random


class MockModel(torch.nn.Module):
    def __init__(self, non_finite=False):
        super().__init__()
        self.config = NeuroSparseConfig.foundation()
        # Meta-device parameters model the exact foundation count without
        # allocating 60M+ real weights in controller unit tests.
        trainable_count = count_parameters(self.config)
        total_count = count_total_parameters(self.config)
        self.foundation_trainable = torch.nn.Parameter(
            torch.empty(trainable_count, device="meta")
        )
        self.foundation_frozen = torch.nn.Parameter(
            torch.empty(total_count - trainable_count, device="meta"),
            requires_grad=False,
        )
        self.reset_calls = 0
        self.non_finite = non_finite
        self.activation_checkpointing = False

    def set_activation_checkpointing(self, enabled):
        if not isinstance(enabled, bool):
            raise TypeError("activation_checkpointing must be boolean")
        self.activation_checkpointing = enabled

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
    def __init__(self, parameters=()):
        self.steps = 0
        self.zero_calls = 0
        self.param_groups = [{"params": list(parameters)}]

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
        self.optimizer = MockOptimizer(
            parameter for parameter in self.model.parameters() if parameter.requires_grad
        )
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
            "split_counts": {"train": 4, "validation": 1, "test": 1},
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

    def _assert_optimizer_rejected_before_batches(self, optimizer, message):
        consumed = []

        def batches():
            consumed.append(True)
            yield self.batches[0]

        with self.assertRaisesRegex((TypeError, ValueError), message):
            run_training_steps(
                self.model, batches(), optimizer, self.report,
                settings=self.settings, training_authorized=True,
            )

        self.assertEqual(consumed, [])
        self.assertEqual(optimizer.steps, 0)

    def test_optimizer_rejects_missing_trainable_parameters_before_batches(self):
        optimizer = MockOptimizer()
        optimizer.param_groups = [{"params": []}]
        self._assert_optimizer_rejected_before_batches(
            optimizer, "optimizer parameters must match"
        )

    def test_optimizer_rejects_unrelated_parameters_before_batches(self):
        optimizer = MockOptimizer([
            torch.nn.Parameter(torch.empty(1, device="meta"))
        ])
        self._assert_optimizer_rejected_before_batches(
            optimizer, "optimizer parameters must match"
        )

    def test_optimizer_rejects_frozen_parameters_before_batches(self):
        optimizer = MockOptimizer([
            parameter for parameter in self.model.parameters()
        ])
        self._assert_optimizer_rejected_before_batches(
            optimizer, "optimizer parameters must match"
        )

    def test_optimizer_rejects_duplicate_parameters_before_batches(self):
        trainable = next(
            parameter for parameter in self.model.parameters() if parameter.requires_grad
        )
        optimizer = MockOptimizer([trainable, trainable])
        self._assert_optimizer_rejected_before_batches(
            optimizer, "duplicate model parameter"
        )

    def test_optimizer_requires_parameter_groups_before_batches(self):
        optimizer = MockOptimizer()
        del optimizer.param_groups
        self._assert_optimizer_rejected_before_batches(
            optimizer, "optimizer must expose non-empty param_groups"
        )

    def test_controller_rejects_actual_trainable_parameter_count_mismatch_before_batches(self):
        self.model.extra_trainable = torch.nn.Parameter(torch.empty(1, device="meta"))
        consumed = []

        def batches():
            consumed.append(True)
            yield self.batches[0]

        with self.assertRaisesRegex(ValueError, "actual model trainable parameter count"):
            run_training_steps(
                self.model, batches(), self.optimizer, self.report,
                settings=self.settings, training_authorized=True,
            )

        self.assertEqual(consumed, [])
        self.assertEqual(self.optimizer.steps, 0)

    def test_controller_rejects_frozen_foundation_parameters_before_batches(self):
        self.model.foundation_trainable.requires_grad_(False)
        consumed = []

        def batches():
            consumed.append(True)
            yield self.batches[0]

        with self.assertRaisesRegex(ValueError, "actual model trainable parameter count"):
            run_training_steps(
                self.model, batches(), self.optimizer, self.report,
                settings=self.settings, training_authorized=True,
            )

        self.assertEqual(consumed, [])
        self.assertEqual(self.optimizer.steps, 0)

    def test_controller_enforces_foundation_floor_before_consuming_batches(self):
        report = dict(self.report)
        below_floor = MIN_FOUNDATION_TRAINABLE_PARAMETERS - 1
        report["parameter_count"] = below_floor
        report["trainable_parameter_count"] = below_floor
        consumed = []

        def batches():
            consumed.append(True)
            yield self.batches[0]

        with self.assertRaisesRegex(
                ValueError, "60,000,000 trainable parameter minimum"):
            run_training_steps(
                self.model, batches(), self.optimizer, report,
                settings=self.settings, training_authorized=True,
            )

        self.assertEqual(consumed, [])
        self.assertEqual(self.optimizer.steps, 0)

    def test_mock_controller_respects_step_cap_and_resets_memory(self):
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 4
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=self.settings.seed,
            dataset_manifest_sha256="a" * 64)
        loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=0)
        saved = []
        result = run_training_steps(
            self.model, loader, self.optimizer, self.report,
            settings=self.settings, training_authorized=True, sampler=sampler,
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
        self.assertEqual(result["data_state"]["sampler_state"]["next_index"], 4)
        self.assertGreaterEqual(self.model.reset_calls, 9)

    def test_loss_metric_storage_stays_bounded_over_long_session(self):
        settings = TrainingSettings(
            max_steps=10, gradient_accumulation_steps=2,
            max_seconds=60, write_memory=False,
        )
        stack_sizes = []
        original_stack = torch.stack

        def tracked_stack(tensors, *args, **kwargs):
            stack_sizes.append(len(tensors))
            return original_stack(tensors, *args, **kwargs)

        with patch("torch.stack", side_effect=tracked_stack):
            result = run_training_steps(
                self.model, self.batches * 5, self.optimizer, self.report,
                settings=settings, training_authorized=True,
            )

        self.assertEqual(result["steps_completed"], 10)
        self.assertEqual(result["microbatches_seen"], 20)
        self.assertTrue(stack_sizes)
        self.assertLessEqual(max(stack_sizes), settings.gradient_accumulation_steps)
        self.assertTrue(torch.isfinite(torch.tensor(result["mean_loss"])))

    def test_training_metrics_sync_once_per_optimizer_step(self):
        original_cpu = torch.Tensor.cpu
        cpu_calls = []
        def counted_cpu(tensor, *args, **kwargs):
            cpu_calls.append(tensor)
            return original_cpu(tensor, *args, **kwargs)
        with patch.object(torch.Tensor, "cpu", new=counted_cpu):
            result = run_training_steps(
                self.model, self.batches, self.optimizer, self.report,
                settings=self.settings, training_authorized=True,
            )
        # Four microbatches are grouped into two optimizer steps. Scalar loss
        # validation should transfer once per step, not once per microbatch.
        self.assertEqual(len(cpu_calls), 2)
        self.assertIsInstance(result["mean_loss"], float)
        self.assertTrue(torch.isfinite(torch.tensor(result["mean_loss"])))

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

    def test_controller_enables_and_restores_activation_checkpointing(self):
        settings = TrainingSettings(max_steps=1, gradient_accumulation_steps=2,
            max_seconds=60, activation_checkpointing=True)
        result = run_training_steps(self.model, self.batches, self.optimizer,
            self.report, settings=settings, training_authorized=True)
        self.assertEqual(result["steps_completed"], 1)
        self.assertFalse(self.model.activation_checkpointing)

    def test_opt_in_performance_metrics_report_tokens_and_cpu_timing(self):
        settings = TrainingSettings(max_steps=1, gradient_accumulation_steps=2,
            max_seconds=60, profile_performance=True)
        result = run_training_steps(self.model, self.batches, self.optimizer,
            self.report, settings=settings, training_authorized=True)
        metrics = result["performance"]
        self.assertTrue(metrics["profiled"])
        self.assertEqual(metrics["completed_optimizer_steps"], 1)
        self.assertEqual(metrics["target_tokens"], 4)
        self.assertGreater(metrics["elapsed_seconds"], 0.0)
        self.assertGreater(metrics["target_tokens_per_second"], 0.0)
        self.assertGreaterEqual(metrics["step_seconds_median"], 0.0)
        self.assertIsNone(metrics["peak_cuda_memory_bytes"])

    def test_performance_profiling_is_off_by_default_and_validated(self):
        self.assertFalse(TrainingSettings().profile_performance)
        with self.assertRaisesRegex(TypeError, "profile_performance"):
            TrainingSettings(profile_performance=1)

    def test_training_memory_writes_default_off(self):
        self.assertFalse(TrainingSettings().write_memory)

    def test_controller_restores_previous_model_mode(self):
        self.model.eval()
        run_training_steps(self.model, self.batches, self.optimizer, self.report,
                           settings=self.settings, training_authorized=True)
        self.assertFalse(self.model.training)

    def test_non_finite_loss_stops_before_optimizer_step(self):
        model = MockModel(non_finite=True)
        optimizer = MockOptimizer(
            parameter for parameter in model.parameters() if parameter.requires_grad
        )
        with self.assertRaisesRegex(FloatingPointError, "loss is non-finite"):
            run_training_steps(model, self.batches, optimizer, self.report,
                              settings=self.settings, training_authorized=True)
        self.assertEqual(optimizer.steps, 0)


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
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 8
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64, epoch=2, next_index=3)
        sampler_state = sampler.state_dict()
        loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=0)
        report = dict(self.report)
        report["split_counts"] = {"train": 8, "validation": 1, "test": 1}
        metadata = {"format_version": 4, "rng_restored": True,
            "optimizer_state_present": True, "optimizer_restored": True,
            "scheduler_state_present": False, "scheduler_restored": False,
            "dataset_hash_verified": True,
                    "step": 12, "seed": 0, "gradient_accumulation_steps": 2,
                    "data_state": {"epoch": 2, "next_batch_index": 3, "seed": 0,
                                   "gradient_accumulation_steps": 2,
                                   "dataset_manifest_sha256": "a" * 64,
                                   "dataset_size": 8, "sampler_state": sampler_state},
                    "dataset_manifest_sha256": "a" * 64}
        settings = TrainingSettings(max_steps=1, gradient_accumulation_steps=2,
                                   max_seconds=60, write_memory=False)
        with patch("ultron_core.training.seed_training_rng") as seed:
            result = run_training_steps(self.model, loader, self.optimizer, report,
                settings=settings, training_authorized=True, resume_metadata=metadata,
                sampler=sampler)
            seed.assert_not_called()
        self.assertTrue(result["resumed_from_checkpoint"])
        self.assertEqual(self.optimizer.steps, 1)
        self.assertEqual(result["steps_completed"], 1)
        self.assertEqual(result["global_step"], 13)
        self.assertEqual(result["data_state"]["epoch"], 2)
        self.assertEqual(result["data_state"]["next_batch_index"], 5)
        self.assertEqual(result["data_state"]["sampler_state"]["next_index"], 5)

    def test_resume_rejects_checkpoint_without_restored_optimizer_state_before_batches(self):
        metadata = {
            "format_version": 5,
            "rng_restored": True,
            "dataset_hash_verified": True,
            "optimizer_state_present": True,
            "optimizer_restored": False,
            "scheduler_state_present": False,
            "scheduler_restored": False,
            "step": 0,
            "dataset_manifest_sha256": "a" * 64,
            "data_state": {
                "epoch": 0,
                "next_batch_index": 0,
                "seed": self.settings.seed,
                "gradient_accumulation_steps": self.settings.gradient_accumulation_steps,
                "dataset_manifest_sha256": "a" * 64,
                "dataset_size": self.report["split_counts"]["train"],
            },
        }
        consumed = []

        def batches():
            consumed.append(True)
            yield self.batches[0]

        with self.assertRaisesRegex(ValueError, "optimizer state was not restored"):
            run_training_steps(
                self.model, batches(), self.optimizer, self.report,
                settings=self.settings, training_authorized=True,
                resume_metadata=metadata,
            )
        self.assertEqual(consumed, [])
        self.assertEqual(self.optimizer.steps, 0)

    def test_resume_rejects_unrestored_scheduler_state_before_batches(self):
        metadata = {
            "format_version": 5,
            "rng_restored": True,
            "dataset_hash_verified": True,
            "optimizer_state_present": True,
            "optimizer_restored": True,
            "scheduler_state_present": True,
            "scheduler_restored": False,
            "step": 0,
            "dataset_manifest_sha256": "a" * 64,
            "data_state": {
                "epoch": 0,
                "next_batch_index": 0,
                "seed": self.settings.seed,
                "gradient_accumulation_steps": self.settings.gradient_accumulation_steps,
                "dataset_manifest_sha256": "a" * 64,
                "dataset_size": self.report["split_counts"]["train"],
            },
        }
        consumed = []

        def batches():
            consumed.append(True)
            yield self.batches[0]

        with self.assertRaisesRegex(ValueError, "scheduler state was not restored"):
            run_training_steps(
                self.model, batches(), self.optimizer, self.report,
                settings=self.settings, training_authorized=True,
                resume_metadata=metadata,
            )
        self.assertEqual(consumed, [])
        self.assertEqual(self.optimizer.steps, 0)

    def test_resume_rejects_precision_mismatch_and_legacy_bf16(self):
        from ultron_core.resumable_sampler import ResumableRandomSampler
        metadata = {
            "format_version": 5, "rng_restored": True,
            "optimizer_state_present": True, "optimizer_restored": True,
            "scheduler_state_present": False, "scheduler_restored": False,
            "dataset_hash_verified": True, "step": 4,
            "dataset_manifest_sha256": "a" * 64,
            "training_settings": {"precision": "bf16", "deterministic": False},
            "data_state": {
                "epoch": 0, "next_batch_index": 0, "seed": 0,
                "gradient_accumulation_steps": 2,
                "dataset_manifest_sha256": "a" * 64, "dataset_size": 4,
            },
        }
        with self.assertRaisesRegex(ValueError, "precision does not match"):
            run_training_steps(self.model, self.batches, self.optimizer, self.report,
                settings=self.settings, training_authorized=True,
                resume_metadata=metadata)
        legacy = dict(metadata)
        legacy.pop("training_settings")
        bf16_settings = TrainingSettings(max_steps=1,
            gradient_accumulation_steps=2, max_seconds=60, precision="bf16")
        with self.assertRaisesRegex(ValueError, "lacks precision metadata"):
            run_training_steps(self.model, self.batches, self.optimizer, self.report,
                settings=bf16_settings, training_authorized=True,
                resume_metadata=legacy)
        self.assertEqual(self.optimizer.steps, 0)

    def test_resume_rejects_changed_seed_or_accumulation(self):
        metadata = {"format_version": 4, "rng_restored": True,
            "optimizer_state_present": True, "optimizer_restored": True,
            "scheduler_state_present": False, "scheduler_restored": False,
                    "dataset_hash_verified": True, "step": 4,
                    "data_state": {"epoch": 0, "next_batch_index": 2, "seed": 0,
                                   "gradient_accumulation_steps": 2,
                                   "dataset_manifest_sha256": "a" * 64,
                                   "dataset_size": 4},
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


    def test_checkpoint_callback_requires_resumable_sampler(self):
        with self.assertRaisesRegex(ValueError, "requires a ResumableRandomSampler"):
            run_training_steps(self.model, self.batches, self.optimizer, self.report,
                settings=self.settings, training_authorized=True,
                checkpoint_callback=lambda step, metrics: None)
        self.assertEqual(self.optimizer.steps, 0)

    def test_sampler_cursor_alignment_supports_batch_size_two(self):
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 4
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64)
        loader = DataLoader(dataset, batch_size=2, sampler=sampler, num_workers=0)
        report = dict(self.report)
        report["batch_size"] = 2
        result = run_training_steps(self.model, loader, self.optimizer, report,
            settings=TrainingSettings(max_steps=1, gradient_accumulation_steps=2,
                                     max_seconds=60, write_memory=False),
            training_authorized=True, sampler=sampler)
        self.assertEqual(result["steps_completed"], 1)
        self.assertEqual(result["data_state"]["next_batch_index"], 2)
        self.assertEqual(result["data_state"]["sampler_state"]["next_index"], 4)

    def test_sampler_cursor_must_match_batch_cursor(self):
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 4
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64, next_index=2)
        loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=0)
        sampler_state = sampler.state_dict()
        metadata = {
            "format_version": 4, "step": 0, "rng_restored": True,
            "optimizer_state_present": True, "optimizer_restored": True,
            "scheduler_state_present": False, "scheduler_restored": False,
            "dataset_hash_verified": True,
            "seed": 0, "gradient_accumulation_steps": 2,
            "dataset_manifest_sha256": "a" * 64,
            "data_state": {"epoch": 0, "next_batch_index": 1, "seed": 0,
                "gradient_accumulation_steps": 2, "dataset_manifest_sha256": "a" * 64,
                "dataset_size": 4, "sampler_state": sampler_state},
        }
        with self.assertRaisesRegex(ValueError, "sample cursor does not match"):
            run_training_steps(self.model, loader, self.optimizer, self.report,
                settings=self.settings, training_authorized=True,
                resume_metadata=metadata, sampler=sampler)
        self.assertEqual(self.optimizer.steps, 0)

    def test_sampler_dataset_size_must_match_preflight(self):
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 8
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64)
        loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=0)
        with self.assertRaisesRegex(ValueError, "dataset size does not match"):
            run_training_steps(self.model, loader, self.optimizer, self.report,
                settings=self.settings, training_authorized=True, sampler=sampler)
        self.assertEqual(self.optimizer.steps, 0)

    def test_resumable_sampler_requires_drop_last_false(self):
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 4
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64)
        loader = DataLoader(dataset, batch_size=1, sampler=sampler,
                            num_workers=0, drop_last=True)
        with self.assertRaisesRegex(ValueError, "drop_last=False"):
            run_training_steps(self.model, loader, self.optimizer, self.report,
                settings=self.settings, training_authorized=True, sampler=sampler)
        self.assertEqual(self.optimizer.steps, 0)

    def test_loader_batch_size_must_match_preflight(self):
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 4
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64)
        loader = DataLoader(dataset, batch_size=2, sampler=sampler, num_workers=0)
        with self.assertRaisesRegex(ValueError, "batch_size must match"):
            run_training_steps(self.model, loader, self.optimizer, self.report,
                settings=self.settings, training_authorized=True, sampler=sampler)
        self.assertEqual(self.optimizer.steps, 0)

    def test_trainer_saves_sampler_state_at_checkpoint_and_return(self):
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 8
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64)
        loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=0)
        saved = []
        report = dict(self.report)
        report["split_counts"] = {"train": 8, "validation": 1, "test": 1}
        result = run_training_steps(self.model, loader, self.optimizer, report,
            settings=TrainingSettings(max_steps=1, gradient_accumulation_steps=2,
                                     max_seconds=60, write_memory=False),
            training_authorized=True, sampler=sampler,
            checkpoint_callback=lambda step, metrics: saved.append((step, metrics)))
        self.assertEqual(saved[0][1]["data_state"]["sampler_state"]["next_index"], 2)
        self.assertEqual(result["data_state"]["sampler_state"]["next_index"], 2)
        self.assertEqual(sampler.next_index, 2)

    def test_trainer_restores_sampler_before_dataloader_iteration(self):
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 8
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64)
        sampler_iterator = iter(sampler)
        [next(sampler_iterator) for _ in range(2)]
        saved_sampler_state = sampler.state_dict()
        loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=0)
        data_state = {
            "epoch": 0, "next_batch_index": 2, "next_sample_index": 2,
            "dataset_size": 8, "dataset_manifest_sha256": "a" * 64,
            "seed": 0, "gradient_accumulation_steps": 2,
            "sampler_state": saved_sampler_state,
        }
        metadata = {
            "format_version": 4, "rng_restored": True,
            "optimizer_state_present": True, "optimizer_restored": True,
            "scheduler_state_present": False, "scheduler_restored": False,
            "dataset_hash_verified": True,
            "step": 6, "seed": 0, "gradient_accumulation_steps": 2,
            "data_state": data_state, "dataset_manifest_sha256": "a" * 64,
        }
        report = dict(self.report)
        report["split_counts"] = {"train": 8, "validation": 1, "test": 1}
        result = run_training_steps(self.model, loader, self.optimizer, report,
            settings=TrainingSettings(max_steps=1, gradient_accumulation_steps=2,
                                     max_seconds=60, write_memory=False),
            training_authorized=True, resume_metadata=metadata, sampler=sampler)
        self.assertEqual(result["global_step"], 7)
        self.assertEqual(result["data_state"]["next_batch_index"], 4)
        self.assertEqual(result["data_state"]["sampler_state"]["next_index"], 4)

    def test_trainer_rewinds_sampler_on_cancellation_after_batch_fetch(self):
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 4
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64)
        loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=0)
        report = dict(self.report)
        report["split_counts"] = {"train": 4, "validation": 1, "test": 1}
        report["gradient_accumulation_steps"] = 1
        checks = iter((False, False, True))
        result = run_training_steps(self.model, loader, self.optimizer, report,
            settings=TrainingSettings(max_steps=3, gradient_accumulation_steps=1,
                                     max_seconds=60, write_memory=False),
            training_authorized=True, sampler=sampler,
            cancellation_check=lambda: next(checks))
        self.assertEqual(result["steps_completed"], 1)
        self.assertEqual(result["stop_reason"], "cancelled")
        self.assertEqual(result["data_state"]["sampler_state"]["next_index"], 1)
        self.assertEqual(sampler.next_index, 1)

    def test_trainer_rewinds_sampler_after_discarded_accumulation(self):
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 3
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64)
        loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=0)
        report = dict(self.report)
        report["split_counts"] = {"train": 3, "validation": 1, "test": 1}
        result = run_training_steps(self.model, loader, self.optimizer, report,
            settings=TrainingSettings(max_steps=2, gradient_accumulation_steps=2,
                                     max_seconds=60, write_memory=False),
            training_authorized=True, sampler=sampler)
        self.assertEqual(result["steps_completed"], 1)
        self.assertEqual(result["discarded_microbatches"], 1)
        self.assertEqual(result["data_state"]["sampler_state"]["next_index"], 2)
        self.assertEqual(sampler.next_index, 2)

    def test_trainer_requires_sampler_state_for_nonzero_initial_cursor(self):
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 8
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64)
        loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=0)
        report = dict(self.report)
        report["split_counts"] = {"train": 8, "validation": 1, "test": 1}
        with self.assertRaisesRegex(ValueError, "non-zero initial cursor"):
            run_training_steps(self.model, loader, self.optimizer, report,
                settings=self.settings, training_authorized=True, sampler=sampler,
                initial_data_state={"epoch": 0, "next_batch_index": 5})
        self.assertEqual(self.optimizer.steps, 0)

    def test_trainer_rejects_prefetch_workers_for_resumable_sampler(self):
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 4
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64)
        loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=1)
        with self.assertRaisesRegex(ValueError, "num_workers=0"):
            run_training_steps(self.model, loader, self.optimizer, self.report,
                settings=self.settings, training_authorized=True, sampler=sampler)
        self.assertEqual(self.optimizer.steps, 0)

    def test_resume_requires_next_batch_cursor(self):
        metadata = {"format_version": 4, "step": 8, "rng_restored": True,
            "optimizer_state_present": True, "optimizer_restored": True,
            "scheduler_state_present": False, "scheduler_restored": False,
                    "dataset_hash_verified": True,
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
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.checkpoint import save_checkpoint, load_checkpoint
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 4
            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64)
        loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mock-resume.pt"
            def save_callback(step, metrics):
                save_checkpoint(path, self.model, self.model.config, step=step,
                    data_state=metrics["data_state"],
                    dataset_manifest_sha256=metrics["dataset_manifest_sha256"])
            settings = TrainingSettings(max_steps=1, gradient_accumulation_steps=2,
                                       max_seconds=60)
            run_training_steps(self.model, loader, self.optimizer, self.report,
                settings=settings, training_authorized=True, checkpoint_callback=save_callback,
                sampler=sampler)
            restored = MockModel()
            metadata = load_checkpoint(path, restored,
                expected_dataset_manifest_sha256="a" * 64)
            self.assertEqual(metadata["step"], 1)
            self.assertEqual(metadata["data_state"]["next_batch_index"], 2)
            self.assertEqual(metadata["data_state"]["sampler_state"]["next_index"], 2)
            self.assertEqual(metadata["dataset_manifest_sha256"], "a" * 64)

    def test_resume_rejects_unrestored_rng_or_wrong_dataset_hash(self):
        base = {"format_version": 4, "rng_restored": True,
            "optimizer_state_present": True, "optimizer_restored": True,
            "scheduler_state_present": False, "scheduler_restored": False,
                "dataset_hash_verified": True,
                "data_state": {"epoch": 0, "next_batch_index": 1},
                "dataset_manifest_sha256": "b" * 64}
        with self.assertRaisesRegex(ValueError, "does not match preflight"):
            run_training_steps(self.model, self.batches, self.optimizer, self.report,
                settings=self.settings, training_authorized=True, resume_metadata=base)
        base["dataset_manifest_sha256"] = "a" * 64
        base["rng_restored"] = False
        with self.assertRaisesRegex(ValueError, "restored RNG"):
            run_training_steps(self.model, self.batches, self.optimizer, self.report,
                settings=self.settings, training_authorized=True, resume_metadata=base)
        self.assertEqual(self.optimizer.steps, 0)


    def test_runtime_memory_guard_rejects_before_consuming_batches(self):
        budget = self.report["memory_budget_bytes"]
        monitor = RuntimeMemoryMonitor(
            budget,
            usage_provider=lambda device: MemoryUsage(budget + 1, 0),
        )
        consumed = []

        def batches():
            consumed.append(True)
            yield self.batches[0]

        with self.assertRaisesRegex(MemoryError, "before_training"):
            run_training_steps(
                self.model, batches(), self.optimizer, self.report,
                settings=self.settings, training_authorized=True,
                memory_monitor=monitor,
            )
        self.assertEqual(consumed, [])
        self.assertEqual(self.optimizer.steps, 0)
        self.assertEqual(monitor.samples, 1)

    def test_runtime_memory_guard_is_reported_on_successful_mock_run(self):
        budget = self.report["memory_budget_bytes"]
        monitor = RuntimeMemoryMonitor(
            budget,
            usage_provider=lambda device: MemoryUsage(1024, 0),
        )
        result = run_training_steps(
            self.model, self.batches[:2], self.optimizer, self.report,
            settings=TrainingSettings(max_steps=1, gradient_accumulation_steps=2,
                                     max_seconds=60),
            training_authorized=True, memory_monitor=monitor,
        )
        self.assertEqual(result["resource_monitoring"],
            "process_rss_plus_cuda_reserved_at_controller_boundaries")
        self.assertEqual(result["resource_memory"]["budget_bytes"], budget)
        self.assertEqual(result["resource_memory"]["peak_sampled_bytes"], 1024)
        self.assertGreaterEqual(result["resource_memory"]["samples"], 5)
        self.assertEqual(result["resource_memory"]["last_stage"], "after_optimizer_step")


    def test_budget_breach_after_optimizer_step_checkpoints_and_stops_cleanly(self):
        budget = self.report["memory_budget_bytes"]
        calls = []

        def provider(device):
            calls.append(device)
            # The first four checks are before optimizer.step. Simulate AdamW
            # state allocation exceeding the cap immediately after its first step.
            rss = budget + 1 if len(calls) >= 5 else 1024
            return MemoryUsage(rss, 0)

        monitor = RuntimeMemoryMonitor(budget, usage_provider=provider)
        from torch.utils.data import DataLoader, Dataset
        from ultron_core.resumable_sampler import ResumableRandomSampler

        class TinyDataset(Dataset):
            def __len__(self):
                return 4

            def __getitem__(self, index):
                return {"input_ids": torch.tensor([1, 2, 3], dtype=torch.long)}

        dataset = TinyDataset()
        sampler = ResumableRandomSampler(dataset, seed=0,
            dataset_manifest_sha256="a" * 64)
        loader = DataLoader(dataset, batch_size=1, sampler=sampler, num_workers=0)
        saved = []
        result = run_training_steps(
            self.model, loader, self.optimizer, self.report,
            settings=TrainingSettings(max_steps=2, gradient_accumulation_steps=2,
                                     max_seconds=60),
            training_authorized=True, memory_monitor=monitor, sampler=sampler,
            checkpoint_callback=lambda step, metrics: saved.append((step, metrics)),
        )
        self.assertEqual(result["stop_reason"], "memory_budget")
        self.assertEqual(result["steps_completed"], 1)
        self.assertEqual(self.optimizer.steps, 1)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0][0], 1)
        self.assertEqual(saved[0][1]["data_state"]["next_batch_index"], 2)
        self.assertEqual(result["resource_memory"]["last_stage"], "after_checkpoint")
        self.assertGreater(result["resource_memory"]["peak_sampled_bytes"], budget)


    def test_settings_enforce_step_and_time_caps(self):
        with self.assertRaisesRegex(ValueError, "max_steps"):
            TrainingSettings(max_steps=1001)
        with self.assertRaisesRegex(ValueError, "max_seconds"):
            TrainingSettings(max_seconds=3601)


if __name__ == "__main__":
    unittest.main()
