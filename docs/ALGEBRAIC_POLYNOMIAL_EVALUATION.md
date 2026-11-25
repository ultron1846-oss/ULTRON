# Exact polynomial evaluation at algebraic numbers

`ultron_core.algebraic_evaluation.evaluate_polynomial(value, polynomial)` evaluates a univariate rational-coefficient polynomial at a selected real algebraic number.

- Uses exact Horner evaluation, rational coefficients, and the existing resultant-based algebraic arithmetic.
- The polynomial variable must match the algebraic value's variable.
- Resource policies are intersected; caller limits cannot loosen the algebraic value's limits.
- Exact rational inputs are evaluated directly. Exact cancellation to zero is normalized to a rational zero.
- Unsupported multivariate inputs, variable mismatches, and exhausted degree/term/exponent/refinement budgets fail explicitly.

The returned defining polynomial may contain extraneous factors. This operation does not perform irreducible factorization, establish a minimal polynomial, approximate roots with floating point, or provide a formal proof kernel.

Run:

`python -m unittest tests.python.test_algebraic_evaluation -v`

No model training, optimizer step, dataset generation, or remote execution is part of this change.
