# University curriculum prerequisite map

**Status:** curated map for all 202 of 202 university curriculum topics across 17 fields. No university catalogue topic remains unmapped.

The source curriculum is tools/math_generators/university/curriculum.json. The separate edge map is tools/math_generators/university/prerequisites.json; it records the source commit, coverage fields, and per-topic prerequisite IDs.

ultron_core/curriculum_prerequisites.py validates exact topic coverage, unique IDs, no unknown or duplicate topics, no self-dependencies or dangling edges, no duplicate edges or cycles, and prerequisite-first topological order.

The Calculus field contains 20 topics. The former Green_stokes_divergence_theorems umbrella was split into greens_theorem_rectangles, stokes_theorem, and divergence_theorem. Only greens_theorem_rectangles has a generator, bounded to exact rational polynomial fields over non-degenerate axis-aligned rational rectangles; Stokes and divergence remain incomplete.

The former first_order_ODEs entry was replaced by four scoped items:
- homogeneous_constant_coefficient_first_order_ODEs — generator available for y'=k y with y(0)=y0 only.
- separable_first_order_ODEs — catalogued, no generator.
- linear_first_order_variable_coefficient_ODEs — catalogued, no generator.
- exact_first_order_ODEs — catalogued, no generator.

The narrow ODE generator has an independent analytic validator for y(t)=y0 exp(k t), its derivative identity and its initial condition. It does not claim arbitrary first-order ODE solving.

Field counts are: Foundations and logic (10), Linear algebra (16), Calculus (20), Real analysis (13), Complex analysis (10), Abstract algebra (12), Number theory (10), Topology (10), Discrete mathematics and combinatorics (12), Probability (13), Statistics (9), Differential equations (15), Optimization and operations research (11), Numerical and computational mathematics (11), Geometry (9), Applied mathematics and mathematical physics (11), and Advanced and interdisciplinary (10), totalling 202.

The prerequisite graph has 378 edges. It is a curated starting sequence, not an exhaustive universal course plan. The grade-band curricula still require separate dependency mapping. A mapped prerequisite is a proposed learning dependency, not proof that ULTRON has mastered it. No training data is generated or imported by this catalogue.
