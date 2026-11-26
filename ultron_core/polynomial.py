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
# Absolute ceilings also apply to direct Polynomial(...) construction.
HARD_LIMITS = PolynomialLimits(max_total_degree=256, max_terms=16384, max_exponent=256)
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

def _resolve_univariate_symbol(polynomials, variable):
    if variable is not None and (
        not isinstance(variable, str) or not variable.isidentifier()
    ):
        raise ValueError("variable must be a valid identifier or None")
    symbols = set()
    for polynomial in polynomials:
        for monomial, _ in polynomial.terms:
            if len(monomial) > 1:
                raise PolynomialError("univariate operation does not accept multivariate monomials")
            if monomial:
                symbols.add(monomial[0][0])
    if len(symbols) > 1:
        raise PolynomialError("univariate operation requires one shared variable")
    inferred = next(iter(symbols), None)
    if variable is not None and inferred not in (None, variable):
        raise PolynomialError(
            f"polynomial variable {inferred!r} does not match requested variable {variable!r}"
        )
    return variable or inferred


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
        _check_budget(dict(self.terms), HARD_LIMITS)

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
        return cls(((((name, 1),), Fraction(1)),))

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
        # Enforce the caller's budget on inputs as well as the result. Without
        # this, oversized operands can bypass limits by cancelling in addition.
        _check_budget(dict(self.terms), limits)
        _check_budget(dict(other.terms), limits)
        terms = self._as_dict()
        for monomial, coefficient in other.terms:
            terms[monomial] = terms.get(monomial, Fraction(0)) + coefficient
        return Polynomial(_canonical(terms, limits))

    def scale(self, coefficient, *, limits=DEFAULT_LIMITS):
        if isinstance(coefficient, bool) or not isinstance(coefficient, (int, Fraction)):
            raise TypeError("scale coefficient must be an integer or Fraction")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        # Validate before scaling (especially scale-by-zero), which otherwise
        # could erase an over-budget input and hide the limit violation.
        _check_budget(dict(self.terms), limits)
        scalar = Fraction(coefficient)
        return Polynomial(_canonical({m: c * scalar for m, c in self.terms}, limits))

    def multiply(self, other, *, limits=DEFAULT_LIMITS):
        if not isinstance(other, Polynomial):
            raise TypeError("other must be a Polynomial")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        _check_budget(dict(self.terms), limits)
        _check_budget(dict(other.terms), limits)
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
        _check_budget(dict(self.terms), limits)
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

    def divide_univariate(
        self,
        divisor: "Polynomial",
        *,
        variable: str | None = None,
        limits: PolynomialLimits = DEFAULT_LIMITS,
    ) -> tuple["Polynomial", "Polynomial"]:
        """Return exact quotient and remainder over Q for univariate inputs only.

        The method rejects multivariate terms instead of applying an ambiguous
        monomial order. Coefficients are Fractions, so each division step is
        exact. The invariant is self = quotient * divisor + remainder, with
        remainder zero or degree(remainder) < degree(divisor).
        """
        if not isinstance(divisor, Polynomial):
            raise TypeError("divisor must be a Polynomial")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        if variable is not None and (
            not isinstance(variable, str) or not variable.isidentifier()
        ):
            raise ValueError("variable must be a valid identifier or None")
        if not divisor.terms:
            raise PolynomialError("polynomial division by zero")

        _check_budget(dict(self.terms), limits)
        _check_budget(dict(divisor.terms), limits)

        symbols = set()
        for polynomial in (self, divisor):
            for monomial, _ in polynomial.terms:
                if len(monomial) > 1:
                    raise PolynomialError("univariate division does not accept multivariate monomials")
                if monomial:
                    symbols.add(monomial[0][0])
        if len(symbols) > 1:
            raise PolynomialError("univariate division requires one shared variable")
        inferred = next(iter(symbols), None)
        if variable is not None and inferred not in (None, variable):
            raise PolynomialError(
                f"polynomial variable {inferred!r} does not match requested variable {variable!r}"
            )
        selected = variable or inferred

        def degree_map(polynomial):
            result = {}
            for monomial, coefficient in polynomial.terms:
                degree = monomial[0][1] if monomial else 0
                result[degree] = coefficient
            return result

        def monomial_for(degree):
            return () if degree == 0 else ((selected, degree),)

        remainder = degree_map(self)
        divisor_terms = degree_map(divisor)
        divisor_degree = max(divisor_terms)
        divisor_lead = divisor_terms[divisor_degree]
        quotient = {}

        while remainder:
            remainder_degree = max(remainder)
            if remainder_degree < divisor_degree:
                break
            shift = remainder_degree - divisor_degree
            if shift > limits.max_exponent:
                raise PolynomialError(
                    f"quotient exponent {shift} exceeds max_exponent={limits.max_exponent}"
                )
            factor = remainder[remainder_degree] / divisor_lead
            quotient[shift] = quotient.get(shift, Fraction(0)) + factor
            if quotient[shift] == 0:
                del quotient[shift]

            for degree, coefficient in divisor_terms.items():
                target_degree = degree + shift
                remainder[target_degree] = (
                    remainder.get(target_degree, Fraction(0)) - factor * coefficient
                )
                if remainder[target_degree] == 0:
                    del remainder[target_degree]

            quotient_terms = {
                monomial_for(degree): coefficient
                for degree, coefficient in quotient.items()
                if coefficient
            }
            remainder_terms = {
                monomial_for(degree): coefficient
                for degree, coefficient in remainder.items()
                if coefficient
            }
            _check_budget(quotient_terms, limits)
            _check_budget(remainder_terms, limits)

        quotient_terms = {
            monomial_for(degree): coefficient
            for degree, coefficient in quotient.items()
            if coefficient
        }
        remainder_terms = {
            monomial_for(degree): coefficient
            for degree, coefficient in remainder.items()
            if coefficient
        }
        return (
            Polynomial(_canonical(quotient_terms, limits)),
            Polynomial(_canonical(remainder_terms, limits)),
        )

    def exact_divide_univariate(
        self,
        divisor: "Polynomial",
        *,
        variable: str | None = None,
        limits: PolynomialLimits = DEFAULT_LIMITS,
    ) -> "Polynomial":
        """Return the exact univariate quotient or fail if a remainder exists."""
        quotient, remainder = self.divide_univariate(
            divisor, variable=variable, limits=limits
        )
        if remainder.terms:
            raise PolynomialError("univariate polynomial division is not exact")
        return quotient

    def gcd_univariate(
        self,
        other: "Polynomial",
        *,
        variable: str | None = None,
        limits: PolynomialLimits = DEFAULT_LIMITS,
    ) -> "Polynomial":
        """Return the monic Euclidean GCD over Q for univariate polynomials."""
        if not isinstance(other, Polynomial):
            raise TypeError("other must be a Polynomial")
        if not self.terms and not other.terms:
            raise PolynomialError("gcd(0, 0) is undefined")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")

        # Validate the left operand even when the right operand is zero and
        # the Euclidean loop would otherwise be skipped entirely.
        if not other.terms:
            self.divide_univariate(Polynomial.one(), variable=variable, limits=limits)

        left, right = self, other
        while right.terms:
            _, remainder = left.divide_univariate(
                right, variable=variable, limits=limits
            )
            left, right = right, remainder

        if not left.terms:
            raise PolynomialError("gcd(0, 0) is undefined")
        return left.scale(1 / left.terms[-1][1], limits=limits)

    def derivative_univariate(
        self,
        *,
        variable: str | None = None,
        limits: PolynomialLimits = DEFAULT_LIMITS,
    ) -> "Polynomial":
        """Differentiate exactly with respect to the sole univariate symbol."""
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        _check_budget(dict(self.terms), limits)
        selected = _resolve_univariate_symbol((self,), variable)
        if selected is None:
            return Polynomial.zero()
        derivative_terms = {}
        for monomial, coefficient in self.terms:
            if not monomial:
                continue
            symbol, exponent = monomial[0]
            if symbol != selected:
                raise PolynomialError("polynomial variable does not match derivative variable")
            derivative_monomial = (
                () if exponent == 1 else ((selected, exponent - 1),)
            )
            derivative_terms[derivative_monomial] = coefficient * exponent
        return Polynomial(_canonical(derivative_terms, limits))

    def sturm_sequence_univariate(
        self,
        *,
        variable: str | None = None,
        limits: PolynomialLimits = DEFAULT_LIMITS,
    ) -> tuple["Polynomial", ...]:
        """Build the exact Sturm sequence over Q for a nonzero univariate polynomial."""
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        if not self.terms:
            raise PolynomialError("Sturm sequence is undefined for the zero polynomial")
        _check_budget(dict(self.terms), limits)
        selected = _resolve_univariate_symbol((self,), variable)
        derivative = self.derivative_univariate(variable=selected, limits=limits)
        sequence = [self]
        if not derivative.terms:
            return tuple(sequence)
        sequence.append(derivative)
        while sequence[-1].terms:
            _, remainder = sequence[-2].divide_univariate(
                sequence[-1], variable=selected, limits=limits
            )
            if not remainder.terms:
                break
            sequence.append(remainder.scale(-1, limits=limits))
            if len(sequence) > limits.max_total_degree + 2:
                raise PolynomialError("Sturm sequence exceeded the configured degree budget")
        return tuple(sequence)

    def real_root_count_univariate(
        self,
        lower: int | Fraction,
        upper: int | Fraction,
        *,
        variable: str | None = None,
        limits: PolynomialLimits = DEFAULT_LIMITS,
    ) -> int:
        """Count distinct real roots in (lower, upper) using exact Sturm variations.

        Interval endpoints must be exact integers/Fractions and must not be roots.
        The method counts roots; it does not approximate or isolate their values.
        """
        if isinstance(lower, bool) or not isinstance(lower, (int, Fraction)):
            raise TypeError("lower endpoint must be an integer or Fraction")
        if isinstance(upper, bool) or not isinstance(upper, (int, Fraction)):
            raise TypeError("upper endpoint must be an integer or Fraction")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        lower, upper = Fraction(lower), Fraction(upper)
        if lower >= upper:
            raise ValueError("lower endpoint must be strictly less than upper endpoint")
        if not self.terms:
            raise PolynomialError("the zero polynomial has no finite root count")
        _check_budget(dict(self.terms), limits)

        selected = _resolve_univariate_symbol((self,), variable)
        environment_lower = {} if selected is None else {selected: lower}
        environment_upper = {} if selected is None else {selected: upper}
        if self.evaluate(environment_lower) == 0 or self.evaluate(environment_upper) == 0:
            raise PolynomialError("Sturm interval endpoints must not be roots")

        sequence = self.sturm_sequence_univariate(
            variable=selected, limits=limits
        )

        def variations_at(environment):
            signs = []
            for polynomial in sequence:
                value = polynomial.evaluate(environment)
                if value > 0:
                    signs.append(1)
                elif value < 0:
                    signs.append(-1)
            return sum(left != right for left, right in zip(signs, signs[1:]))

        count = variations_at(environment_lower) - variations_at(environment_upper)
        if count < 0:
            raise PolynomialError("Sturm variation count violated monotonicity")
        return count

    def isolate_real_roots_univariate(
        self,
        lower: int | Fraction,
        upper: int | Fraction,
        *,
        max_width: int | Fraction = Fraction(1, 1000),
        max_depth: int = 64,
        max_intervals: int = 4096,
        variable: str | None = None,
        limits: PolynomialLimits = DEFAULT_LIMITS,
    ) -> tuple[tuple[Fraction, Fraction], ...]:
        """Return disjoint rational isolating intervals for distinct real roots.

        Each returned pair (a, b) contains exactly one distinct root in its
        open interval. A pair (r, r) denotes an exactly detected rational root.
        Non-degenerate interval endpoints are guaranteed not to be roots.
        The algorithm uses square-free reduction and exact Sturm counts only;
        it performs no floating-point approximation.
        """
        for name, endpoint in (("lower", lower), ("upper", upper)):
            if isinstance(endpoint, bool) or not isinstance(endpoint, (int, Fraction)):
                raise TypeError(f"{name} endpoint must be an integer or Fraction")
        if isinstance(max_width, bool) or not isinstance(max_width, (int, Fraction)):
            raise TypeError("max_width must be an integer or Fraction")
        lower, upper, max_width = Fraction(lower), Fraction(upper), Fraction(max_width)
        if lower >= upper:
            raise ValueError("lower endpoint must be strictly less than upper endpoint")
        if max_width <= 0:
            raise ValueError("max_width must be strictly positive")
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
            raise ValueError("max_depth must be a non-negative integer")
        if isinstance(max_intervals, bool) or not isinstance(max_intervals, int) or max_intervals < 1:
            raise ValueError("max_intervals must be a positive integer")
        if not isinstance(limits, PolynomialLimits):
            raise TypeError("limits must be PolynomialLimits")
        if not self.terms:
            raise PolynomialError("the zero polynomial has no finite root isolation")
        _check_budget(dict(self.terms), limits)
        selected = _resolve_univariate_symbol((self,), variable)
        if selected is None:
            return ()

        lower_env, upper_env = {selected: lower}, {selected: upper}
        if self.evaluate(lower_env) == 0 or self.evaluate(upper_env) == 0:
            raise PolynomialError("isolation interval endpoints must not be roots")

        derivative = self.derivative_univariate(variable=selected, limits=limits)
        repeated_factor = self.gcd_univariate(
            derivative, variable=selected, limits=limits
        )
        square_free = self.exact_divide_univariate(
            repeated_factor, variable=selected, limits=limits
        )
        if not square_free.terms:
            raise PolynomialError("square-free polynomial unexpectedly vanished")

        queue = [(square_free, lower, upper, 0)]
        isolated = []
        processed = 0
        while queue:
            current, left, right, depth = queue.pop()
            processed += 1
            if processed > max_intervals:
                raise PolynomialError(
                    f"root isolation exceeded max_intervals={max_intervals}"
                )
            count = current.real_root_count_univariate(
                left, right, variable=selected, limits=limits
            )
            if count == 0:
                continue
            if count == 1 and right - left <= max_width:
                # A rational root removed from the square-free polynomial may
                # still sit at an endpoint of a neighboring interval. Move
                # such endpoints inward without crossing the remaining root.
                # This preserves the public invariant against the ORIGINAL
                # polynomial, not merely the reduced polynomial.
                if self.evaluate({selected: left}) == 0:
                    shifted = False
                    exact_root = None
                    for attempt in range(max_depth):
                        candidate = left + (right - left) / (2 ** (attempt + 1))
                        if current.evaluate({selected: candidate}) == 0:
                            exact_root = candidate
                            break
                        if current.real_root_count_univariate(
                            candidate, right, variable=selected, limits=limits
                        ) == count:
                            left = candidate
                            shifted = True
                            break
                    if exact_root is not None:
                        isolated.append((exact_root, exact_root))
                        continue
                    if not shifted:
                        raise PolynomialError(
                            "could not move isolating interval away from a root endpoint within max_depth"
                        )
                if self.evaluate({selected: right}) == 0:
                    shifted = False
                    exact_root = None
                    for attempt in range(max_depth):
                        candidate = right - (right - left) / (2 ** (attempt + 1))
                        if current.evaluate({selected: candidate}) == 0:
                            exact_root = candidate
                            break
                        if current.real_root_count_univariate(
                            left, candidate, variable=selected, limits=limits
                        ) == count:
                            right = candidate
                            shifted = True
                            break
                    if exact_root is not None:
                        isolated.append((exact_root, exact_root))
                        continue
                    if not shifted:
                        raise PolynomialError(
                            "could not move isolating interval away from a root endpoint within max_depth"
                        )
                isolated.append((left, right))
                continue
            if depth >= max_depth:
                raise PolynomialError(
                    f"root isolation exceeded max_depth={max_depth}"
                )

            midpoint = (left + right) / 2
            midpoint_value = current.evaluate({selected: midpoint})
            if midpoint_value == 0:
                # square_free has no repeated factors, so one exact linear
                # division removes this root and makes midpoint a valid
                # non-root endpoint for both remaining subintervals.
                linear_factor = Polynomial.variable(selected).add(
                    Polynomial.constant(-midpoint), limits=limits
                )
                reduced = current.exact_divide_univariate(
                    linear_factor, variable=selected, limits=limits
                )
                isolated.append((midpoint, midpoint))
                if reduced.terms:
                    queue.append((reduced, left, midpoint, depth + 1))
                    queue.append((reduced, midpoint, right, depth + 1))
                continue

            queue.append((current, midpoint, right, depth + 1))
            queue.append((current, left, midpoint, depth + 1))

        return tuple(sorted(isolated))

    def canonical_key(self):
        return self.terms
