# ULTRON Grade 8–12 generators

Batch 3 adds 22 deterministic, original-template topics spanning algebra, geometry, trigonometry, precalculus, calculus, matrices, combinatorics, number theory, complex numbers, vectors, statistics, probability, and a limited divisibility proof template.

Topics and grade bands are in `registry.json`. Each item includes its seed, ingredients, solution steps, answer, and a replay-based exact verifier. The optional semantic validator checks selected real-world domains after the topic verifier.

```python
from tools.math_generators.grade8_12 import generate, verify

item = generate(seed=123, difficulty=3, topic="derivatives")
assert verify(item)
```

Run the randomized test suite with the repository's Python AI Core Tests workflow. The generator is not a trained model. The `proof_logic` topic is a narrow divisibility template; it is not a general formal proof checker. Difficulty is heuristic and needs curriculum calibration.

No training or dataset generation is performed by importing or testing this package.
