"""Conservative exact-arithmetic simplification for the current scalar Expr IR.

Only local identities and exact constant folding are applied. No distribution,
factorization, domain inference, trigonometry, or theorem proving is attempted.
"""
from __future__ import annotations

from fractions import Fraction

from .math_ir import Expr, ExprKind
from .verification import EvaluationLimitError, evaluate


_CONSTANT_KINDS = {ExprKind.INTEGER, ExprKind.RATIONAL}
_ARITHMETIC_KINDS = {
    ExprKind.ADD, ExprKind.SUB, ExprKind.MUL, ExprKind.DIV,
    ExprKind.POW, ExprKind.NEG,
}


def _has_assumptions(expr: Expr) -> bool:
    return bool(expr.assumptions) or any(_has_assumptions(child) for child in expr.args)


def _is_constant(expr: Expr) -> bool:
    return expr.kind in _CONSTANT_KINDS or (
        expr.kind in _ARITHMETIC_KINDS and all(_is_constant(child) for child in expr.args)
    )


def _constant_value(expr: Expr) -> Fraction | None:
    if not _is_constant(expr) or _has_assumptions(expr):
        return None
    try:
        return evaluate(expr, {}, max_abs_exponent=64)
    except (ValueError, ZeroDivisionError, EvaluationLimitError):
        return None


def _atom(value: Fraction, assumptions: tuple[str, ...] = ()) -> Expr:
    if value.denominator == 1:
        return Expr(ExprKind.INTEGER, value=int(value), assumptions=assumptions)
    return Expr(
        ExprKind.RATIONAL,
        value=f"{value.numerator}/{value.denominator}",
        assumptions=assumptions,
    )


def _with_assumptions(expr: Expr, extra: tuple[str, ...]) -> Expr:
    if not extra:
        return expr
    merged = tuple(dict.fromkeys(expr.assumptions + extra))
    return Expr(expr.kind, value=expr.value, args=expr.args, assumptions=merged)


def simplify(expression: Expr) -> Expr:
    """Return a conservatively simplified expression without mutating input.

    Exact folding is capped at exponent magnitude 64. Division by zero and
    over-budget constants remain explicit expression nodes.
    """
    if not isinstance(expression, Expr):
        raise TypeError("expression must be an Expr")
    if not expression.args:
        return expression

    children = tuple(simplify(child) for child in expression.args)
    node = Expr(expression.kind, value=expression.value, args=children,
                assumptions=expression.assumptions)

    if node.kind == ExprKind.EQUAL:
        return node

    # Fold a fully numeric subtree only after exact, bounded evaluation.
    folded = _constant_value(node)
    if folded is not None:
        return _atom(folded, node.assumptions)

    if node.kind == ExprKind.NEG:
        child = node.args[0]
        if child.kind == ExprKind.NEG and not child.assumptions and not node.assumptions:
            return child.args[0]
        return node

    if node.kind in (ExprKind.ADD, ExprKind.MUL):
        flattened = []
        for child in node.args:
            if child.kind == node.kind and not child.assumptions:
                flattened.extend(child.args)
            else:
                flattened.append(child)

        identity = Fraction(0) if node.kind == ExprKind.ADD else Fraction(1)
        combined = Fraction(0) if node.kind == ExprKind.ADD else Fraction(1)
        first_constant = None
        remaining = []
        for child in flattened:
            value = _constant_value(child)
            if value is None:
                remaining.append(child)
            else:
                if first_constant is None:
                    first_constant = len(remaining)
                if node.kind == ExprKind.ADD:
                    combined += value
                else:
                    combined *= value

        if first_constant is not None:
            has_non_identity = combined != identity
            if has_non_identity or not remaining:
                remaining.insert(first_constant, _atom(combined))
        if node.kind == ExprKind.ADD:
            remaining = [item for item in remaining if _constant_value(item) != Fraction(0)]
        else:
            remaining = [item for item in remaining if _constant_value(item) != Fraction(1)]

        if not remaining:
            return _atom(identity, node.assumptions)
        if len(remaining) == 1:
            return _with_assumptions(remaining[0], node.assumptions)
        return Expr(node.kind, args=tuple(remaining), assumptions=node.assumptions)

    if node.kind == ExprKind.SUB and _constant_value(node.args[1]) == Fraction(0):
        return _with_assumptions(node.args[0], node.assumptions)
    if node.kind == ExprKind.DIV and _constant_value(node.args[1]) == Fraction(1):
        return _with_assumptions(node.args[0], node.assumptions)
    if node.kind == ExprKind.POW and _constant_value(node.args[1]) == Fraction(1):
        return _with_assumptions(node.args[0], node.assumptions)
    return node
