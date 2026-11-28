import tempfile
import unittest
from pathlib import Path

import torch

from ultron_core.checkpoint import save_checkpoint
from ultron_core.compress import (
    factorize_model,
    load_compression_artifact,
    load_compressed_model_artifact,
    run_compression_pipeline,
    save_compression_artifact,
)
from ultron_core.config import NeuroSparseConfig
from ultron_core.inference import load_compressed_inference_engine
from ultron_core.math_tokenizer import MathTokenizer
from ultron_core.model import NeuroSparseModel


def test_model(vocab_size=64):
    torch.manual_seed(7721)
    config = NeuroSparseConfig(
        vocab_size=vocab_size,
        hidden_size=32,
        num_layers=1,
        num_experts=4,
        top_k=2,
        expert_multiplier=2,
        max_refinements=1,
        fast_memory_slots=4,
        num_attention_heads=4,
        max_sequence_length=64,
        dropout=0.0,
    )
    return NeuroSparseModel(config).eval()


def clone_state(model):
    return {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}


class CompressionValidationTests(unittest.TestCase):
    def test_pipeline_reports_size_and_round_trip_preserves_state_and_outputs(self):
        model = test_model()
        original_state = clone_state(model)
        sample_ids = torch.tensor([[1, 2, 3, 4]], dtype=torch.long)
        target_module = "blocks.0.experts.0.net.0"

        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "compressed.pt"
            compressed, report = run_compression_pipeline(
                model,
                [{
                    "name": "factorize",
                    "options": {
                        "max_relative_error": 0.2,
                        "target_modules": [target_module],
                    },
                }],
                parent_checkpoint_id="initialized-test-parent",
                artifact_version="1.0.0",
                artifact_path=artifact_path,
            )
            self.assertTrue(report["success"], report)
            size = report["compression_size"]
            self.assertGreater(size["source_state_tensor_bytes"], 0)
            self.assertGreater(size["compressed_state_tensor_bytes"], 0)
            self.assertGreater(size["tensor_compression_ratio"], 0)
            self.assertGreater(size["artifact_file_bytes"], 0)
            self.assertGreater(size["artifact_file_to_source_tensor_ratio"], 0)
            self.assertEqual(size["artifact_file_bytes"], artifact_path.stat().st_size)
            self.assertEqual(report["artifact"]["artifact_size_bytes"], artifact_path.stat().st_size)

            restored, restore_report = load_compressed_model_artifact(
                artifact_path,
                model,
                parent_checkpoint_id="initialized-test-parent",
            )
            self.assertTrue(restore_report["success"])
            self.assertEqual(restore_report["replayed_steps"], ["factorize"])
            self.assertEqual(set(compressed.state_dict()), set(restored.state_dict()))
            for name, tensor in compressed.state_dict().items():
                self.assertTrue(torch.equal(tensor, restored.state_dict()[name]), name)

            with torch.inference_mode():
                compressed_logits = compressed(sample_ids)["logits"]
                restored_logits = restored(sample_ids)["logits"]
                source_logits = model(sample_ids)["logits"]
            self.assertTrue(torch.equal(compressed_logits, restored_logits))
            absolute_error = float((source_logits - compressed_logits).abs().max().item())
            baseline_norm = float(torch.linalg.vector_norm(source_logits).item())
            relative_l2_error = (
                float((torch.linalg.vector_norm(source_logits - compressed_logits) / baseline_norm).item())
                if baseline_norm
                else 0.0
            )
            self.assertTrue(torch.isfinite(torch.tensor(absolute_error)))
            self.assertTrue(torch.isfinite(torch.tensor(relative_l2_error)))
            self.assertGreaterEqual(absolute_error, 0.0)
            self.assertGreaterEqual(relative_l2_error, 0.0)
            for name, tensor in model.state_dict().items():
                self.assertTrue(torch.equal(tensor, original_state[name]), name)

    def test_truncated_corrupt_and_incompatible_artifacts_fail_closed(self):
        model = test_model()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = root / "valid.pt"
            save_compression_artifact(
                valid,
                model,
                parent_checkpoint_id="parent-1",
                artifact_version="1.0.0",
                compression_steps=[{"name": "fixture-only", "options": {}}],
            )
            self.assertTrue(load_compression_artifact(valid)["model_state"])

            truncated = root / "truncated.pt"
            truncated.write_bytes(valid.read_bytes()[:32])
            with self.assertRaisesRegex(ValueError, "unreadable or truncated"):
                load_compression_artifact(truncated)

            corrupted = root / "corrupted.pt"
            payload = torch.load(valid, map_location="cpu", weights_only=True)
            first_tensor = next(iter(payload["model_state"].values()))
            first_tensor.view(-1)[0] += 1
            torch.save(payload, corrupted)
            with self.assertRaisesRegex(ValueError, "hash verification failed"):
                load_compression_artifact(corrupted)

            incompatible = root / "incompatible.pt"
            payload = torch.load(valid, map_location="cpu", weights_only=True)
            payload["format_version"] = 999
            torch.save(payload, incompatible)
            with self.assertRaisesRegex(ValueError, "unsupported compressed artifact format"):
                load_compression_artifact(incompatible)

    def test_reconstruction_rejects_wrong_parent_identity_and_model_config(self):
        model = test_model()
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "compressed.pt"
            _compressed, report = run_compression_pipeline(
                model,
                [{
                    "name": "factorize",
                    "options": {
                        "max_relative_error": 0.2,
                        "target_modules": ["blocks.0.experts.0.net.0"],
                    },
                }],
                parent_checkpoint_id="expected-parent",
                artifact_path=artifact,
            )
            self.assertTrue(report["success"])
            with self.assertRaisesRegex(ValueError, "parent checkpoint identifier"):
                load_compressed_model_artifact(
                    artifact, model, parent_checkpoint_id="different-parent"
                )
            incompatible_parent = test_model(vocab_size=65)
            with self.assertRaisesRegex(ValueError, "config does not match"):
                load_compressed_model_artifact(
                    artifact, incompatible_parent, parent_checkpoint_id="expected-parent"
                )

    def test_compressed_artifact_loads_through_the_inference_pipeline(self):
        tokenizer = MathTokenizer()
        model = test_model(vocab_size=len(tokenizer.vocabulary))
        parent_state = clone_state(model)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = root / "parent.pt"
            artifact = root / "deployment.pt"
            save_checkpoint(checkpoint, model, model.config, step=0)
            compressed, report = run_compression_pipeline(
                model,
                [{
                    "name": "factorize",
                    "options": {
                        "max_relative_error": 0.2,
                        "target_modules": ["blocks.0.experts.0.net.0"],
                    },
                }],
                parent_checkpoint_id="parent-checkpoint-v1",
                artifact_path=artifact,
            )
            self.assertTrue(report["success"])
            engine = load_compressed_inference_engine(
                artifact,
                checkpoint,
                parent_checkpoint_id="parent-checkpoint-v1",
                tokenizer=tokenizer,
                device="cpu",
            )
            try:
                result = engine.generate("3+4=", max_new_tokens=3)
                self.assertIsInstance(result["text"], str)
                self.assertTrue(result["model_invoked"])
                self.assertTrue(engine.load_metadata["compressed_artifact_loaded"])
                self.assertEqual(
                    engine.load_metadata["compression"]["replayed_steps"], ["factorize"]
                )
                for name, tensor in engine.model.state_dict().items():
                    self.assertTrue(torch.equal(tensor, compressed.state_dict()[name]), name)
                self.assertFalse(result["training_performed"])
            finally:
                engine.close()
            for name, tensor in model.state_dict().items():
                self.assertTrue(torch.equal(tensor, parent_state[name]), name)


if __name__ == "__main__":
    unittest.main()
