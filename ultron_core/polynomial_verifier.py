"""Exact, bounded verification of polynomial identities over Q.

This module proves only identities representable by the existing sparse-polynomial
IR. It is not a general theorem prover and does not interpret domains or assumptions.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from .math_ir import Expr, ExprKind, FormulaCandidate, VerificationStatus
from .polynomial import Polynomial, PolynomialError, PolynomialLimits


_CERTIFICATE_SCHEMA = "ultron.polynomial_identity.v1"


@dataclass(frozen=True)
class PolynomialIdentityResult:
    """Result of checking one equality in the supported polynomial ring."""

    status: VerificationStatus
    expression_sha256: str
    certificate_json: str | None
    certificate_sha256: str | None
    difference_terms: tuple
    note: str


def _has_assumptions(expression: Expr) -> bool:
    return bool(expression.assumptions) or any(
        _has_assumptions(child) for child in expression.args
    )


def _serialize_terms(polynomial: Polynomial) -> list[dict]:
    return [
        {
            "monomial": [[name, exponent] for name, exponent in monomial],
            "coefficient": [coefficient.numerator, coefficient.denominator],
        }
        for monomial, coefficient in polynomial.terms
    ]


def _make_certificate(expression: Expr, left: Polynomial, right: Polynomial,
                      difference: Polynomial, limits: PolynomialLimits,
                      status: VerificationStatus) -> tuple[str, str]:
    payload = {
        "schema": _CERTIFICATE_SCHEMA,
        "expression_sha256": expression.structural_hash(),
        "limits": {
            "max_total_degree": limits.max_total_degree,
            "max_terms": limits.max_terms,
            "max_exponent": limits.max_exponent,
        },
        "left": _serialize_terms(left),
        "right": _serialize_terms(right),
        "difference": _serialize_terms(difference),
        "status": status.value,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return encoded, sha256(encoded.encode("utf-8")).hexdigest()


def verify_polynomial_identity(
    candidate: Expr | FormulaCandidate,
    *,
    limits: PolynomialLimits = PolynomialLimits(),
) -> PolynomialIdentityResult:
    """Verify an equality exactly, or return UNRESOLVED outside the supported domain.

    Supported expressions are rational-coefficient polynomials using addition,
    subtraction, multiplication, non-negative integer powers, unary negation,
    and division by a non-zero rational constant. Candidate domain conditions
    and assumptions are deliberately not interpreted.
    """
    if isinstance(candidate, FormulaCandidate):
        expression = candidate.expression
        if candidate.domain or candidate.assumptions:
            return PolynomialIdentityResult(
                VerificationStatus.UNRESOLVED, expression.structural_hash(),
                None, None, (), "Candidate domain/assumptions are not interpreted.",
            )
    elif isinstance(candidate, Expr):
        expression = candidate
    else:
        raise TypeError("candidate must be an Expr or FormulaCandidate")

    expression_hash = expression.structural_hash()
    if expression.kind != ExprKind.EQUAL:
        return PolynomialIdentityResult(
            VerificationStatus.UNRESOLVED, expression_hash, None, None, (),
            "Only equality expressions can be checked as polynomial identities.",
        )
    if _has_assumptions(expression):
        return PolynomialIdentityResult(
            VerificationStatus.UNRESOLVED, expression_hash, None, None, (),
            "Expressions with assumptions are outside the verifier's scope.",
        )
    if not isinstance(limits, PolynomialLimits):
        raise TypeError("limits must be PolynomialLimits")

    try:
        left = Polynomial.from_expr(expression.args[0], limits=limits)
        right = Polynomial.from_expr(expression.args[1], limits=limits)
        difference = left.add(right.scale(-1, limits=limits), limits=limits)
    except PolynomialError as exc:
        return PolynomialIdentityResult(
            VerificationStatus.UNRESOLVED, expression_hash, None, None, (),
            f"Expression is outside the bounded polynomial domain: {exc}",
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
        "Exact sparse-polynomial normalization proves LHS-RHS is the zero "
        "polynomial over Q in the supported grammar."
        if status == VerificationStatus.FORMALLY_VERIFIED
        else "Exact polynomial normalization found a non-zero LHS-RHS; this is not an identity."
    )
    return PolynomialIdentityResult(
        status, expression_hash, certificate_json, certificate_sha256,
        difference.terms, note,
    )


def validate_polynomial_identity_certificate(
    candidate: Expr | FormulaCandidate,
    certificate_json: str,
) -> bool:
    """Re-run the bounded checker and validate a canonical certificate byte-for-byte."""
    if not isinstance(certificate_json, str) or len(certificate_json) > 1_000_000:
        return False
    try:
        supplied = json.loads(certificate_json)
        canonical = json.dumps(supplied, sort_keys=True, separators=(",", ":"))
    except (json.JSONDecodeError, TypeError, ValueError):
        return False
    if canonical != certificate_json:
        return False
    result = verify_polynomial_identity(candidate)
    if result.status != VerificationStatus.FORMALLY_VERIFIED:
        return False
    return (
        result.certificate_json == certificate_json
        and result.certificate_sha256 == sha256(certificate_json.encode("utf-8")).hexdigest()
    )
