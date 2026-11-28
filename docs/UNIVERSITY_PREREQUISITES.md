# University curriculum prerequisite map

**Status:** curated map for all 216 of 216 university curriculum topics across 17 fields. No university catalogue topic remains unmapped.

The source curriculum is tools/math_generators/university/curriculum.json. The separate edge map is tools/math_generators/university/prerequisites.json; it records the source commit, coverage fields, and per-topic prerequisite IDs.

ultron_core/curriculum_prerequisites.py validates exact topic coverage, unique IDs, no unknown or duplicate topics, no self-dependencies or dangling edges, no duplicate edges or cycles, and prerequisite-first topological order.

The Calculus field contains 28 topics. The former Green_stokes_divergence_theorems umbrella was split into greens_theorem_rectangles, stokes_theorem, and divergence_theorem. Only greens_theorem_rectangles has a generator, bounded to exact rational polynomial fields over non-degenerate axis-aligned rational rectangles; Stokes and divergence remain incomplete.

The former first_order_ODEs entry was replaced by four scoped items:
- homogeneous_constant_coefficient_first_order_ODEs — generator available for y'=k y with y(0)=y0 only.
- separable_first_order_ODEs — generator available only for bounded rational power-law equations y'=c*x^m*y^n; arbitrary separable factors remain unsupported.
- linear_first_order_variable_coefficient_ODEs — catalogued, no generator.
- exact_first_order_ODEs — catalogued, no generator.

The homogeneous ODE generator has an independent analytic validator for y(t)=y0 exp(k t), its derivative identity and initial condition. The separable ODE family is restricted to rational power-law factors y'=c*x^m*y^n with bounded integer powers and an independent exact derivative/initial-value validator. Neither family claims arbitrary first-order ODE solving.

Field counts are: Foundations and logic (10), Linear algebra (16), Calculus (26), Real analysis (13), Complex analysis (12), Abstract algebra (12), Number theory (10), Topology (10), Discrete mathematics and combinatorics (12), Probability (13), Statistics (9), Differential equations (16), Optimization and operations research (11), Numerical and computational mathematics (11), Geometry (9), Applied mathematics and mathematical physics (11), and Advanced and interdisciplinary (10), totalling 211.

The prerequisite graph has 409 edges. It is a curated starting sequence, not an exhaustive universal course plan. The grade-band curricula still require separate dependency mapping. A mapped prerequisite is a proposed learning dependency, not proof that ULTRON has mastered it. No training data is generated or imported by this catalogue.


## Scope-specific calculus, complex-analysis, and ODE families

The catalogue now distinguishes general topics from several bounded exercise families. The broad `multiple_integrals`, `change_of_variables`, `line_integrals`, `surface_integrals`, and `vector_calculus` rows remain incomplete; the implemented IDs specify affine-polynomial integration over rectangles, diagonal linear substitutions on rectangles, constant-field segment line integrals, flat rectangular surface integrals of one, and divergence of diagonal linear fields respectively. These narrow templates are not evidence of general multivariable or vector calculus.

The broad `Taylor_series` row remains incomplete. `quadratic_Taylor_polynomials` is the available exact degree-two polynomial template. The complex-analysis compound rows were split into `complex_number_arithmetic`, `complex_topology`, `complex_Taylor_series`, and `Laurent_series`; only exact rational complex-number arithmetic currently has a generator.

The variable-coefficient linear first-order ODE row remains incomplete. The separate `homogeneous_variable_coefficient_linear_first_order_ODEs` family supports only `y' + a*x^m*y = 0` for nonzero rational a and m in {1,2}, with rational initial data and an exact logarithmic-derivative validator.


## Additional calculus, PDE, probability, and graph families

The current map includes `polynomial_vector_field_segment_line_integrals` as a bounded polynomial extension of the constant-vector-field segment case, and `rectangular_quadratic_polynomial_double_integrals` as a bounded extension of affine-polynomial rectangle integrals. Both are exact rational families, not general line- or multiple-integral solvers.

The `affine_transport_first_order_PDEs` topic covers only affine solutions of constant-coefficient transport equations (a u_x+b u_y=0). It is a prerequisite for `characteristics_PDE`, but does not claim general PDE solving.

The `binomial_distribution_exact_probabilities` family provides exact bounded binomial PMFs with normalization/mean/variance checks. The `finite_simple_graph_handshaking` family constructs bounded connected simple graphs and validates degrees and the handshaking identity.

Current university map: **216 topics across 17 fields**, with a prerequisite graph of **216 nodes and 409 directed edges**. This graph is a curated learning sequence, not proof of mastery.
