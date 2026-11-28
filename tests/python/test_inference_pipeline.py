import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import torch

from ultron_core.checkpoint import save_checkpoint
from ultron_core.config import NeuroSparseConfig
from ultron_core.inference import load_inference_engine
from ultron_core.math_tokenizer import MathTokenizer
from ultron_core.model import NeuroSparseModel


def tiny_config(vocab_size=None):
    tokenizer = MathTokenizer()
    return NeuroSparseConfig(
        vocab_size=len(tokenizer.vocabulary) if vocab_size is None else vocab_size,
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


def clone_state(model):
    return {name: value.detach().clone() for name, value in model.state_dict().items()}


class InferencePipelineTests(unittest.TestCase):
    def test_verified_checkpoint_load_and_deterministic_end_to_end_inference(self):
        torch.manual_seed(8102)
        tokenizer = MathTokenizer()
        config = tiny_config()
        source_model = NeuroSparseModel(config).eval()
        source_state = clone_state(source_model)

        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "initialized-test-checkpoint.pt"
            save_checkpoint(checkpoint, source_model, config, step=0)

            with patch("ultron_core.inference.torch.load", wraps=torch.load) as load_mock:
                engine = load_inference_engine(checkpoint, tokenizer=tokenizer, device="cpu")
            # A current checkpoint sidecar provides config without loading all
            # tensors twice; only load_checkpoint deserializes the weight payload.
            self.assertEqual(load_mock.call_count, 1)
            self.assertTrue(engine.load_metadata["weights_loaded"])
            self.assertEqual(engine.load_metadata["checkpoint_step"], 0)
            self.assertFalse(engine.load_metadata["optimizer_loaded"])
            self.assertFalse(engine.load_metadata["rng_restored"])
            loaded_state = clone_state(engine.model)
            for name, tensor in engine.model.state_dict().items():
                self.assertTrue(torch.equal(tensor, source_state[name]), name)

            before_inference = clone_state(engine.model)
            first = engine.generate("2+2=", max_new_tokens=4)
            second = engine.generate("2+2=", max_new_tokens=4)
            self.assertEqual(first, second)
            self.assertIsInstance(first["text"], str)
            self.assertIsInstance(first["token_ids"], list)
            self.assertIn(first["finish_reason"], {"eos", "max_new_tokens", "max_sequence_length"})
            self.assertTrue(first["model_invoked"])
            self.assertFalse(first["tools_available_to_model"])
            self.assertFalse(first["external_ai_apis_used"])
            self.assertFalse(first["training_performed"])
            self.assertFalse(first["trained_model_capability_verified"])
            for token_id in first["token_ids"]:
                self.assertGreaterEqual(token_id, 0)
                self.assertLess(token_id, len(tokenizer.vocabulary))
            for name, tensor in engine.model.state_dict().items():
                self.assertTrue(torch.equal(tensor, before_inference[name]), name)
            for name, tensor in source_model.state_dict().items():
                self.assertTrue(torch.equal(tensor, source_state[name]), name)

            engine.close()
            engine.close()
            self.assertTrue(engine.closed)
            with self.assertRaisesRegex(RuntimeError, "closed"):
                engine.generate("3+3=")
            self.assertEqual(set(loaded_state), set(source_state))

    def test_input_validation_rejects_malformed_prompts_and_generation_limits(self):
        tokenizer = MathTokenizer()
        config = tiny_config()
        model = NeuroSparseModel(config).eval()
        from ultron_core.inference import ULTRONInferenceEngine

        engine = ULTRONInferenceEngine(model, tokenizer)
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            engine.generate("   ")
        with self.assertRaises(TypeError):
            engine.generate(None)
        with self.assertRaisesRegex(ValueError, "max_new_tokens"):
            engine.generate("1+1=", max_new_tokens=0)
        with self.assertRaisesRegex(ValueError, "max_new_tokens"):
            engine.generate("1+1=", max_new_tokens=True)
        with self.assertRaisesRegex(ValueError, "unsupported mathematical character"):
            engine.generate("1$1=")
        with self.assertRaisesRegex(ValueError, "no room"):
            engine.generate("1" * config.max_sequence_length)
        engine.close()

    def test_missing_and_corrupted_checkpoint_paths_fail_closed(self):
        config = tiny_config()
        model = NeuroSparseModel(config).eval()
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.pt"
            with self.assertRaises(FileNotFoundError):
                load_inference_engine(missing)

            checkpoint = Path(directory) / "corrupt.pt"
            save_checkpoint(checkpoint, model, config, step=0)
            checkpoint.write_bytes(checkpoint.read_bytes()[:32])
            with self.assertRaisesRegex(ValueError, "integrity verification failed"):
                load_inference_engine(checkpoint)

    def test_checkpoint_vocabulary_mismatch_is_rejected_before_inference(self):
        bad_config = tiny_config(vocab_size=len(MathTokenizer().vocabulary) + 1)
        model = NeuroSparseModel(bad_config).eval()
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "wrong-vocabulary.pt"
            save_checkpoint(checkpoint, model, bad_config, step=0)
            with self.assertRaisesRegex(ValueError, "vocabulary size does not match"):
                load_inference_engine(checkpoint, tokenizer=MathTokenizer())


if __name__ == "__main__":
    unittest.main()
