# ULTRON mathematics curriculum audit and expansion backlog

**Audit date:** 2026-11-28  
**Baseline commit:** Phase 1 candidate head 26d0d940b8f3a62edb5a682169049a0094b6a1c1  
**Implementation branches:** PRs #209, #210, and #212 for Green/ODE foundations; phase2/curriculum-scope-expansion-batch-8-2026-11-28 (proposed PR #213) for scope corrections and further families  
**Status:** Six independently checked mathematics families are represented across the Phase 2 stack: exact-rational Green's theorem on rectangles, homogeneous constant-coefficient first-order ODEs, restricted separable power-law ODEs, bounded affine-polynomial double integrals, rational complex arithmetic, and homogeneous variable-coefficient linear first-order ODEs. Existing narrow Taylor/integral/vector-calculus templates have also been separated from broad catalogue labels. All three bounded families passed exact-head GitHub Actions checks: Green's theorem in PR #209, homogeneous first-order ODEs in PR #210, and the restricted separable power-law family in PR #212 (exact head 094c0bcb51e2449bebe62875dce3f5e85bb33b9f). All Phase 2 PRs remain unmerged pending independent review. No training or dataset generation is authorized by this phase.

## 1. Coverage counts: baseline and current candidate

The counts below are derived from the combined committed topic registry, the per-topic validation evidence manifest, and the university registry. "Generated" means an implemented deterministic exercise generator is registered; it does not mean examples were produced during this audit.

| State | Phase 2 baseline | Current candidate |
|---|---:|---:|
| Catalogued scope entries | 250 | 264 |
| Generator available | 113 | 117 |
| Independently validated exercise topics | 61 | 66 |
| Measured model-task benchmarks | 0 | 0 |
| Mastered topics | 0 | 0 |

The baseline independent-validation count is 53 university topics plus eight core exact-math topics. The current candidate adds five net independently validated topics relative to the Phase 2 baseline, giving 58 university topics plus eight core topics. The latest batch adds two new independently validated families (exact rational complex arithmetic and a bounded homogeneous variable-coefficient ODE); the rectangular affine double-integral subfamily now has its own dedicated Fubini/additivity test. The school-band generators remain implemented but are not included in the independent-validation total unless a separate mathematical recomputation is recorded for each topic.

The manifest requires named test methods and independent-validator descriptions. It rejects evidence paths or methods that are missing. Benchmark and mastery lists are empty: generator tests, generator throughput, synthetic CI fixtures, and random-initialized model smoke tests are not trained-model mathematical benchmarks or mastery evidence.

## 2. University curriculum and prerequisite graph

The university curriculum now contains **211 unique topic IDs across 17 fields**. The original 197-topic count was first increased to 199 by splitting the Green/Stokes/divergence umbrella into three; the ODE split increased it to 202. The current batch raises it to 211 by separating over-broad Taylor, integral, vector-calculus, and complex-analysis scopes and adding one bounded variable-coefficient ODE family.

| Field | Topics |
|---|---:|
| Foundations and logic | 10 |
| Linear algebra | 16 |
| Calculus | 26 |
| Real analysis | 13 |
| Complex analysis | 12 |
| Abstract algebra | 12 |
| Number theory | 10 |
| Topology | 10 |
| Discrete mathematics and combinatorics | 12 |
| Probability | 13 |
| Statistics | 9 |
| Differential equations | 16 |
| Optimization and operations research | 11 |
| Numerical and computational mathematics | 11 |
| Geometry | 9 |
| Applied mathematics and mathematical physics | 11 |
| Advanced and interdisciplinary | 10 |
| **Total** | **211** |

The prerequisite mapping covers all 211 topics and has 397 directed edges. The graph validator checks duplicate IDs, missing mappings, dangling edges, duplicate/self edges, cycles, and prerequisite-first ordering. The Green/Stokes/divergence split increased the previous 366-edge graph to 372; the ODE split adds six more edges (two on the replacement homogeneous family and two each for three unimplemented sibling families).

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
- separable_first_order_ODEs: generator available only for y'=c*x^m*y^n with rational c, x0, y0; m=0..3 and n=0..2 subject to difficulty bounds.
- linear_first_order_variable_coefficient_ODEs: catalogued, no generator.
- exact_first_order_ODEs: catalogued, no generator.

The homogeneous generator is not a general ODE solver. Its supported coefficients satisfy |k|≤4d and 1≤y0≤8d for difficulty d∈{1,2,3,4,5}; these levels scale the integer magnitudes but do not add new equation structures. Its validator checks the exact canonical solution y(t)=y0 exp(k t), its derivative identity, the initial value, and the complete generated problem object. The separable generator supports only y'=c*x^m*y^n with rational c≠0, x0 and y0>0, m≤min(3,d−1), and n≤min(2,⌊(d−1)/2⌋). Input rational numerators have absolute value ≤2d and denominators ≤d (global caps 10 and 5); the n=2 reciprocal branch is restricted to intervals on which its denominator is nonzero. Its independent validator checks the exact derivative coefficient identity and initial-value substitution for the polynomial, exponential, and reciprocal branches. This remains a bounded subfamily, not general separable ODE support.

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

The remaining 147 university topics without generators are not one flat implementation batch. Each family below must have its own bounded problem schema, deterministic generator, separately implemented validator, explicit difficulty semantics, invalid-input behavior, and tests before its status changes.

1. **Calculus and vector calculus:** complete partial derivatives and gradient/directional-derivative families; bounded multiple integrals; line integrals over parameterized segments; surface integrals over explicitly parameterized patches; Green's theorem extensions only after the rectangle family; then Stokes and divergence theorem as separate workstreams.
2. **Ordinary differential equations:** the current batch bounds the existing y'=k y generator as homogeneous constant-coefficient first-order ODEs. Remaining work includes broader separable equations beyond the implemented power-law family, variable-coefficient linear equations, exact equations, second-order constant-coefficient equations, systems, series solutions and numerical ODE schemes. A single exponential-decay example does not establish general first-order ODE coverage.
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


## 7. Separable ODE subfamily added

The existing separable_first_order_ODEs catalogue item now has a generator only for the bounded power-law family

\[
y'=c x^m y^n,\qquad y(x_0)=y_0,
\]

where c, x0 and y0 are exact rationals, c is nonzero and y0 is positive. Integer powers satisfy \(0\le m\le \min(3,d-1)\) and \(0\le n\le \min(2,\lfloor(d-1)/2\rfloor)\) at difficulty \(d\in\{1,\ldots,5\}\). Input rational numerator absolute values are at most \(2d\) (global maximum 10) and positive denominators at most d (global maximum 5). This gives a polynomial solution for n=0, an exponential solution for n=1, and a reciprocal solution for n=2. The reciprocal family is valid on any connected interval containing x0 where its denominator is nonzero.

The validator checks, with exact rational arithmetic, the derivative coefficient and initial-value identities independently for all three solution forms, then verifies the full canonical exercise object. Tests cover 500 deterministic seeds, all three branches and all four x-powers, difficulty progression, tampering, malformed rational inputs, type and bound rejections, and the seed/difficulty limits. This does not claim support for arbitrary separable factors or general separable ODE solving.


## 8. Exact-head validation for the separable ODE batch

PR #212 exact validated head: 094c0bcb51e2449bebe62875dce3f5e85bb33b9f.

| Workflow | Run ID | Result |
|---|---:|---|
| Node tests | 46122281193 | Passed |
| Python AI Core | 46122281223 | 753 tests passed; CPU forward/backward smoke only, no optimizer step |
| Level 1 Math Tooling | 46122281237 | 5 passed; workflow includes 5,000 randomized cases |
| Security/dependency audit | 46122281197 | Passed; npm audit 0 vulnerabilities; pip-audit no known vulnerabilities |

The first Python run on the initial PR #212 head failed because the committed university registry did not match builder output ordering and one test still expected the separable topic to be unimplemented. Those two registry/test issues were fixed. The final exact-head run above is green. The NumPy-unavailable PyTorch warning was non-fatal. No local test execution is claimed; validation was performed by GitHub Actions.

PR #212 is open, unmerged and has no independent submitted review or inline review threads. It is stacked on PR #210, which is stacked on #209 → #208 → #207. Do not merge this child ahead of any parent. No training or optimizer step occurred.


## 9. Scope audit and curriculum expansion — batch 8

The generator audit found that several available templates were materially narrower than their original catalogue names. The catalogue now keeps broad parent topics but marks them incomplete, while moving the existing examples to explicit subfamily IDs:

- `Taylor_series` remains incomplete; the existing quadratic-polynomial expansion is now `quadratic_Taylor_polynomials`.
- `multiple_integrals` remains incomplete; the new `rectangular_linear_polynomial_double_integrals` family integrates affine rational polynomials over bounded axis-aligned rectangles exactly.
- `change_of_variables`, `line_integrals`, `surface_integrals`, and `vector_calculus` remain broad/incomplete. The existing templates are separately labelled diagonal linear substitutions on rectangles, constant-vector-field segment integrals, flat rectangular surface integrals of one, and divergence of diagonal linear vector fields.
- `complex_numbers_and_topology` is replaced by `complex_number_arithmetic` and `complex_topology`; `Taylor_and_Laurent_series` is replaced by `complex_Taylor_series` and `Laurent_series`.
- `homogeneous_variable_coefficient_linear_first_order_ODEs` is added as a restricted family for `y' + a*x^m*y = 0`, nonzero rational a and m in {1,2}; the broader variable-coefficient linear ODE topic remains incomplete.

The new complex arithmetic and variable-coefficient ODE families have independent exact validators. The double-integral tests independently recompute both Fubini integration orders and rectangle additivity across fixed seeds. The current candidate has 211 university topics, 64 generator-available topics, 147 not implemented, 397 prerequisite edges, 264 combined catalogue entries, 117 generators, and 66 independently validated exercise topics. Benchmarks and mastery remain zero. These counts are generated from registry metadata and evidence; they do not measure trained-model ability.

No training, optimizer step, production corpus generation/download, remote execution, deployment, or model-weight publication was performed in this batch.


## 10. Batch 8 exact-head validation

PR #213 (`phase2/curriculum-scope-expansion-batch-8-2026-11-28`) exact validated head: `3ad04c01bfe48bd0debf46017e9351d017c6ae4a`.

| Workflow | Run ID | Result |
|---|---:|---|
| Node Tests | 46140324038 | Passed |
| Python AI Core Tests | 46140323910 | Passed; CPU forward/backward smoke only, no optimizer step |
| ULTRON Level 1 Math Tooling | 46140323952 | Passed; 5,000 randomized cases |
| Security and dependency audit | 46140323947 | Passed |

The dedicated affine double-integral validator evidence points to the Fubini/additivity regression test in `tests/python/test_rectangular_double_integral_generator.py`. No training, optimizer step, production corpus generation, or remote job occurred.


## 11. Bounded Stokes and divergence theorem families

The latest follow-up adds two separately identified theorem exercises while preserving the broad theorem rows as incomplete:

- `stokes_theorem_horizontal_rectangles`: affine fields (F=(P,Q,0)) on horizontal axis-aligned rectangles, with upward surface orientation and counter-clockwise boundary traversal. The independent validator recomputes all four boundary-edge integrals and the curl surface integral.
- `divergence_theorem_axis_aligned_boxes`: diagonal linear fields (F=(ax,by,cz)) on axis-aligned boxes. The independent validator recomputes six oriented face fluxes and the volume integral of `div F`.

Current candidate coverage: **213 university topics**, **66 generator-available**, **147 not implemented**, **213 prerequisite nodes and 401 edges**; **266 combined entries**, **119 generator-available**, and **68 independently validated**. Trained-checkpoint benchmarks and mastered topics remain zero. These additions do not imply general Stokes or divergence theorem support.


## 12. Bounded exact first-order ODE family

The candidate adds `quadratic_potential_exact_first_order_ODEs`, a separately scoped family for one-forms generated by the quadratic potential `Phi(x,y)=a*x^2+b*x*y+c*y^2`. The exercise asks for the implicit level-set solution through a rational initial point. Independent exact tests use central differences to recompute both components of the potential gradient and both cross-partials, then verify the initial-point constant. The broad `exact_first_order_ODEs` entry remains unimplemented.

Updated candidate coverage: **214 university topics**, **67 generator-available**, **147 not implemented**, **214 prerequisite nodes and 403 edges**; **267 combined entries**, **120 generator-available**, and **69 independently validated**. Trained-checkpoint benchmarks and mastered topics remain zero.


## 13. Bounded second-order ODE and transport PDE families

Two more explicit subfamilies are added while their broad parent rows stay unimplemented:

- `distinct_real_root_second_order_linear_homogeneous_ODEs`: homogeneous constant-coefficient second-order equations with two distinct real rational characteristic roots and rational initial values. Independent tests reconstruct the characteristic polynomial and check both initial-condition equations.
- `constant_speed_transport_polynomial_initial_data_PDEs`: the constant-speed transport equation with a degree-at-most-three polynomial initial profile. Independent exact tests evaluate the PDE residual at multiple rational points and verify the initial profile at time zero.

Current candidate: **216 university topics**, **69 generator-available**, **147 without generators**, **216 prerequisite nodes / 407 edges**; **269 combined entries**, **122 generator-available**, **71 independently validated**. Trained-checkpoint benchmarks and mastered topics remain zero.
