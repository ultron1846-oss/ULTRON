"""Bounded exact-rational Green's theorem for axis-aligned rectangles.

Supported inputs are sparse bivariate rational polynomials P(x,y), Q(x,y)
and a non-degenerate axis-aligned rectangle with rational bounds. No symbolic
parser or general region integration is used.
"""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Any

TOPIC = "greens_theorem_rectangles"
MAX_DEGREE = 5
MAX_TERMS_PER_COMPONENT = 8
MAX_TOTAL_TERMS = 12
MAX_COEFFICIENT_NUMERATOR_ABS = 1000
MAX_COEFFICIENT_DENOMINATOR = 100
MAX_BOUND_NUMERATOR_ABS = 100
MAX_BOUND_DENOMINATOR = 20
MAX_EXACT_OPERATIONS = 256
SUPPORTED_ORIENTATIONS = ("counterclockwise", "clockwise")


class GreenTheoremInputError(ValueError):
    """Raised when a Green theorem problem exceeds the declared input contract."""


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _fraction_pair(value: Any, field: str, *, bound: bool = False) -> Fraction:
    if not isinstance(value, list) or len(value) != 2:
        raise GreenTheoremInputError(f"{field} must be a [numerator, denominator] pair")
    numerator, denominator = value
    if not _is_int(numerator) or not _is_int(denominator):
        raise GreenTheoremInputError(f"{field} numerator and denominator must be integers")
    if denominator <= 0:
        raise GreenTheoremInputError(f"{field} denominator must be positive")
    if bound:
        if abs(numerator) > MAX_BOUND_NUMERATOR_ABS:
            raise GreenTheoremInputError(f"{field} numerator exceeds the bound budget")
        if denominator > MAX_BOUND_DENOMINATOR:
            raise GreenTheoremInputError(f"{field} denominator exceeds the bound budget")
    else:
        if abs(numerator) > MAX_COEFFICIENT_NUMERATOR_ABS:
            raise GreenTheoremInputError(f"{field} numerator exceeds the coefficient budget")
        if denominator > MAX_COEFFICIENT_DENOMINATOR:
            raise GreenTheoremInputError(f"{field} denominator exceeds the coefficient budget")
    return Fraction(numerator, denominator)


def _parse_polynomial(value: Any, field: str) -> list[tuple[Fraction, int, int]]:
    if not isinstance(value, list):
        raise GreenTheoremInputError(f"{field} must be a list of sparse polynomial terms")
    if len(value) > MAX_TERMS_PER_COMPONENT:
        raise GreenTheoremInputError(f"{field} exceeds the {MAX_TERMS_PER_COMPONENT}-term limit")

    parsed: list[tuple[Fraction, int, int]] = []
    seen: set[tuple[int, int]] = set()
    for index, term in enumerate(value):
        if not isinstance(term, dict) or set(term) != {"coefficient", "x_power", "y_power"}:
            raise GreenTheoremInputError(
                f"{field}[{index}] must contain coefficient, x_power, and y_power only"
            )
        coefficient = _fraction_pair(term["coefficient"], f"{field}[{index}].coefficient")
        x_power, y_power = term["x_power"], term["y_power"]
        if not _is_int(x_power) or not _is_int(y_power):
            raise GreenTheoremInputError(f"{field}[{index}] powers must be integers")
        if x_power < 0 or y_power < 0:
            raise GreenTheoremInputError(f"{field}[{index}] powers must be non-negative")
        if x_power + y_power > MAX_DEGREE:
            raise GreenTheoremInputError(f"{field}[{index}] total degree exceeds {MAX_DEGREE}")
        if coefficient == 0:
            raise GreenTheoremInputError(f"{field}[{index}] coefficient must be non-zero")
        powers = (x_power, y_power)
        if powers in seen:
            raise GreenTheoremInputError(f"{field} contains a duplicate monomial")
        seen.add(powers)
        parsed.append((coefficient, x_power, y_power))
    return parsed


def _validated_input(data: Any) -> tuple[
    list[tuple[Fraction, int, int]],
    list[tuple[Fraction, int, int]],
    Fraction,
    Fraction,
    Fraction,
    Fraction,
    str,
]:
    if not isinstance(data, dict):
        raise GreenTheoremInputError("Green theorem ingredients must be an object")
    expected = {"topic", "P", "Q", "x_bounds", "y_bounds", "orientation"}
    if set(data) != expected:
        raise GreenTheoremInputError("Green theorem ingredients contain missing or unsupported fields")
    if data["topic"] != TOPIC:
        raise GreenTheoremInputError("unsupported Green theorem topic")
    p_terms = _parse_polynomial(data["P"], "P")
    q_terms = _parse_polynomial(data["Q"], "Q")
    total_terms = len(p_terms) + len(q_terms)
    if total_terms > MAX_TOTAL_TERMS:
        raise GreenTheoremInputError(f"combined polynomial term count exceeds {MAX_TOTAL_TERMS}")
    estimated_operations = total_terms * 4 * (MAX_DEGREE + 1)
    if estimated_operations > MAX_EXACT_OPERATIONS:
        raise GreenTheoremInputError("exact-arithmetic operation budget exceeded")

    x_bounds, y_bounds = data["x_bounds"], data["y_bounds"]
    if not isinstance(x_bounds, list) or len(x_bounds) != 2:
        raise GreenTheoremInputError("x_bounds must contain exactly two rational bounds")
    if not isinstance(y_bounds, list) or len(y_bounds) != 2:
        raise GreenTheoremInputError("y_bounds must contain exactly two rational bounds")
    x0 = _fraction_pair(x_bounds[0], "x_bounds[0]", bound=True)
    x1 = _fraction_pair(x_bounds[1], "x_bounds[1]", bound=True)
    y0 = _fraction_pair(y_bounds[0], "y_bounds[0]", bound=True)
    y1 = _fraction_pair(y_bounds[1], "y_bounds[1]", bound=True)
    if x0 >= x1 or y0 >= y1:
        raise GreenTheoremInputError("rectangle bounds must be strictly increasing and non-degenerate")
    orientation = data["orientation"]
    if orientation not in SUPPORTED_ORIENTATIONS:
        raise GreenTheoremInputError("orientation must be counterclockwise or clockwise")
    return p_terms, q_terms, x0, x1, y0, y1, orientation


def _integral_power(lower: Fraction, upper: Fraction, power: int) -> Fraction:
    return (upper ** (power + 1) - lower ** (power + 1)) / (power + 1)


def _integrate_p_on_horizontal_edge(
    terms: list[tuple[Fraction, int, int]],
    y_value: Fraction,
    x_start: Fraction,
    x_end: Fraction,
) -> Fraction:
    total = Fraction(0)
    for coefficient, x_power, y_power in terms:
        total += coefficient * (y_value ** y_power) * _integral_power(x_start, x_end, x_power)
    return total


def _integrate_q_on_vertical_edge(
    terms: list[tuple[Fraction, int, int]],
    x_value: Fraction,
    y_start: Fraction,
    y_end: Fraction,
) -> Fraction:
    total = Fraction(0)
    for coefficient, x_power, y_power in terms:
        total += coefficient * (x_value ** x_power) * _integral_power(y_start, y_end, y_power)
    return total


def compute_boundary_integral(data: Any) -> Fraction:
    """Integrate P dx + Q dy around the oriented four rectangle edges."""
    p_terms, q_terms, x0, x1, y0, y1, orientation = _validated_input(data)
    bottom = _integrate_p_on_horizontal_edge(p_terms, y0, x0, x1)
    right = _integrate_q_on_vertical_edge(q_terms, x1, y0, y1)
    top = _integrate_p_on_horizontal_edge(p_terms, y1, x1, x0)
    left = _integrate_q_on_vertical_edge(q_terms, x0, y1, y0)
    counterclockwise = bottom + right + top + left
    return counterclockwise if orientation == "counterclockwise" else -counterclockwise


def compute_area_integral(data: Any) -> Fraction:
    """Integrate dQ/dx - dP/dy over the rectangle using separated powers."""
    p_terms, q_terms, x0, x1, y0, y1, orientation = _validated_input(data)
    curl_terms: dict[tuple[int, int], Fraction] = {}
    for coefficient, x_power, y_power in q_terms:
        if x_power:
            key = (x_power - 1, y_power)
            curl_terms[key] = curl_terms.get(key, Fraction(0)) + coefficient * x_power
    for coefficient, x_power, y_power in p_terms:
        if y_power:
            key = (x_power, y_power - 1)
            curl_terms[key] = curl_terms.get(key, Fraction(0)) - coefficient * y_power

    area = Fraction(0)
    for (x_power, y_power), coefficient in curl_terms.items():
        if coefficient:
            area += (
                coefficient
                * _integral_power(x0, x1, x_power)
                * _integral_power(y0, y1, y_power)
            )
    return area if orientation == "counterclockwise" else -area


def calculate_green_integrals(data: Any) -> tuple[Fraction, Fraction]:
    """Return exact boundary and oriented area integrals; raise on invariant failure."""
    boundary = compute_boundary_integral(data)
    area = compute_area_integral(data)
    if boundary != area:
        raise ArithmeticError("independent Green theorem integrals do not agree")
    return boundary, area


def _pair(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _polynomial_text(terms: list[dict[str, Any]]) -> str:
    parts = []
    for term in terms:
        numerator, denominator = term["coefficient"]
        coefficient = str(Fraction(numerator, denominator))
        factors = []
        if term["x_power"]:
            factors.append("x" if term["x_power"] == 1 else f"x^{term['x_power']}")
        if term["y_power"]:
            factors.append("y" if term["y_power"] == 1 else f"y^{term['y_power']}")
        monomial = "*".join(factors) or "1"
        parts.append(f"({coefficient})*{monomial}")
    return " + ".join(parts) if parts else "0"


def build_green_fields(rng: random.Random, difficulty: int = 1):
    """Build the standard university generator fields from a seeded RNG."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    if not _is_int(difficulty) or difficulty not in (1, 2, 3, 4, 5):
        raise ValueError("difficulty must be an integer from 1 through 5")

    def build_polynomial() -> list[dict[str, Any]]:
        degree = rng.randint(0, difficulty)
        candidates = [(x, y) for x in range(degree + 1) for y in range(degree + 1 - x)]
        count = rng.randint(1, min(5, len(candidates), MAX_TERMS_PER_COMPONENT))
        chosen = rng.sample(candidates, count)
        terms = []
        for x_power, y_power in chosen:
            numerator = rng.randint(-4 * difficulty, 4 * difficulty)
            if numerator == 0:
                numerator = 1
            denominator = rng.randint(1, min(5, difficulty + 1))
            terms.append({
                "coefficient": [numerator, denominator],
                "x_power": x_power,
                "y_power": y_power,
            })
        terms.sort(key=lambda term: (term["x_power"] + term["y_power"], term["x_power"], term["y_power"]))
        return terms

    x_lower = Fraction(rng.randint(-3 * difficulty, 3 * difficulty), rng.randint(1, 3))
    x_upper = x_lower + Fraction(rng.randint(1, 3 * difficulty + 1), rng.randint(1, 3))
    y_lower = Fraction(rng.randint(-3 * difficulty, 3 * difficulty), rng.randint(1, 3))
    y_upper = y_lower + Fraction(rng.randint(1, 3 * difficulty + 1), rng.randint(1, 3))
    orientation = rng.choice(SUPPORTED_ORIENTATIONS)
    ingredients = {
        "topic": TOPIC,
        "P": build_polynomial(),
        "Q": build_polynomial(),
        "x_bounds": [_pair(x_lower), _pair(x_upper)],
        "y_bounds": [_pair(y_lower), _pair(y_upper)],
        "orientation": orientation,
    }
    boundary, area = calculate_green_integrals(ingredients)
    answer = f"boundary={boundary}; area={area}"
    fields = {
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "Green theorem for rational polynomial fields on rectangles",
        "difficulty": difficulty,
        "problem": (
            f"For P(x,y)={_polynomial_text(ingredients['P'])} and "
            f"Q(x,y)={_polynomial_text(ingredients['Q'])}, evaluate the oriented "
            f"boundary integral and the curl area integral on "
            f"[{x_lower},{x_upper}] x [{y_lower},{y_upper}] with {orientation} orientation."
        ),
        "steps": [
            "Evaluate P dx + Q dy separately on the four oriented rectangle edges.",
            "Compute dQ/dx - dP/dy and integrate it exactly over the rectangle.",
            "The two exact rational values agree by Green's theorem for this supported region.",
        ],
        "answer": answer,
        "answer_type": "exact_rational_pair",
        "ingredients": ingredients,
        "verifier": "independent_exact_green_boundary_and_area_integrals",
    }
    return fields, lambda: verify_green_problem(fields)


def verify_green_problem(problem: Any) -> bool:
    """Validate a Green problem from its ingredients, not by seeded replay."""
    try:
        if not isinstance(problem, dict):
            return False
        if problem.get("topic") != TOPIC:
            return False
        if not _is_int(problem.get("seed")) or not _is_int(problem.get("difficulty")):
            return False
        if problem["difficulty"] not in (1, 2, 3, 4, 5):
            return False
        if problem.get("id") != f"university-{TOPIC}-{problem['seed']}-{problem['difficulty']}":
            return False
        if not isinstance(problem.get("problem"), str) or not isinstance(problem.get("steps"), list):
            return False
        if not isinstance(problem.get("answer"), str):
            return False
        ingredients = problem.get("ingredients")
        p_terms, q_terms, *_ = _validated_input(ingredients)
        if any(x_power + y_power > problem["difficulty"] for _, x_power, y_power in p_terms + q_terms):
            return False
        p_terms, q_terms, x0, x1, y0, y1, orientation = _validated_input(ingredients)
        if any(x_power + y_power > problem["difficulty"] for _, x_power, y_power in p_terms + q_terms):
            return False
        boundary, area = calculate_green_integrals(ingredients)
        expected = {
            "grade_band": "University",
            "topic": TOPIC,
            "subtopic": "Green theorem for rational polynomial fields on rectangles",
            "difficulty": problem["difficulty"],
            "problem": (
                f"For P(x,y)={_polynomial_text(ingredients['P'])} and "
                f"Q(x,y)={_polynomial_text(ingredients['Q'])}, evaluate the oriented "
                f"boundary integral and the curl area integral on "
                f"[{x0},{x1}] x [{y0},{y1}] with {orientation} orientation."
            ),
            "steps": [
                "Evaluate P dx + Q dy separately on the four oriented rectangle edges.",
                "Compute dQ/dx - dP/dy and integrate it exactly over the rectangle.",
                "The two exact rational values agree by Green's theorem for this supported region.",
            ],
            "answer": f"boundary={boundary}; area={area}",
            "answer_type": "exact_rational_pair",
            "ingredients": ingredients,
            "verifier": "independent_exact_green_boundary_and_area_integrals",
            "id": f"university-{TOPIC}-{problem['seed']}-{problem['difficulty']}",
            "seed": problem["seed"],
        }
        return problem == expected
    except (KeyError, TypeError, ValueError, ArithmeticError):
        return False
