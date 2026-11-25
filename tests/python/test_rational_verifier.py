import json
import unittest

from ultron_core.math_ir import Expr, ExprKind, FormulaCandidate, VerificationStatus
from ultron_core.polynomial import PolynomialLimits
from ultron_core.rational import RationalDomainError, RationalFunction
from ultron_core.rational_verifier import (
    validate_rational_identity_certificate,
    verify_rational_identity,
)


def integer(value):
    return Expr(ExprKind.INTEGER, value=value)


def symbol(name):
    return Expr(ExprKind.SYMBOL, value=name)


def add(*terms):
    return Expr(ExprKind.ADD, args=tuple(terms))


def subtract(left, right):
    return Expr(ExprKind.SUB, args=(left, right))


def divide(left, right):
    return Expr(ExprKind.DIV, args=(left, right))


def power(base, exponent):
    exponent_node = integer(exponent) if exponent >= 0 else Expr(
        ExprKind.NEG, args=(integer(-exponent),)
    )
    return Expr(ExprKind.POW, args=(base, exponent_node))


def equal(left, right):
    return Expr(ExprKind.EQUAL, args=(left, right))


class RationalIdentityVerifierTests(unittest.TestCase):
    def test_verifies_x_over_x_equals_one_without_widening_domain(self):
        x = symbol("x")
        candidate = equal(divide(x, x), integer(1))
        result = verify_rational_identity(candidate)
        self.assertEqual(result.status, VerificationStatus.FORMALLY_VERIFIED)
        self.assertEqual(result.difference_terms, ())
        self.assertEqual(len(result.domain_constraints), 1)
        self.assertEqual(result.domain_constraints[0].evaluate({"x": 0}), 0)
        with self.assertRaises(RationalDomainError):
            RationalFunction.from_expr(divide(x, x)).evaluate({"x": 0})
        self.assertIn("where both expressions are defined", result.note)
        self.assertTrue(validate_rational_identity_certificate(candidate, result.certificate_json))

    def test_verifies_negative_power_and_fraction_forms_equivalent(self):
        x = symbol("x")
        candidate = equal(power(x, -1), divide(integer(1), x))
        result = verify_rational_identity(candidate)
        self.assertEqual(result.status, VerificationStatus.FORMALLY_VERIFIED)
        self.assertEqual(len(result.domain_constraints), 1)

    def test_rejects_nonidentical_rational_functions(self):
        x = symbol("x")
        candidate = equal(divide(integer(1), x), integer(1))
        result = verify_rational_identity(candidate)
        self.assertEqual(result.status, VerificationStatus.REJECTED)
        self.assertNotEqual(result.difference_terms, ())

    def test_preserves_denominator_domain_for_repeated_expression(self):
        x = symbol("x")
        denominator = subtract(x, integer(1))
        expression = divide(integer(1), denominator)
        result = verify_rational_identity(equal(expression, expression))
        self.assertEqual(result.status, VerificationStatus.FORMALLY_VERIFIED)
        self.assertEqual(len(result.domain_constraints), 1)
        self.assertEqual(result.domain_constraints[0].evaluate({"x": 1}), 0)
        with self.assertRaises(RationalDomainError):
            RationalFunction.from_expr(expression).evaluate({"x": 1})

    def test_candidate_domains_assumptions_and_functions_are_unresolved(self):
        x = symbol("x")
        candidate = FormulaCandidate(equal(divide(x, x), integer(1)), domain=("x != 0",))
        self.assertEqual(verify_rational_identity(candidate).status, VerificationStatus.UNRESOLVED)
        assumed = Expr(ExprKind.SYMBOL, value="x", assumptions=("x > 0",))
        self.assertEqual(
            verify_rational_identity(equal(divide(assumed, assumed), integer(1))).status,
            VerificationStatus.UNRESOLVED,
        )
        call = Expr(ExprKind.CALL, value="sin", args=(x,))
        self.assertEqual(verify_rational_identity(equal(call, call)).status, VerificationStatus.UNRESOLVED)

    def test_resource_limit_failure_is_unresolved(self):
        x = symbol("x")
        candidate = equal(divide(power(x, 3), x), power(x, 2))
        result = verify_rational_identity(
            candidate, limits=PolynomialLimits(max_total_degree=2, max_terms=32, max_exponent=2)
        )
        self.assertEqual(result.status, VerificationStatus.UNRESOLVED)

    def test_certificate_is_revalidated_and_tampering_is_rejected(self):
        x = symbol("x")
        candidate = equal(divide(x, x), integer(1))
        result = verify_rational_identity(candidate)
        self.assertTrue(validate_rational_identity_certificate(candidate, result.certificate_json))
        self.assertFalse(validate_rational_identity_certificate(equal(x, integer(1)), result.certificate_json))
        payload = json.loads(result.certificate_json)
        payload["cross_difference"] = [{"monomial": [], "coefficient": [1, 1]}]
        tampered = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        self.assertFalse(validate_rational_identity_certificate(candidate, tampered))

    def test_verified_candidate_still_cannot_enter_trusted_knowledge(self):
        x = symbol("x")
        candidate = FormulaCandidate(equal(divide(x, x), integer(1)))
        result = verify_rational_identity(candidate)
        self.assertEqual(result.status, VerificationStatus.FORMALLY_VERIFIED)
        self.assertFalse(candidate.can_enter_trusted_knowledge())


if __name__ == "__main__":
    unittest.main()
