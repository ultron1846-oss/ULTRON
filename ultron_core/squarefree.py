"""Exact square-free normalization and selected-root factor identification.

This module separates repeated factors over Q and identifies the square-free
component containing a certified real root. It does not perform irreducible
factorization and never labels a square-free component as minimal.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .algebraic import RealAlgebraicNumber
from .polynomial import DEFAULT_LIMITS, Polynomial, PolynomialError, PolynomialLimits


@dataclass(frozen=True)
class SquareFreeFactor:
    """A monic square-free polynomial occurring with positive multiplicity."""

    polynomial: Polynomial
    multiplicity: int


@dataclass(frozen=True)
class SelectedRootFactor:
    """Square-free component containing the algebraic number's selected root."""

    polynomial: Polynomial
    multiplicity: int


def _degree_and_leading(polynomial: Polynomial) -> tuple[int, Fraction]:
    if not polynomial.terms:
        raise PolynomialError("zero polynomial has no degree")
    monomial, coefficient = polynomial.terms[-1]
    return (monomial[0][1] if monomial else 0), coefficient


def _monic(polynomial: Polynomial, *, limits: PolynomialLimits) -> Polynomial:
    if not polynomial.terms:
        raise PolynomialError("zero polynomial cannot be normalized")
    _, leading = _degree_and_leading(polynomial)
    return polynomial.scale(1 / leading, limits=limits)


def _is_one(polynomial: Polynomial) -> bool:
    return polynomial == Polynomial.one()


def square_free_decomposition(
    polynomial: Polynomial,
    *,
    variable: str | None = None,
    limits: PolynomialLimits = DEFAULT_LIMITS,
) -> tuple[SquareFreeFactor, ...]:
    """Return monic square-free factors with their exact multiplicities.

    The factorization identity is polynomial = constant * product(f_i**m_i).
    The returned factors are pairwise coprime and square-free over Q. The
    constant scale is omitted because input polynomials may be non-monic.
    """
    if not isinstance(polynomial, Polynomial):
        raise TypeError("polynomial must be a Polynomial")
    if not isinstance(limits, PolynomialLimits):
        raise TypeError("limits must be PolynomialLimits")
    if not polynomial.terms:
        raise PolynomialError("square-free decomposition of zero is undefined")

    normalized = _monic(polynomial, limits=limits)
    degree, _ = _degree_and_leading(normalized)
    if degree == 0:
        return ()

    derivative = normalized.derivative_univariate(
        variable=variable, limits=limits
    )
    common = normalized.gcd_univariate(
        derivative, variable=variable, limits=limits
    )
    remaining = normalized.exact_divide_univariate(
        common, variable=variable, limits=limits
    )

    result: list[SquareFreeFactor] = []
    multiplicity = 1
    # Each iteration removes the factors whose exact multiplicity is current.
    while not _is_one(remaining):
        shared = remaining.gcd_univariate(
            common, variable=variable, limits=limits
        )
        factor = remaining.exact_divide_univariate(
            shared, variable=variable, limits=limits
        )
        if not _is_one(factor):
            result.append(SquareFreeFactor(
                _monic(factor, limits=limits), multiplicity
            ))
        remaining = shared
        common = common.exact_divide_univariate(
            shared, variable=variable, limits=limits
        )
        multiplicity += 1
        if multiplicity > degree + 1:
            raise PolynomialError("square-free decomposition exceeded degree bound")

    # In characteristic zero, the residual common part must be constant.
    if not _is_one(common):
        residual_degree, _ = _degree_and_leading(common)
        if residual_degree > 0:
            raise PolynomialError(
                "square-free decomposition left a non-constant repeated residual"
            )
    return tuple(result)


def factor_for_root(
    value: RealAlgebraicNumber,
    *,
    limits: PolynomialLimits | None = None,
) -> SelectedRootFactor:
    """Identify the square-free component containing the selected real root.

    Root selection is exact: a rational root is evaluated directly; otherwise
    Sturm root counts are applied to the value's certified isolating interval.
    Exactly one component must contain the selected root.
    """
    if not isinstance(value, RealAlgebraicNumber):
        raise TypeError("value must be a RealAlgebraicNumber")
    effective = value.limits if limits is None else limits
    if not isinstance(effective, PolynomialLimits):
        raise TypeError("limits must be PolynomialLimits")
    # Respect the algebraic value's policy even if a caller supplies another.
    effective = PolynomialLimits(
        max_total_degree=min(effective.max_total_degree, value.limits.max_total_degree),
        max_terms=min(effective.max_terms, value.limits.max_terms),
        max_exponent=min(effective.max_exponent, value.limits.max_exponent),
    )
    components = square_free_decomposition(
        value.polynomial, variable=value.variable, limits=effective
    )
    selected: list[SquareFreeFactor] = []
    for component in components:
        factor = component.polynomial
        if value.is_rational:
            contains = factor.evaluate({value.variable: value.lower}) == 0
        else:
            contains = factor.real_root_count_univariate(
                value.lower, value.upper,
                variable=value.variable, limits=effective,
            ) == 1
        if contains:
            selected.append(component)
    if len(selected) != 1:
        raise PolynomialError(
            "selected root must belong to exactly one square-free component; "
            f"found {len(selected)}"
        )
    component = selected[0]
    return SelectedRootFactor(component.polynomial, component.multiplicity)
