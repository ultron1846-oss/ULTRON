"""Bounded divergence theorem for diagonal linear fields on rectangular boxes."""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "divergence_theorem_axis_aligned_boxes"
VERIFIER = "independent_divergence_box_face_flux_volume_check"


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


def _canonical(seed: int, difficulty: int, coefficients: list[Fraction], bounds: list[int]) -> dict:
    a, b, c = coefficients
    x0, x1, y0, y1, z0, z1 = bounds
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    volume = dx * dy * dz
    divergence = a + b + c
    face_fluxes = [
        a * x1 * dy * dz,
        -a * x0 * dy * dz,
        b * y1 * dx * dz,
        -b * y0 * dx * dz,
        c * z1 * dx * dy,
        -c * z0 * dx * dy,
    ]
    boundary_flux = sum(face_fluxes, Fraction(0))
    volume_integral = divergence * volume
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "divergence theorem for diagonal linear fields on axis-aligned boxes",
        "difficulty": difficulty,
        "problem": (
            f"For F(x,y,z)=({_render(a)}x,{_render(b)}y,{_render(c)}z) on "
            f"B=[{x0},{x1}]×[{y0},{y1}]×[{z0},{z1}], evaluate the outward "
            "boundary flux and the volume integral of div F."
        ),
        "steps": [
            f"div F = {_render(a)}+({_render(b)})+({_render(c)}) = {_render(divergence)}.",
            f"Add the six oriented face fluxes to obtain {_render(boundary_flux)}.",
            f"Volume integral = {_render(divergence)}×{volume} = {_render(volume_integral)}.",
        ],
        "answer": (
            f"boundary_flux={_render(boundary_flux)}; "
            f"volume_integral={_render(volume_integral)}; "
            f"equal={str(boundary_flux == volume_integral).lower()}"
        ),
        "answer_type": "expression",
        "ingredients": {
            "topic": TOPIC,
            "field_coefficients": [_pair(value) for value in coefficients],
            "box_bounds": bounds,
            "divergence": _pair(divergence),
            "face_fluxes": [_pair(value) for value in face_fluxes],
            "boundary_flux": _render(boundary_flux),
            "volume_integral": _render(volume_integral),
        },
        "verifier": VERIFIER,
    }


def build_divergence_box_fields(rng: random.Random, difficulty: int):
    d = difficulty
    x0 = rng.randint(-3 * d, 3 * d)
    x1 = x0 + rng.randint(1, 3 * d)
    y0 = rng.randint(-3 * d, 3 * d)
    y1 = y0 + rng.randint(1, 3 * d)
    z0 = rng.randint(-3 * d, 3 * d)
    z1 = z0 + rng.randint(1, 3 * d)
    coefficients = [
        Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d))
        for _ in range(3)
    ]
    fields = _canonical(0, d, coefficients, [x0, x1, y0, y1, z0, z1])
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_divergence_box({
        **fields,
        "id": f"university-{TOPIC}-0-{d}",
        "seed": 0,
    })


def verify_divergence_box(problem: dict) -> bool:
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
        raw_bounds = data.get("box_bounds")
        if (
            not isinstance(raw_bounds, list)
            or len(raw_bounds) != 6
            or any(not isinstance(value, int) or isinstance(value, bool) for value in raw_bounds)
        ):
            return False
        x0, x1, y0, y1, z0, z1 = raw_bounds
        d = difficulty
        for left, right in ((x0, x1), (y0, y1), (z0, z1)):
            if not (-3 * d <= left <= 3 * d and 1 <= right - left <= 3 * d):
                return False
        raw_coefficients = data.get("field_coefficients")
        if not isinstance(raw_coefficients, list) or len(raw_coefficients) != 3:
            return False
        coefficients = [
            _read_pair(pair, max_abs=2 * d, max_denominator=d)
            for pair in raw_coefficients
        ]
        return problem == _canonical(seed, difficulty, coefficients, raw_bounds)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
