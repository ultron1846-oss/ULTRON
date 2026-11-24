from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Sequence
from .math_ir import Expr, ExprKind, FormulaCandidate, VerificationStatus


@dataclass(frozen=True)
class ProbeResult:
    status: VerificationStatus
    samples_checked: int
    counterexample: dict[str, Fraction] | None
    note: str


def _symbols(expr: Expr) -> set[str]:
    found = {str(expr.value)} if expr.kind == ExprKind.SYMBOL else set()
    for child in expr.args:
        found.update(_symbols(child))
    return found


def _has_assumptions(expr: Expr) -> bool:
    return bool(expr.assumptions) or any(_has_assumptions(child) for child in expr.args)


class EvaluationLimitError(ValueError):
    """Raised when exact evaluation would exceed the configured work budget."""


def evaluate(
    expr: Expr, env: dict[str, Fraction], *, max_abs_exponent: int = 1024
) -> Fraction:
    if isinstance(max_abs_exponent, bool) or not isinstance(max_abs_exponent, int) or max_abs_exponent < 0:
        raise ValueError("max_abs_exponent must be a non-negative integer")
    if expr.kind == ExprKind.INTEGER:
        return Fraction(int(expr.value))
    if expr.kind == ExprKind.RATIONAL:
        return Fraction(str(expr.value))
    if expr.kind == ExprKind.SYMBOL:
        if str(expr.value) not in env:
            raise ValueError(f'missing variable {expr.value}')
        return env[str(expr.value)]
    values = [evaluate(arg, env, max_abs_exponent=max_abs_exponent) for arg in expr.args]
    if expr.kind == ExprKind.ADD:
        return sum(values, Fraction(0))
    if expr.kind == ExprKind.SUB:
        return values[0] - values[1]
    if expr.kind == ExprKind.MUL:
        result = Fraction(1)
        for value in values:
            result *= value
        return result
    if expr.kind == ExprKind.DIV:
        if values[1] == 0:
            raise ZeroDivisionError("division by zero")
        return values[0] / values[1]
    if expr.kind == ExprKind.NEG:
        return -values[0]
    if expr.kind == ExprKind.POW:
        if values[1].denominator != 1:
            raise ValueError('integer exponents only')
        exponent = int(values[1])
        if abs(exponent) > max_abs_exponent:
            raise EvaluationLimitError(
                f"absolute exponent {abs(exponent)} exceeds max_abs_exponent={max_abs_exponent}"
            )
        return values[0] ** exponent
    raise ValueError(f'unsupported expression {expr.kind.value}')


def probe_candidate(
    candidate: FormulaCandidate,
    variable_names: Sequence[str] = ("x", "y"),
    sample_values: Sequence[int | str | Fraction] = (-3, -2, -1, 0, 1, 2, 3),
    max_samples: int = 100_000,
    max_abs_exponent: int = 1024,
) -> ProbeResult:
    if not isinstance(candidate, FormulaCandidate):
        raise TypeError("candidate must be a FormulaCandidate")
    if not isinstance(variable_names, (tuple, list)):
        raise TypeError("variable_names must be a tuple or list of identifiers")
    if not isinstance(sample_values, (tuple, list)):
        raise TypeError("sample_values must be a tuple or list of exact rationals")
    if any(not isinstance(name, str) or not name.isidentifier() for name in variable_names):
        raise ValueError("variable_names must contain valid identifiers")
    if len(set(variable_names)) != len(variable_names):
        raise ValueError("variable_names must be unique")
    if isinstance(max_samples, bool) or not isinstance(max_samples, int) or max_samples <= 0:
        raise ValueError("max_samples must be a positive integer")
    if isinstance(max_abs_exponent, bool) or not isinstance(max_abs_exponent, int) or max_abs_exponent < 0:
        raise ValueError("max_abs_exponent must be a non-negative integer")
    if not sample_values:
        raise ValueError("sample_values must not be empty")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, str, Fraction))
        for value in sample_values
    ):
        raise TypeError("sample_values must contain exact integers, rational strings, or Fractions")
    try:
        exact_samples = tuple(Fraction(value) for value in sample_values)
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise ValueError("sample_values must contain valid finite rationals") from exc
    if len(set(exact_samples)) != len(exact_samples):
        raise ValueError("sample_values must be unique after rational normalization")

    equation = candidate.expression
    if equation.kind != ExprKind.EQUAL:
        raise ValueError("candidate expression must be an equality")
    if candidate.domain or candidate.assumptions or _has_assumptions(equation):
        raise ValueError("finite probing does not interpret candidate domains or assumptions")
    missing = _symbols(equation) - set(variable_names)
    if missing:
        raise ValueError("variable_names omits symbols: " + ", ".join(sorted(missing)))
    total_samples = len(exact_samples) ** len(variable_names)
    if total_samples > max_samples:
        raise ValueError(
            f"finite probe requires {total_samples} samples, exceeding max_samples={max_samples}"
        )
    checked = 0
    for values in product(exact_samples, repeat=len(variable_names)):
        env = {name: value for name, value in zip(variable_names, values)}
        try:
            lhs, rhs = (
                evaluate(arg, env, max_abs_exponent=max_abs_exponent)
                for arg in equation.args
            )
        except EvaluationLimitError:
            raise
        except (ZeroDivisionError, ValueError):
            continue
        checked += 1
        if lhs != rhs:
            return ProbeResult(
                VerificationStatus.REJECTED,
                checked,
                env,
                "A finite-domain counterexample was found; candidate is rejected.",
            )
    if checked == 0:
        raise ValueError("no valid sample points were evaluated")
    return ProbeResult(
        VerificationStatus.EXPERIMENTALLY_SUPPORTED,
        checked,
        None,
        "No counterexample in the tested finite domain. This is not a proof.",
    )
