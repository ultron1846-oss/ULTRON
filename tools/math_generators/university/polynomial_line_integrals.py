"""Exact polynomial vector-field line integrals on bounded straight segments."""
from __future__ import annotations

import math
import random
from fractions import Fraction
from typing import Any

TOPIC = "polynomial_vector_field_segment_line_integrals"
VERIFIER = "independent_polynomial_segment_line_integral_check"
MONOMIALS = ((0, 0), (1, 0), (0, 1), (2, 0), (1, 1), (0, 2))


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _read_pair(value: Any, *, max_abs: int, max_denominator: int) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(part, int) or isinstance(part, bool) for part in value)
    ):
        raise ValueError("rational values must be two-integer pairs")
    numerator, denominator = value
    if abs(numerator) > max_abs or not 1 <= denominator <= max_denominator:
        raise ValueError("rational value exceeds its difficulty bound")
    result = Fraction(numerator, denominator)
    if [result.numerator, result.denominator] != value:
        raise ValueError("rational pairs must be reduced")
    return result


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _poly_integral_on_segment(
    coefficients: tuple[Fraction, ...],
    x0: Fraction,
    y0: Fraction,
    dx: Fraction,
    dy: Fraction,
) -> Fraction:
    """Return integral_0^1 f(x0+t*dx,y0+t*dy) dt."""
    total = Fraction(0)
    for coefficient, (power_x, power_y) in zip(coefficients, MONOMIALS):
        for ix in range(power_x + 1):
            for iy in range(power_y + 1):
                term = (
                    coefficient
                    * math.comb(power_x, ix)
                    * math.comb(power_y, iy)
                    * x0 ** (power_x - ix)
                    * dx ** ix
                    * y0 ** (power_y - iy)
                    * dy ** iy
                )
                total += term / (ix + iy + 1)
    return total


def _expression(coefficients: tuple[Fraction, ...]) -> str:
    variables = ("1", "x", "y", "x^2", "x*y", "y^2")
    return " + ".join(
        f"({_render(coefficient)})*{variable}"
        for coefficient, variable in zip(coefficients, variables)
        if coefficient
    ) or "0"


def _canonical(
    seed: int,
    difficulty: int,
    start: tuple[Fraction, Fraction],
    end: tuple[Fraction, Fraction],
    p_coefficients: tuple[Fraction, ...],
    q_coefficients: tuple[Fraction, ...],
) -> dict:
    x0, y0 = start
    x1, y1 = end
    dx, dy = x1 - x0, y1 - y0
    integral = (
        dx * _poly_integral_on_segment(p_coefficients, x0, y0, dx, dy)
        + dy * _poly_integral_on_segment(q_coefficients, x0, y0, dx, dy)
    )
    data = {
        "topic": TOPIC,
        "start": [_pair(x0), _pair(y0)],
        "end": [_pair(x1), _pair(y1)],
        "p_coefficients": [_pair(value) for value in p_coefficients],
        "q_coefficients": [_pair(value) for value in q_coefficients],
        "integral": _render(integral),
    }
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "polynomial vector fields of total degree at most two on straight segments",
        "difficulty": difficulty,
        "problem": (
            f"Compute the exact line integral of F=(P,Q) along the segment "
            f"({x0},{y0}) to ({x1},{y1}), where P={_expression(p_coefficients)} "
            f"and Q={_expression(q_coefficients)}."
        ),
        "steps": [
            "Parameterize the segment by (x(t),y(t))=(x0,y0)+t*(dx,dy), 0≤t≤1.",
            "Substitute the parameterization into P dx/dt + Q dy/dt and integrate the resulting polynomial exactly.",
        ],
        "answer": _render(integral),
        "answer_type": "expression",
        "ingredients": data,
        "verifier": VERIFIER,
    }


def build_polynomial_line_integral_fields(rng: random.Random, difficulty: int):
    d = difficulty
    max_degree = min(2, d - 1)
    start = (
        Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d)),
        Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d)),
    )
    end = (
        Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d)),
        Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d)),
    )
    while end == start:
        end = (
            Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d)),
            Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d)),
        )
    def coefficients():
        values = []
        for px, py in MONOMIALS:
            if px + py > max_degree:
                values.append(Fraction(0))
            else:
                values.append(Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d)))
        if not any(values):
            values[0] = Fraction(1)
        return tuple(values)
    p_coefficients, q_coefficients = coefficients(), coefficients()
    fields = _canonical(0, d, start, end, p_coefficients, q_coefficients)
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_polynomial_line_integral({
        **fields, "id": f"university-{TOPIC}-0-{d}", "seed": 0
    })


def verify_polynomial_line_integral(problem: dict) -> bool:
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
        raw_start, raw_end = data.get("start"), data.get("end")
        if (
            not isinstance(raw_start, list) or len(raw_start) != 2
            or not isinstance(raw_end, list) or len(raw_end) != 2
        ):
            return False
        d = difficulty
        start = tuple(_read_pair(v, max_abs=2 * d, max_denominator=d) for v in raw_start)
        end = tuple(_read_pair(v, max_abs=2 * d, max_denominator=d) for v in raw_end)
        if start == end:
            return False
        max_degree = min(2, d - 1)
        raw_p, raw_q = data.get("p_coefficients"), data.get("q_coefficients")
        if not isinstance(raw_p, list) or len(raw_p) != 6 or not isinstance(raw_q, list) or len(raw_q) != 6:
            return False
        p_values = tuple(_read_pair(v, max_abs=2 * d, max_denominator=d) for v in raw_p)
        q_values = tuple(_read_pair(v, max_abs=2 * d, max_denominator=d) for v in raw_q)
        if any(px + py > max_degree and (p_values[i] or q_values[i]) for i, (px, py) in enumerate(MONOMIALS)):
            return False
        expected = _canonical(seed, difficulty, start, end, p_values, q_values)
        return problem == expected
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
