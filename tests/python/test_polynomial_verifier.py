import json
import unittest

from ultron_core.math_ir import Expr, ExprKind, FormulaCandidate, VerificationStatus
from ultron_core.polynomial import PolynomialLimits
from ultron_core.polynomial_verifier import (
    validate_polynomial_identity_certificate,
    verify_polynomial_identity,
)


def integer(value):
    return Expr(ExprKind.INTEGER, value=value)


def symbol(name):
    return Expr(ExprKind.SYMBOL, value=name)


def add(*terms):
    return Expr(ExprKind.ADD, args=tuple(terms))


def multiply(*factors):
    return Expr(ExprKind.MUL, args=tuple(factors))


def power(base, exponent):
    return Expr(ExprKind.POW, args=(base, integer(exponent)))


def equal(left, right):
    return Expr(ExprKind.EQUAL, args=(left, right))


class PolynomialIdentityVerifierTests(unittest.TestCase):
    def test_exactly_verifies_multivariate_polynomial_identity(self):
        x, y = symbol("x"), symbol("y")
        candidate = equal(
            power(add(x, y), 2),
            add(power(x, 2), multiply(integer(2), x, y), power(y, 2)),
        )
        result = verify_polynomial_identity(candidate)
        self.assertEqual(result.status, VerificationStatus.EXACT_CHECKED)
        self.assertEqual(result.difference_terms, ())
        self.assertIn("zero polynomial over Q", result.note)
        self.assertIsNotNone(result.certificate_sha256)

    def test_rejects_non_identity_with_exact_nonzero_difference(self):
        x, y = symbol("x"), symbol("y")
        candidate = equal(
            power(add(x, y), 2),
            add(power(x, 2), multiply(integer(2), x, y)),
        )
        result = verify_polynomial_identity(candidate)
        self.assertEqual(result.status, VerificationStatus.REJECTED)
        self.assertNotEqual(result.difference_terms, ())
        self.assertIn("non-zero LHS-RHS", result.note)

    def test_supports_exact_rational_constant_division(self):
        x = symbol("x")
        candidate = equal(
            Expr(ExprKind.DIV, args=(add(x, x), integer(2))),
            x,
        )
        result = verify_polynomial_identity(candidate)
        self.assertEqual(result.status, VerificationStatus.EXACT_CHECKED)

    def test_variable_denominator_is_unresolved_not_assumed_safe(self):
        x = symbol("x")
        candidate = equal(
            Expr(ExprKind.DIV, args=(x, x)),
            integer(1),
        )
        result = verify_polynomial_identity(candidate)
        self.assertEqual(result.status, VerificationStatus.UNRESOLVED)
        self.assertIn("division by a variable polynomial", result.note)
        self.assertIsNone(result.certificate_json)

    def test_candidate_domain_and_assumptions_are_unresolved(self):
        x = symbol("x")
        candidate = FormulaCandidate(
            equal(power(x, 2), multiply(x, x)),
            domain=("x != 0",),
        )
        result = verify_polynomial_identity(candidate)
        self.assertEqual(result.status, VerificationStatus.UNRESOLVED)
        self.assertIn("domain/assumptions", result.note)

        assumed_x = Expr(ExprKind.SYMBOL, value="x", assumptions=("x > 0",))
        result = verify_polynomial_identity(equal(power(assumed_x, 2), multiply(assumed_x, assumed_x)))
        self.assertEqual(result.status, VerificationStatus.UNRESOLVED)
        self.assertIn("assumptions", result.note)

    def test_function_calls_and_non_equalities_are_unresolved(self):
        x = symbol("x")
        call = Expr(ExprKind.CALL, value="sin", args=(x,))
        result = verify_polynomial_identity(equal(call, call))
        self.assertEqual(result.status, VerificationStatus.UNRESOLVED)
        result = verify_polynomial_identity(Expr(ExprKind.LESS_THAN, args=(x, integer(1))))
        self.assertEqual(result.status, VerificationStatus.UNRESOLVED)

    def test_resource_limit_failure_is_unresolved(self):
        x = symbol("x")
        candidate = equal(power(x, 3), power(x, 3))
        result = verify_polynomial_identity(
            candidate, limits=PolynomialLimits(max_total_degree=2, max_terms=10, max_exponent=2)
        )
        self.assertEqual(result.status, VerificationStatus.UNRESOLVED)
        self.assertIn("exceeds max_exponent", result.note)

    def test_certificate_is_deterministic_and_revalidated(self):
        x, y = symbol("x"), symbol("y")
        candidate = equal(add(x, y), add(y, x))
        result = verify_polynomial_identity(candidate)
        self.assertTrue(validate_polynomial_identity_certificate(candidate, result.certificate_json))
        self.assertFalse(validate_polynomial_identity_certificate(equal(x, y), result.certificate_json))

        payload = json.loads(result.certificate_json)
        payload["difference"] = [{"monomial": [], "coefficient": [1, 1]}]
        tampered = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        self.assertFalse(validate_polynomial_identity_certificate(candidate, tampered))

    def test_certificate_reuses_its_validated_resource_limits(self):
        x = symbol("x")
        candidate = equal(add(x, integer(1)), add(integer(1), x))
        limits = PolynomialLimits(max_total_degree=16, max_terms=256, max_exponent=16)
        result = verify_polynomial_identity(candidate, limits=limits)
        self.assertEqual(result.status, VerificationStatus.EXACT_CHECKED)
        self.assertTrue(validate_polynomial_identity_certificate(candidate, result.certificate_json))

    def test_verifier_rejects_limits_above_hard_resource_caps(self):
        x = symbol("x")
        candidate = equal(x, x)
        with self.assertRaisesRegex(ValueError, "exceeds hard verifier limit"):
            verify_polynomial_identity(
                candidate, limits=PolynomialLimits(max_total_degree=257, max_terms=10, max_exponent=10)
            )

    def test_verified_candidate_still_cannot_enter_trusted_knowledge(self):
        x = symbol("x")
        candidate = FormulaCandidate(equal(add(x, integer(0)), x))
        result = verify_polynomial_identity(candidate)
        self.assertEqual(result.status, VerificationStatus.EXACT_CHECKED)
        self.assertFalse(candidate.can_enter_trusted_knowledge())

    def test_legacy_formal_status_certificate_is_rejected(self):
        x = symbol("x")
        candidate = equal(add(x, integer(1)), add(integer(1), x))
        result = verify_polynomial_identity(candidate)
        self.assertEqual(result.status, VerificationStatus.EXACT_CHECKED)
        legacy = result.certificate_json.replace('"status":"exact_checked"', '"status":"formally_verified"')
        self.assertFalse(validate_polynomial_identity_certificate(candidate, legacy))


if __name__ == "__main__":
    unittest.main()
