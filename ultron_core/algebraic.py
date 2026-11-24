"""Exact real algebraic numbers represented by rational polynomials and isolating intervals.

This module deliberately does not claim that a defining polynomial is minimal.
All decisions use exact rational arithmetic and bounded Sturm/GCD operations.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .polynomial import (
    DEFAULT_LIMITS,
    Polynomial,
    PolynomialError,
    PolynomialLimits,
)


def _infer_variable(polynomial: Polynomial, variable: str | None) -> str:
    if not isinstance(polynomial, Polynomial):
        raise TypeError("polynomial must be a Polynomial")
    if variable is not None:
        if not isinstance(variable, str) or not variable.isidentifier():
            raise ValueError("variable must be a valid identifier")
        for monomial, _ in polynomial.terms:
            if len(monomial) > 1:
                raise PolynomialError("algebraic numbers require univariate polynomials")
            if monomial and monomial[0][0] != variable:
                raise PolynomialError("polynomial variable does not match requested variable")
        return variable
    symbols = {
        monomial[0][0]
        for monomial, _ in polynomial.terms
        if monomial
    }
    if any(len(monomial) > 1 for monomial, _ in polynomial.terms):
        raise PolynomialError("algebraic numbers require univariate polynomials")
    if len(symbols) != 1:
        raise PolynomialError("a non-constant univariate polynomial is required")
    return next(iter(symbols))


@dataclass(frozen=True, eq=False)
class RealAlgebraicNumber:
    """One real root, identified by a defining polynomial and rational interval.

    A non-degenerate interval (lower, upper) must contain exactly one distinct
    root and have non-root endpoints. A degenerate interval (r, r) represents
    the exact rational root r. The defining polynomial need not be minimal.
    """

    polynomial: Polynomial
    variable: str
    lower: Fraction
    upper: Fraction
    limits: PolynomialLimits = DEFAULT_LIMITS

    def __post_init__(self):
        if not isinstance(self.polynomial, Polynomial):
            raise TypeError("polynomial must be a Polynomial")
        if not isinstance(self.limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        if not self.polynomial.terms:
            raise PolynomialError("the zero polynomial cannot define an algebraic number")
        _infer_variable(self.polynomial, self.variable)
        if isinstance(self.lower, bool) or not isinstance(self.lower, (int, Fraction)):
            raise TypeError("lower must be an integer or Fraction")
        if isinstance(self.upper, bool) or not isinstance(self.upper, (int, Fraction)):
            raise TypeError("upper must be an integer or Fraction")
        lower, upper = Fraction(self.lower), Fraction(self.upper)
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        if lower == upper:
            if self.polynomial.evaluate({self.variable: lower}) != 0:
                raise PolynomialError("degenerate interval must be an exact rational root")
            return
        if lower > upper:
            raise ValueError("lower must be less than or equal to upper")
        if (
            self.polynomial.evaluate({self.variable: lower}) == 0
            or self.polynomial.evaluate({self.variable: upper}) == 0
        ):
            raise PolynomialError("isolating interval endpoints must not be roots")
        count = self.polynomial.real_root_count_univariate(
            lower, upper, variable=self.variable, limits=self.limits
        )
        if count != 1:
            raise PolynomialError(
                f"isolating interval must contain exactly one distinct real root; found {count}"
            )

    @classmethod
    def from_isolating_interval(
        cls,
        polynomial: Polynomial,
        lower: int | Fraction,
        upper: int | Fraction,
        *,
        variable: str | None = None,
        limits: PolynomialLimits = DEFAULT_LIMITS,
    ) -> "RealAlgebraicNumber":
        selected = _infer_variable(polynomial, variable)
        return cls(polynomial, selected, lower, upper, limits)

    @classmethod
    def from_rational(
        cls,
        value: int | Fraction,
        *,
        variable: str = "x",
        limits: PolynomialLimits = DEFAULT_LIMITS,
    ) -> "RealAlgebraicNumber":
        if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
            raise TypeError("value must be an integer or Fraction")
        if not isinstance(variable, str) or not variable.isidentifier():
            raise ValueError("variable must be a valid identifier")
        rational = Fraction(value)
        defining = Polynomial.variable(variable).add(
            Polynomial.constant(-rational), limits=limits
        )
        return cls(defining, variable, rational, rational, limits)

    @property
    def is_rational(self) -> bool:
        return self.lower == self.upper

    @property
    def rational_value(self) -> Fraction | None:
        return self.lower if self.is_rational else None

    def refine(self) -> "RealAlgebraicNumber":
        """Return a narrower exact interval, or the exact rational root."""
        if self.is_rational:
            return self
        midpoint = (self.lower + self.upper) / 2
        if self.polynomial.evaluate({self.variable: midpoint}) == 0:
            return RealAlgebraicNumber.from_rational(
                midpoint, variable=self.variable, limits=self.limits
            )
        left_count = self.polynomial.real_root_count_univariate(
            self.lower, midpoint, variable=self.variable, limits=self.limits
        )
        if left_count == 1:
            return RealAlgebraicNumber(
                self.polynomial, self.variable, self.lower, midpoint, self.limits
            )
        return RealAlgebraicNumber(
            self.polynomial, self.variable, midpoint, self.upper, self.limits
        )

    def same_value_as(self, other: "RealAlgebraicNumber") -> bool:
        """Decide equality exactly using rational-root evaluation or polynomial GCD."""
        if not isinstance(other, RealAlgebraicNumber):
            raise TypeError("other must be a RealAlgebraicNumber")
        if self.variable != other.variable:
            raise ValueError("algebraic numbers must use the same variable name")
        if self.is_rational and other.is_rational:
            return self.lower == other.lower
        if self.is_rational:
            return (
                other.lower < self.lower < other.upper
                and other.polynomial.evaluate({other.variable: self.lower}) == 0
            )
        if other.is_rational:
            return (
                self.lower < other.lower < self.upper
                and self.polynomial.evaluate({self.variable: other.lower}) == 0
            )
        overlap_lower = max(self.lower, other.lower)
        overlap_upper = min(self.upper, other.upper)
        if overlap_lower >= overlap_upper:
            return False
        common = self.polynomial.gcd_univariate(
            other.polynomial, variable=self.variable, limits=self.limits
        )
        if not any(monomial for monomial, _ in common.terms):
            return False
        return common.real_root_count_univariate(
            overlap_lower, overlap_upper, variable=self.variable, limits=self.limits
        ) == 1

    def compare_to(
        self,
        other: "RealAlgebraicNumber",
        *,
        max_refinements: int = 4096,
    ) -> int:
        """Return -1, 0 or 1 using exact equality and interval refinement."""
        if not isinstance(other, RealAlgebraicNumber):
            raise TypeError("other must be a RealAlgebraicNumber")
        if isinstance(max_refinements, bool) or not isinstance(max_refinements, int) or max_refinements < 0:
            raise ValueError("max_refinements must be a non-negative integer")
        if self.variable != other.variable:
            raise ValueError("algebraic numbers must use the same variable name")
        if self.same_value_as(other):
            return 0

        left, right = self, other
        for step in range(max_refinements + 1):
            if left.is_rational and right.is_rational:
                return (left.lower > right.lower) - (left.lower < right.lower)
            if left.is_rational and not right.is_rational:
                if (
                    right.lower < left.lower < right.upper
                    and right.polynomial.evaluate({right.variable: left.lower}) == 0
                ):
                    return 0
            if right.is_rational and not left.is_rational:
                if (
                    left.lower < right.lower < left.upper
                    and left.polynomial.evaluate({left.variable: right.lower}) == 0
                ):
                    return 0
            if left.is_rational:
                if left.lower <= right.lower:
                    return -1
                if left.lower >= right.upper:
                    return 1
            if right.is_rational:
                if right.lower <= left.lower:
                    return 1
                if right.lower >= left.upper:
                    return -1
            if left.upper <= right.lower:
                return -1
            if right.upper <= left.lower:
                return 1
            if step == max_refinements:
                break
            if left.is_rational:
                right = right.refine()
            elif right.is_rational:
                left = left.refine()
            elif left.upper - left.lower >= right.upper - right.lower:
                left = left.refine()
            else:
                right = right.refine()
        raise PolynomialError(
            f"algebraic comparison exceeded max_refinements={max_refinements}"
        )
