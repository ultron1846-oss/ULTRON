# University curriculum prerequisite map

**Status:** curated map for all 218 of 218 university curriculum topics across 17 fields. No university catalogue topic remains unmapped.

The source curriculum is tools/math_generators/university/curriculum.json. The separate edge map is tools/math_generators/university/prerequisites.json; it records the source commit, coverage fields, and per-topic prerequisite IDs.

ultron_core/curriculum_prerequisites.py validates exact topic coverage, unique IDs, no unknown or duplicate topics, no self-dependencies or dangling edges, no duplicate edges or cycles, and prerequisite-first topological order.

The Calculus field contains 30 topics. The former Green_stokes_divergence_theorems umbrella was split into greens_theorem_rectangles, stokes_theorem, and divergence_theorem. Only greens_theorem_rectangles has a generator, bounded to exact rational polynomial fields over non-degenerate axis-aligned rational rectangles; Stokes and divergence remain incomplete.

The former first_order_ODEs entry was replaced by four scoped items:
- homogeneous_constant_coefficient_first_order_ODEs — generator available for y'=k y with y(0)=y0 only.
- separable_first_order_ODEs — generator available only for bounded rational power-law equations y'=c*x^m*y^n; arbitrary separable factors remain unsupported.
- linear_first_order_variable_coefficient_ODEs — catalogued, no generator.
- exact_first_order_ODEs — catalogued, no generator.

The homogeneous ODE generator has an independent analytic validator for y(t)=y0 exp(k t), its derivative identity and initial condition. The separable ODE family is restricted to rational power-law factors y'=c*x^m*y^n with bounded integer powers and an independent exact derivative/initial-value validator. Neither family claims arbitrary first-order ODE solving.

Field counts are: Foundations and logic (10), Linear algebra (16), Calculus (30), Real analysis (13), Complex analysis (12), Abstract algebra (12), Number theory (10), Topology (10), Discrete mathematics and combinatorics (13), Probability (14), Statistics (9), Differential equations (17), Optimization and operations research (11), Numerical and computational mathematics (11), Geometry (9), Applied mathematics and mathematical physics (11), Advanced and interdisciplinary (10), totalling 218.

The prerequisite graph has 413 edges. It is a curated starting sequence, not an exhaustive universal course plan. The grade-band curricula still require separate dependency mapping. A mapped prerequisite is a proposed learning dependency, not proof that ULTRON has mastered it. No training data is generated or imported by this catalogue.


## Scope-specific calculus, complex-analysis, and ODE families

The catalogue now distinguishes general topics from several bounded exercise families. The broad `multiple_integrals`, `change_of_variables`, `line_integrals`, `surface_integrals`, and `vector_calculus` rows remain incomplete; the implemented IDs specify affine-polynomial integration over rectangles, diagonal linear substitutions on rectangles, constant-field segment line integrals, flat rectangular surface integrals of one, and divergence of diagonal linear fields respectively. These narrow templates are not evidence of general multivariable or vector calculus.

The broad `Taylor_series` row remains incomplete. `quadratic_Taylor_polynomials` is the available exact degree-two polynomial template. The complex-analysis compound rows were split into `complex_number_arithmetic`, `complex_topology`, `complex_Taylor_series`, and `Laurent_series`; only exact rational complex-number arithmetic currently has a generator.

The variable-coefficient linear first-order ODE row remains incomplete. The separate `homogeneous_variable_coefficient_linear_first_order_ODEs` family supports only `y' + a*x^m*y = 0` for nonzero rational a and m in {1,2}, with rational initial data and an exact logarithmic-derivative validator.


## Additional calculus, PDE, probability, and graph families

The current map includes `polynomial_vector_field_segment_line_integrals` as a bounded polynomial extension of the constant-vector-field segment case, and `rectangular_quadratic_polynomial_double_integrals` as a bounded extension of affine-polynomial rectangle integrals. Both are exact rational families, not general line- or multiple-integral solvers.

The `affine_transport_first_order_PDEs` topic covers only affine solutions of constant-coefficient transport equations (a u_x+b u_y=0). It is a prerequisite for `characteristics_PDE`, but does not claim general PDE solving.

The `binomial_distribution_exact_probabilities` family provides exact bounded binomial PMFs with normalization/mean/variance checks. The `finite_simple_graph_handshaking` family constructs bounded connected simple graphs and validates degrees and the handshaking identity.

Current university map: **218 topics across 17 fields**, with a prerequisite graph of **218 nodes and 413 directed edges**. This graph is a curated learning sequence, not proof of mastery.


## Bounded vector-calculus theorem families

The broad `stokes_theorem` and `divergence_theorem` topics remain incomplete. The additional `stokes_theorem_horizontal_rectangles` family checks Stokes' theorem only for affine fields (F=(P,Q,0)) on horizontal axis-aligned rectangles with upward normal and counter-clockwise boundary traversal. Its independent test sums all four oriented boundary-edge integrals and compares the result with the exact curl surface integral.

The `divergence_theorem_axis_aligned_boxes` family checks only diagonal linear fields (F=(ax,by,cz)) on axis-aligned rectangular boxes. Its independent test recomputes all six outward face fluxes and compares their sum with the exact volume integral of the divergence. Neither family is a general Stokes or divergence theorem solver.


## Phase 2 cumulative integration candidate — 2026-11-28

**Candidate branch:** `phase2/integrated-math-curriculum-2026-11-28`. This branch consolidates the multifield batch and bounded vector-calculus follow-up on top of the curriculum scope audit. It is an integration candidate, not a merge to `main`.

- University curriculum: **218 topics**, **71 generator-available**, **147 catalogued without a generator** (32.6% generator availability).
- Combined registry: **271 scope-qualified entries**, **124 generator-available**, **73 independently validated**.
- Prerequisite graph: **218 nodes / 413 directed edges**; all curriculum topics mapped, and graph acyclicity, edge validity, and duplicate checks are required by the audit.
- Trained-checkpoint benchmarks: **0**. Mastered topics: **0**.
- Broad parent topics remain incomplete where only a bounded subfamily exists. Each bounded family has its own scope-specific topic identifier.
- The integrated PR's exact-head CI is the final validation gate; prior individual batch checks passed, but that does not substitute for combined integration checks.

No model training, optimizer step on ULTRON weights, production corpus generation/download, remote training, external AI API, Pages deployment, Supabase mutation, or weight publication was performed.
