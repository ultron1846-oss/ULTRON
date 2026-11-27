"""Tests for verified dataset preflight; fixtures are temporary and synthetic only."""
import tempfile
import unittest
from pathlib import Path

from test_dataset_split_manifest import fixture
from ultron_core.dataset_split_manifest import (
    load_verified_split_rows_by_split,
    prepare_dataset_split_manifest,
)
from ultron_core.runtime_config import RuntimeConfig
from ultron_core.verified_preflight import build_verified_training_preflight


class VerifiedTrainingPreflightTests(unittest.TestCase):
    def setup_data(self, root):
        dataset = root / "data.jsonl"
        split = root / "splits.json"
        fixture(dataset, 90, True)
        contract = prepare_dataset_split_manifest(dataset, split, split_seed=4)
        return dataset, split, contract

    def test_report_and_three_loaders_share_one_verified_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split, contract = self.setup_data(Path(directory))
            result = build_verified_training_preflight(
                dataset,
                split,
                RuntimeConfig(memory_budget_gib=6, batch_size=2, sequence_length=256),
                sampler_seed=0,
            )
            report = result.report
            self.assertEqual(report["status"], "PREFLIGHT_ONLY")
            self.assertTrue(report["validated"])
            self.assertIs(report["training_authorized"], False)
            self.assertEqual(report["optimizer_steps"], 0)
            self.assertIs(report["remote_execution_enabled"], False)
            self.assertEqual(report["dataset_manifest_sha256"], contract.dataset_sha256)
            self.assertEqual(report["split_manifest_sha256"], contract.split_manifest_sha256)
            self.assertEqual(report["split_counts"], contract.split_counts)
            self.assertEqual(report["selected_unique_prompt_examples"], 90)
            self.assertEqual(report["tokenizer_vocabulary_size"], 240)
            self.assertGreater(report["maximum_tokenized_sequence_length"], 2)
            self.assertTrue(report["data_loaders_constructed"])
            self.assertFalse(report["batches_consumed"])
            self.assertFalse(report["model_weights_allocated"])
            self.assertFalse(report["optimizer_created"])
            self.assertFalse(report["checkpoint_restored"])
            self.assertFalse(report["resource_estimate_complete"])
            self.assertEqual(len(result.train_loader.dataset), contract.split_counts["train"])
            self.assertEqual(len(result.validation_loader.dataset), contract.split_counts["validation"])
            self.assertEqual(len(result.test_loader.dataset), contract.split_counts["test"])
            self.assertEqual(result.train_loader.num_workers, 0)
            self.assertEqual(result.validation_loader.num_workers, 0)
            self.assertEqual(result.test_loader.num_workers, 0)
            self.assertFalse(result.train_loader.drop_last)
            self.assertFalse(result.validation_loader.drop_last)
            self.assertFalse(result.test_loader.drop_last)
            self.assertEqual(result.train_loader.sampler.state_dict()["next_index"], 0)
            self.assertEqual(result.train_loader.sampler.state_dict()["seed"], 0)
            self.assertEqual(result.initial_data_state["seed"], 0)
            self.assertEqual(
                result.initial_data_state["sampler_state"],
                result.train_loader.sampler.state_dict(),
            )
            self.assertEqual(result.initial_data_state["gradient_accumulation_steps"], 1)

    def test_sampler_seed_is_independent_of_split_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split, _ = self.setup_data(Path(directory))
            _, rows = load_verified_split_rows_by_split(dataset, split)
            self.assertTrue(all(rows[name] for name in ("train", "validation", "test")))
            result = build_verified_training_preflight(
                dataset, split, RuntimeConfig(sequence_length=256), sampler_seed=17
            )
            self.assertEqual(result.train_loader.sampler.state_dict()["seed"], 17)
            self.assertEqual(result.initial_data_state["seed"], 17)

    def test_overlong_sequence_fails_preflight_without_truncation(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split, _ = self.setup_data(Path(directory))
            runtime = RuntimeConfig(sequence_length=3)
            with self.assertRaisesRegex(ValueError, "Truncation is disabled"):
                build_verified_training_preflight(dataset, split, runtime)

    def test_invalid_sampler_seed_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split, _ = self.setup_data(Path(directory))
            for seed in (True, -1, 2**63):
                with self.subTest(seed=seed):
                    with self.assertRaises(ValueError):
                        build_verified_training_preflight(
                            dataset, split, RuntimeConfig(), sampler_seed=seed
                        )

    def test_runtime_config_type_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, split, _ = self.setup_data(Path(directory))
            with self.assertRaisesRegex(TypeError, "RuntimeConfig"):
                build_verified_training_preflight(dataset, split, {})


if __name__ == "__main__":
    unittest.main()
