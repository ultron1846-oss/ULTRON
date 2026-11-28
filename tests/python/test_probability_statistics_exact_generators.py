"""Independent exact regressions for finite-distribution and binomial topics."""
import math
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify


def _fraction(pair):
    return Fraction(pair[0], pair[1])


class ProbabilityStatisticsExactGeneratorTests(unittest.TestCase):
    def test_500_finite_distribution_expectation_and_variance_examples(self):
        topic = "finite_discrete_distribution_expectation_variance"
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, topic)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            outcomes = data["outcomes"]
            weights = data["relative_weights"]
            total = sum(weights)
            probabilities = [_fraction(pair) for pair in data["probabilities"]]
            self.assertEqual(sum(probabilities, Fraction(0)), Fraction(1))
            self.assertEqual(data["total_weight"], total)
            expected = sum(
                (Fraction(x * w, total) for x, w in zip(outcomes, weights)),
                Fraction(0),
            )
            second = sum(
                (Fraction(x * x * w, total) for x, w in zip(outcomes, weights)),
                Fraction(0),
            )
            variance = second - expected * expected
            self.assertEqual(_fraction(data["expectation"]), expected)
            self.assertEqual(_fraction(data["second_moment"]), second)
            self.assertEqual(_fraction(data["variance"]), variance)
            self.assertGreaterEqual(variance, 0)
            self.assertEqual(item, generate(seed, difficulty, topic))

    def test_500_binomial_point_probabilities_and_moments(self):
        topic = "binomial_distribution_point_probabilities"
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, topic)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            n = data["trials"]
            k = data["successes"]
            p = _fraction(data["success_probability"])
            point = Fraction(math.comb(n, k)) * p**k * (1-p)**(n-k)
            expectation = n*p
            variance = n*p*(1-p)
            normalized = sum(
                (Fraction(math.comb(n, j)) * p**j * (1-p)**(n-j) for j in range(n+1)),
                Fraction(0),
            )
            self.assertEqual(_fraction(data["point_probability"]), point)
            self.assertEqual(_fraction(data["expectation"]), expectation)
            self.assertEqual(_fraction(data["variance"]), variance)
            self.assertEqual(normalized, Fraction(1))
            self.assertEqual(item, generate(seed, difficulty, topic))

    def test_probability_family_verifiers_reject_tampering(self):
        for topic in (
            "finite_discrete_distribution_expectation_variance",
            "binomial_distribution_point_probabilities",
        ):
            with self.subTest(topic=topic):
                item = generate(113, 5, topic)
                altered = dict(item)
                altered["answer"] += "; altered"
                self.assertFalse(verify(altered))


if __name__ == "__main__":
    unittest.main()
