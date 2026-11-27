# ULTRON owner notebook setup

**Artifact:** [notebooks/ULTRON_OWNER_PREFLIGHT.ipynb](../notebooks/ULTRON_OWNER_PREFLIGHT.ipynb)  
**Scope:** runtime config, formula-based capacity, and manifest-bound dataset/split preflight only.

## What it does

1. Checks the repository contains `ultron_core/`.
2. Validates the website-exported schema-v1 runtime config and non-authorizing flags.
3. Calculates foundation parameter counts by formula without allocating weights.
4. Verifies an existing ULTRON JSONL dataset and sidecar manifest.
5. Writes deterministic, prompt-disjoint split-ID metadata bound to the exact dataset SHA-256, then validates it again.

The split operation writes metadata only. It does not create, edit, or download dataset rows. It rejects changed dataset bytes, tampered split metadata, duplicate JSON keys, mismatched membership, empty splits, and prompt-group leakage.

## iPad/browser workflow

1. Export `ultron-runtime-config.json` from the website Settings.
2. Upload the repository checkout, config, and an already-existing dataset plus its `.manifest.json` sidecar to the notebook runtime.
3. Run the notebook in order and enter the runtime-local paths when prompted.
4. Choose a path for the split-ID metadata JSON.

This is a manual file handoff. The static website is not connected to the notebook runtime. Provider access, free-tier quota, session persistence, and iPad compatibility have not been verified.

## Deliberate exclusions

The notebook does not generate/download examples, edit dataset rows, instantiate the model, allocate weights, create an optimizer, load or save a checkpoint, consume batches, perform optimizer steps, train, or dispatch remote jobs. The split file is metadata, not training data.

PR #186 adds a read-only tokenized dataset view and constructs train/validation/test DataLoaders. The train loader uses ResumableRandomSampler bound to the verified full-dataset SHA-256; validation/test loaders are sequential. All loaders use `num_workers=0` and `drop_last=False`, and overlong examples are rejected rather than silently truncated. The notebook records the initial sampler cursor but does not consume batches or save a checkpoint.

Next engineering stage: connect the verified train loader and sampler state to the bounded trainer's checkpoint callback, then validate metadata-only checkpoint round-tripping. Actual checkpoint restoration, batch consumption, optimizer steps, and clean-runtime equivalence remain separately gated.
