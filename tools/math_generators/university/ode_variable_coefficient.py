"""Bounded homogeneous variable-coefficient linear first-order ODE family."""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "homogeneous_variable_coefficient_linear_first_order_ODEs"
VERIFIER = "independent_variable_coefficient_linear_ode_log_derivative_check"


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _read_pair(value: Any, *, max_abs: int, max_denominator: int, positive: bool = False, nonzero: bool = False) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(part, int) or isinstance(part, bool) for part in value)
    ):
        raise ValueError("ODE rational values must be two-integer numerator/denominator pairs")
    numerator, denominator = value
    if abs(numerator) > max_abs or not 1 <= denominator <= max_denominator:
        raise ValueError("ODE rational value exceeds the configured bounds")
    result = Fraction(numerator, denominator)
    if [result.numerator, result.denominator] != value:
        raise ValueError("ODE rational pairs must be reduced")
    if positive and result <= 0:
        raise ValueError("initial value must be positive")
    if nonzero and result == 0:
        raise ValueError("variable coefficient must be nonzero")
    return result


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _canonical(seed: int, difficulty: int, a: Fraction, x0: Fraction, y0: Fraction, power: int) -> dict:
    exponent_coefficient = -a / (power + 1)
    solution = (
        f"y(x)={_render(y0)}*exp({_render(exponent_coefficient)}*"
        f"(x^{power + 1}-({_render(x0)})^{power + 1}))"
    )
    data = {
        "topic": TOPIC,
        "coefficient": _pair(a),
        "coefficient_power": power,
        "initial_point": _pair(x0),
        "initial_value": _pair(y0),
        "exponent_coefficient": _pair(exponent_coefficient),
    }
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "homogeneous linear equations y' + a*x^m*y = 0 with m in {1,2}",
        "difficulty": difficulty,
        "problem": (
            f"Solve y' + ({_render(a)})x^{power}y=0 with initial condition "
            f"y({_render(x0)})={_render(y0)}."
        ),
        "steps": [
            "Use the integrating factor exp(∫a*x^m dx).",
            f"The solution is y(x)=y0*exp(−a*(x^(m+1)−x0^(m+1))/(m+1)).",
            "Differentiate the exponent to verify y'/y = −a*x^m and substitute the initial point.",
        ],
        "answer": solution,
        "answer_type": "expression",
        "ingredients": data,
        "verifier": VERIFIER,
    }


def build_variable_coefficient_ode_fields(rng: random.Random, difficulty: int):
    d = difficulty
    numerator = rng.randint(-2 * d, 2 * d)
    if numerator == 0:
        numerator = 1
    a = Fraction(numerator, rng.randint(1, d))
    x0 = Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d))
    y0 = Fraction(rng.randint(1, 2 * d), rng.randint(1, d))
    power = rng.randint(1, min(2, d))
    fields = _canonical(0, d, a, x0, y0, power)
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_variable_coefficient_ode({**fields, "id": f"university-{TOPIC}-0-{d}", "seed": 0})


def verify_variable_coefficient_ode(problem: dict) -> bool:
    try:
        if not isinstance(problem, dict) or problem.get("topic") != TOPIC:
            return False
        difficulty = problem.get("difficulty")
        seed = problem.get("seed")
        if not isinstance(difficulty, int) or isinstance(difficulty, bool) or difficulty not in (1, 2, 3, 4, 5):
            return False
        if not isinstance(seed, int) or isinstance(seed, bool):
            return False
        data = problem.get("ingredients")
        if not isinstance(data, dict) or data.get("topic") != TOPIC:
            return False
        d = difficulty
        a = _read_pair(data.get("coefficient"), max_abs=2 * d, max_denominator=d, nonzero=True)
        x0 = _read_pair(data.get("initial_point"), max_abs=2 * d, max_denominator=d)
        y0 = _read_pair(data.get("initial_value"), max_abs=2 * d, max_denominator=d, positive=True)
        power = data.get("coefficient_power")
        if not isinstance(power, int) or isinstance(power, bool) or not 1 <= power <= min(2, d):
            return False
        exponent_coefficient = _read_pair(
            data.get("exponent_coefficient"),
            max_abs=2 * d,
            max_denominator=d * (power + 1),
        )
        # The exponent derivative must reproduce the ODE's logarithmic derivative.
        if exponent_coefficient * (power + 1) != -a:
            return False
        if not y0 > 0 or (exponent_coefficient * (x0 ** (power + 1) - x0 ** (power + 1))) != 0:
            return False
        return problem == _canonical(seed, difficulty, a, x0, y0, power)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
