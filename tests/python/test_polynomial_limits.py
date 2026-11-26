import unittest
from fractions import Fraction

from ultron_core.polynomial import Polynomial, PolynomialError, PolynomialLimits


class PolynomialOperandLimitTests(unittest.TestCase):
    def setUp(self):
        self.strict = PolynomialLimits(
            max_total_degree=2,
            max_terms=8,
            max_exponent=2,
        )
        self.over_degree = Polynomial.variable("x").power(3)
        self.zero = Polynomial.zero()

    def test_add_rejects_over_budget_inputs_even_when_terms_cancel(self):
        negative = self.over_degree.scale(-1)
        with self.assertRaisesRegex(PolynomialError, "total degree 3"):
            self.over_degree.add(negative, limits=self.strict)

    def test_scale_rejects_over_budget_input_even_when_scaled_to_zero(self):
        with self.assertRaisesRegex(PolynomialError, "total degree 3"):
            self.over_degree.scale(0, limits=self.strict)

    def test_multiply_rejects_over_budget_input_even_when_other_is_zero(self):
        with self.assertRaisesRegex(PolynomialError, "total degree 3"):
            self.over_degree.multiply(self.zero, limits=self.strict)

    def test_power_zero_still_validates_base_budget(self):
        with self.assertRaisesRegex(PolynomialError, "total degree 3"):
            self.over_degree.power(0, limits=self.strict)

    def test_add_rejects_over_budget_term_count_even_when_terms_cancel(self):
        three_terms = (
            Polynomial.variable("x")
            .add(Polynomial.variable("y"))
            .add(Polynomial.constant(1))
        )
        negative = three_terms.scale(-1)
        limits = PolynomialLimits(
            max_total_degree=4,
            max_terms=2,
            max_exponent=4,
        )
        with self.assertRaisesRegex(PolynomialError, "term count 3"):
            three_terms.add(negative, limits=limits)

    def test_scale_rejects_over_budget_exponent_even_when_scaled_to_zero(self):
        limits = PolynomialLimits(
            max_total_degree=10,
            max_terms=8,
            max_exponent=2,
        )
        with self.assertRaisesRegex(PolynomialError, "monomial exponent"):
            self.over_degree.scale(0, limits=limits)

    def test_within_budget_operations_remain_exact(self):
        x = Polynomial.variable("x")
        square = x.power(2, limits=self.strict)
        result = square.add(Polynomial.constant(-2), limits=self.strict)
        self.assertEqual(result.evaluate({"x": Fraction(3)}), 7)
        self.assertEqual(square.multiply(Polynomial.constant(0), limits=self.strict), self.zero)


if __name__ == "__main__":
    unittest.main()
