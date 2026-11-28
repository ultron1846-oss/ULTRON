"""Independent exact checks for the binomial probability mass function."""
import unittest
from fractions import Fraction
from math import comb

from tools.math_generators.university import generate, verify
from tools.math_generators.university.binomial_probability import TOPIC


class BinomialProbabilityTests(unittest.TestCase):
    def test_500_seeded_pmf_normalization_mean_and_variance(self):
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, TOPIC)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            n = data["trials"]
            p = Fraction(*data["success_probability"])
            selected = data["selected_successes"]
            values = [Fraction(a, b) for a, b in data["probabilities"]]
            expected = [
                Fraction(comb(n, k)) * p ** k * (1 - p) ** (n - k)
                for k in range(n + 1)
            ]
            self.assertEqual(values, expected)
            self.assertEqual(sum(values), 1)
            self.assertEqual(Fraction(item["answer"]), values[selected])
            mean = sum(Fraction(k) * mass for k, mass in enumerate(values))
            second_moment = sum(Fraction(k * k) * mass for k, mass in enumerate(values))
            self.assertEqual(mean, n * p)
            self.assertEqual(second_moment - mean * mean, n * p * (1 - p))
            self.assertEqual(item, generate(seed, difficulty, TOPIC))

    def test_tampering_is_rejected(self):
        item = generate(32, 3, TOPIC)
        altered = dict(item)
        altered["answer"] += "; changed"
        self.assertFalse(verify(altered))


if __name__ == "__main__":
    unittest.main()
