"""Exact rational complex-number arithmetic exercises."""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "complex_number_arithmetic"
VERIFIER = "independent_exact_complex_arithmetic_check"


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _read_pair(value: Any, *, max_abs: int | None = None, max_denominator: int | None = None) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(part, int) or isinstance(part, bool) for part in value)
    ):
        raise ValueError("complex components must be numerator/denominator pairs")
    numerator, denominator = value
    if denominator <= 0:
        raise ValueError("complex component denominator must be positive")
    if max_abs is not None and abs(numerator) > max_abs:
        raise ValueError("complex component numerator exceeds the configured bound")
    if max_denominator is not None and denominator > max_denominator:
        raise ValueError("complex component denominator exceeds the configured bound")
    result = Fraction(numerator, denominator)
    if [result.numerator, result.denominator] != value:
        raise ValueError("complex component pairs must be reduced")
    return result


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _pair_text(value: tuple[Fraction, Fraction]) -> str:
    return f"({_render(value[0])},{_render(value[1])})"


def _canonical(seed: int, difficulty: int, z: tuple[Fraction, Fraction], w: tuple[Fraction, Fraction]) -> dict:
    zr, zi = z
    wr, wi = w
    added = (zr + wr, zi + wi)
    product = (zr * wr - zi * wi, zr * wi + zi * wr)
    conjugate = (zr, -zi)
    norm_squared = zr * zr + zi * zi
    data = {
        "topic": TOPIC,
        "z": [_pair(zr), _pair(zi)],
        "w": [_pair(wr), _pair(wi)],
        "sum": [_pair(added[0]), _pair(added[1])],
        "product": [_pair(product[0]), _pair(product[1])],
        "conjugate_z": [_pair(conjugate[0]), _pair(conjugate[1])],
        "norm_squared_z": _pair(norm_squared),
    }
    problem = (
        f"Let z={_pair_text(z)} and w={_pair_text(w)}. Compute z+w, z·w, "
        "the complex conjugate of z, and |z|²."
    )
    answer = (
        f"z+w={_pair_text(added)}; z*w={_pair_text(product)}; "
        f"conjugate(z)={_pair_text(conjugate)}; |z|^2={_render(norm_squared)}"
    )
    steps = [
        "Add real and imaginary parts componentwise.",
        "Multiply using (a+bi)(c+di)=(ac−bd)+(ad+bc)i.",
        "Negate the imaginary component for the conjugate and compute a²+b² for the squared modulus.",
    ]
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "exact arithmetic, conjugation, and squared modulus in the complex numbers",
        "difficulty": difficulty,
        "problem": problem,
        "steps": steps,
        "answer": answer,
        "answer_type": "expression",
        "ingredients": data,
        "verifier": VERIFIER,
    }


def build_complex_arithmetic_fields(rng: random.Random, difficulty: int):
    d = difficulty
    component = lambda: Fraction(rng.randint(-2 * d, 2 * d), rng.randint(1, d))
    z = (component(), component())
    w = (component(), component())
    fields = _canonical(0, d, z, w)
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_complex_arithmetic({
        **fields,
        "id": f"university-{TOPIC}-0-{d}",
        "seed": 0,
    })


def verify_complex_arithmetic(problem: dict) -> bool:
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
        raw_z, raw_w = data.get("z"), data.get("w")
        if not isinstance(raw_z, list) or len(raw_z) != 2 or not isinstance(raw_w, list) or len(raw_w) != 2:
            return False
        d = difficulty
        z = tuple(_read_pair(pair, max_abs=2 * d, max_denominator=d) for pair in raw_z)
        w = tuple(_read_pair(pair, max_abs=2 * d, max_denominator=d) for pair in raw_w)
        return problem == _canonical(seed, difficulty, z, w)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
