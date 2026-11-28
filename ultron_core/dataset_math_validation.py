"""Independent reconstruction and exact checking of schema-v1 generated samples.

This module does not import the generator's parser or answer validator. It
reconstructs prompts and exact answers from generation parameters. This is a
second implementation of the bounded generator contract, not a proof kernel.
"""
from __future__ import annotations
from collections.abc import Mapping
from fractions import Fraction
import json


def _integer(value: object, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError("integer generation parameter is outside its schema")
    return value


def _fraction_text(value: Fraction | int) -> str:
    return str(Fraction(value))


def _fraction_parameter(value: object, *, max_abs_numerator: int, max_denominator: int) -> Fraction:
    if not isinstance(value, str):
        raise ValueError("rational generation parameter must be text")
    parsed = Fraction(value)
    if str(parsed) != value or abs(parsed.numerator) > max_abs_numerator or parsed.denominator > max_denominator:
        raise ValueError("rational generation parameter is not canonical or is out of range")
    return parsed


def _polynomial_parameters(value: object, *, degree_min: int, degree_max: int) -> tuple[int, dict[int, int]]:
    if not isinstance(value, str):
        raise ValueError("polynomial coefficients must be serialized JSON text")
    pairs = json.loads(value)
    if not isinstance(pairs, list) or not pairs or json.dumps(pairs) != value:
        raise ValueError("polynomial coefficient sequence is malformed or non-canonical")
    coefficients: dict[int, int] = {}
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("polynomial coefficient pair is malformed")
        power = _integer(pair[0], minimum=0, maximum=degree_max)
        coefficient = _integer(pair[1], minimum=-5, maximum=5)
        if power in coefficients:
            raise ValueError("polynomial coefficient powers are duplicated")
        coefficients[power] = coefficient
    degree = max(coefficients)
    if not degree_min <= degree <= degree_max or coefficients[degree] == 0:
        raise ValueError("polynomial degree or leading coefficient is invalid")
    if set(coefficients) != set(range(degree + 1)):
        raise ValueError("polynomial coefficient powers are incomplete")
    return degree, coefficients


def _format_polynomial(coefficients: Mapping[int, int]) -> str:
    terms = []
    for power in sorted(coefficients, reverse=True):
        coefficient = coefficients[power]
        if coefficient == 0:
            continue
        sign = "-" if coefficient < 0 else "+"
        magnitude = abs(coefficient)
        if power == 0:
            body = str(magnitude)
        else:
            coefficient_text = "" if magnitude == 1 else f"{magnitude}*"
            power_text = "" if power == 1 else f"^{power}"
            body = f"{coefficient_text}x{power_text}"
        terms.append(("-" if sign == "-" else "") + body if not terms else f" {sign} {body}")
    return "".join(terms) if terms else "0"


def _expected(topic: str, parameters: Mapping[str, object]) -> tuple[str, str, int]:
    if topic == "arithmetic":
        if set(parameters) != {"a", "operator", "b"}:
            raise ValueError("arithmetic parameter schema mismatch")
        a = _integer(parameters["a"], minimum=-50, maximum=50)
        b = _integer(parameters["b"], minimum=-50, maximum=50)
        operator = parameters["operator"]
        if operator not in ("+", "-", "*"):
            raise ValueError("arithmetic operator is invalid")
        answer = a + b if operator == "+" else a - b if operator == "-" else a * b
        return f"{a} {operator} {b}", _fraction_text(answer), 1 if max(abs(a), abs(b)) < 10 else 2

    if topic == "rational_arithmetic":
        if set(parameters) != {"a", "operator", "b"}:
            raise ValueError("rational arithmetic parameter schema mismatch")
        a = _fraction_parameter(parameters["a"], max_abs_numerator=12, max_denominator=12)
        b = _fraction_parameter(parameters["b"], max_abs_numerator=12, max_denominator=12)
        operator = parameters["operator"]
        if operator not in ("+", "-", "*", "/") or (operator == "/" and b == 0):
            raise ValueError("rational arithmetic operator or divisor is invalid")
        answer = a + b if operator == "+" else a - b if operator == "-" else a * b if operator == "*" else a / b
        return f"{a} {operator} {b}", _fraction_text(answer), 2

    if topic == "linear_equations":
        if set(parameters) != {"coefficient", "constant", "rhs"}:
            raise ValueError("linear equation parameter schema mismatch")
        coefficient = _integer(parameters["coefficient"], minimum=-9, maximum=9)
        constant = _integer(parameters["constant"], minimum=-20, maximum=20)
        rhs = _integer(parameters["rhs"], minimum=-128, maximum=128)
        if coefficient == 0:
            raise ValueError("linear equation coefficient must be non-zero")
        solution = Fraction(rhs - constant, coefficient)
        if solution.denominator != 1 or not -12 <= solution.numerator <= 12:
            raise ValueError("linear equation solution is outside generator bounds")
        sign = "+" if constant >= 0 else "-"
        return f"{coefficient}*x {sign} {abs(constant)} = {rhs}", _fraction_text(solution), 2

    if topic in ("polynomial_derivative", "polynomial_definite_integral"):
        degree_min, degree_max = (2, 5) if topic == "polynomial_derivative" else (1, 4)
        if topic == "polynomial_derivative":
            if set(parameters) != {"degree", "coefficients"}:
                raise ValueError("derivative parameter schema mismatch")
            degree, coefficients = _polynomial_parameters(parameters["coefficients"], degree_min=degree_min, degree_max=degree_max)
            if _integer(parameters["degree"], minimum=degree_min, maximum=degree_max) != degree:
                raise ValueError("derivative degree does not match coefficients")
            derivative = {power - 1: coefficient * power for power, coefficient in coefficients.items() if power > 0 and coefficient * power}
            return "differentiate: " + _format_polynomial(coefficients), _format_polynomial(derivative), degree

        if set(parameters) != {"degree", "coefficients", "lower", "upper"}:
            raise ValueError("definite integral parameter schema mismatch")
        degree, coefficients = _polynomial_parameters(parameters["coefficients"], degree_min=degree_min, degree_max=degree_max)
        if _integer(parameters["degree"], minimum=degree_min, maximum=degree_max) != degree:
            raise ValueError("integral degree does not match coefficients")
        lower = _fraction_parameter(parameters["lower"], max_abs_numerator=4, max_denominator=3)
        upper = _fraction_parameter(parameters["upper"], max_abs_numerator=4, max_denominator=3)
        if lower == upper:
            raise ValueError("integral bounds must differ")
        answer = sum((Fraction(coefficient, power + 1) * (upper ** (power + 1) - lower ** (power + 1)) for power, coefficient in coefficients.items()), Fraction(0))
        prompt = f"integrate: {_format_polynomial(coefficients)} from x={_fraction_text(lower)} to x={_fraction_text(upper)}"
        return prompt, _fraction_text(answer), degree + 1

    if topic == "matrix_determinant_2x2":
        if set(parameters) != {"a", "b", "c", "d"}:
            raise ValueError("determinant parameter schema mismatch")
        a, b, c, d = (_integer(parameters[key], minimum=-9, maximum=9) for key in ("a", "b", "c", "d"))
        return f"determinant: [[{a}, {b}], [{c}, {d}]]", str(a * d - b * c), 3

    if topic == "matrix_inverse_2x2":
        if set(parameters) != {"a", "b", "c", "d", "determinant"}:
            raise ValueError("inverse parameter schema mismatch")
        a, b, c, d = (_integer(parameters[key], minimum=-6, maximum=6) for key in ("a", "b", "c", "d"))
        determinant = a * d - b * c
        if determinant == 0 or _integer(parameters["determinant"], minimum=-72, maximum=72) != determinant:
            raise ValueError("inverse determinant parameter is invalid")
        entries = (Fraction(d, determinant), Fraction(-b, determinant), Fraction(-c, determinant), Fraction(a, determinant))
        answer = f"[[{_fraction_text(entries[0])}, {_fraction_text(entries[1])}], [{_fraction_text(entries[2])}, {_fraction_text(entries[3])}]]"
        return f"inverse: [[{a}, {b}], [{c}, {d}]]", answer, 4

    if topic == "linear_system_2x2":
        if set(parameters) != {"a", "b", "c", "d", "e", "f", "determinant"}:
            raise ValueError("linear system parameter schema mismatch")
        a, b, d, e = (_integer(parameters[key], minimum=-5, maximum=5) for key in ("a", "b", "d", "e"))
        c = _integer(parameters["c"], minimum=-50, maximum=50)
        f = _integer(parameters["f"], minimum=-50, maximum=50)
        determinant = a * e - b * d
        if determinant == 0 or _integer(parameters["determinant"], minimum=-50, maximum=50) != determinant:
            raise ValueError("linear system determinant parameter is invalid")
        x = Fraction(c * e - b * f, determinant)
        y = Fraction(a * f - c * d, determinant)
        if x.denominator != 1 or y.denominator != 1 or not (-5 <= x <= 5 and -5 <= y <= 5):
            raise ValueError("linear system does not reconstruct generator-bounded integer solutions")
        prompt = f"solve: {a}*x {'+' if b >= 0 else '-'} {abs(b)}*y = {c}; {d}*x {'+' if e >= 0 else '-'} {abs(e)}*y = {f}"
        return prompt, f"x={_fraction_text(x)}, y={_fraction_text(y)}", 4

    raise ValueError("unsupported generator topic")


def validate_generated_math_sample(row: object) -> bool:
    """Independently reconstruct a schema-v1 row from its generation parameters."""
    if not isinstance(row, Mapping):
        return False
    try:
        topic = row["topic"]
        parameters = row["generation_parameters"]
        if not isinstance(topic, str) or not isinstance(parameters, Mapping):
            return False
        prompt, answer, difficulty = _expected(topic, parameters)
        return (
            isinstance(row.get("input_text"), str)
            and isinstance(row.get("target_text"), str)
            and isinstance(row.get("exact_answer"), str)
            and row["input_text"] == prompt
            and row["target_text"] == answer
            and row["exact_answer"] == answer
            and isinstance(row.get("difficulty"), int)
            and not isinstance(row.get("difficulty"), bool)
            and row["difficulty"] == difficulty
        )
    except (ArithmeticError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
