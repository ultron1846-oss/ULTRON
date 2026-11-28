"""Bounded exact double integrals of affine polynomials over rectangles."""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "rectangular_linear_polynomial_double_integrals"
VERIFIER = "independent_rectangular_affine_double_integral_check"


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _read_pair(value: Any, *, max_abs: int, max_denominator: int) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(part, int) or isinstance(part, bool) for part in value)
    ):
        raise ValueError("rational values must be two-integer numerator/denominator pairs")
    numerator, denominator = value
    if abs(numerator) > max_abs or not 1 <= denominator <= max_denominator:
        raise ValueError("rational value exceeds the configured bounds")
    result = Fraction(numerator, denominator)
    if [result.numerator, result.denominator] != value:
        raise ValueError("rational pairs must be reduced and have positive denominators")
    return result


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _integral(
    a: Fraction, b: Fraction, c: Fraction,
    left: int, right: int, bottom: int, top: int,
) -> Fraction:
    width = right - left
    height = top - bottom
    return (
        a * Fraction(right * right - left * left, 2) * height
        + b * Fraction(top * top - bottom * bottom, 2) * width
        + c * width * height
    )


def build_rectangular_double_integral_fields(rng: random.Random, difficulty: int):
    d = difficulty
    left = rng.randint(-3 * d, 3 * d)
    right = left + rng.randint(1, 3 * d)
    bottom = rng.randint(-3 * d, 3 * d)
    top = bottom + rng.randint(1, 3 * d)
    coefficients = [
        Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d))
        for _ in range(3)
    ]
    a, b, c = coefficients
    result = _integral(a, b, c, left, right, bottom, top)
    data = {
        "topic": TOPIC,
        "x_bounds": [left, right],
        "y_bounds": [bottom, top],
        "affine_coefficients": [_pair(value) for value in coefficients],
        "integral": _render(result),
    }
    polynomial = f"({_render(a)})x+({_render(b)})y+({_render(c)})"
    problem = (
        f"Evaluate the exact double integral of f(x,y)={polynomial} over "
        f"R=[{left},{right}]×[{bottom},{top}]."
    )
    steps = [
        "Integrate the affine terms separately over the rectangular region.",
        f"Use the exact antiderivatives in x and y to obtain {_render(result)}.",
    ]
    fields = {
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "affine polynomial double integrals over axis-aligned rectangles",
        "difficulty": d,
        "problem": problem,
        "steps": steps,
        "answer": _render(result),
        "answer_type": "expression",
        "ingredients": data,
        "verifier": VERIFIER,
    }
    return fields, lambda: result == _integral(a, b, c, left, right, bottom, top)


def verify_rectangular_double_integral(problem: dict) -> bool:
    try:
        if not isinstance(problem, dict) or problem.get("topic") != TOPIC:
            return False
        seed = problem.get("seed")
        if not isinstance(seed, int) or isinstance(seed, bool):
            return False
        difficulty = problem.get("difficulty")
        if not isinstance(difficulty, int) or isinstance(difficulty, bool) or difficulty not in (1, 2, 3, 4, 5):
            return False
        data = problem.get("ingredients")
        if not isinstance(data, dict) or data.get("topic") != TOPIC:
            return False
        x_bounds, y_bounds = data.get("x_bounds"), data.get("y_bounds")
        if (
            not isinstance(x_bounds, list) or len(x_bounds) != 2
            or not isinstance(y_bounds, list) or len(y_bounds) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) for value in x_bounds + y_bounds)
        ):
            return False
        left, right = x_bounds
        bottom, top = y_bounds
        d = difficulty
        if not (-3 * d <= left <= 3 * d and 1 <= right - left <= 3 * d):
            return False
        if not (-3 * d <= bottom <= 3 * d and 1 <= top - bottom <= 3 * d):
            return False
        raw_coefficients = data.get("affine_coefficients")
        if not isinstance(raw_coefficients, list) or len(raw_coefficients) != 3:
            return False
        a, b, c = [
            _read_pair(pair, max_abs=2 * d, max_denominator=d)
            for pair in raw_coefficients
        ]
        result = _integral(a, b, c, left, right, bottom, top)
        rendered = _render(result)
        polynomial = f"({_render(a)})x+({_render(b)})y+({_render(c)})"
        expected = {
            "id": f"university-{TOPIC}-{seed}-{difficulty}",
            "seed": seed,
            "grade_band": "University",
            "topic": TOPIC,
            "subtopic": "affine polynomial double integrals over axis-aligned rectangles",
            "difficulty": difficulty,
            "problem": (
                f"Evaluate the exact double integral of f(x,y)={polynomial} over "
                f"R=[{left},{right}]×[{bottom},{top}]."
            ),
            "steps": [
                "Integrate the affine terms separately over the rectangular region.",
                f"Use the exact antiderivatives in x and y to obtain {rendered}.",
            ],
            "answer": rendered,
            "answer_type": "expression",
            "ingredients": {
                "topic": TOPIC,
                "x_bounds": [left, right],
                "y_bounds": [bottom, top],
                "affine_coefficients": [_pair(a), _pair(b), _pair(c)],
                "integral": rendered,
            },
            "verifier": VERIFIER,
        }
        return problem == expected
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
