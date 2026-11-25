# Bounded exact polynomial identity verifier

## Scope

`ultron_core/polynomial_verifier.py` checks whether a supported equality is an identity in the multivariate polynomial ring over the rational numbers, \(\mathbb{Q}[x_1,\ldots,x_n]\).

It converts both sides to the existing canonical sparse-polynomial representation, computes \(LHS-RHS\), and returns:

- `FORMALLY_VERIFIED` when the exact canonical difference is the zero polynomial.
- `REJECTED` when the exact difference is non-zero.
- `UNRESOLVED` when the expression is outside the supported grammar, carries assumptions/domain restrictions, or exceeds configured resource limits.

Supported syntax is exact rational constants, symbols, addition, subtraction, multiplication, unary negation, non-negative integer literal powers, and division by a non-zero rational constant. The implementation uses exact `Fraction` arithmetic; no numerical sampling or floating-point approximation is involved.

## Certificate

For resolved polynomial expressions, the checker emits canonical JSON containing the input expression hash, polynomial limits, normalized left/right polynomials, their difference, and the result status. The SHA-256 digest detects accidental certificate changes; it is **not** a digital signature or a standalone proof of authorship.

`validate_polynomial_identity_certificate()` checks canonical encoding and re-runs the exact checker against the supplied expression before accepting the certificate.

## Important limits

- Variable denominators such as \(x/x\) are unresolved. The verifier does not erase the original expression's domain restrictions.
- Candidate domains and assumptions are unresolved because their semantics are not yet represented in a validated assumption language.
- Function calls, inequalities, transcendental identities, rational-function identities, algebraic-number identities, and general theorem proving are not supported by this verifier.
- Resource-budget exhaustion returns `UNRESOLVED`, never a proof.
- A verified polynomial identity does not imply the candidate can enter trusted knowledge. `FormulaCandidate.can_enter_trusted_knowledge()` remains fail-closed until the trusted-knowledge receipt pathway is separately implemented and audited.

## API

```python
from ultron_core.polynomial_verifier import verify_polynomial_identity

result = verify_polynomial_identity(candidate)
print(result.status)
print(result.certificate_sha256)
```

This is a narrow exact algebraic checker, not a universal formal proof kernel and not evidence that ULTRON has learned or autonomously discovered the identity.
