"""Bounded exact separable power-law first-order ODE generator.

Supported family:
    y' = c * x**m * y**n, y(x0) = y0
with rational c, x0, y0, integer 0 <= m <= 3, and integer 0 <= n <= 2.
For n=2 the returned local solution is valid only where its denominator
is nonzero. This is not a general separable-ODE solver.
"""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "separable_first_order_ODEs"
MAX_SEED = (2**31) - 1
MAX_ABS_INPUT_NUMERATOR = 10
MAX_INPUT_DENOMINATOR = 5
MAX_ABS_DERIVED_NUMERATOR = 1_000_000
MAX_DERIVED_DENOMINATOR = 1_000_000
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 5


class SeparableODEInputError(ValueError):
    """Raised when separable ODE ingredients exceed the explicit input budget."""


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _format(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _read_input_pair(value: Any, field: str, difficulty: int) -> Fraction:
    if not isinstance(value, list) or len(value) != 2:
        raise SeparableODEInputError(f"{field} must be a rational [numerator, denominator] pair")
    numerator, denominator = value
    if not _is_int(numerator) or not _is_int(denominator):
        raise SeparableODEInputError(f"{field} numerator and denominator must be integers")
    if denominator <= 0:
        raise SeparableODEInputError(f"{field} denominator must be positive")
    if abs(numerator) > MAX_ABS_INPUT_NUMERATOR:
        raise SeparableODEInputError(f"{field} numerator exceeds {MAX_ABS_INPUT_NUMERATOR}")
    if denominator > MAX_INPUT_DENOMINATOR:
        raise SeparableODEInputError(f"{field} denominator exceeds {MAX_INPUT_DENOMINATOR}")
    if abs(numerator) > 2 * difficulty or denominator > difficulty:
        raise SeparableODEInputError(f"{field} exceeds difficulty {difficulty} rational bounds")
    return Fraction(numerator, denominator)


def _read_derived_pair(value: Any, field: str) -> Fraction:
    if not isinstance(value, list) or len(value) != 2:
        raise SeparableODEInputError(f"{field} must be a rational pair")
    numerator, denominator = value
    if (not _is_int(numerator) or not _is_int(denominator)
            or denominator <= 0
            or abs(numerator) > MAX_ABS_DERIVED_NUMERATOR
            or denominator > MAX_DERIVED_DENOMINATOR):
        raise SeparableODEInputError(f"{field} exceeds the derived rational budget")
    return Fraction(numerator, denominator)


def _max_x_power(difficulty: int) -> int:
    return min(3, difficulty - 1)


def _max_y_power(difficulty: int) -> int:
    return min(2, (difficulty - 1) // 2)


def _derive_solution(
    coefficient: Fraction,
    x_power: int,
    y_power: int,
    initial_x: Fraction,
    initial_y: Fraction,
) -> dict[str, Any]:
    power = x_power + 1
    rate = coefficient / power
    initial_x_power = initial_x ** power
    if y_power == 0:
        return {
            "kind": "polynomial",
            "power": power,
            "constant": _pair(initial_y - rate * initial_x_power),
            "coefficient": _pair(rate),
        }
    if y_power == 1:
        return {
            "kind": "exponential",
            "power": power,
            "initial_value": _pair(initial_y),
            "rate": _pair(rate),
            "initial_power": _pair(initial_x_power),
        }
    return {
        "kind": "reciprocal",
        "power": power,
        "numerator": _pair(initial_y),
        "denominator_constant": _pair(1 + rate * initial_y * initial_x_power),
        "denominator_coefficient": _pair(-rate * initial_y),
    }


def _render_fields(
    coefficient: Fraction,
    x_power: int,
    y_power: int,
    initial_x: Fraction,
    initial_y: Fraction,
    solution: dict[str, Any],
    difficulty: int,
) -> dict[str, Any]:
    power = x_power + 1
    common_problem = (
        f"Solve y'=({_format(coefficient)})x^{x_power}y^{y_power} "
        f"with initial condition y({_format(initial_x)})={_format(initial_y)}."
    )
    if y_power == 0:
        constant = Fraction(*solution["constant"])
        rate = Fraction(*solution["coefficient"])
        answer = f"y(x) = ({_format(constant)}) + ({_format(rate)})x^{power}"
        steps = [
            "Separate variables: dy = c*x^m dx.",
            f"Integrate: y = (c/{power})x^{power} + C.",
            f"Apply y(x0)=y0 to obtain C={_format(constant)} and the stated polynomial solution.",
            "Differentiate the expression and verify y'=c*x^m and y(x0)=y0 exactly.",
        ]
        domain_note = "The polynomial solution is defined for every real x."
    elif y_power == 1:
        rate = Fraction(*solution["rate"])
        initial_power = Fraction(*solution["initial_power"])
        answer = (
            f"y(x) = ({_format(initial_y)}) exp("
            f"({_format(rate)})(x^{power} - ({_format(initial_x)})^{power}))"
        )
        steps = [
            "Near the positive initial value, separate variables: dy/y = c*x^m dx.",
            f"Integrate: ln(y/y0) = (c/{power})(x^{power}-x0^{power}).",
            "Exponentiate and apply the initial condition to obtain the displayed solution.",
            "Differentiate the exponential and verify y'=c*x^m*y and y(x0)=y0 exactly.",
        ]
        domain_note = "The exponential solution is defined for every real x."
    else:
        numerator = Fraction(*solution["numerator"])
        denominator_constant = Fraction(*solution["denominator_constant"])
        denominator_coefficient = Fraction(*solution["denominator_coefficient"])
        answer = (
            f"y(x) = ({_format(numerator)}) / "
            f"(({_format(denominator_constant)}) + "
            f"({_format(denominator_coefficient)})x^{power})"
        )
        steps = [
            "Near the positive initial value, separate variables: y^(-2)dy = c*x^m dx.",
            f"Integrate: -1/y + 1/y0 = (c/{power})(x^{power}-x0^{power}).",
            "Rearrange to the displayed reciprocal solution.",
            "Differentiate the reciprocal and verify y'=c*x^m*y^2 and y(x0)=y0 exactly.",
        ]
        domain_note = (
            "This is the local solution on any connected interval containing x0 "
            "where its displayed denominator is nonzero."
        )
    return {
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "Separable power-law first-order ODEs with rational initial data",
        "difficulty": difficulty,
        "problem": common_problem + " Give the exact local solution.",
        "steps": steps,
        "answer": answer,
        "answer_type": "closed_form_exact_rational_coefficients",
        "ingredients": {
            "topic": TOPIC,
            "coefficient": _pair(coefficient),
            "x_power": x_power,
            "y_power": y_power,
            "initial_x": _pair(initial_x),
            "initial_y": _pair(initial_y),
            "solution": solution,
        },
        "verifier": "independent_separable_ode_derivative_identity_and_initial_value",
        "domain_note": domain_note,
    }


def _verify_solution_identity(
    coefficient: Fraction,
    x_power: int,
    y_power: int,
    initial_x: Fraction,
    initial_y: Fraction,
    solution: Any,
) -> bool:
    """Check derivative and initial-value identities using exact rational algebra."""
    if not isinstance(solution, dict):
        return False
    power = x_power + 1
    if not _is_int(solution.get("power")) or solution.get("power") != power:
        return False
    initial_x_power = initial_x ** power
    if y_power == 0:
        if set(solution) != {"kind", "power", "constant", "coefficient"}:
            return False
        if solution.get("kind") != "polynomial" or solution.get("power") != power:
            return False
        constant = _read_derived_pair(solution.get("constant"), "solution.constant")
        leading = _read_derived_pair(solution.get("coefficient"), "solution.coefficient")
        # y=C+L*x^p: y'=p*L*x^(p-1), so p*L must equal c.
        return leading * power == coefficient and constant + leading * initial_x_power == initial_y

    if y_power == 1:
        if set(solution) != {"kind", "power", "initial_value", "rate", "initial_power"}:
            return False
        if solution.get("kind") != "exponential" or solution.get("power") != power:
            return False
        base = _read_derived_pair(solution.get("initial_value"), "solution.initial_value")
        rate = _read_derived_pair(solution.get("rate"), "solution.rate")
        stored_initial_power = _read_derived_pair(solution.get("initial_power"), "solution.initial_power")
        # y=B*exp(r*(x^p-x0^p)): y'=r*p*x^(p-1)*y.
        return (
            base == initial_y
            and rate * power == coefficient
            and stored_initial_power == initial_x_power
            and rate * (initial_x_power - stored_initial_power) == 0
        )

    if set(solution) != {
        "kind", "power", "numerator", "denominator_constant", "denominator_coefficient"
    }:
        return False
    if solution.get("kind") != "reciprocal" or solution.get("power") != power:
        return False
    numerator = _read_derived_pair(solution.get("numerator"), "solution.numerator")
    denominator_constant = _read_derived_pair(
        solution.get("denominator_constant"), "solution.denominator_constant"
    )
    denominator_coefficient = _read_derived_pair(
        solution.get("denominator_coefficient"), "solution.denominator_coefficient"
    )
    # y=N/(A+B*x^p). At x0 the denominator must be 1; its derivative
    # is B*p*x^(p-1)=-c*y0*x^(p-1), yielding y'=c*x^(p-1)*y^2.
    return (
        numerator == initial_y
        and denominator_coefficient * power == -coefficient * initial_y
        and denominator_constant + denominator_coefficient * initial_x_power == 1
    )


def build_separable_fields(rng: random.Random, difficulty: int = 1):
    """Build a deterministic bounded y'=c*x^m*y^n problem."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    if not _is_int(difficulty) or not MIN_DIFFICULTY <= difficulty <= MAX_DIFFICULTY:
        raise ValueError("difficulty must be an integer from 1 through 5")

    def rational_nonzero() -> Fraction:
        numerator = 0
        while numerator == 0:
            numerator = rng.randint(-2 * difficulty, 2 * difficulty)
        return Fraction(numerator, rng.randint(1, difficulty))

    coefficient = rational_nonzero()
    initial_x = Fraction(rng.randint(-2 * difficulty, 2 * difficulty), rng.randint(1, difficulty))
    initial_y = Fraction(rng.randint(1, 2 * difficulty), rng.randint(1, difficulty))
    x_power = rng.randint(0, _max_x_power(difficulty))
    y_power = rng.randint(0, _max_y_power(difficulty))
    solution = _derive_solution(coefficient, x_power, y_power, initial_x, initial_y)
    fields = _render_fields(
        coefficient, x_power, y_power, initial_x, initial_y, solution, difficulty
    )
    return fields, lambda: _verify_solution_identity(
        coefficient, x_power, y_power, initial_x, initial_y, solution
    )


def verify_separable_problem(problem: Any) -> bool:
    """Independently verify exact derivative/initial-value identities and full object."""
    required = {
        "grade_band", "topic", "subtopic", "difficulty", "problem", "steps",
        "answer", "answer_type", "ingredients", "verifier", "domain_note", "id", "seed",
    }
    try:
        if not isinstance(problem, dict) or set(problem) != required:
            return False
        seed = problem.get("seed")
        difficulty = problem.get("difficulty")
        if not _is_int(seed) or not 0 <= seed <= MAX_SEED:
            return False
        if not _is_int(difficulty) or not MIN_DIFFICULTY <= difficulty <= MAX_DIFFICULTY:
            return False
        if problem.get("id") != f"university-{TOPIC}-{seed}-{difficulty}":
            return False

        ingredients = problem.get("ingredients")
        expected_keys = {
            "topic", "coefficient", "x_power", "y_power", "initial_x", "initial_y", "solution"
        }
        if not isinstance(ingredients, dict) or set(ingredients) != expected_keys:
            return False
        if ingredients.get("topic") != TOPIC:
            return False
        coefficient = _read_input_pair(ingredients.get("coefficient"), "coefficient", difficulty)
        initial_x = _read_input_pair(ingredients.get("initial_x"), "initial_x", difficulty)
        initial_y = _read_input_pair(ingredients.get("initial_y"), "initial_y", difficulty)
        if coefficient == 0 or initial_y <= 0:
            return False
        x_power = ingredients.get("x_power")
        y_power = ingredients.get("y_power")
        if not _is_int(x_power) or not 0 <= x_power <= _max_x_power(difficulty):
            return False
        if not _is_int(y_power) or not 0 <= y_power <= _max_y_power(difficulty):
            return False
        if not _verify_solution_identity(
            coefficient, x_power, y_power, initial_x, initial_y, ingredients.get("solution")
        ):
            return False

        canonical_solution = _derive_solution(
            coefficient, x_power, y_power, initial_x, initial_y
        )
        if ingredients.get("solution") != canonical_solution:
            return False
        expected = _render_fields(
            coefficient, x_power, y_power, initial_x, initial_y, canonical_solution, difficulty
        )
        expected.update(id=f"university-{TOPIC}-{seed}-{difficulty}", seed=seed)
        return problem == expected
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False
