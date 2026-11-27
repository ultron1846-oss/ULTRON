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

The notebook does not generate/download examples, instantiate the model, allocate weights, create an optimizer or DataLoader, load a checkpoint, perform optimizer steps, train, or dispatch remote jobs. The split file is metadata, not training data.

PR #186 adds a read-only tokenized dataset view and constructs train/validation/test DataLoaders. The train loader uses ResumableRandomSampler, `num_workers=0`, and `drop_last=False`; evaluation loaders are sequential. The notebook records an initial cursor object but does not consume batches or save a checkpoint. Next: connect the loader and callback metadata to the existing bounded trainer; actual training remains separately gated.
