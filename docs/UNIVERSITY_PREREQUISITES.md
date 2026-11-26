# University curriculum prerequisite map

**Status:** curated map for Foundations and logic, Linear algebra, Calculus, and Real analysis (133 of 197 topics). The remaining 64 topics are intentionally unmapped.

The source curriculum is `tools/math_generators/university/curriculum.json`. The separate edge map is `tools/math_generators/university/prerequisites.json`; it records the source commit, coverage fields, and per-topic prerequisite IDs.

`ultron_core/curriculum_prerequisites.py` loads and validates the map:
- exact coverage of the declared fields;
- no unknown or duplicate topic IDs;
- no self-dependencies or dangling prerequisite edges;
- no cycles;
- a topological order with prerequisites before dependent topics.

The current mapped fields are Foundations and logic (10), Linear algebra (16), Calculus (18), Real analysis (13), Complex analysis (10), Abstract algebra (12), Number theory (10), Topology (10), Discrete mathematics and combinatorics (12), Probability (13), and Statistics (9). The edges are a curated starting sequence, not an exhaustive universal course plan. Different degree programs may introduce topics in a different order. A mapped prerequisite is a proposed learning dependency, not proof that ULTRON has mastered it.

Do not infer prerequisites for unmapped topics. Expand the map in small reviewed groups, preserve the source curriculum revision, and add regression tests for each group. No training data is generated or imported by this catalog.
