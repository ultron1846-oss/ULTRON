# ULTRON mathematics curriculum audit and expansion backlog

**Audit date:** 2026-11-28  
**Baseline commit:** Phase 1 candidate head 26d0d940b8f3a62edb5a682169049a0094b6a1c1  
**Implementation branches:** phase2/green-theorem-curriculum-batch-2026-11-28 (PR #209); phase2/ode-scope-and-validator-2026-11-28 (PR #210)  
**Status:** Two bounded families are implemented in stacked Phase 2 batches: exact-rational Green's theorem on rectangles, and homogeneous constant-coefficient first-order ODEs. Both mathematical families have passed the required exact-head GitHub Actions checks in their respective PR branches. PR #209 and PR #210 remain unmerged pending independent review. No training or dataset generation is authorized by this phase.

## 1. Coverage counts: baseline and current candidate

The counts below are derived from the combined committed topic registry, the per-topic validation evidence manifest, and the university registry. "Generated" means an implemented deterministic exercise generator is registered; it does not mean examples were produced during this audit.

| State | Phase 2 baseline | Current candidate |
|---|---:|---:|
| Catalogued scope entries | 250 | 255 |
| Generator available | 113 | 114 |
| Independently validated exercise topics | 61 | 63 |
| Measured model-task benchmarks | 0 | 0 |
| Mastered topics | 0 | 0 |

The baseline independent-validation count is 53 university topics plus eight core exact-math topics. The current candidate adds two independently checked families (Green's theorem and the narrowed homogeneous first-order ODE family), giving 55 university topics plus eight core topics. The school-band generators remain implemented but are not included in the independent-validation total unless a separate mathematical recomputation is recorded for each topic.

The manifest requires named test methods and independent-validator descriptions. It rejects evidence paths or methods that are missing. Benchmark and mastery lists are empty: generator tests, generator throughput, synthetic CI fixtures, and random-initialized model smoke tests are not trained-model mathematical benchmarks or mastery evidence.

## 2. University curriculum and prerequisite graph

The university curriculum now contains **202 unique topic IDs across 17 fields**. The original 197-topic count was first increased to 199 by splitting the Green/Stokes/divergence umbrella into three; the follow-up split of the broad first-order ODE entry into four bounded families increased it to 202.

| Field | Topics |
|---|---:|
| Foundations and logic | 10 |
| Linear algebra | 16 |
| Calculus | 20 |
| Real analysis | 13 |
| Complex analysis | 10 |
| Abstract algebra | 12 |
| Number theory | 10 |
| Topology | 10 |
| Discrete mathematics and combinatorics | 12 |
| Probability | 13 |
| Statistics | 9 |
| Differential equations | 15 |
| Optimization and operations research | 11 |
| Numerical and computational mathematics | 11 |
| Geometry | 9 |
| Applied mathematics and mathematical physics | 11 |
| Advanced and interdisciplinary | 10 |
| **Total** | **202** |

The prerequisite mapping covers all 202 topics and has 378 directed edges. The graph validator checks duplicate IDs, missing mappings, dangling edges, duplicate/self edges, cycles, and prerequisite-first ordering. The Green/Stokes/divergence split increased the previous 366-edge graph to 372; the ODE split adds six more edges (two on the replacement homogeneous family and two each for three unimplemented sibling families).

The combined registry now assigns scope-qualified catalog_id values so identically named exercises in different bands do not collide. The raw identifier linear_equations occurs in Core, G7-8, and G8-9; these are separate catalogue entries, not one topic. There are 255 unique scope-qualified IDs and 253 distinct raw topic strings.

## 3. Topic-scope findings

### Bounded scope splits implemented in Phase 2

The prior Green_stokes_divergence_theorems catalogue row was too broad to claim one generator represented three distinct theorems. It is replaced by:

- greens_theorem_rectangles: generator available, bounded to exact rational polynomial fields on non-degenerate axis-aligned rational rectangles.
- stokes_theorem: catalogued, no generator.
- divergence_theorem: catalogued, no generator.

Only the Green rectangle family is implemented in this theorem group. It does not establish support for arbitrary regions, curved boundaries, non-polynomial fields, Stokes' theorem, or the divergence theorem.

The former first_order_ODEs umbrella was also replaced by:

- homogeneous_constant_coefficient_first_order_ODEs: generator available for y'=k y with y(0)=y0, with an independent analytic validator.
- separable_first_order_ODEs: catalogued, no generator.
- linear_first_order_variable_coefficient_ODEs: catalogued, no generator.
- exact_first_order_ODEs: catalogued, no generator.

The existing generator is not a general ODE solver. Its supported coefficients satisfy |k|≤4d and 1≤y0≤8d for difficulty d∈{1,2,3,4,5}; these levels scale the integer magnitudes but do not add new equation structures. The validator checks the exact canonical solution y(t)=y0 exp(k t), its derivative identity, the initial value, and the complete generated problem object.

### Further scope review backlog

Two additional compound labels merit a separate compatibility-aware review before changing IDs or prerequisite edges:

- complex_numbers_and_topology: combines introductory complex-number content with a separate topological subject area.
- Taylor_and_Laurent_series: combines two complex-series families with different convergence and singularity use cases.

They remain unchanged in this batch. Other compound labels such as eigenvalues/eigenvectors, sequences/series, and countable/uncountable sets can be coherent paired learning objectives and should not be split merely because their names contain "and".

Some generator names are broader than their implemented exercise family. For example, the university generator key multivariable_calculus is currently mapped to the curriculum item partial_derivatives; it must not be read as support for all multivariable calculus. Generator keys are implementation routing names, while curriculum IDs define user-facing capability scope.

## 4. Green's theorem support contract

Input is a JSON-like object with two sparse polynomial term lists, rational x/y bounds, and orientation. Each term has exactly a rational coefficient pair plus non-negative integer x/y powers.

| Limit | Bound |
|---|---:|
| Maximum total polynomial degree | 5 |
| Maximum terms in P or Q | 8 each |
| Maximum combined term count | 12 |
| Coefficient numerator absolute value | 1,000 |
| Coefficient denominator | 100 |
| Rectangle-bound numerator absolute value | 100 |
| Rectangle-bound denominator | 20 |
| Conservative exact-operation budget | 256 |
| Difficulty | 1 through 5 |

The conservative operation estimate is checked in addition to component/combined term limits; the operation budget may reject some inputs below the maximum combined term count. Zero denominators, booleans masquerading as integers, floats, duplicate monomials, zero coefficients, negative/out-of-range powers, unsupported fields, malformed rational pairs, unsupported orientations, and degenerate/reversed bounds are rejected.

For counter-clockwise orientation, the implementation independently integrates P dx + Q dy over bottom/right/top/left edges and integrates dQ/dx - dP/dy over the rectangle. Clockwise orientation reverses both signs. Exact Fraction equality is required. Tests add an independent reference implementation, hand-computable fields, a gradient-field zero-circulation invariant, 500 deterministic seeds, tamper detection, and malformed/budget boundaries.

## 4a. Difficulty progression audit

The university curriculum and combined registry do not currently carry a global per-topic difficulty-progression field. Existing generator APIs commonly accept levels 1–5, but those levels are implementation-specific and are not safely comparable across subjects. The previous registry also lacked a separate record of what each difficulty level changes.

This batch defines Green difficulty concretely: level 1–5 bounds the maximum total polynomial degree by the level; the same global resource ceilings still apply at every level. Other generator families must document the mathematical feature changed by each difficulty level (not just random coefficient magnitudes) before their progression can be compared. Difficulty labels do not indicate student mastery.

## 5. Dependency-aware topic expansion order

The remaining 141 university topics without generators are not one flat implementation batch. Each family below must have its own bounded problem schema, deterministic generator, separately implemented validator, explicit difficulty semantics, invalid-input behavior, and tests before its status changes.

1. **Calculus and vector calculus:** complete partial derivatives and gradient/directional-derivative families; bounded multiple integrals; line integrals over parameterized segments; surface integrals over explicitly parameterized patches; Green's theorem extensions only after the rectangle family; then Stokes and divergence theorem as separate workstreams.
2. **Ordinary differential equations:** the current batch bounds the existing y'=k y generator as homogeneous constant-coefficient first-order ODEs. Remaining work includes independent generators/validators for general separable equations, variable-coefficient linear equations, exact equations, second-order constant-coefficient equations, systems, series solutions and numerical ODE schemes. A single exponential-decay example does not establish general first-order ODE coverage.
3. **PDEs and mathematical physics:** classify a narrow PDE family (for example, constant-coefficient first-order transport or selected separable heat-equation cases), with explicit domain/boundary assumptions; then separate wave, Laplace/Poisson and numerical PDE work. Keep applications and general PDE solving distinct.
4. **Linear algebra:** exact row reduction and rank; linear maps and null/range; determinants and inverse families; eigenvalues/eigenvectors for bounded matrices; orthogonality/projections/least squares; then spectral/Jordan forms under explicit field and diagonalizability assumptions.
5. **Abstract algebra:** groups/subgroups and cyclic groups; homomorphisms/kernels/images; cosets/Lagrange; rings/ideals; fields/extensions; then carefully bounded Galois examples. Keep structural proof validation separate from finite computational examples.
6. **Number theory:** divisibility/gcd; Euclidean and extended Euclidean algorithms; modular arithmetic; congruences and CRT; Fermat/Euler results; then Diophantine families with bounded coefficients.
7. **Discrete mathematics, combinatorics and graph theory:** recurrence relations and induction; permutations/combinations; inclusion-exclusion; graph representations, paths/cycles, trees/spanning trees; matching/flows; designs/codes. Each graph family must constrain vertices/edges and validate independently.
8. **Probability and statistics:** finite sample spaces; conditional probability/Bayes; expectation/variance; named distributions; LLN/CLT as theorem-application exercises with assumptions; sampling/estimators; confidence intervals and hypothesis tests. Do not equate a Bayes generator with general statistics.
9. **Real analysis, complex analysis and topology:** sequences/series and metric-space convergence; continuity/compactness; measure and simple Lebesgue-integration cases; Lp examples; complex differentiability/Cauchy-Riemann; contour-integral families; Taylor/Laurent/residues; topology of explicitly bounded examples. Avoid claiming general proof automation.
10. **Optimization and numerical analysis:** convexity and derivatives; constrained smooth optimization/Lagrange multipliers; KKT only with constraint qualifications stated; root finding and convergence assumptions; quadrature; conditioning/stability; numerical ODE/PDE schemes with error criteria.
11. **Geometry, logic/proofs, modeling and advanced algebra:** coordinate and Euclidean constructions; transformations and curvature; propositional/predicate logic; proof methods and counterexamples; finite mathematical models; advanced algebraic structures. Formal proof acceptance must not be inferred from generated solution text.

## 6. Validation and acceptance policy

- A catalogue row is not an implementation.
- A generator is not independent mathematical validation.
- Independent exercise validation is not a trained-model benchmark.
- A benchmark is not mastery.
- Mastery requires measured evaluation evidence from a compatible trained checkpoint and a separately defined acceptance policy.
- No generated corpus, downloaded data, model training, optimizer step, remote job, deployment, or checkpoint publication occurred in this phase.
