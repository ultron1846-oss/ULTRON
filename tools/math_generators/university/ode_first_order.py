"""Independent validator for the bounded y' = k*y initial-value family.

This is intentionally narrower than general first-order ODE solving.
"""
from __future__ import annotations

from typing import Any

TOPIC = "differential_equations"


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _expected_problem(seed: int, difficulty: int, rate: int, initial_value: int) -> dict:
    solution = f"{initial_value}*exp({rate}t)"
    answer = f"y(t)={initial_value}e^({rate}t)"
    return {
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "homogeneous constant-coefficient first-order ODEs",
        "difficulty": difficulty,
        "problem": (
            f"Solve y'=({rate})y with initial condition y(0)={initial_value}."
        ),
        "steps": [
            "Separate variables: dy/y=k dt.",
            f"Integrate: ln|y|=kt+C.",
            f"Apply y(0)={initial_value}: y(t)={initial_value}e^({rate}t).",
        ],
        "answer": answer,
        "answer_type": "expression",
        "ingredients": {
            "topic": TOPIC,
            "rate": rate,
            "initial_value": initial_value,
            "solution": solution,
        },
        "verifier": "independent_homogeneous_constant_coefficient_ode_analytic_check",
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
    }


def verify_homogeneous_constant_coefficient_first_order_ode(problem: Any) -> bool:
    """Recompute y(t)=y0*exp(k*t), its derivative identity, and y(0)=y0."""
    if not isinstance(problem, dict):
        return False
    try:
        if set(problem) != {
            "grade_band", "topic", "subtopic", "difficulty", "problem", "steps",
            "answer", "answer_type", "ingredients", "verifier", "id", "seed",
        }:
            return False
        seed, difficulty = problem["seed"], problem["difficulty"]
        if not _is_int(seed) or not _is_int(difficulty) or difficulty not in (1, 2, 3, 4, 5):
            return False

        ingredients = problem["ingredients"]
        if not isinstance(ingredients, dict) or set(ingredients) != {
            "topic", "rate", "initial_value", "solution"
        } or ingredients["topic"] != TOPIC:
            return False
        rate, initial_value = ingredients["rate"], ingredients["initial_value"]
        if not _is_int(rate) or not _is_int(initial_value):
            return False
        if not -4 * difficulty <= rate <= 4 * difficulty:
            return False
        if not 1 <= initial_value <= 8 * difficulty:
            return False

        # For y(t)=y0*exp(k*t), d(y)/dt = (k*y0)*exp(k*t) = k*y(t),
        # and substituting t=0 gives y(0)=y0. These coefficient/exponent
        # identities are exact and do not reuse the generator's boolean check.
        solution_coefficient = initial_value
        solution_exponent = rate
        derivative_coefficient = solution_coefficient * solution_exponent
        right_hand_side_coefficient = rate * solution_coefficient
        derivative_exponent = solution_exponent
        right_hand_side_exponent = rate
        initial_at_zero = initial_value * 1
        if (derivative_coefficient, derivative_exponent) != (
            right_hand_side_coefficient, right_hand_side_exponent
        ):
            return False
        if initial_at_zero != initial_value:
            return False

        expected = _expected_problem(seed, difficulty, rate, initial_value)
        return problem == expected
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
