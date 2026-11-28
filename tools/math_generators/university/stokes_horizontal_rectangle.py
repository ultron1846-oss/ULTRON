"""Bounded Stokes theorem for affine fields on horizontal rectangles."""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "stokes_theorem_horizontal_rectangles"
VERIFIER = "independent_stokes_horizontal_rectangle_boundary_surface_check"


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _read_pair(value: Any, *, max_abs: int, max_denominator: int) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(part, int) or isinstance(part, bool) for part in value)
    ):
        raise ValueError("coefficients must be numerator/denominator pairs")
    numerator, denominator = value
    if abs(numerator) > max_abs or not 1 <= denominator <= max_denominator:
        raise ValueError("coefficient exceeds the configured bound")
    result = Fraction(numerator, denominator)
    if [result.numerator, result.denominator] != value:
        raise ValueError("rational pairs must be reduced with positive denominators")
    return result


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _boundary_integral(
    px: Fraction, py: Fraction, pz: Fraction,
    qx: Fraction, qy: Fraction, qz: Fraction,
    left: int, right: int, bottom: int, top: int, z0: int,
) -> Fraction:
    width = right - left
    height = top - bottom
    # Counter-clockwise boundary: bottom, right, top, left.
    bottom_edge = (
        px * Fraction(right * right - left * left, 2)
        + (py * bottom + pz * z0) * width
    )
    right_edge = (
        qy * Fraction(top * top - bottom * bottom, 2)
        + (qx * right + qz * z0) * height
    )
    top_edge = -(
        px * Fraction(right * right - left * left, 2)
        + (py * top + pz * z0) * width
    )
    left_edge = -(
        qy * Fraction(top * top - bottom * bottom, 2)
        + (qx * left + qz * z0) * height
    )
    return bottom_edge + right_edge + top_edge + left_edge


def _canonical(seed: int, difficulty: int, coefficients: list[Fraction], bounds: list[int]) -> dict:
    px, py, pz, qx, qy, qz = coefficients
    left, right, bottom, top, z0 = bounds
    curl_z = qx - py
    surface_integral = curl_z * (right - left) * (top - bottom)
    boundary_integral = _boundary_integral(
        px, py, pz, qx, qy, qz, left, right, bottom, top, z0
    )
    p_text = f"({_render(px)})x+({_render(py)})y+({_render(pz)})z"
    q_text = f"({_render(qx)})x+({_render(qy)})y+({_render(qz)})z"
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "Stokes theorem for affine fields on horizontal axis-aligned rectangles",
        "difficulty": difficulty,
        "problem": (
            f"For F=(P,Q,0), P={p_text}, Q={q_text}, and the surface "
            f"S: z={z0}, ({left}≤x≤{right}, {bottom}≤y≤{top}), evaluate "
            "the counter-clockwise boundary integral and the upward curl surface integral."
        ),
        "steps": [
            f"(curl F)·k = ∂Q/∂x−∂P/∂y = {_render(qx)}−({_render(py)}) = {_render(curl_z)}.",
            f"Surface integral = {_render(curl_z)}×{right-left}×{top-bottom} = {_render(surface_integral)}.",
            f"Sum the four oriented boundary-edge integrals to obtain {_render(boundary_integral)}.",
        ],
        "answer": (
            f"boundary={_render(boundary_integral)}; "
            f"surface={_render(surface_integral)}; equal={str(boundary_integral == surface_integral).lower()}"
        ),
        "answer_type": "expression",
        "ingredients": {
            "topic": TOPIC,
            "field_coefficients": [_pair(value) for value in coefficients],
            "rectangle_and_height": bounds,
            "curl_z": _pair(curl_z),
            "boundary_integral": _render(boundary_integral),
            "surface_integral": _render(surface_integral),
        },
        "verifier": VERIFIER,
    }


def build_stokes_horizontal_rectangle_fields(rng: random.Random, difficulty: int):
    d = difficulty
    left = rng.randint(-3 * d, 3 * d)
    right = left + rng.randint(1, 3 * d)
    bottom = rng.randint(-3 * d, 3 * d)
    top = bottom + rng.randint(1, 3 * d)
    z0 = rng.randint(-3 * d, 3 * d)
    coefficients = [
        Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d))
        for _ in range(6)
    ]
    fields = _canonical(0, d, coefficients, [left, right, bottom, top, z0])
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_stokes_horizontal_rectangle({
        **fields,
        "id": f"university-{TOPIC}-0-{d}",
        "seed": 0,
    })


def verify_stokes_horizontal_rectangle(problem: dict) -> bool:
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
        raw_bounds = data.get("rectangle_and_height")
        if (
            not isinstance(raw_bounds, list)
            or len(raw_bounds) != 5
            or any(not isinstance(value, int) or isinstance(value, bool) for value in raw_bounds)
        ):
            return False
        left, right, bottom, top, z0 = raw_bounds
        d = difficulty
        if not (-3 * d <= left <= 3 * d and 1 <= right - left <= 3 * d):
            return False
        if not (-3 * d <= bottom <= 3 * d and 1 <= top - bottom <= 3 * d):
            return False
        if not -3 * d <= z0 <= 3 * d:
            return False
        raw_coefficients = data.get("field_coefficients")
        if not isinstance(raw_coefficients, list) or len(raw_coefficients) != 6:
            return False
        coefficients = [
            _read_pair(pair, max_abs=2 * d, max_denominator=d)
            for pair in raw_coefficients
        ]
        return problem == _canonical(seed, difficulty, coefficients, raw_bounds)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
