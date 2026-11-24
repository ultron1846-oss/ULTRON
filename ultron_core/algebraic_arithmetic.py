"""Bounded exact arithmetic for real algebraic numbers.

The resultant construction is deliberately capped by matrix dimension and the
existing sparse-polynomial budgets. It selects the intended real root only
when a certified rational interval contains exactly one distinct resultant
root. No floating-point approximation or minimal-polynomial claim is made.
"""
from __future__ import annotations

from fractions import Fraction
from math import comb

from .algebraic import RealAlgebraicNumber
from .polynomial import (
    DEFAULT_LIMITS,
    Polynomial,
    PolynomialError,
    PolynomialLimits,
)

MAX_RESULTANT_MATRIX = 10
DEFAULT_MAX_REFINE = 4096


def _effective_limits(left: RealAlgebraicNumber,
                      right: RealAlgebraicNumber | None,
                      requested: PolynomialLimits | None) -> PolynomialLimits:
    policies = [left.limits]
    if right is not None:
        policies.append(right.limits)
    if requested is not None:
        if not isinstance(requested, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits or None")
        policies.append(requested)
    return PolynomialLimits(
        max_total_degree=min(item.max_total_degree for item in policies),
        max_terms=min(item.max_terms for item in policies),
        max_exponent=min(item.max_exponent for item in policies),
    )


def _coefficients(value: RealAlgebraicNumber) -> dict[int, Fraction]:
    result: dict[int, Fraction] = {}
    for monomial, coefficient in value.polynomial.terms:
        if len(monomial) > 1:
            raise PolynomialError("algebraic arithmetic requires univariate polynomials")
        power = monomial[0][1] if monomial else 0
        result[power] = coefficient
    if not result:
        raise PolynomialError("zero polynomial cannot define an algebraic number")
    return result


def _poly_from_z(coefficients: dict[int, Fraction], variable: str,
                 limits: PolynomialLimits) -> Polynomial:
    terms = []
    for power, coefficient in coefficients.items():
        if coefficient:
            monomial = () if power == 0 else ((variable, power),)
            terms.append((monomial, Fraction(coefficient)))
    polynomial = Polynomial(tuple(sorted(terms)))
    # Re-enter through a bounded operation so caller-supplied limits apply
    # even when the reversed polynomial is built directly from sparse terms.
    return polynomial.add(Polynomial.zero(), limits=limits)


def _z_monomial(power: int, variable: str,
                limits: PolynomialLimits) -> Polynomial:
    if power == 0:
        return Polynomial.one()
    return Polynomial((( ((variable, power),), Fraction(1)),))


def _add_poly(left: Polynomial, right: Polynomial,
              limits: PolynomialLimits) -> Polynomial:
    return left.add(right, limits=limits)


def _mul_poly(left: Polynomial, right: Polynomial,
              limits: PolynomialLimits) -> Polynomial:
    return left.multiply(right, limits=limits)


def _resultant_matrix(left: RealAlgebraicNumber,
                      right: RealAlgebraicNumber,
                      operation: str,
                      variable: str,
                      limits: PolynomialLimits) -> list[list[Polynomial]]:
    """Build Sylvester matrix for P(x) and transformed Q(x,z)."""
    p = _coefficients(left)
    q = _coefficients(right)
    m, n = max(p), max(q)
    if m + n < 1:
        raise PolynomialError("resultant requires at least one non-constant polynomial")
    if m + n > MAX_RESULTANT_MATRIX:
        raise PolynomialError(
            f"resultant matrix size {m+n} exceeds hard limit {MAX_RESULTANT_MATRIX}"
        )

    transformed: dict[int, Polynomial] = {}
    if operation in ("add", "subtract"):
        # Q(z - x) for addition; Q(x - z) is not used. Subtraction is
        # represented by negating the right operand before this construction.
        for source_power, coefficient in q.items():
            for x_power in range(source_power + 1):
                z_power = source_power - x_power
                term = _z_monomial(z_power, variable, limits).scale(
                    coefficient * comb(source_power, x_power)
                    * ((-1) ** x_power), limits=limits
                )
                transformed[x_power] = _add_poly(
                    transformed.get(x_power, Polynomial.zero()), term, limits
                )
    elif operation == "mul":
        # x^n Q(z/x) = sum q_j z^j x^(n-j).
        for source_power, coefficient in q.items():
            x_power = n - source_power
            term = _z_monomial(source_power, variable, limits).scale(
                coefficient, limits=limits
            )
            transformed[x_power] = _add_poly(
                transformed.get(x_power, Polynomial.zero()), term, limits
            )
    else:
        raise ValueError("unsupported resultant operation")

    p_desc = [Polynomial.constant(p.get(power, 0)) for power in range(m, -1, -1)]
    q_desc = [transformed.get(power, Polynomial.zero())
              for power in range(n, -1, -1)]
    size = m + n
    matrix = [[Polynomial.zero() for _ in range(size)] for _ in range(size)]

    # n shifted rows of P, followed by m shifted rows of transformed Q.
    for row in range(n):
        for index, coefficient in enumerate(p_desc):
            matrix[row][row + index] = coefficient
    for row in range(m):
        for index, coefficient in enumerate(q_desc):
            matrix[n + row][row + index] = coefficient
    return matrix


def _determinant(matrix: list[list[Polynomial]],
                 limits: PolynomialLimits) -> Polynomial:
    """Exact polynomial DP determinant.

    The subset dynamic program is O(n*2^n) states/transitions, avoiding the
    factorial permutation expansion. All coefficients remain exact Q-polynomials.
    """
    size = len(matrix)
    if size == 0:
        return Polynomial.one()
    states: dict[int, Polynomial] = {0: Polynomial.one()}
    for row in range(size):
        next_states: dict[int, Polynomial] = {}
        for mask, partial in states.items():
            for column in range(size):
                bit = 1 << column
                if mask & bit:
                    continue
                inversions = (mask >> (column + 1)).bit_count()
                term = _mul_poly(partial, matrix[row][column], limits)
                if inversions & 1:
                    term = term.scale(-1, limits=limits)
                target = mask | bit
                next_states[target] = _add_poly(
                    next_states.get(target, Polynomial.zero()), term, limits
                )
        states = next_states
    return states.get((1 << size) - 1, Polynomial.zero())


def resultant_polynomial(left: RealAlgebraicNumber,
                         right: RealAlgebraicNumber,
                         operation: str,
                         *,
                         variable: str | None = None,
                         limits: PolynomialLimits | None = None) -> Polynomial:
    """Return a resultant polynomial for sum or product of two algebraic values.

    The output may contain extraneous factors and is not guaranteed minimal.
    """
    if not isinstance(left, RealAlgebraicNumber) or not isinstance(right, RealAlgebraicNumber):
        raise TypeError("left and right must be RealAlgebraicNumber instances")
    if left.variable != right.variable:
        raise ValueError("algebraic operands must use the same source variable")
    if variable is None:
        variable = left.variable
    if not isinstance(variable, str) or not variable.isidentifier():
        raise ValueError("result variable must be a valid identifier")
    limits = _effective_limits(left, right, limits)
    if operation not in ("add", "subtract", "mul"):
        raise ValueError("operation must be 'add', 'subtract', or 'mul'")

    rhs = right
    if operation == "subtract":
        rhs = right.affine_transform(-1)
    matrix = _resultant_matrix(left, rhs, "add" if operation == "subtract" else operation,
                               variable, limits)
    result = _determinant(matrix, limits)
    if not result.terms:
        raise PolynomialError("resultant unexpectedly vanished")
    return result


def _interval_bounds(left: RealAlgebraicNumber,
                     right: RealAlgebraicNumber,
                     operation: str) -> tuple[Fraction, Fraction]:
    a, b = left.lower, left.upper
    c, d = right.lower, right.upper
    if operation == "add":
        return a + c, b + d
    if operation == "subtract":
        return a - d, b - c
    products = (a * c, a * d, b * c, b * d)
    return min(products), max(products)


def _refine_wider(left: RealAlgebraicNumber,
                  right: RealAlgebraicNumber
                  ) -> tuple[RealAlgebraicNumber, RealAlgebraicNumber]:
    if left.is_rational and right.is_rational:
        raise PolynomialError("cannot refine two exact rational operands")
    if left.is_rational:
        return left, right.refine()
    if right.is_rational:
        return left.refine(), right
    if left.upper - left.lower >= right.upper - right.lower:
        return left.refine(), right
    return left, right.refine()


def _combine(left: RealAlgebraicNumber, right: RealAlgebraicNumber,
             operation: str, *, max_refinements: int = DEFAULT_MAX_REFINE,
             limits: PolynomialLimits | None = None) -> RealAlgebraicNumber:
    if not isinstance(left, RealAlgebraicNumber) or not isinstance(right, RealAlgebraicNumber):
        raise TypeError("both operands must be RealAlgebraicNumber instances")
    if left.variable != right.variable:
        raise ValueError("algebraic operands must use the same source variable")
    if isinstance(max_refinements, bool) or not isinstance(max_refinements, int) or max_refinements < 0:
        raise ValueError("max_refinements must be a non-negative integer")
    limits = _effective_limits(left, right, limits)

    if operation == "subtract" and left.same_value_as(right):
        return RealAlgebraicNumber.from_rational(0, variable=left.variable, limits=limits)
    if left.is_rational and right.is_rational:
        a, b = left.lower, right.lower
        value = a + b if operation == "add" else a - b if operation == "subtract" else a * b
        return RealAlgebraicNumber.from_rational(value, variable=left.variable, limits=limits)

    # Keep the operand's variable label on the result so arithmetic chains
    # remain composable with values created from the same source variable.
    polynomial = resultant_polynomial(
        left, right, operation, variable=left.variable, limits=limits
    )
    a, b = left, right
    for attempt in range(max_refinements + 1):
        lower, upper = _interval_bounds(a, b, operation)
        if lower == upper:
            return RealAlgebraicNumber.from_rational(
                lower, variable=left.variable, limits=limits
            )
        if (
            polynomial.evaluate({left.variable: lower}) == 0
            or polynomial.evaluate({left.variable: upper}) == 0
        ):
            count = -1
        else:
            count = polynomial.real_root_count_univariate(
                lower, upper, variable=left.variable, limits=limits
            )
        if count == 1:
            return RealAlgebraicNumber.from_isolating_interval(
                polynomial, lower, upper, variable=left.variable, limits=limits
            )
        if attempt == max_refinements:
            break
        a, b = _refine_wider(a, b)
    raise PolynomialError(
        f"could not certify a unique resultant root within max_refinements={max_refinements}"
    )


def add(left: RealAlgebraicNumber, right: RealAlgebraicNumber, **kwargs) -> RealAlgebraicNumber:
    return _combine(left, right, "add", **kwargs)


def subtract(left: RealAlgebraicNumber, right: RealAlgebraicNumber, **kwargs) -> RealAlgebraicNumber:
    return _combine(left, right, "subtract", **kwargs)


def multiply(left: RealAlgebraicNumber, right: RealAlgebraicNumber, **kwargs) -> RealAlgebraicNumber:
    return _combine(left, right, "mul", **kwargs)


def reciprocal(value: RealAlgebraicNumber, *,
               max_refinements: int = DEFAULT_MAX_REFINE,
               limits: PolynomialLimits | None = None) -> RealAlgebraicNumber:
    """Return 1/value exactly; reject zero and refine until its interval avoids 0."""
    if not isinstance(value, RealAlgebraicNumber):
        raise TypeError("value must be a RealAlgebraicNumber")
    if isinstance(max_refinements, bool) or not isinstance(max_refinements, int) or max_refinements < 0:
        raise ValueError("max_refinements must be a non-negative integer")
    limits = _effective_limits(value, None, limits)
    current = value
    if current.is_rational:
        if current.lower == 0:
            raise ZeroDivisionError("division by the algebraic number zero")
        return RealAlgebraicNumber.from_rational(
            1 / current.lower, variable=value.variable, limits=limits
        )
    for _ in range(max_refinements + 1):
        if current.lower > 0 or current.upper < 0:
            break
        if current.polynomial.evaluate({current.variable: 0}) == 0:
            raise ZeroDivisionError("selected algebraic value is zero")
        current = current.refine()
    else:
        raise PolynomialError("could not certify that divisor is non-zero")
    coefficients = _coefficients(current)
    degree = max(coefficients)
    reversed_coefficients = {
        degree - power: coefficient for power, coefficient in coefficients.items()
    }
    polynomial = _poly_from_z(reversed_coefficients, current.variable, limits)
    first, second = 1 / current.lower, 1 / current.upper
    lower, upper = min(first, second), max(first, second)
    return RealAlgebraicNumber.from_isolating_interval(
        polynomial, lower, upper, variable=current.variable, limits=limits
    )


def divide(left: RealAlgebraicNumber, right: RealAlgebraicNumber, **kwargs) -> RealAlgebraicNumber:
    inverse = reciprocal(right, limits=kwargs.get("limits"),
                         max_refinements=kwargs.get("max_refinements", DEFAULT_MAX_REFINE))
    return multiply(left, inverse, **kwargs)
