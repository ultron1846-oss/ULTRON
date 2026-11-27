# ULTRON training recovery and evaluation audit

**Audit date:** 2026-11-27  
**Work areas:** Prompt 3, work areas 5–6  
**Implementation branch:** `reliability/evaluation-batch-5-2026-11-27`  
**Status:** Synthetic regression work and documentation added; exact-head CI/review pending.  
**Training:** Not started. No ULTRON optimizer step has been executed.

## Executive summary

The repository already had a substantial recovery foundation: checkpoint format v5, SHA-256 integrity manifests, a previous verified backup, optimizer/scheduler/model/RNG state rollback, dataset-bound sampler cursors, deterministic resume ordering, and a bounded trainer with cancellation and cleanup boundaries.

This batch adds the missing end-to-end process boundary test for **Python and Torch CPU RNG restoration** together with restored model weights and the exact remaining sampler sequence. The test saves a small initialized model and synthetic dataset cursor, then starts a separate Python process, restores the checkpoint, and compares RNG draws, a model-state fingerprint, and the remaining sampler tail. No optimizer object or optimizer step is used in that test.

It also adds explicit rollback coverage for a checkpoint whose Python RNG state is valid but whose Torch CPU RNG state is malformed. The failure occurs after the Python RNG has been changed; the test asserts that model, optimizer, scheduler, Python RNG and Torch RNG all return to their pre-load state. The interrupted manifest-commit test now also asserts that temporary checkpoint and manifest files are cleaned up.

For evaluation, the batch adds a bounded deterministic in-memory suite spanning all eight currently supported exact generator topics, an optional exact-rational absolute/relative tolerance, a more detailed answer-error taxonomy, and a frozen three-way train/validation/final-evaluation manifest. The final evaluation split is checked against the union of train and validation examples, so validation concepts count as previously seen for an `unseen_concept` claim.

## Work area 5 — training engine and recovery

### Existing safeguards confirmed by source review

- Checkpoint format v5 accepts supported historical formats 2–5. The payload includes model state, config, global step, optional optimizer/scheduler state, Python/Torch RNG state, optional data cursor, dataset manifest digest and training settings.
- A SHA-256 sidecar is checked before the checkpoint payload is deserialized. Restore validates format, config, tensor names/shapes/layouts/dtypes, optimizer/scheduler state, cursor contract and dataset hash before mutating runtime state.
- Checkpoint restore snapshots model, optimizer, scheduler and RNG state and rolls them back if the restore transaction fails.
- Checkpoint bundles comprise the `.pt` file, `.sha256` integrity manifest and metadata-only `.metadata.json` sidecar. A save retains at most one previous verified generation.
- `ResumableRandomSampler` is bound to dataset size, dataset digest, seed and epoch. Its permutation is deterministic from seed and epoch; state stores the next sample index. Exact mid-epoch restore requires a `DataLoader` with `num_workers=0` and `drop_last=False`, with batch and sample cursor alignment enforced by the trainer.
- The bounded trainer restores sampler state before iterator creation, rewinds uncommitted microbatches on cancellation/incomplete accumulation, resets model memory, clears gradients, restores activation-checkpointing mode and restores the model's prior train/eval mode in a `finally` block.

### Additional regression coverage

- Fresh-process resume: new subprocess restores the checkpoint's model weights and exact Python/Torch CPU RNG continuation; it also restores the saved sampler cursor and reproduces the remaining deterministic sample order.
- Restore rollback: a malformed Torch RNG payload that fails after a valid alternate Python RNG state was applied must roll back model, optimizer, scheduler, Python RNG and Torch RNG.
- Interrupted write: simulated failure while committing the checksum manifest must fall back to the previous verified checkpoint; temporary checkpoint and manifest files must not remain.
- Existing transfer/recovery tests continue to cover bundle copy to another directory, optimizer/scheduler state reconstruction from synthetic state, corruption fallback and checksum-bound metadata.

### Recovery limits

- The subprocess test verifies CPU RNG only. CUDA RNG serialization is present in source, but a separate CUDA device-count/topology replay test is not run on this CPU CI path.
- The checkpoint and its two sidecars are replaced as separate filesystem operations, not one atomic multi-file transaction. An interruption between replacements may invalidate the current generation; recovery depends on a prior verified backup. A first-ever checkpoint has no backup fallback.
- Only one previous verified generation is retained.
- Clean-process testing uses a synthetic local temporary directory, not a real free-cloud runtime, transferred iPad session or external filesystem.
- Sampler-sequence equivalence is tested; numerical equivalence of an uninterrupted real training run and a resumed real training run is not established and remains unauthorized.
- The test suite does not execute a real ULTRON optimizer step or train ULTRON.

## Work area 6 — evaluation and mathematical reasoning tests

### Deterministic task suite

`build_deterministic_math_task_suite` provides a bounded in-memory suite across the eight currently supported exact generator topics. It is limited to 1–100 examples per topic (at most 800 examples per call), is deterministic by seed/topic, independently rechecks every reference with `validate_example_text`, and returns a stable ID manifest. It writes no dataset or corpus and is explicitly marked evaluation-only.

### Frozen three-way manifest

`build_frozen_evaluation_manifest` requires caller-supplied non-empty train, validation and final evaluation splits. It binds:

- unique example IDs across all three splits;
- whitespace-normalized, case-folded prompt hashes;
- generation-ingredient hashes independent of the emitted prompt;
- topic, difficulty, generator version, seed and index;
- exact reference-answer hashes;
- concept IDs and the concept-registry digest;
- curator-supplied evaluation transfer categories and a required benchmark revision identifier.

Raw prompt and answer strings are not copied into the manifest. Input order does not change the digest. `verify_frozen_evaluation_manifest` rebuilds and compares the fingerprint from the supplied examples.

The evaluation categories are checked against the union of train and validation examples. This means a concept seen in validation cannot be labelled unseen in the final evaluation set. IDs, normalized prompts and generator ingredients are required to be disjoint across train, validation and final evaluation.

### Scoring and error taxonomy

Evaluation report schema v4 retains strict exact scoring as the default. Optional absolute and relative tolerance values apply only to documented scalar numeric task topics. Tolerance-accepted outputs are reported separately from exact answers and do not increase `exact_accuracy`.

The detailed answer-level taxonomy distinguishes:
- `abstention`;
- `malformed_output`;
- `domain_invalid_output` (for example, an undefined rational such as division by zero);
- `mathematically_incorrect_answer` (well-formed but incorrect final answer);
- `exact_correct_answer`;
- `within_numeric_tolerance` (only when explicitly enabled).

This is a final-answer taxonomy. It does **not** assess derivation validity, chain-of-thought quality, theorem-proof soundness or the cause of a reasoning failure. Formal proof checking is not implemented.

### Independent correctness boundary

The suite builder and frozen-manifest builder re-run the existing independent exact reference validator, which parses task text and recomputes supported answers separately from the generator's answer assignment path. This is useful deterministic regression coverage; it is not a formally verified proof kernel or external human review.

### Evaluation limits

- The frozen manifest infrastructure is implemented, but an owner-curated production benchmark with human-reviewed semantic near-duplicates and reviewed category labels has not been supplied.
- Exact normalized prompt and generator-ingredient isolation cannot guarantee detection of every semantic paraphrase. Near-duplicate review remains a manual/independent curation responsibility.
- The implemented concept taxonomy maps the eight core generator topics; it is not a complete mapping of all grade-band and university curriculum tasks.
- Symbolic equivalence is exact for the currently documented polynomial/rational task grammars, not general symbolic mathematics.
- No valid trained checkpoint exists for reporting model accuracy, transfer performance or reasoning capability. These utilities score caller-supplied predictions and explicitly report `model_evaluated=false`.
- No model performance, mathematical mastery, proof capability or training progress is claimed.

## Validation gate

The implementation is on the branch listed above. Run the Python AI Core regression suite, Node Tests and Level 1 Math Tooling against the exact PR head. Only after checks pass and review is complete should the PR be merged. Manual clean-runtime checkpoint transfer, CUDA RNG replay, semantic near-duplicate curation and any later real-model evaluation remain separate acceptance items.
