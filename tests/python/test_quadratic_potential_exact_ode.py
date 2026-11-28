"""Independent exact tests for quadratic-potential exact first-order ODEs."""
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify


def _fraction(pair):
    return Fraction(pair[0], pair[1])


def _potential(a, b, c, x, y):
    return a * x * x + b * x * y + c * y * y


def _m(a, b, x, y):
    return 2 * a * x + b * y


def _n(b, c, x, y):
    return b * x + 2 * c * y


class QuadraticPotentialExactODETests(unittest.TestCase):
    def test_500_seeded_exactness_gradient_and_initial_value_checks(self):
        topic = "quadratic_potential_exact_first_order_ODEs"
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, topic)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            a, b, c = [_fraction(pair) for pair in data["potential_coefficients"]]
            x0, y0 = [_fraction(pair) for pair in data["initial_point"]]
            m0, n0 = [_fraction(pair) for pair in data["initial_partials"]]
            constant = _fraction(data["potential_constant"])

            self.assertEqual(m0, _m(a, b, x0, y0))
            self.assertEqual(n0, _n(b, c, x0, y0))
            self.assertEqual(_potential(a, b, c, x0, y0), constant)

            # Verify both components of grad(Phi) by independent central differences.
            h = Fraction(1, 7)
            for x, y in ((Fraction(1, 2), Fraction(-2, 3)), (Fraction(-3), Fraction(5, 4))):
                dphi_dx = (
                    _potential(a, b, c, x + h, y)
                    - _potential(a, b, c, x - h, y)
                ) / (2 * h)
                dphi_dy = (
                    _potential(a, b, c, x, y + h)
                    - _potential(a, b, c, x, y - h)
                ) / (2 * h)
                self.assertEqual(dphi_dx, _m(a, b, x, y))
                self.assertEqual(dphi_dy, _n(b, c, x, y))

                # Cross-partials of the one-form agree, so the equation is exact.
                m_y = (_m(a, b, x, y + h) - _m(a, b, x, y - h)) / (2 * h)
                n_x = (_n(b, c, x + h, y) - _n(b, c, x - h, y)) / (2 * h)
                self.assertEqual(m_y, b)
                self.assertEqual(n_x, b)
                self.assertEqual(m_y, n_x)
            self.assertEqual(item, generate(seed, difficulty, topic))

    def test_tampering_and_malformed_coefficients_are_rejected(self):
        topic = "quadratic_potential_exact_first_order_ODEs"
        item = generate(41, 3, topic)
        altered = dict(item)
        altered["answer"] += "; tampered"
        self.assertFalse(verify(altered))
        malformed = dict(item)
        malformed["ingredients"] = dict(item["ingredients"])
        malformed["ingredients"]["potential_coefficients"] = [[True, 1], [0, 1], [1, 1]]
        self.assertFalse(verify(malformed))


if __name__ == "__main__":
    unittest.main()
