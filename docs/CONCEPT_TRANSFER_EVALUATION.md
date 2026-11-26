# Core concept taxonomy and transfer evaluation protocol

**Status:** validated metadata and split-protocol infrastructure for ULTRON's eight core exact-synthetic generator topics. This is not a trained capability result and does not create a dataset.

## Concept-first contract

Each core generator topic maps to a stable concept ID with:
- a mathematical principle;
- prerequisite concept IDs;
- assumptions or conditions;
- a common misconception.

The registry is in `ultron_core/concepts.py`. Its validator checks complete topic coverage, valid prerequisite references, and acyclicity. The taxonomy is intentionally narrow: it does not yet map all 197 topics in the university curriculum registry, and several concepts are prerequisite nodes without a dedicated generator.

## Concept-aware curation

`sample_concept_balanced(examples, max_per_concept, seed)` deterministically caps supplied examples per concept. It only selects existing examples; it does not generate or augment them. `concept_coverage_report` reports topic-to-concept coverage and missing concepts.

For future curation, preserve source/example IDs and group near-duplicate prompts before sampling. Concept labels must be assigned from reviewed mathematical content or trusted generator metadata, not silently produced by command tools. A concept label or ingestion count is not evidence of mastery.

## Held-out transfer protocol v1

Before a model-quality evaluation:

1. Freeze the concept registry version, tokenizer/task serialization, generator/source revision, and evaluation manifest.
2. Split by exact normalized prompt groups; also review semantic near-duplicates manually. No test prompt or near-duplicate may enter training.
3. Keep final test examples out of optimizer training, model selection, and threshold tuning.
4. Curate test examples into one or more categories:
   - `unseen_surface_form`: different wording or representation for a supported concept;
   - `unseen_numeric_values`: values absent from training prompts;
   - `multi_concept_composition`: a task requiring at least two annotated concepts;
   - `prerequisite_sensitive`: a task whose solution depends on a documented prerequisite;
   - `unseen_concept`: a concept absent from the training concept set.
5. Record category labels, concept IDs, prompt hashes, source/provenance, and independent answer-verifier status.
6. Report exact correctness, coverage, valid-answer rate, abstention, and invalid output by concept and transfer category. Report model-only results separately from any tool-assisted result.
7. Use an independent exact verifier for answers; use a genuine proof checker only for formal-proof claims.

`validate_concept_transfer_split` checks train/test ID and normalized-prompt isolation, validates category labels, confirms unseen numeric values, requires multiple concept IDs for composition, verifies prerequisites for prerequisite-sensitive examples, and ensures unseen-concept labels refer to concepts absent from training.

## Limits and next work

- Exact normalized-prompt disjointness does not detect all semantic paraphrases; human or independently validated near-duplicate review remains required.
- Numeric novelty is a lexical check, not semantic novelty.
- Transfer categories are curator-supplied; the validator checks their locally verifiable properties but does not infer them.
- The core taxonomy covers only the current eight exact-synthetic topics. Extend concept/prerequisite coverage across curriculum generators before claiming broad concept transfer.
- No corpus download/import, data augmentation, optimizer step, training, or remote execution is performed by this protocol.
