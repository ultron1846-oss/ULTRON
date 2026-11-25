import unittest
from fractions import Fraction

from ultron_core.algebraic import RealAlgebraicNumber
from ultron_core.algebraic_evaluation import evaluate_polynomial
from ultron_core.math_parser import parse_math
from ultron_core.polynomial import Polynomial, PolynomialError, PolynomialLimits


class ExactPolynomialEvaluationTests(unittest.TestCase):
    def setUp(self):
        defining = Polynomial.from_expr(parse_math("x^2 - 2"))
        self.sqrt2 = RealAlgebraicNumber.from_isolating_interval(defining, 1, 2)

    def poly(self, expression):
        return Polynomial.from_expr(parse_math(expression))

    def test_evaluates_polynomial_to_exact_zero(self):
        result = evaluate_polynomial(self.sqrt2, self.poly("x^2 - 2"))
        self.assertTrue(result.is_rational)
        self.assertEqual(result.rational_value, Fraction(0))

    def test_evaluates_nonzero_polynomial_exactly(self):
        result = evaluate_polynomial(self.sqrt2, self.poly("x^2 + 1"))
        expected = RealAlgebraicNumber.from_rational(3)
        self.assertTrue(result.same_value_as(expected))

    def test_horner_result_matches_existing_algebraic_arithmetic(self):
        result = evaluate_polynomial(self.sqrt2, self.poly("x + 1"))
        one = RealAlgebraicNumber.from_rational(1)
        expected = self.sqrt2.add(one)
        self.assertTrue(result.same_value_as(expected))

    def test_exact_rational_input_uses_direct_fraction_evaluation(self):
        value = RealAlgebraicNumber.from_rational(Fraction(1, 2))
        result = evaluate_polynomial(value, self.poly("2*x^3 - x + 1"))
        self.assertTrue(result.is_rational)
        self.assertEqual(result.rational_value, Fraction(3, 4))

    def test_zero_polynomial_returns_zero(self):
        result = evaluate_polynomial(self.sqrt2, Polynomial.zero())
        self.assertEqual(result.rational_value, Fraction(0))

    def test_rejects_variable_mismatch(self):
        with self.assertRaises(PolynomialError):
            evaluate_polynomial(self.sqrt2, self.poly("y^2 - 2"))

    def test_rejects_multivariate_polynomial(self):
        with self.assertRaises(PolynomialError):
            evaluate_polynomial(self.sqrt2, self.poly("x*y + 1"))

    def test_enforces_requested_degree_budget(self):
        strict = PolynomialLimits(max_total_degree=2, max_terms=16, max_exponent=2)
        with self.assertRaises(PolynomialError):
            evaluate_polynomial(self.sqrt2, self.poly("x^3"), limits=strict)

    def test_invalid_refinement_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_polynomial(self.sqrt2, self.poly("x + 1"), max_refinements=-1)


if __name__ == "__main__":
    unittest.main()
