"""Independent tests for the bounded homogeneous first-order ODE family."""
import math
import unittest

from tools.math_generators.university import generate, verify
from tools.math_generators.university.ode_first_order import (
    verify_homogeneous_constant_coefficient_first_order_ode,
)


def _expected_problem(seed, difficulty, rate, initial_value):
    solution = f"{initial_value}*exp({rate}t)"
    return {
        "grade_band": "University",
        "topic": "homogeneous_constant_coefficient_first_order_ODEs",
        "subtopic": "homogeneous constant-coefficient first-order ODEs",
        "difficulty": difficulty,
        "problem": f"Solve y'=({rate})y with initial condition y(0)={initial_value}.",
        "steps": [
            "Separate variables: dy/y=k dt.",
            f"Integrate: ln|y|=kt+C.",
            f"Apply y(0)={initial_value}: y(t)={initial_value}e^({rate}t).",
        ],
        "answer": f"y(t)={initial_value}e^({rate}t)",
        "answer_type": "expression",
        "ingredients": {
            "topic": "homogeneous_constant_coefficient_first_order_ODEs",
            "rate": rate,
            "initial_value": initial_value,
            "solution": solution,
        },
        "verifier": "independent_homogeneous_constant_coefficient_ode_analytic_check",
        "id": f"university-homogeneous_constant_coefficient_first_order_ODEs-{seed}-{difficulty}",
        "seed": seed,
    }


class FirstOrderODEGeneratorTests(unittest.TestCase):
    def test_seeded_generation_is_deterministic_and_analytically_valid(self):
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, "homogeneous_constant_coefficient_first_order_ODEs")
            self.assertEqual(
                item, generate(seed, difficulty, "homogeneous_constant_coefficient_first_order_ODEs")
            )
            self.assertTrue(verify(item), (seed, difficulty, item))
            data = item["ingredients"]
            rate = data["rate"]
            initial_value = data["initial_value"]

            # Independent analytic identity for y=y0*exp(k*t):
            # derivative coefficients equal k times the solution coefficient.
            solution_coefficient = int(data["solution"].split("*exp(", 1)[0])
            solution_exponent = int(data["solution"].split("exp(", 1)[1].split("t", 1)[0])
            derivative_term = (solution_coefficient * solution_exponent, solution_exponent)
            equation_term = (rate * solution_coefficient, rate)
            self.assertEqual(derivative_term, equation_term)
            self.assertEqual(rate, solution_exponent)
            self.assertEqual(initial_value, int(data["solution"].split("*exp(", 1)[0]))
            self.assertEqual(initial_value * math.exp(rate * 0.0), initial_value)

            for time_value in (-0.5, 0.0, 0.5, 1.0):
                def solution_at(value):
                    return initial_value * math.exp(rate * value)

                value = solution_at(time_value)
                delta = 1e-6
                numeric_derivative = (
                    solution_at(time_value + delta) - solution_at(time_value - delta)
                ) / (2 * delta)
                self.assertTrue(
                    math.isclose(
                        numeric_derivative,
                        rate * value,
                        rel_tol=1e-6,
                        abs_tol=1e-7,
                    ),
                    (seed, difficulty, rate, time_value),
                )

    def test_inclusive_difficulty_bounds_and_zero_rate(self):
        for difficulty in range(1, 6):
            for rate, initial_value in (
                (-4 * difficulty, 1),
                (4 * difficulty, 8 * difficulty),
                (0, 1),
                (0, 8 * difficulty),
            ):
                item = _expected_problem(17, difficulty, rate, initial_value)
                self.assertTrue(verify_homogeneous_constant_coefficient_first_order_ode(item))
                self.assertTrue(verify(item))
                if rate == 0:
                    self.assertEqual(item["ingredients"]["solution"], f"{initial_value}*exp(0t)")

    def test_rejects_tampered_solution_question_steps_and_metadata(self):
        original = generate(71, 4, "homogeneous_constant_coefficient_first_order_ODEs")
        mutations = (
            lambda item: item.update(answer="y(t)=tampered"),
            lambda item: item.update(problem="Solve y'=sin(t)y."),
            lambda item: item.update(steps=["Skip the initial condition."]),
            lambda item: item.update(verifier="seed_replay_only"),
            lambda item: item.update(subtopic="all first-order ODEs"),
            lambda item: item["ingredients"].update(solution="wrong"),
            lambda item: item["ingredients"].update(rate=999),
            lambda item: item.update(unreviewed=True),
        )
        for mutation in mutations:
            altered = dict(original)
            altered["ingredients"] = dict(original["ingredients"])
            mutation(altered)
            self.assertFalse(verify_homogeneous_constant_coefficient_first_order_ode(altered))
            self.assertFalse(verify(altered))

    def test_rejects_malformed_values_and_out_of_budget_inputs(self):
        original = generate(7, 3, "homogeneous_constant_coefficient_first_order_ODEs")
        for field, value in (
            ("rate", True),
            ("rate", 1.5),
            ("initial_value", False),
            ("initial_value", 2.5),
            ("initial_value", 0),
            ("initial_value", -1),
            ("rate", 13),
            ("rate", -13),
        ):
            altered = dict(original)
            altered["ingredients"] = dict(original["ingredients"])
            altered["ingredients"][field] = value
            self.assertFalse(verify(altered), (field, value))

        for difficulty in (0, 6, True, 1.5):
            altered = dict(original)
            altered["difficulty"] = difficulty
            self.assertFalse(verify_homogeneous_constant_coefficient_first_order_ode(altered))

        self.assertFalse(verify_homogeneous_constant_coefficient_first_order_ode(None))
        with self.assertRaises(TypeError):
            generate(True, 1, "homogeneous_constant_coefficient_first_order_ODEs")
        with self.assertRaises(ValueError):
            generate(0, True, "homogeneous_constant_coefficient_first_order_ODEs")
        with self.assertRaises(ValueError):
            generate(0, 6, "homogeneous_constant_coefficient_first_order_ODEs")

    def test_unknown_or_tampered_seed_and_identifier_are_rejected(self):
        original = generate(19, 2, "homogeneous_constant_coefficient_first_order_ODEs")
        for key, value in (("seed", True), ("id", "other"), ("topic", "first_order_ODEs")):
            altered = dict(original)
            altered[key] = value
            self.assertFalse(verify(altered), (key, value))


if __name__ == "__main__":
    unittest.main()
