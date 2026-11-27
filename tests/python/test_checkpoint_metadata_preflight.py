"""Metadata-only checkpoint compatibility checks (no weight deserialization)."""
import json
import tempfile
import unittest
from pathlib import Path

import torch

from ultron_core.checkpoint import (
    inspect_checkpoint_resume_metadata,
    save_checkpoint,
)
from ultron_core.config import NeuroSparseConfig


class _StatefulMock:
    def state_dict(self):
        return {"mock_state": True}


class CheckpointMetadataPreflightTests(unittest.TestCase):
    def setUp(self):
        self.config = NeuroSparseConfig.foundation()
        self.digest = "a" * 64
        self.data_state = {
            "epoch": 0,
            "next_batch_index": 2,
            "next_sample_index": 4,
            "dataset_manifest_sha256": self.digest,
            "dataset_size": 5,
            "batch_size": 2,
            "seed": 11,
            "gradient_accumulation_steps": 3,
            "sampler_state": {
                "schema_version": 1,
                "dataset_size": 5,
                "dataset_manifest_sha256": self.digest,
                "seed": 11,
                "epoch": 0,
                "next_index": 4,
            },
            "training_settings": {
                "precision": "fp32",
                "seed": 11,
                "gradient_accumulation_steps": 3,
            },
        }
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "checkpoint.pt"
        model = torch.nn.Module()
        model.config = self.config
        save_checkpoint(
            self.path,
            model,
            self.config,
            optimizer=_StatefulMock(),
            step=4,
            data_state=self.data_state,
            dataset_manifest_sha256=self.digest,
            training_settings=self.data_state["training_settings"],
        )

    def tearDown(self):
        self.directory.cleanup()

    def inspect(self, **overrides):
        args = {
            "expected_dataset_manifest_sha256": self.digest,
            "expected_dataset_size": 5,
            "expected_batch_size": 2,
            "expected_seed": 11,
            "expected_gradient_accumulation_steps": 3,
            "expected_config": self.config.to_dict(),
        }
        args.update(overrides)
        return inspect_checkpoint_resume_metadata(self.path, **args)

    def test_compatible_report_is_metadata_only(self):
        report = self.inspect()
        self.assertTrue(report["compatible"], report["blockers"])
        self.assertEqual(report["step"], 4)
        self.assertTrue(report["metadata_only"])
        self.assertFalse(report["checkpoint_deserialized"])
        self.assertFalse(report["weights_loaded"])

    def test_dataset_mismatch_is_reported_as_blocker(self):
        report = self.inspect(expected_dataset_manifest_sha256="b" * 64)
        self.assertFalse(report["compatible"])
        self.assertTrue(any("dataset hash" in item for item in report["blockers"]))

    def test_cursor_setting_mismatch_is_reported(self):
        report = self.inspect(expected_batch_size=1)
        self.assertFalse(report["compatible"])
        self.assertTrue(any("data cursor" in item for item in report["blockers"]))

    def test_checkpoint_byte_tamper_is_detected_without_deserialization(self):
        with self.path.open("ab") as stream:
            stream.write(b"tamper")
        report = self.inspect()
        self.assertFalse(report["compatible"])
        self.assertTrue(any("integrity" in item or "bound" in item for item in report["blockers"]))
        self.assertFalse(report["checkpoint_deserialized"])

    def test_missing_sidecar_returns_explicit_blocker(self):
        Path(str(self.path) + ".metadata.json").unlink()
        report = self.inspect()
        self.assertFalse(report["compatible"])
        self.assertIn("checkpoint metadata sidecar is missing or invalid", report["blockers"])


if __name__ == "__main__":
    unittest.main()
