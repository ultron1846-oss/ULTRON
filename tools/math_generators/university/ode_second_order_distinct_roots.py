"""Bounded homogeneous second-order linear ODEs with distinct rational real roots."""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "distinct_real_root_second_order_linear_homogeneous_ODEs"
VERIFIER = "independent_distinct_real_root_second_order_ode_check"


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _read_pair(value: Any, *, max_abs: int, max_denominator: int) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(part, int) or isinstance(part, bool) for part in value)
    ):
        raise ValueError("ODE values must be integer numerator/denominator pairs")
    numerator, denominator = value
    if abs(numerator) > max_abs or not 1 <= denominator <= max_denominator:
        raise ValueError("ODE value exceeds configured rational bounds")
    result = Fraction(numerator, denominator)
    if [result.numerator, result.denominator] != value:
        raise ValueError("rational pairs must be reduced and have positive denominators")
    return result


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _canonical(
    seed: int,
    difficulty: int,
    roots: tuple[Fraction, Fraction],
    initial_value: Fraction,
    initial_derivative: Fraction,
) -> dict:
    r1, r2 = roots
    coefficient_y1 = -(r1 + r2)
    coefficient_y = r1 * r2
    c1 = (initial_derivative - r2 * initial_value) / (r1 - r2)
    c2 = (r1 * initial_value - initial_derivative) / (r1 - r2)
    equation = (
        f"y''+({_render(coefficient_y1)})y'+({_render(coefficient_y)})y=0"
    )
    solution = (
        f"y(t)=({_render(c1)})exp(({_render(r1)})t)"
        f"+({_render(c2)})exp(({_render(r2)})t)"
    )
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "homogeneous second-order linear equations with distinct real rational characteristic roots",
        "difficulty": difficulty,
        "problem": (
            f"Solve {equation} with initial conditions "
            f"y(0)={_render(initial_value)} and y'(0)={_render(initial_derivative)}."
        ),
        "steps": [
            f"The characteristic roots are r1={_render(r1)} and r2={_render(r2)}.",
            f"The characteristic polynomial is (r−({_render(r1)}))(r−({_render(r2)})).",
            f"Use y(t)=C1 exp(r1 t)+C2 exp(r2 t), with C1={_render(c1)} and C2={_render(c2)}.",
            "The constants satisfy C1+C2=y(0) and r1*C1+r2*C2=y'(0).",
        ],
        "answer": solution,
        "answer_type": "expression",
        "ingredients": {
            "topic": TOPIC,
            "characteristic_roots": [_pair(r1), _pair(r2)],
            "initial_value": _pair(initial_value),
            "initial_derivative": _pair(initial_derivative),
            "equation_coefficients": [_pair(coefficient_y1), _pair(coefficient_y)],
            "solution_coefficients": [_pair(c1), _pair(c2)],
        },
        "verifier": VERIFIER,
    }


def build_distinct_root_second_order_ode_fields(rng: random.Random, difficulty: int):
    d = difficulty
    def component():
        return Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d))
    r1 = component()
    r2 = component()
    while r2 == r1:
        r2 = component()
    initial_value = component()
    initial_derivative = component()
    fields = _canonical(0, d, (r1, r2), initial_value, initial_derivative)
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_distinct_root_second_order_ode({
        **fields,
        "id": f"university-{TOPIC}-0-{d}",
        "seed": 0,
    })


def verify_distinct_root_second_order_ode(problem: dict) -> bool:
    try:
        if not isinstance(problem, dict) or problem.get("topic") != TOPIC:
            return False
        seed = problem.get("seed")
        difficulty = problem.get("difficulty")
        if not isinstance(seed, int) or isinstance(seed, bool):
            return False
        if not isinstance(difficulty, int) or isinstance(difficulty, bool) or difficulty not in (1, 2, 3, 4, 5):
            return False
        data = problem.get("ingredients")
        if not isinstance(data, dict) or data.get("topic") != TOPIC:
            return False
        raw_roots = data.get("characteristic_roots")
        if not isinstance(raw_roots, list) or len(raw_roots) != 2:
            return False
        d = difficulty
        roots = tuple(
            _read_pair(value, max_abs=2 * d, max_denominator=d)
            for value in raw_roots
        )
        if roots[0] == roots[1]:
            return False
        initial_value = _read_pair(data.get("initial_value"), max_abs=2 * d, max_denominator=d)
        initial_derivative = _read_pair(data.get("initial_derivative"), max_abs=2 * d, max_denominator=d)
        return problem == _canonical(seed, difficulty, roots, initial_value, initial_derivative)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
