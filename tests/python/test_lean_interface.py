import hashlib
import unittest

from ultron_core.lean_interface import (
    LeanProofChecker, ProofCheckResult, ProofCheckStatus, source_sha256,
)
from ultron_core.math_ir import Expr, ExprKind, FormulaCandidate


class FakeChecker(LeanProofChecker):
    def check(self, source, theorem_name, *, environment_sha256):
        return ProofCheckResult(
            status=ProofCheckStatus.TYPECHECKED,
            theorem_name=theorem_name,
            source_sha256=source_sha256(source),
            checker_version="fake-test-only",
            environment_sha256=environment_sha256,
            diagnostics=("fake checker: no Lean kernel was invoked",),
        )


class LeanInterfaceContractTests(unittest.TestCase):
    def test_interface_is_abstract(self):
        with self.assertRaises(TypeError):
            LeanProofChecker()

    def test_fake_checker_result_is_bound_to_source_and_environment(self):
        source = "theorem add_comm_demo : 1 + 2 = 2 + 1 := by decide"
        environment = hashlib.sha256(b"fake-env").hexdigest()
        result = FakeChecker().check(source, "add_comm_demo", environment_sha256=environment)
        self.assertEqual(result.status, ProofCheckStatus.TYPECHECKED)
        self.assertEqual(result.source_sha256, hashlib.sha256(source.encode()).hexdigest())
        self.assertEqual(result.environment_sha256, environment)
        self.assertIsNone(result.receipt_sha256)
        self.assertIn("fake checker", result.diagnostics[0])

    def test_fake_typecheck_result_does_not_admit_candidate_to_trust(self):
        candidate = FormulaCandidate(Expr(ExprKind.EQUAL, args=(
            Expr(ExprKind.INTEGER, value=1), Expr(ExprKind.INTEGER, value=1),
        )))
        self.assertFalse(candidate.can_enter_trusted_knowledge())


if __name__ == "__main__":
    unittest.main()
