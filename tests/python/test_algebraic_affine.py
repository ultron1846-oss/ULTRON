import unittest
from fractions import Fraction

from ultron_core.algebraic import RealAlgebraicNumber
from ultron_core.math_parser import parse_math
from ultron_core.polynomial import Polynomial, PolynomialError


class RealAlgebraicAffineTransformTests(unittest.TestCase):
    def setUp(self):
        polynomial = Polynomial.from_expr(parse_math("x^2 - 2"))
        self.sqrt2 = RealAlgebraicNumber.from_isolating_interval(
            polynomial, 1, 2
        )

    def test_positive_affine_transform_builds_exact_defining_polynomial(self):
        transformed = self.sqrt2.affine_transform(2, 1)
        expected = Polynomial.from_expr(parse_math("(x - 1)^2 - 8"))
        self.assertEqual(transformed.polynomial, expected)
        self.assertEqual((transformed.lower, transformed.upper), (3, 5))
        self.assertEqual(
            expected.real_root_count_univariate(
                transformed.lower, transformed.upper
            ),
            1,
        )

    def test_negative_multiplier_reverses_interval_endpoints(self):
        transformed = self.sqrt2.affine_transform(-2, 1)
        expected = Polynomial.from_expr(parse_math("(x - 1)^2 - 8"))
        self.assertEqual(transformed.polynomial, expected)
        self.assertEqual((transformed.lower, transformed.upper), (-3, -1))
        self.assertEqual(
            expected.real_root_count_univariate(
                transformed.lower, transformed.upper
            ),
            1,
        )

    def test_fractional_affine_transform_is_exact(self):
        transformed = self.sqrt2.affine_transform(
            Fraction(1, 2), Fraction(1, 3)
        )
        expected = Polynomial.from_expr(
            parse_math("(6*x - 2)^2 - 18")
        )
        # Defining polynomials may differ by a nonzero rational scalar.
        self.assertEqual(
            transformed.polynomial.scale(4),
            expected,
        )
        self.assertEqual(
            transformed.polynomial.real_root_count_univariate(
                transformed.lower, transformed.upper
            ),
            1,
        )

    def test_rational_value_transform_stays_exact(self):
        value = RealAlgebraicNumber.from_rational(Fraction(3, 2))
        transformed = value.affine_transform(-2, Fraction(1, 3))
        self.assertTrue(transformed.is_rational)
        self.assertEqual(transformed.rational_value, Fraction(-8, 3))

    def test_transform_rejects_zero_multiplier_and_inexact_inputs(self):
        with self.assertRaises(ValueError):
            self.sqrt2.affine_transform(0)
        with self.assertRaises(TypeError):
            self.sqrt2.affine_transform(True)
        with self.assertRaises(TypeError):
            self.sqrt2.affine_transform(1.5)
        with self.assertRaises(TypeError):
            self.sqrt2.affine_transform(1, False)

    def test_transform_respects_polynomial_resource_limits(self):
        from ultron_core.polynomial import PolynomialLimits

        limited = RealAlgebraicNumber.from_isolating_interval(
            self.sqrt2.polynomial, 1, 2,
            limits=PolynomialLimits(max_total_degree=1),
        )
        with self.assertRaises(PolynomialError):
            limited.affine_transform(2, 1)


if __name__ == "__main__":
    unittest.main()
