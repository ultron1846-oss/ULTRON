"""Pure validation tests for resumable training data cursor metadata."""
import unittest

from ultron_core.data_state import validate_training_data_state


class TrainingDataStateTests(unittest.TestCase):
    def valid_state(self):
        digest = "a" * 64
        return {
            "epoch": 2,
            "next_batch_index": 3,
            "next_sample_index": 5,
            "dataset_manifest_sha256": digest,
            "dataset_size": 5,
            "batch_size": 2,
            "seed": 17,
            "gradient_accumulation_steps": 4,
            "sampler_state": {
                "schema_version": 1,
                "dataset_size": 5,
                "dataset_manifest_sha256": digest,
                "seed": 17,
                "epoch": 2,
                "next_index": 5,
            },
            "training_settings": {
                "precision": "fp32",
                "seed": 17,
                "gradient_accumulation_steps": 4,
            },
        }

    def validate(self, state):
        return validate_training_data_state(
            state,
            dataset_manifest_sha256="a" * 64,
            dataset_size=5,
            batch_size=2,
            seed=17,
            gradient_accumulation_steps=4,
        )

    def test_valid_cursor_accepts_final_partial_batch(self):
        validated = self.validate(self.valid_state())
        self.assertEqual(validated["next_batch_index"], 3)
        self.assertEqual(validated["next_sample_index"], 5)
        self.assertEqual(validated["sampler_state"]["next_index"], 5)

    def test_legacy_cursor_derives_sample_index_from_validated_sampler_state(self):
        state = self.valid_state()
        del state["next_sample_index"]
        del state["batch_size"]
        validated = self.validate(state)
        self.assertEqual(validated["next_sample_index"], 5)
        self.assertEqual(validated["batch_size"], 2)
        self.assertNotIn("next_sample_index", state)
        self.assertNotIn("batch_size", state)

    def test_valid_cursor_returns_detached_copy(self):
        state = self.valid_state()
        validated = self.validate(state)
        validated["sampler_state"]["next_index"] = 0
        self.assertEqual(state["sampler_state"]["next_index"], 5)

    def test_rejects_batch_and_sample_cursor_mismatch(self):
        state = self.valid_state()
        state["next_batch_index"] = 2
        with self.assertRaisesRegex(ValueError, "sample cursor does not align"):
            self.validate(state)

    def test_rejects_sampler_cursor_mismatch(self):
        state = self.valid_state()
        state["sampler_state"]["next_index"] = 4
        with self.assertRaisesRegex(ValueError, "sampler sample cursor does not match"):
            self.validate(state)

    def test_legacy_cursor_rejects_sampler_position_mismatch(self):
        state = self.valid_state()
        del state["next_sample_index"]
        del state["batch_size"]
        state["sampler_state"]["next_index"] = 4
        with self.assertRaisesRegex(ValueError, "sampler sample cursor does not align"):
            self.validate(state)

    def test_rejects_dataset_hash_or_size_mismatch(self):
        state = self.valid_state()
        state["dataset_manifest_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "dataset manifest hash does not match"):
            self.validate(state)
        state = self.valid_state()
        state["sampler_state"]["dataset_size"] = 6
        with self.assertRaisesRegex(ValueError, "sampler dataset size does not match"):
            self.validate(state)

    def test_rejects_changed_saved_batch_size(self):
        state = self.valid_state()
        state["batch_size"] = 1
        with self.assertRaisesRegex(ValueError, "data_state batch_size does not match"):
            self.validate(state)

    def test_rejects_seed_or_accumulation_mismatch(self):
        state = self.valid_state()
        state["sampler_state"]["seed"] = 18
        with self.assertRaisesRegex(ValueError, "sampler seed does not match"):
            self.validate(state)
        state = self.valid_state()
        state["gradient_accumulation_steps"] = 2
        with self.assertRaisesRegex(ValueError, "accumulation does not match"):
            self.validate(state)

    def test_rejects_epoch_and_schema_mismatch(self):
        state = self.valid_state()
        state["sampler_state"]["epoch"] = 1
        with self.assertRaisesRegex(ValueError, "sampler epoch does not match"):
            self.validate(state)
        state = self.valid_state()
        state["sampler_state"]["schema_version"] = 2
        with self.assertRaisesRegex(ValueError, "unsupported sampler state schema"):
            self.validate(state)

    def test_rejects_missing_or_malformed_metadata(self):
        state = self.valid_state()
        del state["sampler_state"]
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            self.validate(state)
        state = self.valid_state()
        state["next_sample_index"] = True
        with self.assertRaisesRegex(ValueError, "next_sample_index must be an integer"):
            self.validate(state)
        state = self.valid_state()
        state["training_settings"] = {"seed": 18}
        with self.assertRaisesRegex(ValueError, "training_settings seed does not match"):
            self.validate(state)

    def test_rejects_cursor_beyond_epoch_batches(self):
        state = self.valid_state()
        state["next_batch_index"] = 4
        with self.assertRaisesRegex(ValueError, "exceeds the training split"):
            self.validate(state)


if __name__ == "__main__":
    unittest.main()
