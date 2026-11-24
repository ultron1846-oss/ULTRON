"""Bounded exact sparse-polynomial algebra over rational coefficients."""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping
from .math_ir import Expr, ExprKind

Monomial = tuple[tuple[str, int], ...]
Term = tuple[Monomial, Fraction]

class PolynomialError(ValueError):
    """Expression is outside the supported polynomial domain or resource budget."""

@dataclass(frozen=True)
class PolynomialLimits:
    max_total_degree: int = 64
    max_terms: int = 4096
    max_exponent: int = 64

    def __post_init__(self):
        for name in ("max_total_degree", "max_terms", "max_exponent"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.max_terms == 0:
            raise ValueError("max_terms must be a positive integer")

DEFAULT_LIMITS = PolynomialLimits()
ZERO_MONOMIAL: Monomial = ()

def _validate_monomial(monomial):
    if not isinstance(monomial, tuple):
        raise TypeError("monomial must be a tuple")
    previous = None
    for item in monomial:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError("monomial entries must be (symbol, exponent) tuples")
        name, exponent = item
        if not isinstance(name, str) or not name.isidentifier():
            raise ValueError("monomial symbols must be valid identifiers")
        if isinstance(exponent, bool) or not isinstance(exponent, int) or exponent <= 0:
            raise ValueError("monomial exponents must be positive integers")
        if previous is not None and name <= previous:
            raise ValueError("monomial symbols must be unique and lexicographically ordered")
        previous = name

def _check_budget(terms, limits):
    if len(terms) > limits.max_terms:
        raise PolynomialError(f"polynomial term count {len(terms)} exceeds max_terms={limits.max_terms}")
    for monomial in terms:
        degree = sum(power for _, power in monomial)
        if degree > limits.max_total_degree:
            raise PolynomialError(f"polynomial total degree {degree} exceeds max_total_degree={limits.max_total_degree}")
        if any(power > limits.max_exponent for _, power in monomial):
            raise PolynomialError(f"monomial exponent exceeds max_exponent={limits.max_exponent}")

def _canonical(terms, limits):
    cleaned = {m: c for m, c in terms.items() if c}
    _check_budget(cleaned, limits)
    return tuple((m, cleaned[m]) for m in sorted(cleaned))

def _merge_monomials(left, right):
    powers = dict(left)
    for symbol, exponent in right:
        powers[symbol] = powers.get(symbol, 0) + exponent
    return tuple(sorted(powers.items()))

@dataclass(frozen=True)
class Polynomial:
    """Immutable canonical sparse polynomial with exact Fraction coefficients."""
    terms: tuple[Term, ...] = ()

    def __post_init__(self):
        if not isinstance(self.terms, tuple):
            raise TypeError("terms must be a tuple")
        previous = None
        for term in self.terms:
            if not isinstance(term, tuple) or len(term) != 2:
                raise TypeError("each term must be a (monomial, coefficient) tuple")
            monomial, coefficient = term
            _validate_monomial(monomial)
            if not isinstance(coefficient, Fraction):
                raise TypeError("polynomial coefficients must be fractions.Fraction values")
            if coefficient == 0:
                raise ValueError("zero coefficients must be omitted from canonical terms")
            if previous is not None and monomial <= previous:
                raise ValueError("polynomial terms must be unique and canonically ordered")
            previous = monomial

    @classmethod
    def zero(cls):
        return cls(())

    @classmethod
    def one(cls):
        return cls(((ZERO_MONOMIAL, Fraction(1)),))

    @classmethod
    def constant(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
            raise TypeError("constant must be an integer or Fraction")
        value = Fraction(value)
        return cls(()) if value == 0 else cls(((ZERO_MONOMIAL, value),))

    @classmethod
    def variable(cls, name):
        if not isinstance(name, str) or not name.isidentifier():
            raise ValueError("variable name must be a valid identifier")
        return cls((((name, 1),), Fraction(1)))

    @classmethod
    def from_expr(cls, expression: Expr, *, limits: PolynomialLimits = DEFAULT_LIMITS):
        if not isinstance(expression, Expr):
            raise TypeError("expression must be an Expr")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        return cls._from_expr(expression, limits)

    @classmethod
    def _from_expr(cls, expr, limits):
        if expr.assumptions:
            raise PolynomialError("expressions with assumptions are not supported")
        kind = expr.kind
        if kind == ExprKind.INTEGER:
            result = cls.constant(expr.value)
        elif kind == ExprKind.RATIONAL:
            result = cls.constant(Fraction(str(expr.value)))
        elif kind == ExprKind.SYMBOL:
            result = cls.variable(expr.value)
        elif kind == ExprKind.NEG:
            result = cls._from_expr(expr.args[0], limits).scale(-1, limits=limits)
        elif kind == ExprKind.ADD:
            result = cls.zero()
            for child in expr.args:
                result = result.add(cls._from_expr(child, limits), limits=limits)
        elif kind == ExprKind.SUB:
            left, right = (cls._from_expr(child, limits) for child in expr.args)
            result = left.add(right.scale(-1, limits=limits), limits=limits)
        elif kind == ExprKind.MUL:
            result = cls.one()
            for child in expr.args:
                result = result.multiply(cls._from_expr(child, limits), limits=limits)
        elif kind == ExprKind.DIV:
            numerator, denominator = (cls._from_expr(child, limits) for child in expr.args)
            if any(monomial for monomial, _ in denominator.terms):
                raise PolynomialError("division by a variable polynomial is not supported")
            if not denominator.terms:
                raise PolynomialError("division by zero is undefined")
            result = numerator.scale(1 / denominator.terms[0][1], limits=limits)
        elif kind == ExprKind.POW:
            base, exponent_node = expr.args
            if exponent_node.kind != ExprKind.INTEGER:
                raise PolynomialError("polynomial powers must be non-negative integer literals")
            exponent = exponent_node.value
            if exponent < 0:
                raise PolynomialError("negative powers are not polynomials")
            if exponent > limits.max_exponent:
                raise PolynomialError(f"power {exponent} exceeds max_exponent={limits.max_exponent}")
            result = cls._from_expr(base, limits).power(exponent, limits=limits)
        else:
            raise PolynomialError(f"expression kind {kind.value!r} is not supported in polynomial algebra")
        _check_budget(dict(result.terms), limits)
        return result

    def _as_dict(self):
        return dict(self.terms)

    def add(self, other, *, limits=DEFAULT_LIMITS):
        if not isinstance(other, Polynomial):
            raise TypeError("other must be a Polynomial")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        terms = self._as_dict()
        for monomial, coefficient in other.terms:
            terms[monomial] = terms.get(monomial, Fraction(0)) + coefficient
        return Polynomial(_canonical(terms, limits))

    def scale(self, coefficient, *, limits=DEFAULT_LIMITS):
        if isinstance(coefficient, bool) or not isinstance(coefficient, (int, Fraction)):
            raise TypeError("scale coefficient must be an integer or Fraction")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        scalar = Fraction(coefficient)
        return Polynomial(_canonical({m: c * scalar for m, c in self.terms}, limits))

    def multiply(self, other, *, limits=DEFAULT_LIMITS):
        if not isinstance(other, Polynomial):
            raise TypeError("other must be a Polynomial")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        terms = {}
        for lm, lc in self.terms:
            for rm, rc in other.terms:
                monomial = _merge_monomials(lm, rm)
                terms[monomial] = terms.get(monomial, Fraction(0)) + lc * rc
                _check_budget({m: c for m, c in terms.items() if c}, limits)
        return Polynomial(_canonical(terms, limits))

    def power(self, exponent, *, limits=DEFAULT_LIMITS):
        if isinstance(exponent, bool) or not isinstance(exponent, int):
            raise TypeError("polynomial exponent must be an integer")
        if exponent < 0:
            raise PolynomialError("negative powers are not polynomials")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        if exponent > limits.max_exponent:
            raise PolynomialError(f"power {exponent} exceeds max_exponent={limits.max_exponent}")
        result, factor, remaining = Polynomial.one(), self, exponent
        while remaining:
            if remaining & 1:
                result = result.multiply(factor, limits=limits)
            remaining >>= 1
            if remaining:
                factor = factor.multiply(factor, limits=limits)
        return result

    def evaluate(self, environment: Mapping[str, int | Fraction]) -> Fraction:
        if not isinstance(environment, Mapping):
            raise TypeError("environment must be a mapping")
        normalized = {}
        for name, value in environment.items():
            if not isinstance(name, str) or not name.isidentifier():
                raise ValueError("environment keys must be valid identifiers")
            if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
                raise TypeError("environment values must be integers or Fractions")
            normalized[name] = Fraction(value)
        total = Fraction(0)
        for monomial, coefficient in self.terms:
            value = coefficient
            for symbol, exponent in monomial:
                if symbol not in normalized:
                    raise ValueError(f"missing variable {symbol}")
                value *= normalized[symbol] ** exponent
            total += value
        return total

    def to_expr(self) -> Expr:
        """Export a deterministic structural expression in the existing IR."""
        terms = []
        for monomial, coefficient in self.terms:
            factors = []
            if not monomial or coefficient != 1:
                if coefficient.denominator == 1:
                    factors.append(Expr(ExprKind.INTEGER, value=coefficient.numerator))
                else:
                    factors.append(Expr(ExprKind.RATIONAL, value=f"{coefficient.numerator}/{coefficient.denominator}"))
            for symbol, exponent in monomial:
                variable = Expr(ExprKind.SYMBOL, value=symbol)
                factors.append(variable if exponent == 1 else Expr(
                    ExprKind.POW, args=(variable, Expr(ExprKind.INTEGER, value=exponent))
                ))
            terms.append(factors[0] if len(factors) == 1 else Expr(ExprKind.MUL, args=tuple(factors)))
        if not terms:
            return Expr(ExprKind.INTEGER, value=0)
        return terms[0] if len(terms) == 1 else Expr(ExprKind.ADD, args=tuple(terms))

    def canonical_key(self):
        return self.terms
