"""Independent exact validation of rational complex-number operations."""
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify
from tools.math_generators.university.complex_arithmetic import TOPIC


def _read_pair(pair):
    return Fraction(pair[0], pair[1])


class ComplexNumberArithmeticTests(unittest.TestCase):
    def test_500_seeded_exact_operations_and_conjugate_identity(self):
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, TOPIC)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            zr, zi = (_read_pair(pair) for pair in data["z"])
            wr, wi = (_read_pair(pair) for pair in data["w"])
            expected_sum = (zr + wr, zi + wi)
            expected_product = (zr * wr - zi * wi, zr * wi + zi * wr)
            expected_conjugate = (zr, -zi)
            expected_norm = zr * zr + zi * zi
            actual_sum = tuple(_read_pair(pair) for pair in data["sum"])
            actual_product = tuple(_read_pair(pair) for pair in data["product"])
            actual_conjugate = tuple(_read_pair(pair) for pair in data["conjugate_z"])
            self.assertEqual(actual_sum, expected_sum)
            self.assertEqual(actual_product, expected_product)
            self.assertEqual(actual_conjugate, expected_conjugate)
            self.assertEqual(_read_pair(data["norm_squared_z"]), expected_norm)
            # z * conjugate(z) is the non-negative real number |z|².
            conjugate_product = (zr * zr + zi * zi, Fraction(0))
            self.assertEqual(conjugate_product, (expected_norm, Fraction(0)))
            self.assertEqual(item, generate(seed, difficulty, TOPIC))

    def test_tamper_and_invalid_rational_pairs_are_rejected(self):
        item = generate(19, 3, TOPIC)
        altered = dict(item)
        altered["answer"] += "; tampered"
        self.assertFalse(verify(altered))
        malformed = dict(item)
        malformed["ingredients"] = dict(item["ingredients"])
        malformed["ingredients"]["z"] = [[True, 1], [0, 1]]
        self.assertFalse(verify(malformed))


if __name__ == "__main__":
    unittest.main()
