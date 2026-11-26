"""Deterministic-seed Level 1 math problem generation."""
from __future__ import annotations
import random
from fractions import Fraction

DIFFICULTIES = ("easy", "medium", "hard")

def _fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"

def generate_problem(rng: random.Random, difficulty: str = "easy") -> dict:
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"difficulty must be one of {DIFFICULTIES}")
    level = DIFFICULTIES.index(difficulty)
    if rng.choice(("arithmetic", "linear")) == "arithmetic":
        limit = (20, 100, 500)[level]
        a, b = rng.randint(1, limit), rng.randint(1, limit)
        op = rng.choice(("+", "-", "*", "/"))
        if op == "/":
            b = rng.randint(1, max(2, limit // 5))
            a = b * rng.randint(1, max(2, limit // b))
        if op == "-" and b > a:
            a, b = b, a
        result = {"+": a + b, "-": a - b, "*": a * b, "/": Fraction(a, b)}[op]
        answer = Fraction(result)
        expression = f"{a} {op} {b}"
        return {"kind": "arithmetic", "difficulty": difficulty, "prompt": expression,
                "expression": expression, "answer": _fraction_text(answer),
                "steps": [f"Compute {a} {op} {b}.", f"Result = {_fraction_text(answer)}."]}
    coef_limit, const_limit = ((5, 10), (20, 50), (100, 250))[level]
    x = rng.randint(-coef_limit, coef_limit)
    a = rng.choice([v for v in range(-coef_limit, coef_limit + 1) if v != 0])
    b = rng.randint(-const_limit, const_limit)
    c = a * x + b
    prompt = f"{a}*x {b:+d} = {c}"
    return {"kind": "linear", "difficulty": difficulty, "prompt": prompt,
            "a": a, "b": b, "c": c, "answer": str(x),
            "steps": [f"Subtract {b} from both sides: {a}*x = {c-b}.",
                     f"Divide by {a}: x = {x}."]}
