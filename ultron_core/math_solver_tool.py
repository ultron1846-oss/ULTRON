"""Safe deterministic math solver exposed as a callable ULTRON agent tool.

The tool delegates parsing and exact arithmetic to ULTRON's existing Expr IR.
It intentionally supports a documented subset and fails closed outside it.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any

from .math_ir import Expr, ExprKind
from .math_parser import MathParser
from .symbolic import simplify
from .verification import evaluate


MAX_INPUT_CHARS = 4096
MAX_ABS_EXPONENT = 64
_PARSER = MathParser(max_source_chars=MAX_INPUT_CHARS, max_tokens=256, max_nesting=64)


def _render(expr: Expr) -> str:
    """Render a compact, unambiguous expression from the typed IR."""
    if expr.kind == ExprKind.INTEGER:
        return str(expr.value)
    if expr.kind == ExprKind.RATIONAL:
        return str(expr.value)
    if expr.kind == ExprKind.SYMBOL:
        return str(expr.value)
    if expr.kind == ExprKind.CALL:
        return f"{expr.value}({_render(expr.args[0])})"
    if expr.kind == ExprKind.NEG:
        return f"-({_render(expr.args[0])})"
    if expr.kind == ExprKind.POW:
        return f"({_render(expr.args[0])})^({_render(expr.args[1])})"
    operators = {
        ExprKind.ADD: " + ",
        ExprKind.SUB: " - ",
        ExprKind.MUL: " * ",
        ExprKind.DIV: " / ",
        ExprKind.EQUAL: " = ",
        ExprKind.NOT_EQUAL: " != ",
        ExprKind.LESS_THAN: " < ",
        ExprKind.LESS_EQUAL: " <= ",
        ExprKind.GREATER_THAN: " > ",
        ExprKind.GREATER_EQUAL: " >= ",
    }
    operator = operators.get(expr.kind)
    if operator is None:
        raise ValueError(f"cannot render unsupported node {expr.kind.value}")
    return "(" + operator.join(_render(child) for child in expr.args) + ")"


def _fraction_input(value: Any, name: str) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise TypeError(f"{name} must be an integer or exact rational string")
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise ValueError(f"{name} must be a valid exact rational") from exc
    return result


def _linear_coefficients(expr: Expr, variable: str) -> tuple[Fraction, Fraction]:
    """Return (coefficient, constant) for a supported linear expression."""
    if expr.kind == ExprKind.INTEGER:
        return Fraction(0), Fraction(int(expr.value))
    if expr.kind == ExprKind.RATIONAL:
        return Fraction(0), Fraction(str(expr.value))
    if expr.kind == ExprKind.SYMBOL:
        if expr.value == variable:
            return Fraction(1), Fraction(0)
        raise ValueError(f"equation contains unsupported symbol {expr.value!r}")
    if expr.kind == ExprKind.NEG:
        a, b = _linear_coefficients(expr.args[0], variable)
        return -a, -b
    if expr.kind == ExprKind.ADD:
        pairs = [_linear_coefficients(child, variable) for child in expr.args]
        return sum((a for a, _ in pairs), Fraction(0)), sum((b for _, b in pairs), Fraction(0))
    if expr.kind == ExprKind.SUB:
        a1, b1 = _linear_coefficients(expr.args[0], variable)
        a2, b2 = _linear_coefficients(expr.args[1], variable)
        return a1 - a2, b1 - b2
    if expr.kind == ExprKind.MUL:
        variable_factor: tuple[Fraction, Fraction] | None = None
        scale = Fraction(1)
        for child in expr.args:
            a, b = _linear_coefficients(child, variable)
            if a:
                if variable_factor is not None:
                    raise ValueError("only linear equations are supported; variable products are nonlinear")
                variable_factor = (a, b)
            else:
                scale *= b
        if variable_factor is None:
            return Fraction(0), scale
        return variable_factor[0] * scale, variable_factor[1] * scale
    if expr.kind == ExprKind.POW:
        raise ValueError("nonlinear powers are unsupported by the linear solver")
    if expr.kind == ExprKind.DIV:
        numerator_a, numerator_b = _linear_coefficients(expr.args[0], variable)
        denominator_a, denominator_b = _linear_coefficients(expr.args[1], variable)
        if denominator_a:
            raise ValueError("division by an expression containing the variable is nonlinear")
        if denominator_b == 0:
            raise ZeroDivisionError("equation divides by zero")
        return numerator_a / denominator_b, numerator_b / denominator_b
    raise ValueError(f"linear solver does not support {expr.kind.value}")


def solve_linear(source: str, variable: str | None = None) -> dict[str, Any]:
    equation = _PARSER.parse(source)
    if equation.kind != ExprKind.EQUAL:
        raise ValueError("solve requires one equality, such as 2x + 3 = 7")
    symbols = set()

    def collect(node: Expr) -> None:
        if node.kind == ExprKind.SYMBOL:
            symbols.add(str(node.value))
        for child in node.args:
            collect(child)

    collect(equation)
    if variable is None:
        if len(symbols) != 1:
            raise ValueError("provide variable when the equation does not contain exactly one symbol")
        variable = next(iter(symbols))
    if not isinstance(variable, str) or not variable.isidentifier():
        raise ValueError("variable must be a valid identifier")
    unexpected = symbols - {variable}
    if unexpected:
        raise ValueError("equation contains other symbols: " + ", ".join(sorted(unexpected)))

    left_a, left_b = _linear_coefficients(equation.args[0], variable)
    right_a, right_b = _linear_coefficients(equation.args[1], variable)
    coefficient = left_a - right_a
    constant = right_b - left_b
    if coefficient == 0:
        if constant == 0:
            return {"status": "identity", "variable": variable, "message": "Every value of the variable satisfies this equation."}
        return {"status": "no_solution", "variable": variable, "message": "The equation has no solution."}
    answer = constant / coefficient
    return {
        "status": "solved",
        "variable": variable,
        "value": f"{answer.numerator}/{answer.denominator}" if answer.denominator != 1 else str(answer.numerator),
        "steps": [
            f"Collect terms: {coefficient}*{variable} = {constant}",
            f"Divide by {coefficient}: {variable} = {_format_fraction(answer)}",
        ],
        "exact": True,
    }


def _format_fraction(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def run_math_solver(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute the registered tool with strict argument validation."""
    if not isinstance(arguments, dict):
        raise TypeError("tool arguments must be an object")
    allowed = {"operation", "expression", "variables", "variable"}
    extra = set(arguments) - allowed
    if extra:
        raise ValueError("unknown argument(s): " + ", ".join(sorted(extra)))
    operation = arguments.get("operation")
    source = arguments.get("expression")
    if operation not in {"evaluate", "simplify", "solve"}:
        raise ValueError("operation must be evaluate, simplify, or solve")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("expression must be a non-empty string")
    if len(source) > MAX_INPUT_CHARS:
        raise ValueError(f"expression exceeds {MAX_INPUT_CHARS} characters")

    if operation == "solve":
        variable = arguments.get("variable")
        if variable is not None and (not isinstance(variable, str) or not variable.isidentifier()):
            raise ValueError("variable must be a valid identifier")
        return {"tool": "math_solver", **solve_linear(source, variable)}

    expression = _PARSER.parse(source)
    if operation == "simplify":
        result = simplify(expression)
        return {
            "tool": "math_solver",
            "status": "simplified",
            "expression": _render(result),
            "exact": True,
            "scope": "conservative exact simplification; not general symbolic equivalence",
        }

    raw_variables = arguments.get("variables", {})
    if not isinstance(raw_variables, dict):
        raise TypeError("variables must be an object of exact rational values")
    if len(raw_variables) > 64:
        raise ValueError("at most 64 variable bindings are allowed")
    env = {}
    for name, value in raw_variables.items():
        if not isinstance(name, str) or not name.isidentifier():
            raise ValueError("variable names must be valid identifiers")
        env[name] = _fraction_input(value, f"variables.{name}")
    value = evaluate(expression, env, max_abs_exponent=MAX_ABS_EXPONENT)
    if isinstance(value, bool):
        return {"tool": "math_solver", "status": "evaluated", "value": value, "exact": True}
    return {
        "tool": "math_solver",
        "status": "evaluated",
        "value": _format_fraction(value),
        "exact": True,
    }
