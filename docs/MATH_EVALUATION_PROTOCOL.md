# Mathematical evaluation protocol — current foundation

**Status:** exact-answer scoring infrastructure for the current generated tasks; not a trained-model benchmark result.

## Current evaluator

`ultron_core/evaluation.py` accepts caller-supplied prediction strings and compares them with independently validated exact targets. Schema version 3 reports:

- attempted predictions (any non-`None` output);
- valid parsed answers (`answered`);
- exact correct count and incorrect-but-valid count;
- exact accuracy over all references and among valid answers;
- coverage (attempted / total), valid-answer rate (valid / total), and abstentions (only `None` outputs);
- invalid predictions separately, including non-string outputs, so malformed outputs are not incorrectly counted as abstentions;
- mutually exclusive error classes: abstention, malformed output, incorrect valid answer, and correct answer;
- per-topic error-class counts;
- exact semantic equivalence for supported polynomial derivatives (coefficient-map comparison) and rational/integral answers (exact fractions), even when output formatting differs;
- per-topic counts, coverage, validity, and accuracy.

The evaluator does not instantiate or run a neural model. Its output sets `model_evaluated=false`, `training_performed=false`, and `proof_verified=false`.

## Supported scope

Current generator topics (version 0.5.0) are:
- integer arithmetic;
- rational arithmetic;
- simple one-variable linear equations;
- bounded polynomial derivatives with integer coefficients and degree 2–5;
- exact definite integrals of integer-coefficient polynomials (degree 1–4, rational bounds);
- exact 2×2 matrix inverses for non-singular integer matrices, with rational matrix outputs.

For rational tasks, predictions are exact rational strings such as `-7/3` or `4`. For polynomial-derivative tasks, predictions use the bounded integer-polynomial grammar and are compared by exact coefficient maps rather than raw string equality. Definite-integral predictions use exact rational strings. Matrix-inverse predictions use a 2×2 rational matrix grammar and are compared entrywise with exact Fraction values. It does not parse natural-language explanations, derivations, or proof steps.

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

For the supported polynomial derivative topic, semantic equality is checked by exact integer-coefficient maps, not raw string comparison. Rational and definite-integral answers are compared as exact fractions. These equivalence checks are limited to the current generator grammar and are not a general-purpose computer algebra system.

No model evaluation or training run has been performed as part of this protocol.


## Stage A paired comparison gate

Use `ultron_core/benchmark_comparison.py` to compare ULTRON and the baseline on the exact same frozen `MathExample` references and prompt serialization. The tool accepts prediction maps from files; it does not invoke either model.

The preregistered default gate is:
- At least 200 examples for each topic (a minimum floor, not a power analysis).
- Higher exact accuracy for ULTRON on that topic.
- Two-sided exact McNemar/binomial test on paired per-example correctness, with Holm step-down correction across the included topics; adjusted p-value must be below 0.05.
- ULTRON coverage and valid-answer rate may not fall more than 2 percentage points below the baseline.
- Missing outputs count as abstentions; malformed outputs remain invalid, not abstentions.

The JSON report includes per-topic raw counts, paired wins/losses/ties, accuracy, coverage, validity, raw and adjusted p-values, and each gate condition. The default baseline label is Fable 5.2, but the code does not call Fable or any external AI service. Only actual, independently recorded prediction files can support a comparison claim. The default sample floor is not a substitute for prospective power analysis, and a Stage A pass is limited to the tested topics and benchmark version.
