# Mathematical evaluation protocol — current foundation

**Status:** exact-answer scoring infrastructure for the current generated tasks; not a trained-model benchmark result.

## Current evaluator

`ultron_core/evaluation.py` accepts caller-supplied prediction strings and compares them with independently validated exact targets. Schema version 2 reports:

- attempted predictions (any non-`None` output);
- valid parsed answers (`answered`);
- exact correct count and incorrect-but-valid count;
- exact accuracy over all references and among valid answers;
- coverage (attempted / total), valid-answer rate (valid / total), and abstentions (only `None` outputs);
- invalid predictions separately, including non-string outputs, so malformed outputs are not incorrectly counted as abstentions;
- per-topic counts, coverage, validity, and accuracy.

The evaluator does not instantiate or run a neural model. Its output sets `model_evaluated=false`, `training_performed=false`, and `proof_verified=false`.

## Supported scope

Current generator topics are:
- integer arithmetic;
- rational arithmetic;
- simple one-variable linear equations;
- bounded polynomial derivatives with integer coefficients and degree 2–5.

For rational tasks, predictions are exact rational strings such as `-7/3` or `4`. For polynomial-derivative tasks, predictions use the bounded canonical polynomial grammar. It does not parse natural-language explanations, derivations, or proof steps.

## Held-out evaluation rules

1. Generate only from ULTRON's own deterministic generator.
2. Split by normalized prompt group using `split_examples`; duplicate prompts are collapsed before assignment.
3. Use train for fitting, validation for configuration/early stopping, and final test only for one final report.
4. Do not tune on the final test set or move failed examples between splits after inspecting model output.
5. Report the seed, generator version, dataset manifest digest, tokenizer version, model config, and raw prediction file.
6. Report per-topic accuracy and coverage; do not hide invalid outputs or abstentions.
7. Correct numeric answers are not evidence that the model generated a valid derivation or formal proof.

## Future evaluation prerequisites

Before any trained-model quality claim:
- freeze task serialization and tokenizer vocabulary;
- add broader independently verified task sets (algebra, calculus, linear algebra, discrete math, probability, analysis, etc.);
- add symbolic-equivalence checks where exact strings are too strict;
- use an independent proof checker for proof claims;
- pre-register primary metrics and keep a separate untouched test split;
- compare against deterministic baselines and report multiple seeds.

No model evaluation or training run has been performed as part of this protocol. The evaluator is still limited to the current four generated topics and exact-answer validation; broader university mathematics, symbolic equivalence, derivation scoring, and formal proof verification are not implemented.
