"""Independent checks for affine first-order transport PDE solutions."""
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify
from tools.math_generators.university.affine_transport_pde import TOPIC


class AffineTransportPDETests(unittest.TestCase):
    def test_500_seeded_pde_residual_and_initial_condition(self):
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, TOPIC)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            a, b = (Fraction(n, d) for n, d in data["transport_coefficients"])
            scale = Fraction(*data["solution_scale"])
            x0, y0 = (Fraction(n, d) for n, d in data["initial_point"])
            value = Fraction(*data["initial_value"])
            ux, uy = Fraction(*data["partial_x"]), Fraction(*data["partial_y"])
            offset = Fraction(*data["constant_offset"])
            # Differentiate the affine solution and substitute in a*u_x+b*u_y.
            self.assertEqual(ux, scale * b)
            self.assertEqual(uy, -scale * a)
            self.assertEqual(a * ux + b * uy, 0)
            self.assertEqual(scale * (b * x0 - a * y0) + offset, value)
            self.assertEqual(Fraction(*data["pde_residual"]), 0)
            self.assertEqual(item, generate(seed, difficulty, TOPIC))

    def test_nonzero_transport_coefficients_and_tamper_rejection(self):
        item = generate(98, 4, TOPIC)
        altered = dict(item)
        altered["answer"] += "; changed"
        self.assertFalse(verify(altered))
        malformed = dict(item)
        malformed["ingredients"] = dict(item["ingredients"])
        malformed["ingredients"]["transport_coefficients"] = [[0, 1], [1, 1]]
        self.assertFalse(verify(malformed))


if __name__ == "__main__":
    unittest.main()
