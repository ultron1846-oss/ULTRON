"""Exact rational-function identity verification with preserved domain conditions."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json

from .math_ir import Expr, ExprKind, FormulaCandidate, VerificationStatus
from .polynomial import HARD_LIMITS, Polynomial, PolynomialError, PolynomialLimits, Term
from .rational import RationalExpressionError, RationalFunction


_CERTIFICATE_SCHEMA = "ultron.rational_identity.v1"


@dataclass(frozen=True)
class RationalIdentityResult:
    """Exact equality result for rational functions on their common domain."""

    status: VerificationStatus
    expression_sha256: str
    certificate_json: str | None
    certificate_sha256: str | None
    difference_terms: tuple[Term, ...]
    domain_constraints: tuple[Polynomial, ...]
    note: str


def _validate_limits(limits: PolynomialLimits) -> None:
    if not isinstance(limits, PolynomialLimits):
        raise TypeError("limits must be PolynomialLimits")
    for name in ("max_total_degree", "max_terms", "max_exponent"):
        if getattr(limits, name) > getattr(HARD_LIMITS, name):
            raise ValueError(f"{name} exceeds hard verifier limit")


def _has_assumptions(expression: Expr) -> bool:
    return bool(expression.assumptions) or any(
        _has_assumptions(child) for child in expression.args
    )


def _serialize_polynomial(polynomial: Polynomial) -> list[dict]:
    return [
        {
            "monomial": [[name, exponent] for name, exponent in monomial],
            "coefficient": [coefficient.numerator, coefficient.denominator],
        }
        for monomial, coefficient in polynomial.terms
    ]


def _serialize_rational(value: RationalFunction) -> dict:
    return {
        "numerator": _serialize_polynomial(value.numerator),
        "denominator": _serialize_polynomial(value.denominator),
        "nonzero_constraints": [
            _serialize_polynomial(constraint)
            for constraint in value.nonzero_constraints
        ],
    }


def _combined_constraints(left: RationalFunction, right: RationalFunction):
    unique = {}
    for constraint in left.nonzero_constraints + right.nonzero_constraints:
        unique[constraint.canonical_key()] = constraint
    return tuple(unique[key] for key in sorted(unique))


def _make_certificate(expression: Expr, left: RationalFunction,
                      right: RationalFunction, difference: Polynomial,
                      limits: PolynomialLimits, status: VerificationStatus) -> tuple[str, str]:
    payload = {
        "schema": _CERTIFICATE_SCHEMA,
        "expression_sha256": expression.structural_hash(),
        "limits": {
            "max_total_degree": limits.max_total_degree,
            "max_terms": limits.max_terms,
            "max_exponent": limits.max_exponent,
        },
        "left": _serialize_rational(left),
        "right": _serialize_rational(right),
        "cross_difference": _serialize_polynomial(difference),
        "status": status.value,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return encoded, sha256(encoded.encode("utf-8")).hexdigest()


def verify_rational_identity(
    candidate: Expr | FormulaCandidate,
    *,
    limits: PolynomialLimits = PolynomialLimits(),
) -> RationalIdentityResult:
    """Check rational-function equality, preserving every definedness condition.

    A verified result means the two rational functions are equal wherever both
    expressions are defined. It does not claim their domains are identical.
    """
    if isinstance(candidate, FormulaCandidate):
        expression = candidate.expression
        if candidate.domain or candidate.assumptions:
            return RationalIdentityResult(
                VerificationStatus.UNRESOLVED, expression.structural_hash(),
                None, None, (), (),
                "Candidate domain/assumptions are not interpreted.",
            )
    elif isinstance(candidate, Expr):
        expression = candidate
    else:
        raise TypeError("candidate must be an Expr or FormulaCandidate")

    expression_hash = expression.structural_hash()
    if expression.kind != ExprKind.EQUAL:
        return RationalIdentityResult(
            VerificationStatus.UNRESOLVED, expression_hash, None, None, (), (),
            "Only equality expressions can be checked as rational identities.",
        )
    if _has_assumptions(expression):
        return RationalIdentityResult(
            VerificationStatus.UNRESOLVED, expression_hash, None, None, (), (),
            "Expressions with assumptions are outside the verifier's scope.",
        )
    _validate_limits(limits)

    try:
        left = RationalFunction.from_expr(expression.args[0], limits=limits)
        right = RationalFunction.from_expr(expression.args[1], limits=limits)
        left_cross = left.numerator.multiply(right.denominator, limits=limits)
        right_cross = right.numerator.multiply(left.denominator, limits=limits)
        difference = left_cross.add(right_cross.scale(-1, limits=limits), limits=limits)
        constraints = _combined_constraints(left, right)
    except (RationalExpressionError, PolynomialError) as exc:
        return RationalIdentityResult(
            VerificationStatus.UNRESOLVED, expression_hash, None, None, (), (),
            f"Expression is outside the bounded rational domain: {exc}",
        )

    status = (
        VerificationStatus.FORMALLY_VERIFIED
        if not difference.terms
        else VerificationStatus.REJECTED
    )
    certificate_json, certificate_sha256 = _make_certificate(
        expression, left, right, difference, limits, status
    )
    note = (
        "Exact cross-multiplication proves the rational functions are equal "
        "where both expressions are defined; domain restrictions are preserved."
        if status == VerificationStatus.FORMALLY_VERIFIED
        else "Exact cross-multiplication found a non-zero polynomial difference; the rational functions are not identical."
    )
    return RationalIdentityResult(
        status, expression_hash, certificate_json, certificate_sha256,
        difference.terms, constraints, note,
    )


def validate_rational_identity_certificate(
    candidate: Expr | FormulaCandidate,
    certificate_json: str,
) -> bool:
    """Re-run rational identity verification using the certificate's bounded limits."""
    if not isinstance(certificate_json, str) or len(certificate_json) > 1_000_000:
        return False
    try:
        supplied = json.loads(certificate_json)
        canonical = json.dumps(supplied, sort_keys=True, separators=(",", ":"))
        if not isinstance(supplied, dict) or supplied.get("schema") != _CERTIFICATE_SCHEMA:
            return False
        limit_values = supplied.get("limits")
        if not isinstance(limit_values, dict) or set(limit_values) != {
            "max_total_degree", "max_terms", "max_exponent"
        }:
            return False
        if any(isinstance(value, bool) or not isinstance(value, int) for value in limit_values.values()):
            return False
        limits = PolynomialLimits(**limit_values)
        _validate_limits(limits)
    except (json.JSONDecodeError, TypeError, ValueError):
        return False
    if canonical != certificate_json:
        return False
    result = verify_rational_identity(candidate, limits=limits)
    if result.status != VerificationStatus.FORMALLY_VERIFIED:
        return False
    return (
        result.certificate_json == certificate_json
        and result.certificate_sha256 == sha256(certificate_json.encode("utf-8")).hexdigest()
    )
