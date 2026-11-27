"""Checkpoint-boundary validation for resumable cursor metadata."""
import copy
import unittest

from ultron_core.checkpoint import _validate_checkpoint_data_state_contract


class CheckpointCursorContractTests(unittest.TestCase):
    def valid_state(self):
        digest = "a" * 64
        return {
            "epoch": 1,
            "next_batch_index": 2,
            "next_sample_index": 4,
            "dataset_manifest_sha256": digest,
            "dataset_size": 5,
            "batch_size": 2,
            "seed": 7,
            "gradient_accumulation_steps": 3,
            "sampler_state": {
                "schema_version": 1,
                "dataset_size": 5,
                "dataset_manifest_sha256": digest,
                "seed": 7,
                "epoch": 1,
                "next_index": 4,
            },
        }

    def test_complete_cursor_is_accepted_as_detached_metadata(self):
        state = self.valid_state()
        validated = _validate_checkpoint_data_state_contract(state, "a" * 64)
        self.assertEqual(validated, state)
        self.assertIsNot(validated, state)
        self.assertIsNot(validated["sampler_state"], state["sampler_state"])

    def test_cursor_dataset_hash_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "hash does not match"):
            _validate_checkpoint_data_state_contract(self.valid_state(), "b" * 64)

    def test_cursor_batch_sample_mismatch_is_rejected(self):
        state = self.valid_state()
        state["next_sample_index"] = 3
        state["sampler_state"]["next_index"] = 3
        with self.assertRaisesRegex(ValueError, "sample cursor does not align"):
            _validate_checkpoint_data_state_contract(state, "a" * 64)

    def test_sampler_cursor_mismatch_is_rejected(self):
        state = self.valid_state()
        state["sampler_state"]["next_index"] = 3
        with self.assertRaisesRegex(ValueError, "sampler sample cursor"):
            _validate_checkpoint_data_state_contract(state, "a" * 64)

    def test_legacy_metadata_without_batch_size_is_preserved(self):
        state = self.valid_state()
        del state["batch_size"]
        result = _validate_checkpoint_data_state_contract(state, "a" * 64)
        self.assertEqual(result, state)
        self.assertIsNot(result, state)


if __name__ == "__main__":
    unittest.main()
