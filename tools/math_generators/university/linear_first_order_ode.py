"""Bounded exact solutions for linear constant-coefficient first-order ODEs.

Supported family: y' = a*y + b with y(0) = y0, where a, b, and y0 are
small exact rational numbers. The generated family is not a general ODE solver.
"""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "linear_constant_coefficient_first_order_ODEs"
MAX_ABS_INPUT_NUMERATOR = 10
MAX_INPUT_DENOMINATOR = 5
MAX_SEED = (2**31) - 1
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 5


class LinearODEInputError(ValueError):
    """Raised when ODE ingredients exceed the explicit rational-input contract."""


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _format(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _read_input_pair(value: Any, field: str, difficulty: int) -> Fraction:
    if not isinstance(value, list) or len(value) != 2:
        raise LinearODEInputError(f"{field} must be a rational [numerator, denominator] pair")
    numerator, denominator = value
    if not _is_int(numerator) or not _is_int(denominator):
        raise LinearODEInputError(f"{field} numerator and denominator must be integers")
    if denominator <= 0:
        raise LinearODEInputError(f"{field} denominator must be positive")
    if abs(numerator) > MAX_ABS_INPUT_NUMERATOR:
        raise LinearODEInputError(f"{field} numerator exceeds {MAX_ABS_INPUT_NUMERATOR}")
    if denominator > MAX_INPUT_DENOMINATOR:
        raise LinearODEInputError(f"{field} denominator exceeds {MAX_INPUT_DENOMINATOR}")
    if abs(numerator) > 2 * difficulty or denominator > difficulty:
        raise LinearODEInputError(f"{field} exceeds difficulty {difficulty} coefficient bounds")
    return Fraction(numerator, denominator)


def _read_solution_pair(value: Any, field: str) -> Fraction:
    if not isinstance(value, list) or len(value) != 2:
        raise LinearODEInputError(f"{field} must be a rational pair")
    numerator, denominator = value
    if (not _is_int(numerator) or not _is_int(denominator)
            or denominator <= 0 or abs(numerator) > 1000 or denominator > 1000):
        raise LinearODEInputError(f"{field} is outside the derived-solution rational budget")
    return Fraction(numerator, denominator)


def _derive_solution(a: Fraction, b: Fraction, y0: Fraction) -> dict[str, Any]:
    if a == 0:
        return {"kind": "affine", "constant": _pair(y0), "linear": _pair(b)}
    return {
        "kind": "exponential_affine",
        "rate": _pair(a),
        "exponential_coefficient": _pair(y0 + b / a),
        "constant": _pair(-b / a),
    }


def _render_fields(
    a: Fraction,
    b: Fraction,
    y0: Fraction,
    difficulty: int,
    solution: dict[str, Any],
) -> dict[str, Any]:
    if a == 0:
        answer = f"y(t) = {_format(y0)} + ({_format(b)})t"
        steps = [
            "Because a=0, the differential equation reduces to y'=b.",
            f"Integrate and apply y(0)={_format(y0)} to obtain y(t)={_format(y0)}+({_format(b)})t.",
            "Differentiate the result and substitute it into y'=a*y+b to verify the identity and initial value.",
        ]
    else:
        exponential_coefficient = Fraction(*solution["exponential_coefficient"])
        constant = Fraction(*solution["constant"])
        answer = (
            f"y(t) = ({_format(exponential_coefficient)})e^({_format(a)}t) "
            f"+ ({_format(constant)})"
        )
        steps = [
            f"Since a={_format(a)} is nonzero, the equilibrium value is -b/a={_format(constant)}.",
            f"Shift by the equilibrium: y(t)+b/a = ({_format(y0 + b / a)})e^({_format(a)}t).",
            f"Therefore y(t)=({_format(exponential_coefficient)})e^({_format(a)}t)+({_format(constant)}).",
            "Differentiate and substitute into y'=a*y+b; also check y(0)=y0 exactly.",
        ]
    return {
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "Linear constant-coefficient first-order ODEs with rational data",
        "difficulty": difficulty,
        "problem": f"Solve y'=({_format(a)})y+({_format(b)}) with initial condition y(0)={_format(y0)}.",
        "steps": steps,
        "answer": answer,
        "answer_type": "closed_form_exact_rational_coefficients",
        "ingredients": {
            "topic": TOPIC,
            "a": _pair(a),
            "b": _pair(b),
            "initial_value": _pair(y0),
            "solution": solution,
        },
        "verifier": "independent_symbolic_ode_identity_and_initial_condition",
    }


def build_linear_ode_fields(rng: random.Random, difficulty: int = 1):
    """Create reproducible y'=a*y+b problems with exact rational parameters."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    if not _is_int(difficulty) or not MIN_DIFFICULTY <= difficulty <= MAX_DIFFICULTY:
        raise ValueError("difficulty must be an integer from 1 through 5")

    def sample() -> Fraction:
        return Fraction(rng.randint(-2 * difficulty, 2 * difficulty), rng.randint(1, difficulty))

    a, b, y0 = sample(), sample(), sample()
    solution = _derive_solution(a, b, y0)
    fields = _render_fields(a, b, y0, difficulty, solution)
    return fields, lambda: verify_linear_ode_problem(fields)


def verify_linear_ode_problem(problem: Any) -> bool:
    """Independently validate the closed-form ODE identity and initial condition."""
    required = {
        "grade_band", "topic", "subtopic", "difficulty", "problem", "steps",
        "answer", "answer_type", "ingredients", "verifier", "id", "seed",
    }
    try:
        if not isinstance(problem, dict) or set(problem) != required:
            return False
        seed, difficulty = problem.get("seed"), problem.get("difficulty")
        if (not _is_int(seed) or not 0 <= seed <= MAX_SEED
                or not _is_int(difficulty) or not MIN_DIFFICULTY <= difficulty <= MAX_DIFFICULTY):
            return False
        if problem.get("id") != f"university-{TOPIC}-{seed}-{difficulty}":
            return False
        ingredients = problem.get("ingredients")
        expected_ingredients = {"topic", "a", "b", "initial_value", "solution"}
        if not isinstance(ingredients, dict) or set(ingredients) != expected_ingredients:
            return False
        if ingredients.get("topic") != TOPIC:
            return False

        a = _read_input_pair(ingredients.get("a"), "a", difficulty)
        b = _read_input_pair(ingredients.get("b"), "b", difficulty)
        y0 = _read_input_pair(ingredients.get("initial_value"), "initial_value", difficulty)
        solution = ingredients.get("solution")
        if not isinstance(solution, dict):
            return False

        # Recompute and verify the symbolic solution from the differential equation.
        if a == 0:
            if set(solution) != {"kind", "constant", "linear"} or solution.get("kind") != "affine":
                return False
            constant = _read_solution_pair(solution.get("constant"), "solution.constant")
            linear = _read_solution_pair(solution.get("linear"), "solution.linear")
            # For y=c0+c1*t, y'=c1 and a*y+b=a*c0+b.
            if constant != y0 or linear != b or linear != a * constant + b:
                return False
            canonical_solution = {"kind": "affine", "constant": _pair(constant), "linear": _pair(linear)}
        else:
            if set(solution) != {"kind", "rate", "exponential_coefficient", "constant"}:
                return False
            if solution.get("kind") != "exponential_affine":
                return False
            rate = _read_solution_pair(solution.get("rate"), "solution.rate")
            exponential = _read_solution_pair(
                solution.get("exponential_coefficient"), "solution.exponential_coefficient"
            )
            constant = _read_solution_pair(solution.get("constant"), "solution.constant")
            # For y=c1*exp(rate*t)+c0, match exponent, constant and y(0).
            if rate != a or a * constant + b != 0 or exponential + constant != y0:
                return False
            canonical_solution = {
                "kind": "exponential_affine",
                "rate": _pair(rate),
                "exponential_coefficient": _pair(exponential),
                "constant": _pair(constant),
            }

        expected = _render_fields(a, b, y0, difficulty, canonical_solution)
        expected.update(id=f"university-{TOPIC}-{seed}-{difficulty}", seed=seed)
        return problem == expected
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
