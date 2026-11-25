# ULTRON Grade 1–4 generators

Batch 1 contains ten deterministic, original-template generators. Python 3.11, standard library only.

```python
from tools.math_generators.grade1_4 import generate, verify
p = generate(seed=123, difficulty=3, topic="addition")
assert verify(p)
print(p)
```

Topics and grade bands are listed in `registry.json`. Each generated item is checked before return; `verify()` checks deterministic replay and an arithmetic/inverse invariant. Difficulty is heuristic, not curriculum-calibrated. Generated records are question-source tooling, not model capability or training. Do not run training without explicit authorization.

Create separate training and held-out JSONL files:

```bash
python tools/math_generators/grade1_4/split_dataset.py --count-per-topic 100 --out data/grade1_4
```

Train and benchmark seeds use different ranges. The script also checks normalized prompt-answer fingerprints for overlap.
