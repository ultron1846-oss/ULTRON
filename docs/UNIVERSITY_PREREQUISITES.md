# University curriculum prerequisite map

**Status:** curated map for all 218 of 218 university curriculum topics across 17 fields. No university catalogue topic remains unmapped.

The source curriculum is tools/math_generators/university/curriculum.json. The separate edge map is tools/math_generators/university/prerequisites.json; it records the source commit, coverage fields, and per-topic prerequisite IDs.

ultron_core/curriculum_prerequisites.py validates exact topic coverage, unique IDs, no unknown or duplicate topics, no self-dependencies or dangling edges, no duplicate edges or cycles, and prerequisite-first topological order.

The Calculus field contains 26 topics. The former Green_stokes_divergence_theorems umbrella was split into greens_theorem_rectangles, stokes_theorem, and divergence_theorem. Only greens_theorem_rectangles has a generator, bounded to exact rational polynomial fields over non-degenerate axis-aligned rational rectangles; Stokes and divergence remain incomplete.

The former first_order_ODEs entry was replaced by four scoped items:
- homogeneous_constant_coefficient_first_order_ODEs — generator available for y'=k y with y(0)=y0 only.
- separable_first_order_ODEs — generator available only for bounded rational power-law equations y'=c*x^m*y^n; arbitrary separable factors remain unsupported.
- linear_first_order_variable_coefficient_ODEs — catalogued, no generator.
- exact_first_order_ODEs — catalogued, no generator.

The homogeneous ODE generator has an independent analytic validator for y(t)=y0 exp(k t), its derivative identity and initial condition. The separable ODE family is restricted to rational power-law factors y'=c*x^m*y^n with bounded integer powers and an independent exact derivative/initial-value validator. Neither family claims arbitrary first-order ODE solving.

Field counts are: Foundations and logic (10), Linear algebra (16), Calculus (28), Real analysis (13), Complex analysis (12), Abstract algebra (12), Number theory (10), Topology (10), Discrete mathematics and combinatorics (12), Probability (14), Statistics (10), Differential equations (19), Optimization and operations research (11), Numerical and computational mathematics (11), Geometry (9), Applied mathematics and mathematical physics (11), and Advanced and interdisciplinary (10), totalling 218.

The prerequisite graph has 412 edges. It is a curated starting sequence, not an exhaustive universal course plan. The grade-band curricula still require separate dependency mapping. A mapped prerequisite is a proposed learning dependency, not proof that ULTRON has mastered it. No training data is generated or imported by this catalogue.


## Scope-specific calculus, complex-analysis, and ODE families

The catalogue now distinguishes general topics from several bounded exercise families. The broad `multiple_integrals`, `change_of_variables`, `line_integrals`, `surface_integrals`, and `vector_calculus` rows remain incomplete; the implemented IDs specify affine-polynomial integration over rectangles, diagonal linear substitutions on rectangles, constant-field segment line integrals, flat rectangular surface integrals of one, and divergence of diagonal linear fields respectively. These narrow templates are not evidence of general multivariable or vector calculus.

The broad `Taylor_series` row remains incomplete. `quadratic_Taylor_polynomials` is the available exact degree-two polynomial template. The complex-analysis compound rows were split into `complex_number_arithmetic`, `complex_topology`, `complex_Taylor_series`, and `Laurent_series`; only exact rational complex-number arithmetic currently has a generator.

The variable-coefficient linear first-order ODE row remains incomplete. The separate `homogeneous_variable_coefficient_linear_first_order_ODEs` family supports only `y' + a*x^m*y = 0` for nonzero rational a and m in {1,2}, with rational initial data and an exact logarithmic-derivative validator.


## Bounded vector-calculus theorem families

The broad `stokes_theorem` and `divergence_theorem` topics remain incomplete. The additional `stokes_theorem_horizontal_rectangles` family checks Stokes' theorem only for affine fields (F=(P,Q,0)) on horizontal axis-aligned rectangles with upward normal and counter-clockwise boundary traversal. Its independent test sums all four oriented boundary-edge integrals and compares the result with the exact curl surface integral.

The `divergence_theorem_axis_aligned_boxes` family checks only diagonal linear fields (F=(ax,by,cz)) on axis-aligned rectangular boxes. Its independent test recomputes all six outward face fluxes and compares their sum with the exact volume integral of the divergence. Neither family is a general Stokes or divergence theorem solver.


## Bounded exact first-order ODE family

The broad `exact_first_order_ODEs` topic remains incomplete. The separate `quadratic_potential_exact_first_order_ODEs` family covers exact one-forms derived from a quadratic potential `Phi(x,y)=a*x^2+b*x*y+c*y^2`. Its coefficients and initial point are bounded exact rationals, and its implicit solution is `Phi(x,y)=Phi(x0,y0)`. The independent tests verify both potential derivatives, equality of the mixed partial derivatives, the initial level-set constant, and tamper rejection. This is not a general exact-ODE solver.


## Bounded second-order ODE and transport PDE families

The broad `second_order_linear_ODEs` row remains incomplete. The new `distinct_real_root_second_order_linear_homogeneous_ODEs` family covers homogeneous constant-coefficient equations whose characteristic polynomial has two distinct real rational roots. It computes the exponential solution from two rational initial conditions and validates both characteristic roots and the initial equations exactly. Repeated roots, complex roots, forcing terms, and variable coefficients are not included.

The broad `characteristics_PDE` row remains incomplete. The new `constant_speed_transport_polynomial_initial_data_PDEs` family covers only (u_t+c u_x=0) with nonzero rational constant speed and polynomial initial data of degree at most three. Its independent test evaluates the PDE residual at rational points and checks the initial data at (t=0). It does not represent general first-order PDE support.


## Bounded probability and statistics families

The broad `discrete_distributions` and `expectation_and_variance` topics remain catalogued but unimplemented. The scoped `binomial_distribution_point_probabilities` family computes one exact binomial point probability, mean and variance for bounded trial counts and rational success probabilities. The scoped `finite_discrete_distribution_expectation_variance` family computes exact moments for a three-point finite distribution with integer support and relative weights. Tests independently normalize probabilities, recompute moments, and verify the binomial PMF sums to one over its full support. These families do not imply coverage of arbitrary named distributions or general statistical inference.
