import unittest

from ultron_core.sampling import ResumableBatchSampler


class ResumableBatchSamplerTests(unittest.TestCase):
    def test_same_seed_and_epoch_produce_same_batches(self):
        first = list(ResumableBatchSampler(13, 4, seed=27, epoch=2))
        second = list(ResumableBatchSampler(13, 4, seed=27, epoch=2))
        self.assertEqual(first, second)
        flattened = [index for batch in first for index in batch]
        self.assertEqual(sorted(flattened), list(range(13)))

    def test_state_restore_resumes_at_exact_next_batch(self):
        sampler = ResumableBatchSampler(13, 4, seed=27, epoch=2)
        full = list(sampler)
        state = sampler.state_dict(next_batch_index=2)
        resumed = ResumableBatchSampler(13, 4, seed=27)
        resumed.load_state_dict(state)
        self.assertEqual(list(resumed), full[2:])
        self.assertEqual(resumed.next_batch_index, 4)

    def test_state_cursor_override_does_not_mutate_sampler(self):
        sampler = ResumableBatchSampler(10, 3, seed=8)
        state = sampler.state_dict(next_batch_index=2)
        self.assertEqual(state["next_batch_index"], 2)
        self.assertEqual(sampler.next_batch_index, 0)

    def test_epoch_changes_shuffle_and_resets_cursor(self):
        sampler = ResumableBatchSampler(12, 3, seed=4, epoch=0, next_batch_index=2)
        first_epoch = list(sampler)
        sampler.set_epoch(1)
        self.assertEqual(sampler.next_batch_index, 0)
        second_epoch = list(sampler)
        self.assertNotEqual(first_epoch, second_epoch)

    def test_drop_last_and_length(self):
        sampler = ResumableBatchSampler(10, 4, seed=3, shuffle=False, drop_last=True)
        self.assertEqual(len(sampler), 2)
        self.assertEqual(list(sampler), [[0, 1, 2, 3], [4, 5, 6, 7]])
        self.assertEqual(len(sampler), 0)

    def test_state_rejects_dataset_or_batch_mismatch(self):
        state = ResumableBatchSampler(10, 3, seed=4).state_dict()
        wrong_dataset = ResumableBatchSampler(11, 3, seed=4)
        with self.assertRaisesRegex(ValueError, "dataset_size"):
            wrong_dataset.load_state_dict(state)
        wrong_batch = ResumableBatchSampler(10, 4, seed=4)
        with self.assertRaisesRegex(ValueError, "batch_size"):
            wrong_batch.load_state_dict(state)

    def test_invalid_cursor_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside the sampler epoch"):
            ResumableBatchSampler(5, 2, seed=0, next_batch_index=4)


if __name__ == "__main__":
    unittest.main()
