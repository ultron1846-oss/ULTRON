"""Bounded exact evaluation of rational polynomials at real algebraic numbers.

Evaluation uses Horner's rule and the exact algebraic arithmetic engine.
Every intermediate operation is subject to the intersected resource limits.
"""
from __future__ import annotations

from fractions import Fraction

from .algebraic import RealAlgebraicNumber
from .polynomial import (
    DEFAULT_LIMITS,
    Polynomial,
    PolynomialError,
    PolynomialLimits,
)


def _effective_limits(
    value: RealAlgebraicNumber,
    requested: PolynomialLimits | None,
) -> PolynomialLimits:
    if requested is not None and not isinstance(requested, PolynomialLimits):
        raise TypeError("limits must be PolynomialLimits or None")
    policies = [value.limits]
    if requested is not None:
        policies.append(requested)
    return PolynomialLimits(
        max_total_degree=min(item.max_total_degree for item in policies),
        max_terms=min(item.max_terms for item in policies),
        max_exponent=min(item.max_exponent for item in policies),
    )


def evaluate_polynomial(
    value: RealAlgebraicNumber,
    polynomial: Polynomial,
    *,
    max_refinements: int = 4096,
    limits: PolynomialLimits | None = None,
) -> RealAlgebraicNumber:
    """Return the exact value p(value), or fail when a budget is exceeded.

    The polynomial must be univariate over Q and use the same variable label
    as the algebraic number. The result's defining polynomial may contain
    extraneous factors and is not asserted to be minimal or irreducible.
    """
    if not isinstance(value, RealAlgebraicNumber):
        raise TypeError("value must be a RealAlgebraicNumber")
    if not isinstance(polynomial, Polynomial):
        raise TypeError("polynomial must be a Polynomial")
    if (
        isinstance(max_refinements, bool)
        or not isinstance(max_refinements, int)
        or max_refinements < 0
    ):
        raise ValueError("max_refinements must be a non-negative integer")

    effective = _effective_limits(value, limits)
    # Revalidate a directly constructed polynomial against the effective
    # operand policy, not only against Polynomial's absolute hard ceiling.
    polynomial = polynomial.add(Polynomial.zero(), limits=effective)

    symbols: set[str] = set()
    coefficients: dict[int, Fraction] = {}
    for monomial, coefficient in polynomial.terms:
        if len(monomial) > 1:
            raise PolynomialError("algebraic evaluation requires a univariate polynomial")
        if monomial:
            symbol, power = monomial[0]
            symbols.add(symbol)
        else:
            power = 0
        coefficients[power] = coefficient

    if len(symbols) > 1:
        raise PolynomialError("algebraic evaluation requires one polynomial variable")
    if symbols and next(iter(symbols)) != value.variable:
        raise PolynomialError(
            f"polynomial variable must match algebraic variable {value.variable!r}"
        )

    if not coefficients:
        return RealAlgebraicNumber.from_rational(
            0, variable=value.variable, limits=effective
        )

    if value.is_rational:
        result = polynomial.evaluate({value.variable: value.lower})
        return RealAlgebraicNumber.from_rational(
            result, variable=value.variable, limits=effective
        )

    degree = max(coefficients)
    result = RealAlgebraicNumber.from_rational(
        coefficients.get(degree, Fraction(0)),
        variable=value.variable,
        limits=effective,
    )
    for power in range(degree - 1, -1, -1):
        result = result.multiply(
            value,
            max_refinements=max_refinements,
            limits=effective,
        )
        coefficient = coefficients.get(power, Fraction(0))
        if coefficient:
            constant = RealAlgebraicNumber.from_rational(
                coefficient, variable=value.variable, limits=effective
            )
            result = result.add(
                constant,
                max_refinements=max_refinements,
                limits=effective,
            )

    # Cancellation often yields a rational result whose resultant polynomial
    # is not reduced. Canonicalize the important exact-zero case.
    zero = RealAlgebraicNumber.from_rational(
        0, variable=value.variable, limits=effective
    )
    if result.same_value_as(zero):
        return zero
    return result
