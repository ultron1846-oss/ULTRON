"""Bounded affine solutions of the constant-coefficient first-order transport PDE."""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "affine_transport_first_order_PDEs"
VERIFIER = "independent_affine_transport_pde_identity_check"


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _read_pair(value: Any, *, max_abs: int, max_denominator: int, nonzero: bool = False) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(part, int) or isinstance(part, bool) for part in value)
    ):
        raise ValueError("PDE rational values must be numerator/denominator pairs")
    numerator, denominator = value
    if abs(numerator) > max_abs or not 1 <= denominator <= max_denominator:
        raise ValueError("PDE rational value exceeds its difficulty bound")
    result = Fraction(numerator, denominator)
    if [result.numerator, result.denominator] != value:
        raise ValueError("PDE rational pairs must be reduced")
    if nonzero and result == 0:
        raise ValueError("transport coefficients must be nonzero")
    return result


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _canonical(seed, difficulty, a, b, scale, x0, y0, initial_value):
    offset = initial_value - scale * (b * x0 - a * y0)
    ux = scale * b
    uy = -scale * a
    residual = a * ux + b * uy
    data = {
        "topic": TOPIC,
        "transport_coefficients": [_pair(a), _pair(b)],
        "solution_scale": _pair(scale),
        "initial_point": [_pair(x0), _pair(y0)],
        "initial_value": _pair(initial_value),
        "constant_offset": _pair(offset),
        "partial_x": _pair(ux),
        "partial_y": _pair(uy),
        "pde_residual": _pair(residual),
    }
    solution = (
        f"u(x,y)=({_render(scale)})*(({_render(b)})x-({_render(a)})y)"
        f"+({_render(offset)})"
    )
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "affine solutions of a*u_x+b*u_y=0 for nonzero constant a,b",
        "difficulty": difficulty,
        "problem": (
            f"Solve a*u_x+b*u_y=0 with a={_render(a)}, b={_render(b)}, "
            f"and condition u({_render(x0)},{_render(y0)})={_render(initial_value)} "
            "within the affine solution family."
        ),
        "steps": [
            "For an affine solution u(x,y)=A*x+B*y+C, the PDE requires a*A+b*B=0.",
            "Choose A=scale*b and B=−scale*a; use the point condition to determine C.",
            "Substitute the partial derivatives into the PDE and the initial point into u.",
        ],
        "answer": solution,
        "answer_type": "expression",
        "ingredients": data,
        "verifier": VERIFIER,
    }


def build_affine_transport_pde_fields(rng: random.Random, difficulty: int):
    d = difficulty
    def nonzero_fraction():
        numerator = rng.randint(-2 * d, 2 * d)
        while numerator == 0:
            numerator = rng.randint(-2 * d, 2 * d)
        return Fraction(numerator, rng.randint(1, d))
    a, b, scale = nonzero_fraction(), nonzero_fraction(), nonzero_fraction()
    x0 = Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d))
    y0 = Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d))
    initial_value = Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d))
    fields = _canonical(0, d, a, b, scale, x0, y0, initial_value)
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_affine_transport_pde({
        **fields, "id": f"university-{TOPIC}-0-{d}", "seed": 0
    })


def verify_affine_transport_pde(problem: dict) -> bool:
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
        d = difficulty
        raw_ab = data.get("transport_coefficients")
        raw_point = data.get("initial_point")
        if not isinstance(raw_ab, list) or len(raw_ab) != 2:
            return False
        if not isinstance(raw_point, list) or len(raw_point) != 2:
            return False
        a, b = (
            _read_pair(value, max_abs=2 * d, max_denominator=d, nonzero=True)
            for value in raw_ab
        )
        scale = _read_pair(data.get("solution_scale"), max_abs=2 * d, max_denominator=d, nonzero=True)
        x0, y0 = (
            _read_pair(value, max_abs=2 * d, max_denominator=d)
            for value in raw_point
        )
        initial_value = _read_pair(data.get("initial_value"), max_abs=2 * d, max_denominator=d)
        expected = _canonical(seed, difficulty, a, b, scale, x0, y0, initial_value)
        return problem == expected and expected["ingredients"]["pde_residual"] == [0, 1]
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
