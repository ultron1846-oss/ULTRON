"""Exact binomial-distribution probabilities with bounded trial counts."""
from __future__ import annotations

import math
import random
from fractions import Fraction
from typing import Any

TOPIC = "binomial_distribution_exact_probabilities"
VERIFIER = "independent_exact_binomial_mass_and_normalization_check"


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _read_input_pair(value: Any, *, max_abs: int, max_denominator: int) -> Fraction:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(part, int) or isinstance(part, bool) for part in value)
    ):
        raise ValueError("probability inputs must be integer rational pairs")
    numerator, denominator = value
    if abs(numerator) > max_abs or not 1 <= denominator <= max_denominator:
        raise ValueError("probability input exceeds the difficulty bound")
    result = Fraction(numerator, denominator)
    if [result.numerator, result.denominator] != value:
        raise ValueError("probability rational pair must be reduced")
    return result


def _render(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _canonical(seed: int, difficulty: int, trials: int, probability: Fraction, selected: int) -> dict:
    masses = [
        Fraction(math.comb(trials, k)) * probability ** k * (1 - probability) ** (trials - k)
        for k in range(trials + 1)
    ]
    chosen = masses[selected]
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "exact probability mass function of a bounded binomial random variable",
        "difficulty": difficulty,
        "problem": (
            f"A binomial random variable has n={trials} independent trials and success "
            f"probability p={_render(probability)}. Find P(X={selected}) exactly."
        ),
        "steps": [
            "Use P(X=k)=C(n,k)*p^k*(1-p)^(n-k).",
            "Substitute the trial count, selected successes, and exact rational p.",
            "The complete probability mass function sums to one by the binomial theorem.",
        ],
        "answer": _render(chosen),
        "answer_type": "rational",
        "ingredients": {
            "topic": TOPIC,
            "trials": trials,
            "success_probability": _pair(probability),
            "selected_successes": selected,
            "probabilities": [_pair(value) for value in masses],
            "probability_sum": _pair(sum(masses, Fraction(0))),
            "expected_successes": _pair(trials * probability),
        },
        "verifier": VERIFIER,
    }


def build_binomial_probability_fields(rng: random.Random, difficulty: int):
    d = difficulty
    trials = rng.randint(2, min(10, 2 * d))
    denominator = 2 * d
    numerators = [value for value in range(1, denominator) if math.gcd(value, denominator) == 1]
    probability = Fraction(rng.choice(numerators), denominator)
    selected = rng.randint(0, trials)
    fields = _canonical(0, d, trials, probability, selected)
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_binomial_probability({
        **fields, "id": f"university-{TOPIC}-0-{d}", "seed": 0
    })


def verify_binomial_probability(problem: dict) -> bool:
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
        selected = data.get("selected_successes")
        if not isinstance(trials, int) or isinstance(trials, bool) or not 2 <= trials <= min(10, 2 * difficulty):
            return False
        if not isinstance(selected, int) or isinstance(selected, bool) or not 0 <= selected <= trials:
            return False
        raw_probability = data.get("success_probability")
        if not isinstance(raw_probability, list) or len(raw_probability) != 2:
            return False
        probability = _read_input_pair(
            raw_probability,
            max_abs=2 * difficulty - 1,
            max_denominator=2 * difficulty,
        )
        if not 0 < probability < 1 or probability.denominator != 2 * difficulty:
            return False
        expected = _canonical(seed, difficulty, trials, probability, selected)
        return problem == expected and expected["ingredients"]["probability_sum"] == [1, 1]
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
