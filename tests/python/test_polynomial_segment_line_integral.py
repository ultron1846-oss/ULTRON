"""Independent checks for polynomial vector-field line integrals."""
import math
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify
from tools.math_generators.university.polynomial_line_integrals import MONOMIALS, TOPIC


def _independent_component_integral(coefficients, start, end):
    x0, y0 = start
    dx, dy = end[0] - x0, end[1] - y0
    total = Fraction(0)
    for coefficient, (px, py) in zip(coefficients, MONOMIALS):
        for ix in range(px + 1):
            for iy in range(py + 1):
                total += (
                    coefficient * math.comb(px, ix) * math.comb(py, iy)
                    * x0 ** (px - ix) * dx ** ix
                    * y0 ** (py - iy) * dy ** iy
                    / (ix + iy + 1)
                )
    return total


class PolynomialSegmentLineIntegralTests(unittest.TestCase):
    def test_500_seeded_exact_integrals_and_orientation_reversal(self):
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, TOPIC)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            start = tuple(Fraction(n, d) for n, d in data["start"])
            end = tuple(Fraction(n, d) for n, d in data["end"])
            p = tuple(Fraction(n, d) for n, d in data["p_coefficients"])
            q = tuple(Fraction(n, d) for n, d in data["q_coefficients"])
            dx, dy = end[0] - start[0], end[1] - start[1]
            expected = dx * _independent_component_integral(p, start, end)
            expected += dy * _independent_component_integral(q, start, end)
            self.assertEqual(Fraction(item["answer"]), expected)
            reverse = (end, start)
            reverse_dx, reverse_dy = -dx, -dy
            reversed_value = reverse_dx * _independent_component_integral(p, *reverse)
            reversed_value += reverse_dy * _independent_component_integral(q, *reverse)
            self.assertEqual(reversed_value, -expected)
            max_degree = min(2, difficulty - 1)
            for coeffs in (p, q):
                for coefficient, (px, py) in zip(coeffs, MONOMIALS):
                    if px + py > max_degree:
                        self.assertEqual(coefficient, 0)
            self.assertEqual(item, generate(seed, difficulty, TOPIC))

    def test_tampering_and_degenerate_segments_are_rejected(self):
        item = generate(147, 5, TOPIC)
        altered = dict(item)
        altered["answer"] += "; changed"
        self.assertFalse(verify(altered))
        malformed = dict(item)
        malformed["ingredients"] = dict(item["ingredients"])
        malformed["ingredients"]["end"] = malformed["ingredients"]["start"]
        self.assertFalse(verify(malformed))


if __name__ == "__main__":
    unittest.main()
