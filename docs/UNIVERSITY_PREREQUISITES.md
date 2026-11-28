# University curriculum prerequisite map

**Status:** curated map for all 200 of 200 university curriculum topics across 17 fields. No university catalogue topic remains unmapped.

The source curriculum is tools/math_generators/university/curriculum.json. The separate edge map is tools/math_generators/university/prerequisites.json; it records the source commit, coverage fields, and per-topic prerequisite IDs.

ultron_core/curriculum_prerequisites.py validates:
- exact coverage of all declared fields;
- no unknown or duplicate topic IDs;
- no self-dependencies or dangling prerequisite edges;
- no duplicate edges or cycles;
- a topological order with prerequisites before dependent topics.

The Calculus field now contains 20 topics. The former Green_stokes_divergence_theorems umbrella was split into three distinct entries: greens_theorem_rectangles, stokes_theorem, and divergence_theorem. The first has a generator only for exact rational polynomial fields on non-degenerate axis-aligned rational rectangles. Stokes' theorem and the divergence theorem remain catalogued but unimplemented. Their prerequisite edges are explicit and preserve the distinction between line integrals, surface integrals and multiple integrals.

The mapped field counts are: Foundations and logic (10), Linear algebra (16), Calculus (20), Real analysis (13), Complex analysis (10), Abstract algebra (12), Number theory (10), Topology (10), Discrete mathematics and combinatorics (12), Probability (13), Statistics (9), Differential equations (13), Optimization and operations research (11), Numerical and computational mathematics (11), Geometry (9), Applied mathematics and mathematical physics (11), and Advanced and interdisciplinary (10).

The 373 edges are a curated starting sequence, not an exhaustive universal course plan. Different degree programs may introduce topics in a different order. A mapped prerequisite is a proposed learning dependency, not proof that ULTRON has mastered it.

All current university catalogue topics have curated prerequisite edges. The grade-band curricula still require separate dependency mapping. No training data is generated or imported by this catalogue.


## ODE scope correction (2026-11-28)

The broad first_order_ODEs entry is a prerequisite/catalogue concept only and has no broad generator. The bounded linear_constant_coefficient_first_order_ODEs family is a child topic with first_order_ODEs as its prerequisite. The prerequisite map now covers 200 nodes; the additional ODE edge brings the graph to 373 directed edges. Other first-order ODE classes remain incomplete.
