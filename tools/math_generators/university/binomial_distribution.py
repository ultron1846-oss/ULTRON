"""Exact point probabilities, mean, and variance for bounded binomial laws."""
from __future__ import annotations

import math
import random
from fractions import Fraction
from typing import Any

TOPIC = "binomial_distribution_point_probabilities"
VERIFIER = "independent_binomial_probability_and_moments_check"


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _read_pair(value: Any, *, max_abs: int, max_denominator: int) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(part, int) or isinstance(part, bool) for part in value)
    ):
        raise ValueError("probability must be an integer numerator/denominator pair")
    numerator, denominator = value
    if abs(numerator) > max_abs or not 1 <= denominator <= max_denominator:
        raise ValueError("probability exceeds configured rational bounds")
    result = Fraction(numerator, denominator)
    if [result.numerator, result.denominator] != value:
        raise ValueError("probability pair must be reduced with positive denominator")
    return result


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _canonical(seed: int, difficulty: int, trials: int, successes: int, probability: Fraction) -> dict:
    point_probability = Fraction(math.comb(trials, successes)) * probability**successes * (1-probability)**(trials-successes)
    expectation = trials * probability
    variance = trials * probability * (1-probability)
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "point probability and moments of a binomial distribution",
        "difficulty": difficulty,
        "problem": (
            f"Let X~Binomial(n={trials}, p={_render(probability)}). "
            f"Find P(X={successes}), E[X], and Var(X)."
        ),
        "steps": [
            f"P(X={successes})=C({trials},{successes})p^{successes}(1−p)^{trials-successes}={_render(point_probability)}.",
            f"E[X]=np={trials}×{_render(probability)}={_render(expectation)}.",
            f"Var(X)=np(1−p)={_render(variance)}.",
        ],
        "answer": (
            f"P(X={successes})={_render(point_probability)}; "
            f"E[X]={_render(expectation)}; "
            f"Var(X)={_render(variance)}"
        ),
        "answer_type": "expression",
        "ingredients": {
            "topic": TOPIC,
            "trials": trials,
            "successes": successes,
            "success_probability": _pair(probability),
            "point_probability": _pair(point_probability),
            "expectation": _pair(expectation),
            "variance": _pair(variance),
        },
        "verifier": VERIFIER,
    }


def build_binomial_distribution_fields(rng: random.Random, difficulty: int):
    d = difficulty
    probability = Fraction(rng.randint(1, 4 * d - 1), rng.randint(2, 4 * d))
    while not 0 < probability < 1:
        probability = Fraction(rng.randint(1, 4 * d - 1), rng.randint(2, 4 * d))
    trials = rng.randint(1, 5 * d)
    successes = rng.randint(0, trials)
    fields = _canonical(0, d, trials, successes, probability)
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_binomial_distribution({
        **fields,
        "id": f"university-{TOPIC}-0-{d}",
        "seed": 0,
    })


def verify_binomial_distribution(problem: dict) -> bool:
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
        trials = data.get("trials")
        successes = data.get("successes")
        d = difficulty
        if not isinstance(trials, int) or isinstance(trials, bool) or not 1 <= trials <= 5*d:
            return False
        if not isinstance(successes, int) or isinstance(successes, bool) or not 0 <= successes <= trials:
            return False
        probability = _read_pair(
            data.get("success_probability"),
            max_abs=4*d-1,
            max_denominator=4*d,
        )
        if not 0 < probability < 1:
            return False
        return problem == _canonical(seed, difficulty, trials, successes, probability)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
