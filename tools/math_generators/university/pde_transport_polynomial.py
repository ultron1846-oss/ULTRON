"""Bounded constant-speed transport PDEs with cubic-or-lower polynomial data."""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "constant_speed_transport_polynomial_initial_data_PDEs"
VERIFIER = "independent_polynomial_transport_pde_residual_check"


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _read_pair(value: Any, *, max_abs: int, max_denominator: int, nonzero: bool = False) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(part, int) or isinstance(part, bool) for part in value)
    ):
        raise ValueError("PDE values must be integer numerator/denominator pairs")
    numerator, denominator = value
    if abs(numerator) > max_abs or not 1 <= denominator <= max_denominator:
        raise ValueError("PDE value exceeds configured rational bounds")
    result = Fraction(numerator, denominator)
    if [result.numerator, result.denominator] != value:
        raise ValueError("rational pairs must be reduced and have positive denominators")
    if nonzero and result == 0:
        raise ValueError("transport speed must be nonzero")
    return result


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _poly_text(coefficients: tuple[Fraction, Fraction, Fraction, Fraction], variable: str) -> str:
    a0, a1, a2, a3 = coefficients
    return (
        f"({_render(a0)})+({_render(a1)}){variable}"
        f"+({_render(a2)}){variable}^2+({_render(a3)}){variable}^3"
    )


def _canonical(seed: int, difficulty: int, speed: Fraction, coefficients: tuple[Fraction, Fraction, Fraction, Fraction]) -> dict:
    initial = _poly_text(coefficients, "x")
    shifted = _poly_text(coefficients, f"(x−({_render(speed)})t)")
    solution = f"u(x,t)={shifted}"
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "constant-speed one-dimensional transport with polynomial initial data of degree at most three",
        "difficulty": difficulty,
        "problem": (
            f"Solve u_t+({_render(speed)})u_x=0 for all real x,t, "
            f"with initial data u(x,0)={initial}."
        ),
        "steps": [
            "Use the characteristic coordinate s=x−c*t.",
            "The solution is constant along lines x−c*t=constant.",
            f"Thus u(x,t)=p(x−c*t)={shifted}.",
            "Differentiate with respect to t and x to verify u_t+c*u_x=0.",
        ],
        "answer": solution,
        "answer_type": "expression",
        "ingredients": {
            "topic": TOPIC,
            "transport_speed": _pair(speed),
            "initial_polynomial_coefficients": [_pair(value) for value in coefficients],
            "polynomial_degree_bound": 3,
        },
        "verifier": VERIFIER,
    }


def build_polynomial_transport_pde_fields(rng: random.Random, difficulty: int):
    d = difficulty
    def component():
        return Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d))
    speed = component()
    while speed == 0:
        speed = component()
    coefficients = tuple(component() for _ in range(4))
    fields = _canonical(0, d, speed, coefficients)
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_polynomial_transport_pde({
        **fields,
        "id": f"university-{TOPIC}-0-{d}",
        "seed": 0,
    })


def verify_polynomial_transport_pde(problem: dict) -> bool:
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
        speed = _read_pair(data.get("transport_speed"), max_abs=2 * difficulty, max_denominator=difficulty, nonzero=True)
        raw_coefficients = data.get("initial_polynomial_coefficients")
        if not isinstance(raw_coefficients, list) or len(raw_coefficients) != 4:
            return False
        coefficients = tuple(
            _read_pair(value, max_abs=2 * difficulty, max_denominator=difficulty)
            for value in raw_coefficients
        )
        if data.get("polynomial_degree_bound") != 3:
            return False
        return problem == _canonical(seed, difficulty, speed, coefficients)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
