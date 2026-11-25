import hashlib
import random
import tempfile
import unittest
from pathlib import Path

import torch
from torch.nn import functional as F

from ultron_core import NeuroSparseConfig, NeuroSparseModel, count_parameters, count_total_parameters
from ultron_core.model import SparseExpert, _dispatch_sparse_experts
from ultron_core.checkpoint import load_checkpoint, save_checkpoint
from ultron_core.discovery import polynomial_identity_candidates
from ultron_core.math_ir import Expr, ExprKind, FormulaCandidate, VerificationStatus
from ultron_core.memory import FastWeightMemory
from ultron_core.predictive import PredictiveRefiner
from ultron_core.routing import load_balance_loss
from ultron_core.training import causal_language_model_loss
from ultron_core.verification import evaluate, probe_candidate


class CoreTests(unittest.TestCase):
    def test_chunked_causal_loss_matches_full_reference_and_gradients(self):
        torch.manual_seed(91)
        ids = torch.tensor([[1, 2, 0, 4, 5], [3, 4, 5, 0, 0]], dtype=torch.long)
        base = torch.randn(2, 5, 17, dtype=torch.float32, requires_grad=True)
        reference = F.cross_entropy(
            base[:, :-1, :].reshape(-1, 17), ids[:, 1:].reshape(-1), ignore_index=0
        )
        reference.backward()
        expected_grad = base.grad.detach().clone()
        chunked_logits = base.detach().clone().requires_grad_(True)
        chunked = causal_language_model_loss(chunked_logits, ids, loss_chunk_size=2)
        chunked.backward()
        torch.testing.assert_close(chunked, reference.detach(), rtol=1e-6, atol=1e-7)
        torch.testing.assert_close(chunked_logits.grad, expected_grad, rtol=1e-6, atol=1e-7)

    def test_chunked_causal_loss_without_padding_and_optimizer_factory(self):
        from torch import nn
        from ultron_core.training import make_optimizer
        ids = torch.tensor([[1, 2, 3], [4, 5, 6]], dtype=torch.long)
        logits = torch.randn(2, 3, 11, requires_grad=True)
        reference = F.cross_entropy(logits[:, :-1, :].reshape(-1, 11), ids[:, 1:].reshape(-1))
        actual = causal_language_model_loss(logits, ids, ignore_index=None, loss_chunk_size=1)
        torch.testing.assert_close(actual, reference, rtol=1e-6, atol=1e-7)
        model = nn.Linear(4, 3)
        optimizer = make_optimizer(model, fused=False)
        self.assertIsInstance(optimizer, torch.optim.AdamW)
        with self.assertRaisesRegex(ValueError, "one CUDA device"):
            make_optimizer(model, fused=True)

    def test_chunked_loss_rejects_invalid_chunk_size(self):
        logits = torch.randn(1, 3, 5)
        ids = torch.tensor([[1, 2, 3]])
        for invalid in (0, -1, True, 1.5):
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, "loss_chunk_size"):
                causal_language_model_loss(logits, ids, loss_chunk_size=invalid)


    def config(self):
        return NeuroSparseConfig(vocab_size=64, hidden_size=32, num_layers=1,
            num_experts=4, top_k=2, max_refinements=2, fast_memory_slots=8)

    def test_config_validation(self):
        with self.assertRaises(ValueError):
            NeuroSparseConfig(top_k=9)

    def test_config_rejects_non_integer_dimensions(self):
        for field in ("vocab_size", "hidden_size", "num_layers", "num_experts", "top_k", "pad_token_id", "num_attention_heads", "max_sequence_length"):
            with self.subTest(field=field), self.assertRaises((TypeError, ValueError)):
                NeuroSparseConfig(**{field: 2.5})

    def test_config_rejects_non_positive_sequence_settings(self):
        for field in ("num_attention_heads", "max_sequence_length"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                NeuroSparseConfig(**{field: 0})

    def test_config_rejects_non_finite_float_settings(self):
        for field in ("halt_threshold", "dropout"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                NeuroSparseConfig(**{field: float("nan")})

    def test_grouped_sparse_dispatch_matches_reference_output_and_gradients(self):
        torch.manual_seed(2026)
        token_count, hidden, expert_count, top_k = 7, 8, 4, 2
        flat = torch.randn(token_count, hidden, requires_grad=True)
        weights = torch.rand(token_count, top_k, requires_grad=True)
        indices = torch.tensor([
            [0, 2], [1, 3], [0, 1], [2, 3], [1, 2], [0, 3], [2, 1],
        ], dtype=torch.long)
        experts = torch.nn.ModuleList([
            SparseExpert(hidden, multiplier=2, dropout=0.0)
            for _ in range(expert_count)
        ])

        reference = torch.zeros_like(flat)
        for expert_id, expert in enumerate(experts):
            token_pos, slot_pos = torch.where(indices == expert_id)
            if token_pos.numel():
                values = expert(flat.index_select(0, token_pos))
                values = values * weights[token_pos, slot_pos].unsqueeze(-1)
                reference.index_add_(0, token_pos, values)
        reference_loss = reference.square().sum()
        reference_loss.backward()
        expected_flat_grad = flat.grad.detach().clone()
        expected_weight_grad = weights.grad.detach().clone()
        expected_expert_grads = [
            parameter.grad.detach().clone() for parameter in experts.parameters()
        ]

        flat.grad = None
        weights.grad = None
        actual = _dispatch_sparse_experts(flat, weights, indices, experts)
        actual_loss = actual.square().sum()
        actual_loss.backward()

        torch.testing.assert_close(actual, reference.detach(), rtol=1e-6, atol=1e-7)
        torch.testing.assert_close(flat.grad, expected_flat_grad, rtol=1e-6, atol=1e-7)
        torch.testing.assert_close(weights.grad, expected_weight_grad, rtol=1e-6, atol=1e-7)
        for parameter, expected in zip(experts.parameters(), expected_expert_grads):
            torch.testing.assert_close(parameter.grad, expected, rtol=1e-6, atol=1e-7)

    def test_forward_shapes_and_finite_values(self):
        model = NeuroSparseModel(self.config())
        ids = torch.randint(1, 64, (2, 7))
        output = model(ids)
        self.assertEqual(tuple(output['logits'].shape), (2, 7, 64))
        self.assertTrue(torch.isfinite(output['logits']).all())
        self.assertEqual(model.active_parameter_fraction(), 0.5)

    def test_activation_checkpointing_preserves_forward_and_gradients(self):
        config = NeuroSparseConfig(vocab_size=64, hidden_size=32, num_layers=2,
            num_experts=4, top_k=2, max_refinements=2, fast_memory_slots=8,
            dropout=0.0)
        model = NeuroSparseModel(config).train()
        ids = torch.tensor([[1, 2, 3, 4], [5, 6, 7, 8]], dtype=torch.long)
        model.reset_memory()
        baseline = model(ids)
        baseline_loss = causal_language_model_loss(
            baseline["logits"], ids, baseline["load_balance_loss"],
            baseline["prediction_error"])
        baseline_loss.backward()
        baseline_logits = baseline["logits"].detach().clone()
        baseline_grads = {
            name: parameter.grad.detach().clone()
            for name, parameter in model.named_parameters()
            if parameter.grad is not None
        }
        model.zero_grad(set_to_none=True)
        model.reset_memory()
        model.set_activation_checkpointing(True)
        checkpointed = model(ids)
        checkpointed_loss = causal_language_model_loss(
            checkpointed["logits"], ids, checkpointed["load_balance_loss"],
            checkpointed["prediction_error"])
        checkpointed_loss.backward()
        torch.testing.assert_close(checkpointed["logits"], baseline_logits,
            rtol=1e-5, atol=1e-6)
        for name, parameter in model.named_parameters():
            if name in baseline_grads:
                torch.testing.assert_close(parameter.grad, baseline_grads[name],
                    rtol=2e-4, atol=2e-6, msg=name)
        self.assertTrue(model.activation_checkpointing)

    def test_activation_checkpointing_setting_requires_boolean(self):
        model = NeuroSparseModel(self.config())
        with self.assertRaisesRegex(TypeError, "must be boolean"):
            model.set_activation_checkpointing(1)
        self.assertFalse(model.activation_checkpointing)

    def test_backward_smoke(self):
        model = NeuroSparseModel(self.config())
        ids = torch.randint(1, 64, (2, 6))
        output = model(ids)
        loss = causal_language_model_loss(output['logits'], ids, output['load_balance_loss'], output['prediction_error'])
        loss.backward()
        self.assertTrue(any(p.grad is not None for p in model.parameters()))

    def test_router_balance_frequency_normalized(self):
        logits = torch.zeros(4, 4, requires_grad=True)
        indices = torch.tensor([[0, 1], [0, 1], [2, 3], [2, 3]])
        loss = load_balance_loss(logits, indices)
        self.assertTrue(torch.isfinite(loss))
        self.assertAlmostEqual(float(loss.detach()), 1.0, places=5)
        loss.backward()

    def test_router_balance_rejects_empty_top_k_and_duplicate_assignments(self):
        logits = torch.zeros(2, 4)
        with self.assertRaisesRegex(ValueError, "dimensions"):
            load_balance_loss(logits, torch.empty(2, 0, dtype=torch.long))
        with self.assertRaisesRegex(ValueError, "distinct"):
            load_balance_loss(logits, torch.tensor([[1, 1], [2, 3]]))

    def test_router_balance_accepts_integer_index_widths(self):
        logits = torch.zeros(2, 4)
        indices = torch.tensor([[0, 1], [2, 3]], dtype=torch.int32)
        self.assertTrue(torch.isfinite(load_balance_loss(logits, indices)))

    def test_router_balance_internal_fast_path_skips_host_validation(self):
        logits = torch.zeros(2, 4)
        # Duplicate assignments are rejected by the public validation path,
        # while the model's router-generated fast path avoids that sync check.
        indices = torch.tensor([[1, 1], [2, 3]])
        self.assertTrue(torch.isfinite(load_balance_loss(logits, indices, validate_indices=False)))

    def test_router_balance_rejects_non_integer_indices(self):
        with self.assertRaisesRegex(TypeError, "integer dtype"):
            load_balance_loss(torch.zeros(2, 4), torch.tensor([[0.0], [1.0]]))

    def test_refiner_and_memory_reject_invalid_constructor_dimensions(self):
        with self.assertRaisesRegex(ValueError, "positive integer"):
            PredictiveRefiner(hidden_size=0, max_refinements=1, halt_threshold=0.1)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            FastWeightMemory(hidden_size=8, slots=0)

    def test_predictive_refiner_rejects_invalid_shapes(self):
        refiner = PredictiveRefiner(hidden_size=8, max_refinements=1, halt_threshold=0.1)
        with self.assertRaisesRegex(ValueError, "shape"):
            refiner(torch.randn(2, 8))
        with self.assertRaisesRegex(ValueError, "non-empty"):
            refiner(torch.empty(1, 0, 8))
        with self.assertRaisesRegex(ValueError, "hidden dimension"):
            refiner(torch.randn(1, 2, 7))

    def test_expression_ir_rejects_truncating_integer_values(self):
        with self.assertRaisesRegex(TypeError, "must be an int"):
            Expr(ExprKind.INTEGER, value=1.5)
        with self.assertRaisesRegex(ValueError, "identifier"):
            Expr(ExprKind.SYMBOL, value="not a symbol")
        with self.assertRaisesRegex(ValueError, "rational"):
            Expr(ExprKind.RATIONAL, value="1/0")

    def test_fast_and_episodic_memory_write_reset(self):
        memory = FastWeightMemory(hidden_size=8, slots=3)
        x = torch.randn(1, 4, 8)
        memory.train()
        before = memory(x)
        memory(x, write=True)
        self.assertEqual(int(memory.cursor), 1)
        self.assertEqual(int(memory.valid.sum()), 3)
        after = memory(x)
        self.assertFalse(torch.equal(before, after))
        memory.reset_memory()
        self.assertEqual(int(memory.valid.sum()), 0)
        self.assertEqual(int(memory.cursor), 0)

    def test_read_only_memory_skips_key_and_value_projections(self):
        memory = FastWeightMemory(hidden_size=8, slots=4)
        memory.train()
        x = torch.randn(2, 3, 8)
        calls = {"key": 0, "value": 0, "query": 0}
        handles = [
            memory.key.register_forward_hook(lambda *_: calls.__setitem__("key", calls["key"] + 1)),
            memory.value.register_forward_hook(lambda *_: calls.__setitem__("value", calls["value"] + 1)),
            memory.query.register_forward_hook(lambda *_: calls.__setitem__("query", calls["query"] + 1)),
        ]
        try:
            output = memory(x, write=False)
        finally:
            for handle in handles:
                handle.remove()
        self.assertEqual(tuple(output.shape), tuple(x.shape))
        self.assertTrue(torch.isfinite(output).all())
        self.assertEqual(calls, {"key": 0, "value": 0, "query": 1})

    def test_read_only_recall_after_write_skips_write_projections(self):
        memory = FastWeightMemory(hidden_size=8, slots=4)
        memory.train()
        x = torch.randn(1, 3, 8)
        memory(x, write=True)
        memory.eval()
        calls = {"key": 0, "value": 0}
        key_handle = memory.key.register_forward_hook(lambda *_: calls.__setitem__("key", calls["key"] + 1))
        value_handle = memory.value.register_forward_hook(lambda *_: calls.__setitem__("value", calls["value"] + 1))
        try:
            output = memory(x, write=True)
        finally:
            key_handle.remove()
            value_handle.remove()
        self.assertTrue(torch.isfinite(output).all())
        self.assertEqual(calls, {"key": 0, "value": 0})

    def test_formal_status_label_alone_cannot_enter_trusted_knowledge(self):
        candidate = FormulaCandidate(
            Expr(ExprKind.EQUAL, args=(Expr(ExprKind.INTEGER, value=1), Expr(ExprKind.INTEGER, value=1))),
            status=VerificationStatus.FORMALLY_VERIFIED,
            evidence=("caller supplied status label",),
        )
        self.assertFalse(candidate.can_enter_trusted_knowledge())

    def test_formula_candidate_rejects_malformed_metadata(self):
        expression = polynomial_identity_candidates()[0].expression
        with self.assertRaisesRegex(TypeError, "expression must be an Expr"):
            FormulaCandidate(expression=object())
        with self.assertRaisesRegex(TypeError, "evidence must be a tuple"):
            FormulaCandidate(expression=expression, evidence=["caller supplied"])
        with self.assertRaisesRegex(TypeError, "status must be a VerificationStatus"):
            FormulaCandidate(expression=expression, status="formally_verified")

    def test_candidates_are_not_trusted_by_default(self):
        candidates = polynomial_identity_candidates()
        self.assertGreaterEqual(len(candidates), 3)
        self.assertFalse(candidates[0].can_enter_trusted_knowledge())
        self.assertEqual(candidates[0].status, VerificationStatus.CANDIDATE)

    def test_counterexample_rejects_false_claim(self):
        x = Expr(ExprKind.SYMBOL, value='x')
        zero = Expr(ExprKind.INTEGER, value=0)
        candidate = FormulaCandidate(Expr(ExprKind.EQUAL, args=(x, zero)))
        result = probe_candidate(candidate, variable_names=('x',))
        self.assertEqual(result.status, VerificationStatus.REJECTED)
        self.assertIsNotNone(result.counterexample)

    def test_finite_probe_rejects_inexact_or_boolean_sample_values(self):
        candidate = polynomial_identity_candidates()[0]
        with self.assertRaisesRegex(TypeError, "exact integers"):
            probe_candidate(candidate, sample_values=(0.5, 1))
        with self.assertRaisesRegex(TypeError, "exact integers"):
            probe_candidate(candidate, sample_values=(False, 1))

    def test_finite_probe_normalizes_exact_rational_samples(self):
        candidate = polynomial_identity_candidates()[0]
        result = probe_candidate(
            candidate, variable_names=("x", "y"), sample_values=("1/2", 1)
        )
        self.assertEqual(result.status, VerificationStatus.EXPERIMENTALLY_SUPPORTED)
        self.assertEqual(result.samples_checked, 4)

    def test_finite_probe_rejects_duplicate_normalized_samples(self):
        candidate = polynomial_identity_candidates()[0]
        with self.assertRaisesRegex(ValueError, "unique after rational normalization"):
            probe_candidate(candidate, sample_values=(1, "1/1"))

    def test_exact_evaluator_validates_exponent_limit(self):
        one = Expr(ExprKind.INTEGER, value=1)
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            evaluate(one, {}, max_abs_exponent=-1)

    def test_finite_probe_bounds_exact_exponent_growth(self):
        x = Expr(ExprKind.SYMBOL, value="x")
        huge = Expr(ExprKind.INTEGER, value=2048)
        power = Expr(ExprKind.POW, args=(x, huge))
        candidate = FormulaCandidate(Expr(ExprKind.EQUAL, args=(power, power)))
        with self.assertRaisesRegex(ValueError, "exceeds max_abs_exponent"):
            probe_candidate(candidate, variable_names=("x",), sample_values=(2,))
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            probe_candidate(candidate, max_abs_exponent=-1)

    def test_finite_probe_enforces_evaluation_budget(self):
        candidate = polynomial_identity_candidates()[0]
        with self.assertRaisesRegex(ValueError, "exceeding max_samples"):
            probe_candidate(
                candidate, variable_names=("x", "y", "z"),
                sample_values=(0, 1), max_samples=7,
            )
        with self.assertRaisesRegex(ValueError, "positive integer"):
            probe_candidate(candidate, max_samples=0)

    def test_finite_probe_rejects_empty_sample_domain(self):
        candidate = polynomial_identity_candidates()[0]
        with self.assertRaisesRegex(ValueError, 'sample_values must not be empty'):
            probe_candidate(candidate, sample_values=())

    def test_finite_probe_rejects_vacuous_undefined_domain(self):
        x = Expr(ExprKind.SYMBOL, value='x')
        minus_one = Expr(ExprKind.INTEGER, value=-1)
        inverse = Expr(ExprKind.POW, args=(x, minus_one))
        candidate = FormulaCandidate(Expr(ExprKind.EQUAL, args=(inverse, inverse)))
        with self.assertRaisesRegex(ValueError, 'no valid sample points'):
            probe_candidate(candidate, variable_names=('x',), sample_values=(0,))

    def test_finite_probe_does_not_ignore_assumptions(self):
        x = Expr(ExprKind.SYMBOL, value='x')
        one = Expr(ExprKind.INTEGER, value=1)
        candidate = FormulaCandidate(
            Expr(ExprKind.EQUAL, args=(x, x)),
            assumptions=('x > 0',),
        )
        with self.assertRaisesRegex(ValueError, 'does not interpret'):
            probe_candidate(candidate, variable_names=('x',))

    def test_finite_probe_rejects_duplicate_variable_names(self):
        candidate = polynomial_identity_candidates()[0]
        with self.assertRaisesRegex(ValueError, 'must be unique'):
            probe_candidate(candidate, variable_names=('x', 'x'))

    def test_predictive_refiner_error_matches_returned_state(self):
        torch.manual_seed(23)
        refiner = PredictiveRefiner(hidden_size=8, max_refinements=1, halt_threshold=0.0)
        state = torch.randn(2, 3, 8)
        refined, reported_error, _ = refiner(state)
        expected_error = torch.nn.functional.mse_loss(
            refiner.predictor(refined), refined, reduction='none'
        ).mean(dim=-1).mean()
        self.assertTrue(torch.allclose(reported_error, expected_error))

    def test_finite_probe_never_claims_formal_proof(self):
        result = probe_candidate(polynomial_identity_candidates()[0])
        self.assertEqual(result.status, VerificationStatus.EXPERIMENTALLY_SUPPORTED)
        self.assertIn('not a proof', result.note)


    def test_checkpoint_restores_rng_and_data_cursor(self):
        config = self.config()
        model = NeuroSparseModel(config)
        random.seed(731)
        torch.manual_seed(731)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "resume.pt"
            save_checkpoint(path, model, config, step=12, data_state={"epoch": 2, "batch": 9}, dataset_manifest_sha256="a" * 64)
            expected_torch = torch.rand(4)
            expected_python = random.random()
            torch.manual_seed(5)
            random.seed(5)
            restored = NeuroSparseModel(config)
            metadata = load_checkpoint(path, restored, expected_dataset_manifest_sha256="a" * 64)
            self.assertEqual(metadata["format_version"], 5)
            self.assertTrue(metadata["rng_restored"])
            self.assertTrue(metadata["dataset_hash_verified"])
            self.assertTrue(metadata["dataset_hash_verified"])
            self.assertEqual(metadata["data_state"], {"epoch": 2, "batch": 9})
            self.assertEqual(metadata["dataset_manifest_sha256"], "a" * 64)
            torch.testing.assert_close(torch.rand(4), expected_torch)
            self.assertEqual(random.random(), expected_python)

    def test_checkpoint_recovers_previous_verified_generation(self):
        config = self.config()
        model = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recover.pt"
            save_checkpoint(path, model, config, step=4, data_state={"cursor": 4}, dataset_manifest_sha256="a" * 64)
            first_state = {name: value.detach().clone() for name, value in model.state_dict().items()}
            with torch.no_grad():
                for parameter in model.parameters():
                    parameter.add_(0.25)
            save_checkpoint(path, model, config, step=5, data_state={"cursor": 5}, dataset_manifest_sha256="b" * 64)
            with path.open("ab") as stream:
                stream.write(b"corrupt-current")
            restored = NeuroSparseModel(config)
            metadata = load_checkpoint(path, restored, restore_rng=False,
                                      expected_dataset_manifest_sha256="a" * 64)
            self.assertFalse(metadata["rng_restored"])
            self.assertEqual(metadata["step"], 4)
            self.assertEqual(metadata["data_state"], {"cursor": 4})
            self.assertEqual(metadata["dataset_manifest_sha256"], "a" * 64)
            self.assertTrue(metadata["source_path"].endswith(".bak"))
            for name, value in restored.state_dict().items():
                self.assertTrue(torch.equal(value, first_state[name]), name)



    def test_checkpoint_cursor_restore_requires_expected_manifest_hash(self):
        config = self.config()
        model = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "verified-cursor.pt"
            save_checkpoint(path, model, config, step=2, data_state={"cursor": 2},
                           dataset_manifest_sha256="a" * 64)
            target = NeuroSparseModel(config)
            with self.assertRaisesRegex(ValueError, "expected dataset manifest hash is required"):
                load_checkpoint(path, target)
            metadata = load_checkpoint(path, target,
                expected_dataset_manifest_sha256="a" * 64)
            self.assertTrue(metadata["dataset_hash_verified"])

    def test_checkpoint_cursor_restore_requires_expected_manifest_hash(self):
        config = self.config()
        model = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "verified-cursor.pt"
            save_checkpoint(path, model, config, step=2, data_state={"cursor": 2},
                           dataset_manifest_sha256="a" * 64)
            target = NeuroSparseModel(config)
            with self.assertRaisesRegex(ValueError, "expected dataset manifest hash is required"):
                load_checkpoint(path, target)
            metadata = load_checkpoint(path, target,
                expected_dataset_manifest_sha256="a" * 64)
            self.assertTrue(metadata["dataset_hash_verified"])

    def test_checkpoint_rejects_dataset_hash_mismatch_before_mutating_model(self):
        config = self.config()
        source = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset-bound.pt"
            save_checkpoint(path, source, config, step=3, data_state={"cursor": 3},
                           dataset_manifest_sha256="a" * 64)
            target = NeuroSparseModel(config)
            target_before = {name: value.detach().clone() for name, value in target.state_dict().items()}
            with self.assertRaisesRegex(ValueError, "does not match expected dataset"):
                load_checkpoint(path, target, expected_dataset_manifest_sha256="b" * 64)
            for name, value in target.state_dict().items():
                self.assertTrue(torch.equal(value, target_before[name]), name)

    def test_expected_dataset_hash_rejects_legacy_checkpoint_without_manifest(self):
        config = self.config()
        model = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.pt"
            save_checkpoint(path, model, config, step=0)
            target = NeuroSparseModel(config)
            with self.assertRaisesRegex(ValueError, "no dataset manifest hash"):
                load_checkpoint(path, target, expected_dataset_manifest_sha256="a" * 64)

    def test_checkpoint_requires_valid_dataset_hash_for_cursor(self):
        config = self.config()
        model = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hash-required.pt"
            with self.assertRaisesRegex(ValueError, "requires a dataset manifest"):
                save_checkpoint(path, model, config, data_state={"cursor": 0})
            with self.assertRaisesRegex(ValueError, "lowercase SHA-256"):
                save_checkpoint(path, model, config, data_state={"cursor": 0},
                               dataset_manifest_sha256="bad")

    def test_checkpoint_rejects_invalid_step_and_config_mismatch(self):
        config = self.config()
        model = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.pt"
            with self.assertRaisesRegex(ValueError, "non-negative integer"):
                save_checkpoint(path, model, config, step=1.5)
            with self.assertRaisesRegex(ValueError, "does not match"):
                save_checkpoint(path, model, NeuroSparseConfig(vocab_size=65, hidden_size=32,
                    num_layers=1, num_experts=4, top_k=2, max_refinements=2, fast_memory_slots=8))

    def test_checkpoint_persists_training_precision_settings(self):
        config = self.config()
        model = NeuroSparseModel(config)
        settings = {
            "precision": "bf16",
            "seed": 1846,
            "gradient_accumulation_steps": 4,
            "deterministic": True,
            "profile_performance": False,
            "activation_checkpointing": True,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "precision.pt"
            save_checkpoint(path, model, config, step=7,
                data_state={"epoch": 0, "next_batch_index": 4,
                    "training_settings": settings},
                dataset_manifest_sha256="a" * 64)
            payload = torch.load(path, map_location="cpu", weights_only=True)
            self.assertEqual(payload["training_settings"], settings)
            target = NeuroSparseModel(config)
            metadata = load_checkpoint(path, target,
                expected_dataset_manifest_sha256="a" * 64)
            self.assertEqual(metadata["training_settings"], settings)
            self.assertEqual(metadata["step"], 7)

    def test_checkpoint_rejects_invalid_training_precision_metadata(self):
        config = self.config()
        model = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid-precision.pt"
            with self.assertRaisesRegex(ValueError, "precision must"):
                save_checkpoint(path, model, config,
                    training_settings={"precision": "fp16"})
            with self.assertRaisesRegex(TypeError, "deterministic"):
                save_checkpoint(path, model, config,
                    training_settings={"precision": "fp32", "deterministic": 1})

    def test_checkpoint_format_version_tracks_causal_architecture(self):
        config = self.config()
        model = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.pt"
            save_checkpoint(path, model, config, step=0)
            payload = torch.load(path, map_location="cpu", weights_only=True)
            self.assertEqual(payload["format_version"], 5)

    def test_checkpoint_rejects_bad_tensor_shapes_before_mutating_model(self):
        config = self.config()
        source = NeuroSparseModel(config)
        target = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.pt"
            save_checkpoint(path, source, config, step=3)
            payload = torch.load(path, map_location="cpu", weights_only=True)
            first_key = next(iter(payload["model"]))
            payload["model"][first_key] = torch.zeros(1)
            torch.save(payload, path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            path.with_suffix(path.suffix + ".sha256").write_text(
                digest + "  " + path.name + "\n", encoding="utf-8"
            )
            before = {
                name: value.detach().clone()
                for name, value in target.state_dict().items()
            }
            with self.assertRaisesRegex(ValueError, "has shape"):
                load_checkpoint(path, target)
            for name, value in target.state_dict().items():
                self.assertTrue(torch.equal(value, before[name]), name)

    def test_checkpoint_rejects_bad_tensor_layout_before_mutating_model(self):
        config = self.config()
        source = NeuroSparseModel(config)
        target = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.pt"
            save_checkpoint(path, source, config, step=3)
            payload = torch.load(path, map_location="cpu", weights_only=True)
            last_key = next(reversed(payload["model"]))
            payload["model"][last_key] = payload["model"][last_key].to_sparse()
            torch.save(payload, path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            path.with_suffix(path.suffix + ".sha256").write_text(
                digest + "  " + path.name + "\\n", encoding="utf-8"
            )
            before = {
                name: value.detach().clone()
                for name, value in target.state_dict().items()
            }
            with self.assertRaisesRegex(ValueError, "has layout"):
                load_checkpoint(path, target)
            for name, value in target.state_dict().items():
                self.assertTrue(torch.equal(value, before[name]), name)

    def test_checkpoint_round_trip_and_tamper_detection(self):
        config = self.config()
        model = NeuroSparseModel(config)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'checkpoint.pt'
            save_checkpoint(path, model, config, step=7)
            restored = NeuroSparseModel(config)
            metadata = load_checkpoint(path, restored)
            self.assertEqual(metadata['step'], 7)
            with path.open('ab') as stream:
                stream.write(b'tamper')
            with self.assertRaises(ValueError):
                load_checkpoint(path, restored)

    def test_probe_requires_every_expression_variable(self):
        x = Expr(ExprKind.SYMBOL, value='x')
        y = Expr(ExprKind.SYMBOL, value='y')
        candidate = FormulaCandidate(Expr(ExprKind.EQUAL, args=(x, y)))
        with self.assertRaisesRegex(ValueError, 'omits symbols'):
            probe_candidate(candidate, variable_names=('x',))

    def test_model_rejects_empty_sequence(self):
        model = NeuroSparseModel(self.config())
        with self.assertRaisesRegex(ValueError, 'non-empty'):
            model(torch.empty((1, 0), dtype=torch.long))

    def test_loss_ignores_padding_targets(self):
        logits = torch.zeros(1, 3, 4)
        ids = torch.tensor([[1, 2, 0]])
        loss = causal_language_model_loss(logits, ids, ignore_index=0)
        self.assertAlmostEqual(float(loss), torch.log(torch.tensor(4.0)).item(), places=6)

    def test_loss_accepts_int32_token_ids(self):
        logits = torch.zeros(1, 3, 4)
        ids = torch.tensor([[1, 2, 3]], dtype=torch.int32)
        self.assertTrue(torch.isfinite(causal_language_model_loss(logits, ids)))

    def test_loss_rejects_all_padding_targets(self):
        logits = torch.randn(1, 3, 5)
        ids = torch.zeros((1, 3), dtype=torch.long)
        with self.assertRaisesRegex(ValueError, 'all next-token targets are padding'):
            causal_language_model_loss(logits, ids)

    def test_loss_can_disable_padding_mask(self):
        logits = torch.zeros(1, 3, 4)
        logits[0, 1, 0] = 10.0  # Make the padding target spuriously easy to predict.
        ids = torch.tensor([[1, 2, 0]])
        masked = causal_language_model_loss(logits, ids, ignore_index=0)
        unmasked = causal_language_model_loss(logits, ids, ignore_index=None)
        self.assertGreater(float(masked), float(unmasked))

    def test_loss_rejects_non_finite_auxiliary_weights(self):
        logits = torch.randn(1, 3, 5)
        ids = torch.randint(0, 5, (1, 3))
        with self.assertRaisesRegex(ValueError, "finite non-negative"):
            causal_language_model_loss(logits, ids, balance_weight=float("nan"))

    def test_optimizer_rejects_non_finite_hyperparameters(self):
        from ultron_core.training import make_optimizer
        model = NeuroSparseModel(self.config())
        with self.assertRaisesRegex(ValueError, "learning_rate"):
            make_optimizer(model, learning_rate=float("nan"))
        with self.assertRaisesRegex(ValueError, "weight_decay"):
            make_optimizer(model, weight_decay=float("inf"))

    def test_optimizer_factory_includes_only_trainable_parameters(self):
        from ultron_core.training import make_optimizer
        model = NeuroSparseModel(self.config())
        optimizer = make_optimizer(model)
        optimized = [p for group in optimizer.param_groups for p in group["params"]]
        self.assertTrue(optimized)
        self.assertTrue(all(parameter.requires_grad for parameter in optimized))
        self.assertEqual(sum(parameter.numel() for parameter in optimized),
                         sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad))

    def test_loss_rejects_negative_auxiliary_weight(self):
        logits = torch.randn(1, 3, 5)
        ids = torch.randint(0, 5, (1, 3))
        with self.assertRaisesRegex(ValueError, 'non-negative'):
            causal_language_model_loss(logits, ids, balance_weight=-1)


    def test_causal_attention_allows_past_context_to_change_later_logits(self):
        torch.manual_seed(41)
        model = NeuroSparseModel(self.config()).eval()
        first = torch.tensor([[1, 7, 9, 11, 13]])
        changed_context = torch.tensor([[2, 7, 9, 11, 13]])
        with torch.inference_mode():
            first_logits = model(first)["logits"]
            changed_logits = model(changed_context)["logits"]
        self.assertFalse(torch.allclose(first_logits[:, 3, :], changed_logits[:, 3, :]))

    def test_causal_attention_prevents_future_tokens_changing_past_logits(self):
        torch.manual_seed(43)
        model = NeuroSparseModel(self.config()).eval()
        first = torch.tensor([[1, 7, 9, 11, 13]])
        changed_future = torch.tensor([[1, 7, 9, 21, 23]])
        with torch.inference_mode():
            first_logits = model(first)["logits"]
            changed_logits = model(changed_future)["logits"]
        prefix_difference = (first_logits[:, :3, :] - changed_logits[:, :3, :]).abs()
        self.assertTrue(
            torch.isfinite(prefix_difference).all()
            and float(prefix_difference.max()) <= 1e-5,
            f"future-token isolation failed; max prefix-logit difference={float(prefix_difference.max())}",
        )

    def test_model_rejects_sequence_longer_than_position_table(self):
        config = NeuroSparseConfig(
            vocab_size=64, hidden_size=32, num_layers=1, num_experts=4,
            top_k=2, max_refinements=2, fast_memory_slots=8,
            max_sequence_length=4,
        )
        model = NeuroSparseModel(config)
        with self.assertRaisesRegex(ValueError, "max_sequence_length"):
            model(torch.ones((1, 5), dtype=torch.long))

    def test_config_requires_attention_head_divisibility(self):
        with self.assertRaisesRegex(ValueError, "divisible"):
            NeuroSparseConfig(hidden_size=30, num_attention_heads=4)

    def test_parameter_count_formula_matches_instantiated_model(self):
        config = self.config()
        model = NeuroSparseModel(config)
        self.assertEqual(count_total_parameters(config), sum(p.numel() for p in model.parameters()))
        self.assertEqual(count_parameters(config), sum(p.numel() for p in model.parameters() if p.requires_grad))
        for block in model.blocks:
            for projection in (block.memory.key, block.memory.value, block.memory.gate):
                self.assertFalse(any(parameter.requires_grad for parameter in projection.parameters()))

    def test_foundation_config_exceeds_60m_trainable_target_without_instantiating_large_model(self):
        config = NeuroSparseConfig.foundation()
        self.assertEqual(config.vocab_size, 240)
        self.assertEqual(count_total_parameters(config), 63400451)
        self.assertEqual(count_parameters(config), 61826048)
        self.assertGreater(count_parameters(config), 60000000)


if __name__ == '__main__':
    unittest.main()
