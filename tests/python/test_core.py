import tempfile
import unittest
from pathlib import Path

import torch

from ultron_core import NeuroSparseConfig, NeuroSparseModel
from ultron_core.checkpoint import load_checkpoint, save_checkpoint
from ultron_core.discovery import polynomial_identity_candidates
from ultron_core.math_ir import Expr, ExprKind, FormulaCandidate, VerificationStatus
from ultron_core.memory import FastWeightMemory
from ultron_core.predictive import PredictiveRefiner
from ultron_core.routing import load_balance_loss
from ultron_core.training import causal_language_model_loss
from ultron_core.verification import probe_candidate


class CoreTests(unittest.TestCase):
    def config(self):
        return NeuroSparseConfig(vocab_size=64, hidden_size=32, num_layers=1,
            num_experts=4, top_k=2, max_refinements=2, fast_memory_slots=8)

    def test_config_validation(self):
        with self.assertRaises(ValueError):
            NeuroSparseConfig(top_k=9)

    def test_config_rejects_non_integer_dimensions(self):
        for field in ("vocab_size", "hidden_size", "num_layers", "num_experts", "top_k", "pad_token_id"):
            with self.subTest(field=field), self.assertRaises((TypeError, ValueError)):
                NeuroSparseConfig(**{field: 2.5})

    def test_config_rejects_non_finite_float_settings(self):
        for field in ("halt_threshold", "dropout"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                NeuroSparseConfig(**{field: float("nan")})

    def test_forward_shapes_and_finite_values(self):
        model = NeuroSparseModel(self.config())
        ids = torch.randint(1, 64, (2, 7))
        output = model(ids)
        self.assertEqual(tuple(output['logits'].shape), (2, 7, 64))
        self.assertTrue(torch.isfinite(output['logits']).all())
        self.assertEqual(model.active_parameter_fraction(), 0.5)

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

    def test_loss_rejects_negative_auxiliary_weight(self):
        logits = torch.randn(1, 3, 5)
        ids = torch.randint(0, 5, (1, 3))
        with self.assertRaisesRegex(ValueError, 'non-negative'):
            causal_language_model_loss(logits, ids, balance_weight=-1)


if __name__ == '__main__':
    unittest.main()
