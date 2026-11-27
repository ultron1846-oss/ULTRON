"""Resume cursor equivalence and dataset-hash restore gates (mock-only)."""
import tempfile
import unittest
from pathlib import Path

import torch
from torch.utils.data import Dataset

from ultron_core.checkpoint import load_checkpoint, save_checkpoint
from ultron_core.config import NeuroSparseConfig
from ultron_core.resumable_sampler import ResumableRandomSampler


class _IndexDataset(Dataset):
    def __init__(self, size):
        self.size = size

    def __len__(self):
        return self.size

    def __getitem__(self, index):
        return index


class _TrackingModel(torch.nn.Module):
    def __init__(self, value):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor([float(value)]))
        self.config = NeuroSparseConfig.foundation()
        self.load_state_dict_calls = 0

    def load_state_dict(self, state_dict, *args, **kwargs):
        self.load_state_dict_calls += 1
        return super().load_state_dict(state_dict, *args, **kwargs)


class _StateSpy:
    def __init__(self):
        self.load_state_dict_calls = 0

    def state_dict(self):
        return {"mock": 1}

    def load_state_dict(self, state):
        self.load_state_dict_calls += 1


class ResumeCursorEquivalenceTests(unittest.TestCase):
    DATASET_HASH = "a" * 64

    def test_uninterrupted_and_resumed_sampler_sequences_match(self):
        dataset = _IndexDataset(11)
        uninterrupted = ResumableRandomSampler(
            dataset, seed=29, dataset_manifest_sha256=self.DATASET_HASH
        )
        expected_order = list(iter(uninterrupted))
        self.assertEqual(uninterrupted.state_dict()["next_index"], len(dataset))

        interrupted = ResumableRandomSampler(
            dataset, seed=29, dataset_manifest_sha256=self.DATASET_HASH
        )
        iterator = iter(interrupted)
        consumed_prefix = [next(iterator) for _ in range(6)]
        saved_state = interrupted.state_dict()
        self.assertEqual(saved_state["next_index"], len(consumed_prefix))
        self.assertEqual(saved_state["dataset_manifest_sha256"], self.DATASET_HASH)

        resumed = ResumableRandomSampler(
            dataset, seed=29, dataset_manifest_sha256=self.DATASET_HASH
        )
        resumed.load_state_dict(saved_state)
        resumed_suffix = list(iter(resumed))

        self.assertEqual(consumed_prefix + resumed_suffix, expected_order)
        self.assertEqual(resumed.state_dict()["next_index"], len(dataset))

    def test_sampler_resume_rejects_dataset_or_seed_mismatch(self):
        dataset = _IndexDataset(7)
        source = ResumableRandomSampler(
            dataset, seed=5, dataset_manifest_sha256=self.DATASET_HASH
        )
        state = source.state_dict()
        wrong_dataset = ResumableRandomSampler(
            dataset, seed=5, dataset_manifest_sha256="b" * 64
        )
        with self.assertRaisesRegex(ValueError, "manifest hash"):
            wrong_dataset.load_state_dict(state)
        wrong_seed = ResumableRandomSampler(
            dataset, seed=6, dataset_manifest_sha256=self.DATASET_HASH
        )
        with self.assertRaisesRegex(ValueError, "seed"):
            wrong_seed.load_state_dict(state)

    def test_expected_dataset_hash_rejects_before_any_state_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata-gate.pt"
            source_model = _TrackingModel(1.0)
            save_checkpoint(
                path,
                source_model,
                source_model.config,
                optimizer=_StateSpy(),
                scheduler=_StateSpy(),
                step=3,
                dataset_manifest_sha256=self.DATASET_HASH,
            )

            target_model = _TrackingModel(9.0)
            optimizer = _StateSpy()
            scheduler = _StateSpy()
            with self.assertRaisesRegex(ValueError, "does not match expected dataset"):
                load_checkpoint(
                    path,
                    target_model,
                    optimizer=optimizer,
                    scheduler=scheduler,
                    expected_dataset_manifest_sha256="b" * 64,
                )

            self.assertEqual(target_model.load_state_dict_calls, 0)
            self.assertEqual(float(target_model.weight.detach().item()), 9.0)
            self.assertEqual(optimizer.load_state_dict_calls, 0)
            self.assertEqual(scheduler.load_state_dict_calls, 0)


if __name__ == "__main__":
    unittest.main()
