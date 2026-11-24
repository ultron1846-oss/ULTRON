# Exact affine transforms of real algebraic numbers

ULTRON now supports exact rational affine transforms of a represented real algebraic number.

For a represented root \(\alpha\) of \(p(x)=0\), and rational \(a\ne0\), \(b\), the operation returns \(\beta=a\alpha+b\) using the transformed defining polynomial

\[
q(y)=a^n p\left(\frac{y-b}{a}\right),
\]

where \(n=\deg p\). The factor \(a^n\) clears the substitution denominator without changing the roots. The isolating interval is mapped exactly; endpoint order is reversed when \(a<0\). Rational inputs remain represented as exact rationals.

## API

```python
result = value.affine_transform(multiplier=2, offset=1)
```

Inputs must be integers or `fractions.Fraction`; booleans and floats are rejected. A zero multiplier is rejected because it does not define an invertible polynomial substitution. The operation respects the value's configured `PolynomialLimits`.

## Scope and limitations

- The operation is exact over \(\mathbb{Q}\); no floating-point approximation is used.
- The resulting defining polynomial is not guaranteed minimal or irreducible.
- This is an affine transformation, not general algebraic addition or multiplication between two unrelated algebraic numbers.
- It does not add multivariate algebraic numbers, resultants, a general CAS, or a formal proof kernel.

## Validation

The regression suite covers positive, negative and fractional multipliers, rational inputs, invalid inputs, interval orientation, transformed root counts, and resource-budget enforcement. Run:

```sh
python -m unittest tests.python.test_algebraic_affine -v
python -m unittest discover -s tests/python -v
```

No model training, optimizer step, external dataset, remote execution, or website/backend modification is part of this change.
