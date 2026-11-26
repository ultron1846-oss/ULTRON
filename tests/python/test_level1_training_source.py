import unittest
import torch
from ultron_core.resumable_sampler import ResumableRandomSampler

from ultron_core.level1_training import (Level1TrainingDataset, collate_level1_batch,
                                         build_level1_training_loader)


class Level1TrainingSourceTests(unittest.TestCase):
    def test_source_requires_explicit_authorization_before_generation(self):
        with self.assertRaisesRegex(PermissionError, "explicit training authorization"):
            Level1TrainingDataset(count=3, seed=7)

    def test_authorized_source_generates_verified_tokenized_examples(self):
        dataset = Level1TrainingDataset(count=12, seed=1846, training_authorized=True)
        self.assertEqual(len(dataset), 12)
        first = dataset[0]
        self.assertEqual(set(first), {"input_ids"})
        self.assertEqual(first["input_ids"].dtype, torch.long)
        self.assertGreater(first["input_ids"].numel(), 3)
        batch = collate_level1_batch([dataset[0], dataset[1]])
        self.assertEqual(batch["input_ids"].shape[0], 2)
        self.assertEqual(batch["attention_mask"].shape, batch["input_ids"].shape)
        self.assertTrue(batch["attention_mask"].any(dim=1).all())

    def test_seed_reproduces_sequences(self):
        a = Level1TrainingDataset(count=9, seed=42, training_authorized=True)
        b = Level1TrainingDataset(count=9, seed=42, training_authorized=True)
        for index in range(9):
            self.assertTrue((a[index]["input_ids"] == b[index]["input_ids"]).all())

    def test_invalid_count_and_seed_rejected(self):
        for count in (0, -1, True, 100001):
            with self.subTest(count=count), self.assertRaises(ValueError):
                Level1TrainingDataset(count=count, seed=1, training_authorized=True)
        with self.assertRaises(ValueError):
            Level1TrainingDataset(count=1, seed=-1, training_authorized=True)

    def test_training_loader_is_built_only_with_authorization(self):
        with self.assertRaises(PermissionError):
            build_level1_training_loader(count=4, seed=5, batch_size=2)
        loader = build_level1_training_loader(count=5, seed=5, batch_size=2,
                                              training_authorized=True, shuffle=False)
        batches = list(loader)
        self.assertEqual([batch["input_ids"].shape[0] for batch in batches], [2, 2, 1])
        self.assertTrue(all(batch["attention_mask"].shape == batch["input_ids"].shape
                           for batch in batches))

    def test_default_loader_has_dataset_hash_and_resumable_sampler(self):
        loader = build_level1_training_loader(count=7, seed=1846, batch_size=2,
                                              training_authorized=True)
        self.assertRegex(loader.dataset_manifest_sha256, r"^[0-9a-f]{64}$")
        self.assertIsInstance(loader.sampler, ResumableRandomSampler)
        self.assertEqual(loader.sampler.dataset_manifest_sha256,
                         loader.dataset_manifest_sha256)
        self.assertEqual(loader.num_workers, 0)
        self.assertFalse(loader.drop_last)


if __name__ == "__main__":
    unittest.main()
