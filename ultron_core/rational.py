"""Exact rational expressions with explicit, preserved non-zero domain constraints.

No polynomial GCD cancellation is performed. Keeping numerator, denominator
and every non-zero condition separate prevents rewrites from widening domains.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from .math_ir import Expr, ExprKind
from .polynomial import DEFAULT_LIMITS, Polynomial, PolynomialLimits

MAX_DOMAIN_CONSTRAINTS = 256


class RationalExpressionError(ValueError):
    """An expression is outside the supported exact rational domain."""


class RationalDomainError(ZeroDivisionError):
    """A point violates an expression's preserved non-zero domain conditions."""


def _normalize_nonzero(polynomial: Polynomial) -> Polynomial:
    if not polynomial.terms:
        raise RationalExpressionError("a domain non-zero constraint cannot be the zero polynomial")
    return polynomial.scale(1 / polynomial.terms[-1][1])


def _merge_constraints(*groups: tuple[Polynomial, ...]) -> tuple[Polynomial, ...]:
    unique = {}
    for group in groups:
        for constraint in group:
            normalized = _normalize_nonzero(constraint)
            unique[normalized.canonical_key()] = normalized
    if len(unique) > MAX_DOMAIN_CONSTRAINTS:
        raise RationalExpressionError(
            f"domain constraint count exceeds hard limit {MAX_DOMAIN_CONSTRAINTS}"
        )
    return tuple(unique[key] for key in sorted(unique))


@dataclass(frozen=True)
class RationalFunction:
    """Exact numerator/denominator plus all required non-zero conditions."""

    numerator: Polynomial
    denominator: Polynomial
    nonzero_constraints: tuple[Polynomial, ...] = ()

    def __post_init__(self):
        if not isinstance(self.numerator, Polynomial) or not isinstance(self.denominator, Polynomial):
            raise TypeError("numerator and denominator must be Polynomial instances")
        if not isinstance(self.nonzero_constraints, tuple) or any(
            not isinstance(item, Polynomial) for item in self.nonzero_constraints
        ):
            raise TypeError("nonzero_constraints must be a tuple of Polynomial instances")
        if not self.denominator.terms:
            raise RationalExpressionError("rational denominator cannot be the zero polynomial")
        scale = 1 / self.denominator.terms[-1][1]
        numerator = self.numerator.scale(scale)
        denominator = self.denominator.scale(scale)
        constraints = _merge_constraints(self.nonzero_constraints, (denominator,))
        object.__setattr__(self, "numerator", numerator)
        object.__setattr__(self, "denominator", denominator)
        object.__setattr__(self, "nonzero_constraints", constraints)

    @classmethod
    def zero(cls):
        return cls(Polynomial.zero(), Polynomial.one())

    @classmethod
    def one(cls):
        return cls(Polynomial.one(), Polynomial.one())

    @classmethod
    def constant(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
            raise TypeError("constant must be an integer or Fraction")
        return cls(Polynomial.constant(value), Polynomial.one())

    @classmethod
    def from_polynomial(cls, polynomial: Polynomial):
        if not isinstance(polynomial, Polynomial):
            raise TypeError("polynomial must be a Polynomial")
        return cls(polynomial, Polynomial.one())

    @classmethod
    def from_expr(cls, expression: Expr, *, limits: PolynomialLimits = DEFAULT_LIMITS):
        if not isinstance(expression, Expr):
            raise TypeError("expression must be an Expr")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        return cls._from_expr(expression, limits)

    @classmethod
    def _from_expr(cls, expression: Expr, limits: PolynomialLimits):
        if expression.assumptions:
            raise RationalExpressionError("expressions with assumptions are not supported")
        kind = expression.kind
        if kind in (ExprKind.INTEGER, ExprKind.RATIONAL, ExprKind.SYMBOL):
            return cls.from_polynomial(Polynomial.from_expr(expression, limits=limits))
        if kind == ExprKind.NEG:
            return cls._from_expr(expression.args[0], limits).scale(-1, limits=limits)
        if kind == ExprKind.ADD:
            result = cls.zero()
            for child in expression.args:
                result = result.add(cls._from_expr(child, limits), limits=limits)
            return result
        if kind == ExprKind.SUB:
            left, right = (cls._from_expr(child, limits) for child in expression.args)
            return left.add(right.scale(-1, limits=limits), limits=limits)
        if kind == ExprKind.MUL:
            result = cls.one()
            for child in expression.args:
                result = result.multiply(cls._from_expr(child, limits), limits=limits)
            return result
        if kind == ExprKind.DIV:
            left, right = (cls._from_expr(child, limits) for child in expression.args)
            return left.divide(right, limits=limits)
        if kind == ExprKind.POW:
            base, exponent_node = expression.args
            if exponent_node.kind != ExprKind.INTEGER:
                raise RationalExpressionError("rational powers must be integer literals")
            exponent = exponent_node.value
            if abs(exponent) > limits.max_exponent:
                raise RationalExpressionError(
                    f"absolute power {abs(exponent)} exceeds max_exponent={limits.max_exponent}"
                )
            return cls._from_expr(base, limits).power(exponent, limits=limits)
        raise RationalExpressionError(
            f"expression kind {kind.value!r} is not supported in exact rational algebra"
        )

    def _constraints_with(self, other, extra=()):
        return _merge_constraints(self.nonzero_constraints, other.nonzero_constraints, tuple(extra))

    def add(self, other: "RationalFunction", *, limits=DEFAULT_LIMITS):
        if not isinstance(other, RationalFunction):
            raise TypeError("other must be a RationalFunction")
        numerator = self.numerator.multiply(other.denominator, limits=limits).add(
            other.numerator.multiply(self.denominator, limits=limits), limits=limits
        )
        denominator = self.denominator.multiply(other.denominator, limits=limits)
        return RationalFunction(numerator, denominator, self._constraints_with(other))

    def scale(self, coefficient, *, limits=DEFAULT_LIMITS):
        if isinstance(coefficient, bool) or not isinstance(coefficient, (int, Fraction)):
            raise TypeError("scale coefficient must be an integer or Fraction")
        return RationalFunction(
            self.numerator.scale(coefficient, limits=limits),
            self.denominator,
            self.nonzero_constraints,
        )

    def multiply(self, other: "RationalFunction", *, limits=DEFAULT_LIMITS):
        if not isinstance(other, RationalFunction):
            raise TypeError("other must be a RationalFunction")
        return RationalFunction(
            self.numerator.multiply(other.numerator, limits=limits),
            self.denominator.multiply(other.denominator, limits=limits),
            self._constraints_with(other),
        )

    def divide(self, other: "RationalFunction", *, limits=DEFAULT_LIMITS):
        if not isinstance(other, RationalFunction):
            raise TypeError("other must be a RationalFunction")
        if not other.numerator.terms:
            raise RationalExpressionError("division by the zero rational function")
        return RationalFunction(
            self.numerator.multiply(other.denominator, limits=limits),
            self.denominator.multiply(other.numerator, limits=limits),
            self._constraints_with(other, (other.numerator,)),
        )

    def power(self, exponent: int, *, limits=DEFAULT_LIMITS):
        if isinstance(exponent, bool) or not isinstance(exponent, int):
            raise TypeError("rational exponent must be an integer")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        if abs(exponent) > limits.max_exponent:
            raise RationalExpressionError(
                f"absolute power {abs(exponent)} exceeds max_exponent={limits.max_exponent}"
            )
        if exponent == 0:
            if not self.numerator.terms:
                raise RationalExpressionError("zero to the zero power has an empty domain")
            return RationalFunction(
                Polynomial.one(), Polynomial.one(),
                _merge_constraints(self.nonzero_constraints, (self.numerator,))
            )
        if exponent < 0:
            if not self.numerator.terms:
                raise RationalExpressionError("negative power of zero is undefined")
            return RationalFunction(
                self.denominator.power(-exponent, limits=limits),
                self.numerator.power(-exponent, limits=limits),
                _merge_constraints(self.nonzero_constraints, (self.numerator,))
            )
        return RationalFunction(
            self.numerator.power(exponent, limits=limits),
            self.denominator.power(exponent, limits=limits),
            self.nonzero_constraints,
        )

    def evaluate(self, environment: Mapping[str, int | Fraction]) -> Fraction:
        if not isinstance(environment, Mapping):
            raise TypeError("environment must be a mapping")
        for constraint in self.nonzero_constraints:
            if constraint.evaluate(environment) == 0:
                raise RationalDomainError(
                    "evaluation point violates a preserved non-zero domain constraint"
                )
        denominator_value = self.denominator.evaluate(environment)
        if denominator_value == 0:
            raise RationalDomainError("rational denominator evaluates to zero")
        return self.numerator.evaluate(environment) / denominator_value

    def canonical_key(self):
        """Structural key includes the complete preserved domain restriction set."""
        return (
            self.numerator.canonical_key(),
            self.denominator.canonical_key(),
            tuple(item.canonical_key() for item in self.nonzero_constraints),
        )

    def same_representation(self, other: "RationalFunction") -> bool:
        """Compare normalized structure, not general algebraic equivalence."""
        return isinstance(other, RationalFunction) and self.canonical_key() == other.canonical_key()
