"""Independent Fubini and additivity checks for quadratic double integrals."""
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify
from tools.math_generators.university.quadratic_double_integrals import MONOMIALS, TOPIC


def _read_pairs(values):
    return tuple(Fraction(n, d) for n, d in values)


def _integrate_y_first(coefficients, bounds):
    left, right, bottom, top = bounds
    total = Fraction(0)
    for coefficient, (px, py) in zip(coefficients, MONOMIALS):
        y_factor = (top ** (py + 1) - bottom ** (py + 1)) / (py + 1)
        x_factor = (right ** (px + 1) - left ** (px + 1)) / (px + 1)
        total += coefficient * y_factor * x_factor
    return total


def _integrate_x_first(coefficients, bounds):
    left, right, bottom, top = bounds
    total = Fraction(0)
    for coefficient, (px, py) in zip(coefficients, MONOMIALS):
        x_primitive = (right ** (px + 1) - left ** (px + 1)) / (px + 1)
        y_primitive = (top ** (py + 1) - bottom ** (py + 1)) / (py + 1)
        total += coefficient * x_primitive * y_primitive
    return total


class QuadraticDoubleIntegralTests(unittest.TestCase):
    def test_500_seeded_exact_fubini_recomputation(self):
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, TOPIC)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            coefficients = _read_pairs(data["coefficients"])
            left, right = _read_pairs(data["x_bounds"])
            bottom, top = _read_pairs(data["y_bounds"])
            bounds = (left, right, bottom, top)
            first = _integrate_y_first(coefficients, bounds)
            second = _integrate_x_first(coefficients, bounds)
            self.assertEqual(first, second)
            self.assertEqual(Fraction(item["answer"]), first)
            self.assertEqual(item, generate(seed, difficulty, TOPIC))

    def test_rectangle_additivity_and_tamper_detection(self):
        item = generate(901, 5, TOPIC)
        data = item["ingredients"]
        coefficients = _read_pairs(data["coefficients"])
        left, right = _read_pairs(data["x_bounds"])
        bottom, top = _read_pairs(data["y_bounds"])
        split = (left + right) / 2
        whole = _integrate_x_first(coefficients, (left, right, bottom, top))
        pieces = (
            _integrate_x_first(coefficients, (left, split, bottom, top))
            + _integrate_x_first(coefficients, (split, right, bottom, top))
        )
        self.assertEqual(whole, pieces)
        altered = dict(item)
        altered["answer"] += "; changed"
        self.assertFalse(verify(altered))


if __name__ == "__main__":
    unittest.main()
