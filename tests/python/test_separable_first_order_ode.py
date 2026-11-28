"""Independent exact tests for the bounded separable power-law ODE family."""
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify
from tools.math_generators.university.ode_separable import MAX_SEED, TOPIC


def _fraction(pair):
    return Fraction(pair[0], pair[1])


class SeparableFirstOrderODETests(unittest.TestCase):
    def test_seeded_generation_and_independent_derivative_identities(self):
        branches = set()
        x_powers = set()
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, TOPIC)
            self.assertEqual(item, generate(seed, difficulty, TOPIC))
            self.assertTrue(verify(item), (seed, difficulty, item))
            data = item["ingredients"]
            coefficient = _fraction(data["coefficient"])
            initial_x = _fraction(data["initial_x"])
            initial_y = _fraction(data["initial_y"])
            m, n = data["x_power"], data["y_power"]
            power = m + 1
            x_powers.add(m)
            solution = data["solution"]

            # Independently substitute x=x0 into the exact solution and
            # compare the coefficient identities for its derivative.
            if n == 0:
                branches.add("polynomial")
                constant = _fraction(solution["constant"])
                leading = _fraction(solution["coefficient"])
                self.assertEqual(power * leading, coefficient)
                self.assertEqual(constant + leading * initial_x**power, initial_y)
            elif n == 1:
                branches.add("exponential")
                rate = _fraction(solution["rate"])
                stored_power = _fraction(solution["initial_power"])
                self.assertEqual(_fraction(solution["initial_value"]), initial_y)
                self.assertEqual(power * rate, coefficient)
                self.assertEqual(stored_power, initial_x**power)
                self.assertEqual(rate * (initial_x**power - stored_power), 0)
            else:
                branches.add("reciprocal")
                numerator = _fraction(solution["numerator"])
                denominator_constant = _fraction(solution["denominator_constant"])
                denominator_coefficient = _fraction(solution["denominator_coefficient"])
                self.assertEqual(numerator, initial_y)
                self.assertEqual(denominator_constant + denominator_coefficient * initial_x**power, 1)
                self.assertEqual(power * denominator_coefficient, -coefficient * initial_y)
                self.assertIn("denominator is nonzero", item["domain_note"])

        self.assertEqual(branches, {"polynomial", "exponential", "reciprocal"})
        self.assertEqual(x_powers, {0, 1, 2, 3})

    def test_difficulty_levels_bound_both_integer_powers_and_rational_inputs(self):
        for difficulty in range(1, 6):
            for seed in range(100):
                item = generate(seed, difficulty, TOPIC)
                data = item["ingredients"]
                self.assertLessEqual(data["x_power"], min(3, difficulty - 1))
                self.assertLessEqual(data["y_power"], min(2, (difficulty - 1) // 2))
                for field in ("coefficient", "initial_x", "initial_y"):
                    numerator, denominator = data[field]
                    self.assertLessEqual(abs(numerator), 2 * difficulty)
                    self.assertLessEqual(denominator, difficulty)
                    self.assertLessEqual(abs(numerator), 10)
                    self.assertLessEqual(denominator, 5)
                self.assertGreater(_fraction(data["initial_y"]), 0)
                self.assertNotEqual(_fraction(data["coefficient"]), 0)

    def test_metamorphic_initial_value_and_reciprocal_domain_contract(self):
        for seed in range(250):
            item = generate(seed, 5, TOPIC)
            data = item["ingredients"]
            m, n = data["x_power"], data["y_power"]
            x0 = _fraction(data["initial_x"])
            y0 = _fraction(data["initial_y"])
            coefficient = _fraction(data["coefficient"])
            solution = data["solution"]
            power = m + 1

            if n == 0:
                value_at_initial = (
                    _fraction(solution["constant"])
                    + _fraction(solution["coefficient"]) * x0**power
                )
                self.assertEqual(value_at_initial, y0)
            elif n == 1:
                self.assertEqual(_fraction(solution["initial_value"]), y0)
                self.assertEqual(
                    _fraction(solution["rate"]) * power,
                    coefficient,
                )
            else:
                denominator_at_initial = (
                    _fraction(solution["denominator_constant"])
                    + _fraction(solution["denominator_coefficient"]) * x0**power
                )
                self.assertEqual(denominator_at_initial, 1)
                self.assertNotEqual(denominator_at_initial, 0)
                self.assertEqual(_fraction(solution["numerator"]), y0)

    def test_tampered_problem_answer_steps_and_solution_are_rejected(self):
        original = generate(88, 5, TOPIC)
        mutations = (
            lambda item: item.update(answer="y(x)=0"),
            lambda item: item.update(problem="Solve an unrelated equation."),
            lambda item: item.update(steps=["skip integration"]),
            lambda item: item.update(verifier="seed-replay-only"),
            lambda item: item.update(domain_note="all x without restrictions"),
            lambda item: item["ingredients"].update(coefficient=[0, 1]),
            lambda item: item["ingredients"]["solution"].update(power=True),
            lambda item: item["ingredients"]["solution"].update(kind="unrelated"),
            lambda item: item.update(unreviewed=True),
        )
        for mutate in mutations:
            altered = dict(original)
            altered["ingredients"] = dict(original["ingredients"])
            altered["ingredients"]["solution"] = dict(original["ingredients"]["solution"])
            mutate(altered)
            self.assertFalse(verify(altered))

    def test_rejects_malformed_rationals_types_and_budget_violations(self):
        invalid_pairs = (
            [1, 0],
            [1, -1],
            [1.5, 1],
            [True, 1],
            [21, 1],
            [1, 6],
        )
        for field in ("coefficient", "initial_x", "initial_y"):
            for invalid in invalid_pairs:
                with self.subTest(field=field, invalid=invalid):
                    item = generate(7, 5, TOPIC)
                    item["ingredients"][field] = invalid
                    self.assertFalse(verify(item))

        item = generate(7, 5, TOPIC)
        item["ingredients"]["coefficient"] = [0, 1]
        self.assertFalse(verify(item))
        item = generate(7, 5, TOPIC)
        item["ingredients"]["initial_y"] = [0, 1]
        self.assertFalse(verify(item))
        item = generate(7, 1, TOPIC)
        item["ingredients"]["coefficient"] = [2, 1]
        self.assertFalse(verify(item))
        item = generate(7, 5, TOPIC)
        item["ingredients"]["x_power"] = True
        self.assertFalse(verify(item))
        item = generate(7, 5, TOPIC)
        item["ingredients"]["y_power"] = 3
        self.assertFalse(verify(item))

    def test_seed_difficulty_and_topic_boundaries(self):
        self.assertTrue(verify(generate(MAX_SEED, 5, TOPIC)))
        with self.assertRaises(ValueError):
            generate(MAX_SEED + 1, 5, TOPIC)
        with self.assertRaises(ValueError):
            generate(-1, 5, TOPIC)
        with self.assertRaises(TypeError):
            generate(True, 5, TOPIC)
        with self.assertRaises(ValueError):
            generate(1, True, TOPIC)
        with self.assertRaises(ValueError):
            generate(1, 0, TOPIC)
        with self.assertRaises(ValueError):
            generate(1, 6, TOPIC)
        with self.assertRaises(ValueError):
            generate(1, 1, "linear_first_order_variable_coefficient_ODEs")


if __name__ == "__main__":
    unittest.main()
