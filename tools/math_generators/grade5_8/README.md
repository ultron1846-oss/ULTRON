# ULTRON Grades 5–8 generators

Python 3.11; standard library only. Thirteen deterministic original-template generators cover decimals, fraction operations, ratios, percentages, integers, exponents, order of operations, linear equations, inequalities, basic geometry, angles, statistics, and probability. Contextual word-problem phrasings are included in ratios, percentages, integers, order of operations, linear equations, inequalities, geometry, angles, statistics, and probability.

```python
from tools.math_generators.grade5_8 import generate, verify
p = generate(seed=123, difficulty=3, topic="percentages")
assert verify(p)
```

Answers are checked before return. Difficulty is heuristic, and the package is curriculum question-source tooling—not evidence of trained model capability. Train/benchmark output is created only when the split script is explicitly run.
