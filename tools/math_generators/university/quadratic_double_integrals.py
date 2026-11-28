"""Exact quadratic-polynomial double integrals over rational rectangles."""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "rectangular_quadratic_polynomial_double_integrals"
VERIFIER = "independent_rectangular_quadratic_double_integral_check"
MONOMIALS = ((2, 0), (1, 1), (0, 2), (1, 0), (0, 1), (0, 0))
NAMES = ("x^2", "x*y", "y^2", "x", "y", "1")


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


def _power_integral(left: Fraction, right: Fraction, degree: int) -> Fraction:
    return (right ** (degree + 1) - left ** (degree + 1)) / (degree + 1)


def _integrate(
    coefficients: tuple[Fraction, ...],
    left: Fraction, right: Fraction,
    bottom: Fraction, top: Fraction,
) -> Fraction:
    total = Fraction(0)
    for coefficient, (power_x, power_y) in zip(coefficients, MONOMIALS):
        total += (
            coefficient
            * _power_integral(left, right, power_x)
            * _power_integral(bottom, top, power_y)
        )
    return total


def _expression(coefficients: tuple[Fraction, ...]) -> str:
    return " + ".join(
        f"({_render(value)})*{name}"
        for value, name in zip(coefficients, NAMES)
        if value
    ) or "0"


def _canonical(seed: int, difficulty: int, bounds, coefficients) -> dict:
    left, right, bottom, top = bounds
    result = _integrate(coefficients, left, right, bottom, top)
    data = {
        "topic": TOPIC,
        "x_bounds": [_pair(left), _pair(right)],
        "y_bounds": [_pair(bottom), _pair(top)],
        "coefficients": [_pair(value) for value in coefficients],
        "integral": _render(result),
    }
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "quadratic polynomial double integrals over rational rectangles",
        "difficulty": difficulty,
        "problem": (
            f"Evaluate the exact double integral of f(x,y)={_expression(coefficients)} "
            f"over [{_render(left)},{_render(right)}]×[{_render(bottom)},{_render(top)}]."
        ),
        "steps": [
            "Use Fubini's theorem to separate each monomial into an x-factor and a y-factor.",
            f"Apply the exact power antiderivatives and sum the six rational contributions to obtain {_render(result)}.",
        ],
        "answer": _render(result),
        "answer_type": "expression",
        "ingredients": data,
        "verifier": VERIFIER,
    }


def build_quadratic_double_integral_fields(rng: random.Random, difficulty: int):
    d = difficulty
    def fraction():
        return Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d))
    x_values = sorted((fraction(), fraction()))
    while x_values[0] == x_values[1]:
        x_values = sorted((fraction(), fraction()))
    y_values = sorted((fraction(), fraction()))
    while y_values[0] == y_values[1]:
        y_values = sorted((fraction(), fraction()))
    bounds = (x_values[0], x_values[1], y_values[0], y_values[1])
    max_degree = min(2, d - 1)
    coefficients = tuple(
        fraction() if sum(monomial) <= max_degree else Fraction(0)
        for monomial in MONOMIALS
    )
    fields = _canonical(0, d, bounds, coefficients)
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_quadratic_double_integral({
        **fields, "id": f"university-{TOPIC}-0-{d}", "seed": 0
    })


def verify_quadratic_double_integral(problem: dict) -> bool:
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
        raw_x, raw_y = data.get("x_bounds"), data.get("y_bounds")
        if (
            not isinstance(raw_x, list) or len(raw_x) != 2
            or not isinstance(raw_y, list) or len(raw_y) != 2
        ):
            return False
        d = difficulty
        left, right = (_read_pair(v, max_abs=2 * d, max_denominator=d) for v in raw_x)
        bottom, top = (_read_pair(v, max_abs=2 * d, max_denominator=d) for v in raw_y)
        if not left < right or not bottom < top:
            return False
        raw_coefficients = data.get("coefficients")
        if not isinstance(raw_coefficients, list) or len(raw_coefficients) != 6:
            return False
        coefficients = tuple(
            _read_pair(v, max_abs=2 * d, max_denominator=d)
            for v in raw_coefficients
        )
        max_degree = min(2, d - 1)
        if any(
            sum(monomial) > max_degree and coefficients[index]
            for index, monomial in enumerate(MONOMIALS)
        ):
            return False
        expected = _canonical(
            seed, difficulty, (left, right, bottom, top), coefficients
        )
        return problem == expected
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
