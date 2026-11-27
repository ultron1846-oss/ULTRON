# ULTRON owner notebook setup

**Artifact:** [notebooks/ULTRON_OWNER_PREFLIGHT.ipynb](../notebooks/ULTRON_OWNER_PREFLIGHT.ipynb)  
**Scope:** runtime config, formula-based capacity, manifest-bound split verification, tokenization limits, and non-authorizing dataset preflight only.

## What it does

1. Checks the repository contains `ultron_core/`.
2. Validates the website-exported schema-v1 runtime config and non-authorizing flags.
3. Calculates foundation parameter counts by formula without allocating weights.
4. Verifies an existing ULTRON JSONL dataset and sidecar manifest.
5. Writes deterministic, prompt-disjoint split-ID metadata bound to the exact dataset SHA-256.
6. Adapts verified records to MathExample, checks canonical tokenization and sequence limits, and produces a readiness report with model parameter and persistent-state memory estimates.
7. Constructs train/validation/test DataLoaders from one verified split snapshot; the train sampler state is included in the initial data cursor.

The split operation writes metadata only. It does not create, edit, or download dataset rows. It rejects changed dataset bytes, tampered split metadata, duplicate JSON keys, mismatched membership, empty splits, and prompt-group leakage.

## iPad/browser workflow

1. Export `ultron-runtime-config.json` from the website Settings.
2. Upload the repository checkout, config, and an already-existing dataset plus its `.manifest.json` sidecar to the notebook runtime.
3. Run the notebook in order and enter the runtime-local paths when prompted.
4. Choose a path for the split-ID metadata JSON.

This is a manual file handoff. The static website is not connected to the notebook runtime. Provider access, free-tier quota, session persistence, and iPad compatibility have not been verified.

## Deliberate exclusions

The notebook does not generate/download examples, edit dataset rows, instantiate the model, allocate weights, create an optimizer, load or save a checkpoint, consume batches, perform optimizer steps, train, or dispatch remote jobs. The split file is metadata, not training data.

PR #186 added a read-only tokenized dataset view and DataLoader contract. PR #187 adds `build_verified_training_preflight`, which validates exact MathExample semantics and tokenizes every selected prompt/answer before constructing all three loaders from the same verified split snapshot. The train loader uses ResumableRandomSampler bound to the full-dataset SHA-256; validation/test loaders are sequential. All loaders use `num_workers=0` and `drop_last=False`. No sequence is silently truncated. The readiness report returns formula-based model parameter/memory estimates and clearly marks unmeasured dataset/activation/allocator costs.

The split seed is independent from sampler seed. The default sampler seed is 0 and is part of `initial_data_state`; it must match `TrainingSettings.seed` if a separately authorized trainer run is configured.

The bounded trainer already passes committed cursor metadata to its checkpoint callback after completed optimizer steps. A callback can persist `metrics["data_state"]` and `metrics["dataset_manifest_sha256"]` with `save_checkpoint`. The initial cursor includes the batch size, dataset-bound sampler state, and zero batch/sample positions. Checkpoint format v6 validates batch/sample/sampler alignment before state restoration; format-v5 checkpoints remain readable.

This notebook does not instantiate the model or optimizer, invoke the checkpoint callback, save a model checkpoint, restore one, or consume batches. Next: validate clean-runtime resume with `num_workers=0` and prove uninterrupted-versus-resumed equivalence only after separate explicit authorization for a tiny optimizer-step test.
