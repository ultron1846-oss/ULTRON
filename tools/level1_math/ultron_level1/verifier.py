"""Exact answer verification using SymPy plus independent substitution."""
from __future__ import annotations
from fractions import Fraction
from sympy import Eq, Integer, Symbol, solve, simplify, sympify

def _parse_answer(value) -> Fraction:
    if isinstance(value, bool):
        raise ValueError("boolean is not a numeric answer")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        return Fraction(value.strip())
    raise ValueError("answer must be int, Fraction, or fraction-form string")

def verify(problem: dict, submitted_answer) -> bool:
    """Accept only when exact symbolic result and independent check agree."""
    try:
        submitted = _parse_answer(submitted_answer)
        expected = _parse_answer(problem["answer"])
        if problem["kind"] == "arithmetic":
            left, op, right = problem["expression"].split()
            a, b = int(left), int(right)
            exact = {"+": Fraction(a+b), "-": Fraction(a-b),
                     "*": Fraction(a*b), "/": Fraction(a, b)}[op]
            sym = sympify(problem["expression"], rational=True)
            sympy_value = Fraction(int(sym.p), int(sym.q)) if hasattr(sym, "p") else Fraction(int(sym), 1)
            return sympy_value == expected == exact == submitted
        if problem["kind"] == "linear":
            a, b, c = (int(problem[k]) for k in ("a", "b", "c"))
            x = Symbol("x")
            roots = solve(Eq(Integer(a)*x + Integer(b), Integer(c)), x)
            if len(roots) != 1:
                return False
            root = roots[0]
            if not root.is_Rational:
                return False
            sympy_root = Fraction(int(root.p), int(root.q))
            substitution_ok = Fraction(a)*submitted + Fraction(b) == Fraction(c)
            return sympy_root == expected == submitted and substitution_ok
        return False
    except (KeyError, TypeError, ValueError, ZeroDivisionError, SyntaxError, AttributeError):
        return False
