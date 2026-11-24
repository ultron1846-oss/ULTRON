import tempfile
import unittest
from pathlib import Path

import torch

from ultron_core import NeuroSparseConfig, NeuroSparseModel
from ultron_core.checkpoint import load_checkpoint, save_checkpoint
from ultron_core.discovery import polynomial_identity_candidates
from ultron_core.math_ir import Expr, ExprKind, FormulaCandidate, VerificationStatus
from ultron_core.memory import FastWeightMemory
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
        loss = causal_language_model_loss(output['logits'], ids, output['load_balance_loss'])
        loss.backward()
        self.assertTrue(any(p.grad is not None for p in model.parameters()))

    def test_router_balance_frequency_normalized(self):
        logits = torch.zeros(4, 4, requires_grad=True)
        indices = torch.tensor([[0, 1], [0, 1], [2, 3], [2, 3]])
        loss = load_balance_loss(logits, indices)
        self.assertTrue(torch.isfinite(loss))
        self.assertAlmostEqual(float(loss.detach()), 1.0, places=5)
        loss.backward()

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


if __name__ == '__main__':
    unittest.main()
