# Dataset balance and coverage report

`ultron_core.data_generation.summarize_corpus` reports a supplied collection of generated examples without creating a dataset or running training.

The report includes:

- total examples and unique/duplicate example IDs;
- normalized unique prompt groups and duplicate prompt count;
- independently validated versus invalid rows;
- topic counts and proportions;
- difficulty distribution overall and per topic;
- when train/validation/test splits are supplied, split sizes and normalized prompt-group overlap.

A `splits_prompt_disjoint=false` result is a hard data-review finding: do not train until the split is rebuilt and leakage is eliminated. This report diagnoses the supplied rows; it does not repair or silently deduplicate them.

The function is deterministic for the same input collection. It reports `data_generated=false` and `training_performed=false`; it does not write files, access external data, instantiate the model, or run an optimizer.

Example:

```python
from ultron_core.data_generation import generate_examples, split_examples, summarize_corpus

examples = generate_examples(seed=2026, count=1000)
splits = split_examples(examples, seed=2026)
report = summarize_corpus(examples, splits=splits)
assert report["invalid_example_count"] == 0
assert report["splits_prompt_disjoint"]
```

This is a structural coverage report, not a claim that the generated topics represent university mathematics or that the model has learned them.
