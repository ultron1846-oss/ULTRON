# Square-free algebraic normalization

This exact module provides two operations:

- `square_free_decomposition(p)` returns monic, pairwise-coprime square-free components and their multiplicities over \\(\\mathbb Q\\).
- `factor_for_root(alpha)` identifies which component contains the root selected by `RealAlgebraicNumber`'s exact rational isolating interval.

All polynomial arithmetic uses exact `Fraction` coefficients, Euclidean GCD/division, and Sturm root counts. The resource limits attached to the algebraic value are never loosened.

**Scope:** square-free decomposition is not irreducible factorization. A square-free component may still factor into multiple irreducible polynomials. This milestone does not produce a minimal polynomial, perform numerical root approximation, or prove a theorem about arbitrary expressions. Zero polynomial decomposition is undefined and fails closed. Constant nonzero polynomials return an empty decomposition.

Regression tests cover multiplicity grouping, monic normalization, exact rational and irrational selected roots, constants, zero input, and resource-limit enforcement. No model training, optimizer step, dataset generation, or remote execution is part of this change.
