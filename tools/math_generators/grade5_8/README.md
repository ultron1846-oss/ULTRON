# ULTRON Grades 5–8 generators

Python 3.11; standard library only. Thirteen deterministic original-template generators cover decimals, fraction operations, ratios, percentages, integers, exponents, order of operations, linear equations, inequalities, basic geometry, angles, statistics, and probability. Contextual word-problem phrasings are included in ratios, percentages, integers, order of operations, linear equations, inequalities, geometry, angles, statistics, and probability.

```python
from tools.math_generators.grade5_8 import generate, verify
p = generate(seed=123, difficulty=3, topic="percentages")
assert verify(p)
```

Answers are checked before return. Difficulty is heuristic, and the package is curriculum question-source tooling—not evidence of trained model capability. Train/benchmark output is created only when the split script is explicitly run.


## Semantic validation and registry source of truth

Each topic declares its grade band and contextual template identifiers in `GENERATOR_METADATA`. Run `python -m tools.math_generators.build_registry` from the repository root to regenerate both the Grade 5–8 registry and the combined registry. Tests compare the committed JSON with the generated rendering, preventing contextual-coverage flags from drifting.

The optional `semantic_check(ingredients, answer)` hook runs after the exact topic verifier. It checks percentage quantity types, integer counts, non-negative geometry, valid supplementary angles, valid probability bounds, and contextual statistics/equation constraints.

Percentage generation distinguishes `count` from `continuous` quantities. For counts, the total is selected as a multiple of `100 / gcd(percent, 100)`, so the result is an integer. Continuous answers are exact to at most two decimal places; money prompts state cent rounding and distance prompts state hundredth rounding.

Audit findings fixed in this batch:
- Percentages could produce fractional people; count totals now satisfy the divisibility condition.
- Quiz-score templates could exceed 100; score contexts now stay within 0–100.
- Contextual ticket equations could have negative totals; contextual selection now requires non-negative values.
- Cost inequalities now specify a non-negative unit variable and use valid contextual bounds.
- Geometry dimensions, ratio counts, statistics values, and probability counts are checked for valid domains.

Regression tests cover 2,500 percentage seeds across all five difficulty levels, deterministic replay, distinct-seed variation, complete contextual-topic declarations, and registry parity. This remains question-generator validation—not a trained-model capability result.
