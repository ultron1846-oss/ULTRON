import unittest
from fractions import Fraction

from ultron_core.algebraic import RealAlgebraicNumber
from ultron_core.math_parser import parse_math
from ultron_core.polynomial import Polynomial, PolynomialError, PolynomialLimits


class ExactAlgebraicArithmeticTests(unittest.TestCase):
    def setUp(self):
        self.sqrt2_poly = Polynomial.from_expr(parse_math("x^2 - 2"))
        self.sqrt3_poly = Polynomial.from_expr(parse_math("x^2 - 3"))
        self.sqrt2 = RealAlgebraicNumber.from_isolating_interval(
            self.sqrt2_poly, 1, 2
        )
        self.sqrt3 = RealAlgebraicNumber.from_isolating_interval(
            self.sqrt3_poly, 1, 2
        )

    def test_sum_uses_resultant_and_selects_positive_root(self):
        result = self.sqrt2.add(self.sqrt3)
        expected = Polynomial.from_expr(parse_math("x^4 - 10*x^2 + 1"))
        self.assertEqual(result.polynomial, expected)
        self.assertEqual((result.lower, result.upper), (Fraction(2), Fraction(4)))
        self.assertEqual(
            result.polynomial.real_root_count_univariate(
                result.lower, result.upper, variable="x"
            ),
            1,
        )

    def test_difference_selects_correct_resultant_root(self):
        result = self.sqrt3.subtract(self.sqrt2)
        expected = Polynomial.from_expr(parse_math("x^4 - 10*x^2 + 1"))
        self.assertEqual(result.polynomial, expected)
        self.assertGreater(result.lower, 0)
        self.assertLess(result.upper, 1)
        self.assertEqual(
            result.polynomial.real_root_count_univariate(
                result.lower, result.upper, variable="x"
            ),
            1,
        )

    def test_product_is_exact(self):
        result = self.sqrt2 * self.sqrt3
        expected = Polynomial.from_expr(parse_math("x^4 - 12*x^2 + 36"))
        self.assertEqual(result.polynomial, expected)
        self.assertEqual((result.lower, result.upper), (Fraction(1), Fraction(4)))

    def test_product_handles_zero_as_an_unselected_conjugate(self):
        polynomial = Polynomial.from_expr(parse_math("x^2 - x"))
        selected_one = RealAlgebraicNumber.from_isolating_interval(
            polynomial, Fraction(1, 2), Fraction(3, 2)
        )
        result = self.sqrt2.multiply(selected_one)
        expected = Polynomial.from_expr(parse_math("x^4 - 2*x^2"))
        self.assertEqual(result.polynomial, expected)
        self.assertGreater(result.lower, 0)

    def test_reciprocal_and_quotient_are_exact(self):
        inverse = self.sqrt3.reciprocal()
        inverse_expected = Polynomial.from_expr(parse_math("1 - 3*x^2"))
        self.assertEqual(inverse.polynomial, inverse_expected)
        quotient = self.sqrt2 / self.sqrt3
        quotient_expected = Polynomial.from_expr(parse_math("9*x^4 - 12*x^2 + 4"))
        self.assertEqual(quotient.polynomial, quotient_expected)
        self.assertGreater(quotient.lower, 0)
        self.assertLess(quotient.upper, 1)

    def test_rational_operands_remain_exact(self):
        one_half = RealAlgebraicNumber.from_rational(Fraction(1, 2))
        result = one_half.add(one_half)
        self.assertTrue(result.is_rational)
        self.assertEqual(result.rational_value, Fraction(1))
        product = one_half.multiply(self.sqrt2)
        self.assertEqual(
            product.polynomial,
            Polynomial.from_expr(parse_math("x^2 - 1/2")),
        )

    def test_subtracting_same_value_returns_exact_zero(self):
        result = self.sqrt2.subtract(self.sqrt2)
        self.assertTrue(result.is_rational)
        self.assertEqual(result.rational_value, 0)

    def test_division_by_zero_is_rejected(self):
        zero = RealAlgebraicNumber.from_rational(0)
        with self.assertRaises(ZeroDivisionError):
            self.sqrt2.divide(zero)

    def test_resultant_matrix_has_a_hard_degree_cap(self):
        left_poly = Polynomial.from_expr(parse_math("x^6 - 2"))
        right_poly = Polynomial.from_expr(parse_math("x^5 - 3"))
        left = RealAlgebraicNumber.from_isolating_interval(left_poly, 1, 2)
        right = RealAlgebraicNumber.from_isolating_interval(right_poly, 1, 2)
        with self.assertRaises(PolynomialError):
            left.add(right)

    def test_refinement_budget_fails_closed(self):
        with self.assertRaises(PolynomialError):
            self.sqrt3.subtract(self.sqrt2, max_refinements=0)

    def test_result_variable_is_preserved_for_chained_operations(self):
        partial = self.sqrt2 + self.sqrt3
        chained = partial + self.sqrt2
        self.assertEqual(chained.variable, self.sqrt2.variable)
        self.assertEqual(
            chained.polynomial.real_root_count_univariate(
                chained.lower, chained.upper, variable=self.sqrt2.variable
            ),
            1,
        )

    def test_stricter_operand_limits_are_not_bypassed(self):
        limited = RealAlgebraicNumber.from_isolating_interval(
            self.sqrt2_poly, 1, 2,
            limits=PolynomialLimits(max_total_degree=2, max_terms=32,
                                    max_exponent=2),
        )
        with self.assertRaises(PolynomialError):
            limited.add(self.sqrt3)


if __name__ == "__main__":
    unittest.main()
