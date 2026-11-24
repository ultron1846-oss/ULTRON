from dataclasses import dataclass
from fractions import Fraction
from itertools import product
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


def evaluate(expr: Expr, env: dict[str, Fraction]) -> Fraction:
    if expr.kind == ExprKind.INTEGER:
        return Fraction(int(expr.value))
    if expr.kind == ExprKind.RATIONAL:
        return Fraction(str(expr.value))
    if expr.kind == ExprKind.SYMBOL:
        if str(expr.value) not in env:
            raise ValueError(f'missing variable {expr.value}')
        return env[str(expr.value)]
    values = [evaluate(arg, env) for arg in expr.args]
    if expr.kind == ExprKind.ADD:
        return sum(values, Fraction(0))
    if expr.kind == ExprKind.MUL:
        result = Fraction(1)
        for value in values:
            result *= value
        return result
    if expr.kind == ExprKind.NEG:
        return -values[0]
    if expr.kind == ExprKind.POW:
        if values[1].denominator != 1:
            raise ValueError('integer exponents only')
        return values[0] ** int(values[1])
    raise ValueError(f'unsupported expression {expr.kind.value}')


def probe_candidate(candidate: FormulaCandidate, variable_names=('x', 'y'),
                    sample_values=(-3, -2, -1, 0, 1, 2, 3)) -> ProbeResult:
    equation = candidate.expression
    if equation.kind != ExprKind.EQUAL:
        raise ValueError('candidate expression must be an equality')
    if candidate.domain or candidate.assumptions or _has_assumptions(equation):
        raise ValueError('finite probing does not interpret candidate domains or assumptions')
    if not sample_values:
        raise ValueError('sample_values must not be empty')
    if len(set(variable_names)) != len(variable_names):
        raise ValueError('variable_names must be unique')
    if any(not isinstance(name, str) or not name.isidentifier() for name in variable_names):
        raise ValueError('variable_names must contain valid identifiers')
    missing = _symbols(equation) - set(variable_names)
    if missing:
        raise ValueError('variable_names omits symbols: ' + ', '.join(sorted(missing)))
    checked = 0
    for values in product(sample_values, repeat=len(variable_names)):
        env = {name: Fraction(value) for name, value in zip(variable_names, values)}
        try:
            lhs, rhs = (evaluate(arg, env) for arg in equation.args)
        except (ZeroDivisionError, ValueError):
            continue
        checked += 1
        if lhs != rhs:
            return ProbeResult(VerificationStatus.REJECTED, checked, env,
                               'A finite-domain counterexample was found; candidate is rejected.')
    if checked == 0:
        raise ValueError('no valid sample points were evaluated')
    return ProbeResult(VerificationStatus.EXPERIMENTALLY_SUPPORTED, checked, None,
                       'No counterexample in the tested finite domain. This is not a proof.')
