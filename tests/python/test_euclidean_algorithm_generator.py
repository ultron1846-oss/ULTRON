"""Independent checks for the Euclidean algorithm generator."""
import math
import unittest

from tools.math_generators.university import generate, verify


class EuclideanAlgorithmGeneratorTests(unittest.TestCase):
    def test_seed_replay_and_independent_bezout_identity(self):
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, "Euclidean_algorithm")
            data = item["ingredients"]
            a, b = data["a"], data["b"]
            x, y = data["bezout_coefficients"]
            gcd_value = data["gcd"]

            # Independent check: recompute gcd using the standard remainder loop.
            left, right = a, b
            while right:
                left, right = right, left % right
            self.assertEqual(gcd_value, left)
            self.assertEqual(gcd_value, math.gcd(a, b))
            self.assertEqual(a * x + b * y, gcd_value)
            self.assertEqual(item, generate(seed, difficulty, "Euclidean_algorithm"))
            self.assertTrue(verify(item))

            trace = data["quotient_trace"]
            self.assertTrue(trace)
            for dividend, divisor, quotient, remainder in trace:
                self.assertEqual(dividend, quotient * divisor + remainder)
                self.assertGreaterEqual(remainder, 0)
                self.assertLess(remainder, divisor)

    def test_invalid_topic_and_difficulty_rejected(self):
        with self.assertRaises(ValueError):
            generate(0, 1, "not_a_topic")
        with self.assertRaises(ValueError):
            generate(0, 6, "Euclidean_algorithm")


if __name__ == "__main__":
    unittest.main()
