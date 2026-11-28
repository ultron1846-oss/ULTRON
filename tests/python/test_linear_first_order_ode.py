"""Independent exact checks for bounded linear constant-coefficient first-order ODEs."""
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify
from tools.math_generators.university.linear_first_order_ode import MAX_SEED, TOPIC


def _f(pair):
    return Fraction(pair[0], pair[1])


class LinearFirstOrderODETests(unittest.TestCase):
    def test_seeded_determinism_and_independent_solution_validation(self):
        branches = set()
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, TOPIC)
            self.assertEqual(item, generate(seed, difficulty, TOPIC))
            self.assertTrue(verify(item), (seed, difficulty))
            data = item["ingredients"]
            a, b, y0 = _f(data["a"]), _f(data["b"]), _f(data["initial_value"])
            solution = data["solution"]
            if a == 0:
                branches.add("zero_rate")
                constant = _f(solution["constant"])
                linear = _f(solution["linear"])
                # Independent derivative/RHS identity for y=c0+c1*t.
                self.assertEqual(constant, y0)
                self.assertEqual(linear, b)
                self.assertEqual(linear, a * constant + b)
            else:
                branches.add("nonzero_rate")
                rate = _f(solution["rate"])
                exponential = _f(solution["exponential_coefficient"])
                constant = _f(solution["constant"])
                # Independent symbolic coefficient comparison for y=c1*e^(a*t)+c0.
                self.assertEqual(rate, a)
                self.assertEqual(a * constant + b, 0)
                self.assertEqual(exponential + constant, y0)
                if b == 0:
                    branches.add("homogeneous")
                    self.assertEqual(constant, 0)
                    self.assertEqual(exponential, y0)
                else:
                    branches.add("inhomogeneous")
        self.assertEqual(branches, {"zero_rate", "nonzero_rate", "homogeneous", "inhomogeneous"})

    def test_difficulty_progression_is_bounded_and_reproducible(self):
        for difficulty in range(1, 6):
            for seed in range(100):
                item = generate(seed, difficulty, TOPIC)
                data = item["ingredients"]
                for field in ("a", "b", "initial_value"):
                    numerator, denominator = data[field]
                    self.assertLessEqual(abs(numerator), 2 * difficulty)
                    self.assertLessEqual(denominator, difficulty)
                    self.assertLessEqual(abs(numerator), 10)
                    self.assertLessEqual(denominator, 5)

    def test_metamorphic_equilibrium_and_initial_value_invariants(self):
        for seed in range(250):
            item = generate(seed, 1 + seed % 5, TOPIC)
            data = item["ingredients"]
            a, b, y0 = _f(data["a"]), _f(data["b"]), _f(data["initial_value"])
            solution = data["solution"]
            if a == 0:
                self.assertEqual(_f(solution["constant"]), y0)
                self.assertEqual(_f(solution["linear"]), b)
            else:
                equilibrium = -b / a
                exponential = y0 - equilibrium
                self.assertEqual(_f(solution["constant"]), equilibrium)
                self.assertEqual(_f(solution["exponential_coefficient"]), exponential)
                self.assertEqual(_f(solution["rate"]), a)

    def test_tampered_answers_coefficients_and_solution_are_rejected(self):
        item = generate(71, 4, TOPIC)
        altered = dict(item)
        altered["answer"] = "y(t)=0"
        self.assertFalse(verify(altered))

        altered = dict(item)
        altered["ingredients"] = dict(item["ingredients"])
        altered["ingredients"]["b"] = [altered["ingredients"]["b"][0] + 1, altered["ingredients"]["b"][1]]
        self.assertFalse(verify(altered))

        altered = dict(item)
        altered["ingredients"] = dict(item["ingredients"])
        altered["ingredients"]["solution"] = dict(item["ingredients"]["solution"])
        altered["ingredients"]["solution"]["constant"] = [9999, 1]
        self.assertFalse(verify(altered))

        altered = dict(item)
        altered["steps"] = ["skip"]
        self.assertFalse(verify(altered))

        altered = dict(item)
        altered["unreviewed"] = True
        self.assertFalse(verify(altered))

    def test_rejects_malformed_and_over_budget_rationals(self):
        for field, bad_pair in (
            ("a", [1, 0]),
            ("b", [1, -1]),
            ("initial_value", [1.5, 1]),
            ("a", [True, 1]),
            ("b", [21, 1]),
            ("initial_value", [1, 6]),
        ):
            with self.subTest(field=field, bad_pair=bad_pair):
                item = generate(7, 5, TOPIC)
                item["ingredients"][field] = bad_pair
                self.assertFalse(verify(item))

        item = generate(7, 1, TOPIC)
        item["ingredients"]["a"] = [2, 1]  # within global cap, outside difficulty-1 envelope
        self.assertFalse(verify(item))

        item = generate(7, 5, TOPIC)
        item["ingredients"]["solution"]["constant"] = [1001, 1]
        self.assertFalse(verify(item))

    def test_seed_and_difficulty_boundaries(self):
        self.assertTrue(verify(generate(MAX_SEED, 5, TOPIC)))
        with self.assertRaises(ValueError):
            generate(MAX_SEED + 1, 5, TOPIC)
        with self.assertRaises(ValueError):
            generate(-1, 5, TOPIC)
        with self.assertRaises(ValueError):
            generate(1, True, TOPIC)
        with self.assertRaises(ValueError):
            generate(1, 0, TOPIC)
        with self.assertRaises(ValueError):
            generate(1, 6, TOPIC)
        with self.assertRaises(ValueError):
            generate(1, 1, "first_order_ODEs")


if __name__ == "__main__":
    unittest.main()
