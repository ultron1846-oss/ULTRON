"""Exact moments for bounded finite discrete distributions."""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "finite_discrete_distribution_expectation_variance"
VERIFIER = "independent_finite_distribution_moment_check"


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _read_pair(value: Any) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(part, int) or isinstance(part, bool) for part in value)
    ):
        raise ValueError("moment values must be integer numerator/denominator pairs")
    numerator, denominator = value
    if denominator <= 0:
        raise ValueError("moment denominator must be positive")
    result = Fraction(numerator, denominator)
    if [result.numerator, result.denominator] != value:
        raise ValueError("moment pairs must be reduced")
    return result


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _canonical(seed: int, difficulty: int, outcomes: tuple[int, int, int], weights: tuple[int, int, int]) -> dict:
    total = sum(weights)
    probabilities = tuple(Fraction(weight, total) for weight in weights)
    expectation = sum(
        (Fraction(outcome) * probability for outcome, probability in zip(outcomes, probabilities)),
        Fraction(0),
    )
    second_moment = sum(
        (Fraction(outcome * outcome) * probability for outcome, probability in zip(outcomes, probabilities)),
        Fraction(0),
    )
    variance = second_moment - expectation * expectation
    distribution = ", ".join(
        f"P(X={outcome})={_render(probability)}"
        for outcome, probability in zip(outcomes, probabilities)
    )
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "expectation and variance of a three-point finite discrete distribution",
        "difficulty": difficulty,
        "problem": f"A random variable X has support {list(outcomes)} with relative weights {list(weights)}. Find E[X], E[X^2], and Var(X).",
        "steps": [
            f"Normalize the relative weights: {distribution}.",
            f"E[X]={_render(expectation)} and E[X^2]={_render(second_moment)}.",
            f"Var(X)=E[X^2]−E[X]^2={_render(variance)}.",
        ],
        "answer": (
            f"E[X]={_render(expectation)}; "
            f"E[X^2]={_render(second_moment)}; "
            f"Var(X)={_render(variance)}"
        ),
        "answer_type": "expression",
        "ingredients": {
            "topic": TOPIC,
            "outcomes": list(outcomes),
            "relative_weights": list(weights),
            "total_weight": total,
            "probabilities": [_pair(value) for value in probabilities],
            "expectation": _pair(expectation),
            "second_moment": _pair(second_moment),
            "variance": _pair(variance),
        },
        "verifier": VERIFIER,
    }


def build_finite_distribution_moment_fields(rng: random.Random, difficulty: int):
    d = difficulty
    outcomes = tuple(sorted(rng.sample(range(-5 * d, 5 * d + 1), 3)))
    weights = tuple(rng.randint(1, 5 * d) for _ in range(3))
    fields = _canonical(0, d, outcomes, weights)
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_finite_distribution_moments({
        **fields,
        "id": f"university-{TOPIC}-0-{d}",
        "seed": 0,
    })


def verify_finite_distribution_moments(problem: dict) -> bool:
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
        outcomes = data.get("outcomes")
        weights = data.get("relative_weights")
        if not isinstance(outcomes, list) or len(outcomes) != 3:
            return False
        if not isinstance(weights, list) or len(weights) != 3:
            return False
        if any(not isinstance(x, int) or isinstance(x, bool) for x in outcomes + weights):
            return False
        d = difficulty
        if any(not -5 * d <= outcome <= 5 * d for outcome in outcomes):
            return False
        if not (outcomes[0] < outcomes[1] < outcomes[2]):
            return False
        if any(not 1 <= weight <= 5 * d for weight in weights):
            return False
        return problem == _canonical(seed, difficulty, tuple(outcomes), tuple(weights))
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
