# Domain-preserving rational identity verifier

## Scope

`ultron_core/rational_verifier.py` verifies identities between supported exact rational functions. It converts both sides to `RationalFunction` objects, preserves their normalized non-zero domain constraints, and cross-multiplies the numerator/denominator pairs using bounded exact polynomial arithmetic.

- `FORMALLY_VERIFIED`: the exact cross-multiplied polynomial difference is zero. The rational functions are equal wherever both expressions are defined.
- `REJECTED`: the cross-multiplied polynomial difference is non-zero, so the rational functions are not identical.
- `UNRESOLVED`: the expression is unsupported, has unparsed assumptions/domain annotations, or exceeds a resource limit.

## Domain preservation

For example, `x/x = 1` is verified as a rational-function identity **with the condition (x \ne 0)**. The verifier returns that non-zero constraint and does not rewrite the original expression as globally defined at (x=0).

A verified result does not assert that the two sides have identical domains. It establishes equality on the intersection of their defined domains, while retaining each side's original non-zero constraints in the certificate.

## Supported grammar and limits

The existing exact rational-expression layer supports rational constants, symbols, arithmetic, integer powers (including negative powers), and rational-function division. Function calls, inequalities, candidate-supplied domain strings, and assumptions remain unresolved.

The verifier uses exact `Fraction` arithmetic and polynomial operations. It enforces the polynomial engine's hard resource caps. Exhaustion or unsupported syntax returns `UNRESOLVED`, never a proof.

## Certificate

Canonical JSON records the expression hash, limits, normalized numerator/denominator pairs, each side's preserved non-zero constraints, the cross-multiplied difference, and status. SHA-256 is an integrity digest, not a digital signature. Certificate validation parses the bounded limits and re-runs the verifier against the candidate.

## Trust boundary

`FormulaCandidate.can_enter_trusted_knowledge()` remains fail-closed. A rational identity result is not itself a candidate-bound trusted-knowledge receipt and does not authorize knowledge promotion.

This is a restricted exact algebraic verifier, not a general theorem prover, and it does not establish autonomous formula discovery or learned mathematical capability.
