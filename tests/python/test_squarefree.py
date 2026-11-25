import unittest
from fractions import Fraction

from ultron_core.algebraic import RealAlgebraicNumber
from ultron_core.math_parser import parse_math
from ultron_core.polynomial import Polynomial, PolynomialError, PolynomialLimits
from ultron_core.squarefree import factor_for_root, square_free_decomposition


class SquareFreeNormalizationTests(unittest.TestCase):
    def poly(self, expression):
        return Polynomial.from_expr(parse_math(expression))

    def test_square_free_polynomial_has_single_multiplicity_one_component(self):
        factors = square_free_decomposition(self.poly("x^3 - 2"))
        self.assertEqual(len(factors), 1)
        self.assertEqual(factors[0].polynomial, self.poly("x^3 - 2"))
        self.assertEqual(factors[0].multiplicity, 1)

    def test_repeated_factors_are_grouped_by_exact_multiplicity(self):
        factors = square_free_decomposition(self.poly("(x - 1)^3 * (x + 2)^2"))
        by_multiplicity = {factor.multiplicity: factor.polynomial for factor in factors}
        self.assertEqual(by_multiplicity[2], self.poly("x + 2"))
        self.assertEqual(by_multiplicity[3], self.poly("x - 1"))

    def test_non_monic_input_returns_monic_components(self):
        factors = square_free_decomposition(self.poly("6*(x - 1)^2*(x + 3)"))
        self.assertEqual(
            {item.multiplicity: item.polynomial for item in factors},
            {1: self.poly("x + 3"), 2: self.poly("x - 1")},
        )

    def test_constant_polynomial_has_empty_decomposition(self):
        self.assertEqual(square_free_decomposition(Polynomial.constant(7)), ())

    def test_zero_polynomial_is_rejected(self):
        with self.assertRaises(PolynomialError):
            square_free_decomposition(Polynomial.zero())

    def test_selects_factor_for_positive_root_with_repeated_conjugate(self):
        defining = self.poly("(x^2 - 2)^2 * (x - 3)^3")
        root = RealAlgebraicNumber.from_isolating_interval(defining, 1, 2)
        selected = factor_for_root(root)
        self.assertEqual(selected.polynomial, self.poly("x^2 - 2"))
        self.assertEqual(selected.multiplicity, 2)

    def test_selects_exact_rational_root(self):
        defining = self.poly("(x - 1/2)^3 * (x + 2)^2")
        root = RealAlgebraicNumber.from_rational(Fraction(1, 2))
        # Rational root selection does not depend on the defining polynomial
        # carried by root; supply the selected defining polynomial explicitly.
        root = RealAlgebraicNumber(
            defining, "x", Fraction(1, 2), Fraction(1, 2), root.limits
        )
        selected = factor_for_root(root)
        self.assertEqual(selected.polynomial, self.poly("x - 1/2"))
        self.assertEqual(selected.multiplicity, 3)

    def test_resource_limit_is_not_bypassed(self):
        defining = self.poly("(x^2 - 2)^2")
        root = RealAlgebraicNumber.from_isolating_interval(
            defining, 1, 2,
            )
        strict = PolynomialLimits(max_total_degree=2, max_terms=16,
                                  max_exponent=2)
        with self.assertRaises(PolynomialError):
            factor_for_root(root, limits=strict)


if __name__ == "__main__":
    unittest.main()
