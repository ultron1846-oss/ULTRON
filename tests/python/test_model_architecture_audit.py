"""Non-training architecture, numerical, and checkpoint contract audits."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import torch
import torch.nn.functional as F

from ultron_core.checkpoint import load_checkpoint, save_checkpoint, inspect_checkpoint_resume_metadata
from ultron_core.config import NeuroSparseConfig, count_parameters
from ultron_core.math_tokenizer import MathTokenizer
from ultron_core.model import NeuroSparseModel


def small_config():
    return NeuroSparseConfig(
        vocab_size=len(MathTokenizer().vocabulary),
        hidden_size=32,
        num_layers=2,
        num_experts=4,
        top_k=2,
        expert_multiplier=2,
        max_refinements=2,
        fast_memory_slots=8,
        num_attention_heads=4,
        max_sequence_length=16,
        dropout=0.0,
    )


class ModelArchitectureAuditTests(unittest.TestCase):
    def test_forward_shapes_auxiliary_metrics_and_finiteness(self):
        torch.manual_seed(2026)
        model = NeuroSparseModel(small_config()).eval()
        ids = torch.randint(0, model.config.vocab_size, (2, 16))
        with torch.inference_mode():
            output = model(ids)
        self.assertEqual(output["logits"].shape, (2, 16, model.config.vocab_size))
        for name in ("logits", "load_balance_loss", "prediction_error", "refinement_steps"):
            self.assertTrue(torch.isfinite(output[name]).all(), name)

    def test_left_padding_and_attention_mask_remain_numerically_finite(self):
        model = NeuroSparseModel(small_config()).eval()
        ids = torch.tensor([[0, 0, 1, 2, 3], [0, 4, 5, 6, 7]])
        mask = ids.ne(0)
        with torch.inference_mode():
            output = model(ids, attention_mask=mask)
        self.assertTrue(torch.isfinite(output["logits"]).all())
        self.assertTrue(torch.isfinite(output["prediction_error"]))

    def test_invalid_input_and_attention_masks_fail_closed(self):
        model = NeuroSparseModel(small_config())
        with self.assertRaisesRegex(ValueError, "token id outside vocabulary"):
            model(torch.tensor([[0, model.config.vocab_size]], dtype=torch.long))
        with self.assertRaisesRegex(ValueError, "at least one non-padding"):
            model(torch.zeros((1, 4), dtype=torch.long), attention_mask=torch.zeros((1, 4), dtype=torch.bool))
        with self.assertRaisesRegex(TypeError, "torch.bool"):
            model(torch.ones((1, 4), dtype=torch.long), attention_mask=torch.ones((1, 4), dtype=torch.long))

    def test_backward_smoke_has_finite_gradients_without_optimizer_step(self):
        torch.manual_seed(1846)
        model = NeuroSparseModel(small_config()).train()
        ids = torch.randint(1, model.config.vocab_size, (1, 8))
        logits = model(ids)["logits"]
        loss = F.cross_entropy(
            logits[:, :-1, :].reshape(-1, model.config.vocab_size),
            ids[:, 1:].reshape(-1),
        )
        loss.backward()
        self.assertIsNotNone(model.embedding.weight.grad)
        self.assertGreater(float(model.embedding.weight.grad.abs().sum()), 0.0)
        self.assertIsNotNone(model.blocks[0].attention.in_proj_weight.grad)
        for name, parameter in model.named_parameters():
            if parameter.grad is not None:
                self.assertTrue(torch.isfinite(parameter.grad).all(), name)
        for block in model.blocks:
            for projection in (block.memory.key, block.memory.value, block.memory.gate):
                self.assertTrue(all(not p.requires_grad for p in projection.parameters()))
                self.assertTrue(all(p.grad is None for p in projection.parameters()))

    def test_tied_output_embedding_and_forward_do_not_mutate_parameters(self):
        torch.manual_seed(77)
        model = NeuroSparseModel(small_config()).eval()
        self.assertIs(model.lm_head.weight, model.embedding.weight)
        before = {name: value.detach().clone() for name, value in model.state_dict().items()}
        with torch.inference_mode():
            model(torch.tensor([[1, 2, 3, 4]], dtype=torch.long))
        for name, value in model.state_dict().items():
            self.assertTrue(torch.equal(value, before[name]), name)

    def test_checkpoint_serializes_tokenizer_version_and_restores(self):
        config = small_config()
        source = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tokenizer-version.pt"
            save_checkpoint(path, source, config, step=0)
            payload = torch.load(path, map_location="cpu", weights_only=True)
            self.assertEqual(payload["config"]["tokenizer_version"], 1)
            target = NeuroSparseModel(config)
            metadata = load_checkpoint(path, target, restore_rng=False)
            self.assertEqual(metadata["config"]["tokenizer_version"], 1)
            MathTokenizer().assert_compatible_config(target.config)


    def test_legacy_checkpoint_without_tokenizer_version_defaults_to_v1(self):
        config = small_config()
        source = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy-tokenizer-config.pt"
            save_checkpoint(path, source, config, step=0)
            payload = torch.load(path, map_location="cpu", weights_only=True)
            payload["config"].pop("tokenizer_version")
            torch.save(payload, path)

            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            path.with_suffix(path.suffix + ".sha256").write_text(
                digest + "  " + path.name + "\\n", encoding="utf-8"
            )
            metadata_path = Path(str(path) + ".metadata.json")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["config"].pop("tokenizer_version")
            metadata["checkpoint_sha256"] = digest
            metadata_path.write_text(
                json.dumps(metadata, sort_keys=True, separators=(",", ":")) + "\\n",
                encoding="utf-8",
            )

            target = NeuroSparseModel(config)
            restored = load_checkpoint(path, target, restore_rng=False)
            self.assertEqual(restored["config"]["tokenizer_version"], 1)

            report = inspect_checkpoint_resume_metadata(
                path,
                expected_dataset_manifest_sha256="a" * 64,
                expected_dataset_size=1,
                expected_batch_size=1,
                expected_seed=0,
                expected_gradient_accumulation_steps=1,
                expected_config=config.to_dict(),
            )
            self.assertFalse(any("model config does not match" in blocker for blocker in report["blockers"]))


    def test_checkpoint_rejects_unsupported_tokenizer_version(self):
        config = small_config()
        source = NeuroSparseModel(config)
        for invalid in (2, True):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "invalid-tokenizer-version.pt"
                save_checkpoint(path, source, config, step=0)
                payload = torch.load(path, map_location="cpu", weights_only=True)
                payload["config"]["tokenizer_version"] = invalid
                torch.save(payload, path)
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                path.with_suffix(path.suffix + ".sha256").write_text(
                    digest + "  " + path.name + "\\n", encoding="utf-8"
                )
                target = NeuroSparseModel(config)
                with self.assertRaisesRegex(ValueError, "tokenizer version is unsupported"):
                    load_checkpoint(path, target, restore_rng=False)

    def test_padding_does_not_change_valid_logits_or_auxiliary_metrics(self):
        torch.manual_seed(20261127)
        model = NeuroSparseModel(small_config()).eval()
        unpadded = torch.tensor([[1, 4, 5, 2]], dtype=torch.long)
        padded = torch.tensor([[1, 4, 5, 2, 0, 0]], dtype=torch.long)
        mask = padded.ne(0)
        with torch.inference_mode():
            expected = model(unpadded)
            actual = model(padded, attention_mask=mask)
        torch.testing.assert_close(actual["logits"][:, :4], expected["logits"], rtol=1e-5, atol=1e-6)
        torch.testing.assert_close(actual["load_balance_loss"], expected["load_balance_loss"], rtol=1e-6, atol=1e-7)
        torch.testing.assert_close(actual["prediction_error"], expected["prediction_error"], rtol=1e-6, atol=1e-7)
        self.assertEqual(int(actual["refinement_steps"]), int(expected["refinement_steps"]))

    def test_meta_instantiated_foundation_parameter_count_matches_formula_without_weight_allocation(self):
        config = NeuroSparseConfig.foundation()
        with torch.device("meta"):
            model = NeuroSparseModel(config)
        total = sum(parameter.numel() for parameter in model.parameters())
        trainable = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
        self.assertTrue(all(parameter.is_meta for parameter in model.parameters()))
        self.assertEqual(total, 63_400_451)
        self.assertEqual(trainable, 61_826_048)
        self.assertGreaterEqual(trainable, 60_000_000)

    def test_initialization_is_finite_and_layer_norm_starts_neutral(self):
        torch.manual_seed(2026)
        model = NeuroSparseModel(small_config())
        for name, parameter in model.named_parameters():
            self.assertTrue(torch.isfinite(parameter).all(), name)
        for module in model.modules():
            if isinstance(module, torch.nn.LayerNorm):
                torch.testing.assert_close(module.weight, torch.ones_like(module.weight))
                torch.testing.assert_close(module.bias, torch.zeros_like(module.bias))
        self.assertTrue(torch.equal(model.embedding.weight[0], torch.zeros_like(model.embedding.weight[0])))

    def test_forward_rejects_non_integer_ids_and_non_boolean_attention_masks(self):
        model = NeuroSparseModel(small_config())
        with self.assertRaisesRegex(TypeError, "integer"):
            model(torch.ones((1, 4), dtype=torch.float32))
        with self.assertRaisesRegex(TypeError, "torch.bool"):
            model(torch.ones((1, 4), dtype=torch.long), attention_mask=torch.ones((1, 4), dtype=torch.int32))

    def test_foundation_parameter_floor_is_not_reduced_by_tokenizer_binding(self):
        config = NeuroSparseConfig.foundation()
        self.assertGreaterEqual(count_parameters(config), 60_000_000)
        self.assertEqual(config.tokenizer_version, 1)


if __name__ == "__main__":
    unittest.main()
