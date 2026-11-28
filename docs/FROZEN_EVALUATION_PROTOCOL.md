# Frozen math evaluation protocol v2

**Scope:** Deterministic evaluation fixtures and leakage-safe metadata only. This document describes engineering infrastructure, not model results.

## 1. Deterministic task suite

Use `build_deterministic_math_task_suite(seed=..., examples_per_topic=...)` to create a bounded in-memory test suite from existing generators. The default suite covers the eight currently supported exact generator topics. `examples_per_topic` is bounded from 1 to 100, so a single call returns no more than 800 examples.

The suite:
- is reproducible from seed, topic list, generator version and per-topic count;
- validates each exact reference with the separate `validate_example_text` path;
- returns a manifest containing the sorted example IDs, topic coverage and SHA-256 fingerprint;
- writes no JSONL dataset, corpus or training split;
- is marked `evaluation_only`, with `training_performed=false` and `corpus_written=false`.

These are synthetic exact-answer regression fixtures. Their availability does not imply a trained model's ability.

## 2. Freeze three disjoint splits

Before any model evaluation, supply three reviewed sets to `build_frozen_evaluation_manifest`:

- `train_examples`: records permitted for training;
- `validation_examples`: records permitted for model selection and validation only;
- `evaluation_examples`: final held-out records, never used for optimizer training, model selection or threshold tuning.

The builder requires a non-empty set for every split and re-validates every reference answer. It rejects cross-split overlap in:

1. example IDs;
2. whitespace-normalized and case-folded prompt hashes;
3. hashes of generator ingredients (generator version, topic, difficulty, seed, index and generation parameters).

The final evaluation split receives one explicit curator-supplied category for every example. The transfer-category contract is checked against the **union of train and validation**, not training alone. An example cannot be labelled as an unseen concept when that concept appears in validation.

A non-empty `benchmark_revision` is required and is included in the manifest. Use an immutable source commit or frozen curation revision, not a mutable branch name.

## 3. Manifest contents and verification

The returned manifest fingerprints sorted per-example records, exact reference-answer hashes, topic/generator metadata, concept annotations, category labels, benchmark revision and the current concept-registry digest. Prompt text and answer text are not embedded in the manifest.

Use `verify_frozen_evaluation_manifest` to rebuild the manifest from the same three source collections and compare the complete content and SHA-256 digest. This is a deterministic integrity check; it does not establish that human curation was correct.

## 4. Transfer categories

Supported evaluation categories are:

- `unseen_surface_form`: a reviewed change of wording/representation for a supported task concept;
- `unseen_numeric_values`: numeric values not present in train or validation prompts;
- `multi_concept_composition`: at least two explicit concept IDs;
- `prerequisite_sensitive`: a task whose concept has documented prerequisites;
- `unseen_concept`: a concept absent from both train and validation.

The category labels are curated metadata. The validator checks the locally verifiable conditions, but it does not infer task semantics or discover all near-duplicates. Manual/independent review of semantic paraphrases and category labels remains mandatory.

## 5. Scoring

`evaluate_predictions` accepts caller-supplied prediction strings keyed by example ID. It does not invoke a model. Exact scoring remains the default (`absolute_tolerance=0`, `relative_tolerance=0`).

Optional numeric tolerances:
- use exact rational arithmetic over the decimal/rational strings rather than floating-point epsilon comparisons;
- apply only to supported scalar numeric topics;
- are counted separately as `within_numeric_tolerance`;
- never overwrite `exact_correct` or `exact_accuracy`.

Schema-v4 reports include coverage, valid-answer rate, exact accuracy, accepted accuracy, and per-topic answer-level error classes. Detailed classes are abstention, malformed output, domain-invalid output, mathematically incorrect answer, exact correct answer and tolerance-accepted answer.

The report explicitly states `reasoning_trace_scored=false`, `proof_verified=false`, `model_evaluated=false` and `training_performed=false`. A well-formed incorrect final answer cannot identify the actual cause of a reasoning failure. No derivation or formal-proof validation is implied.

## 6. Release requirements

Before using the benchmark to report model performance:
- provide a valid, independently verified checkpoint;
- freeze the model/tokenizer/task contract and benchmark revision;
- verify the three-way manifest and preserve it with the run;
- complete semantic near-duplicate review and independent reference verification;
- run model-only evaluation with tool access disabled and report any tool-assisted results separately;
- keep final evaluation data out of training, model selection and threshold tuning;
- record environment, hardware, runtime, checkpoint hash and benchmark manifest hash.

No valid trained checkpoint or owner-curated frozen final benchmark is currently available. Do not report accuracy, generalization, mathematics mastery or reasoning capability from synthetic fixture tests or caller-supplied answer maps.
