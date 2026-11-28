"""Independent exact tests for bounded affine-polynomial double integrals."""
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify
from tools.math_generators.university.rectangular_double_integrals import TOPIC


def _coefficients(item):
    return [Fraction(n, d) for n, d in item["ingredients"]["affine_coefficients"]]


def _integrate_y_then_x(a, b, c, left, right, bottom, top):
    width = right - left
    height = top - bottom
    # Integrate (a*x + b*y + c) with respect to y first, then x.
    y_antiderivative_delta = b * Fraction(top * top - bottom * bottom, 2)
    return (
        a * Fraction(right * right - left * left, 2) * height
        + (y_antiderivative_delta + c * height) * width
    )


def _integrate_x_then_y(a, b, c, left, right, bottom, top):
    width = right - left
    height = top - bottom
    # Integrate with respect to x first; this is a separate Fubini ordering.
    x_antiderivative_delta = a * Fraction(right * right - left * left, 2)
    return (
        x_antiderivative_delta * height
        + (b * Fraction(top * top - bottom * bottom, 2) + c * height) * width
    )


class RectangularDoubleIntegralTests(unittest.TestCase):
    def test_500_seeded_integrals_and_independent_fubini_recomputation(self):
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, TOPIC)
            self.assertTrue(verify(item), (seed, item))
            a, b, c = _coefficients(item)
            left, right = item["ingredients"]["x_bounds"]
            bottom, top = item["ingredients"]["y_bounds"]
            first = _integrate_y_then_x(a, b, c, left, right, bottom, top)
            second = _integrate_x_then_y(a, b, c, left, right, bottom, top)
            self.assertEqual(first, second)
            self.assertEqual(Fraction(item["answer"]), first)
            self.assertEqual(item, generate(seed, difficulty, TOPIC))
            self.assertTrue(-3 * difficulty <= left <= 3 * difficulty)
            self.assertTrue(1 <= right - left <= 3 * difficulty)
            self.assertTrue(-3 * difficulty <= bottom <= 3 * difficulty)
            self.assertTrue(1 <= top - bottom <= 3 * difficulty)

    def test_rectangle_additivity_and_tamper_rejection(self):
        item = generate(812, 4, TOPIC)
        a, b, c = _coefficients(item)
        left, right = item["ingredients"]["x_bounds"]
        bottom, top = item["ingredients"]["y_bounds"]
        split = Fraction(left + right, 2)
        full = _integrate_x_then_y(a, b, c, left, right, bottom, top)
        pieces = (
            _integrate_x_then_y(a, b, c, Fraction(left), split, bottom, top)
            + _integrate_x_then_y(a, b, c, split, Fraction(right), bottom, top)
        )
        self.assertEqual(full, pieces)
        altered = dict(item)
        altered["answer"] = item["answer"] + "; tampered"
        self.assertFalse(verify(altered))
        malformed = dict(item)
        malformed["ingredients"] = dict(item["ingredients"])
        malformed["ingredients"]["affine_coefficients"] = [[1, 0], [0, 1], [0, 1]]
        self.assertFalse(verify(malformed))


if __name__ == "__main__":
    unittest.main()
