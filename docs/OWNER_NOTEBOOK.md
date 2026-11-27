# ULTRON owner notebook setup

**Artifact:** [notebooks/ULTRON_OWNER_PREFLIGHT.ipynb](../notebooks/ULTRON_OWNER_PREFLIGHT.ipynb)  
**Scope:** preflight setup only; not training authorization.

## What it does

1. Checks that the notebook is running from a repository checkout/upload containing `ultron_core/`.
2. Imports and validates the website-exported schema-v1 `ultron-runtime-config.json`.
3. Confirms the config cannot authorize training or remote execution.
4. Calculates the foundation configuration's total and trainable parameter counts from formulas without instantiating the model.

## iPad/browser workflow

1. Open the ULTRON website and export the runtime config from Settings.
2. In a notebook runtime you are permitted to use, upload the repository files and the config using that runtime's file-upload interface.
3. Open the notebook from the repository and run cells in order.
4. When prompted, enter the runtime-local path to `ultron-runtime-config.json`.

This is a manual file handoff. The static website is not connected to a notebook runtime. Provider access, free-tier quota, session persistence, and iPad compatibility have not been verified here.

## Deliberate exclusions

The notebook does not load or generate datasets, create splits, instantiate `NeuroSparseModel`, allocate model weights, create an optimizer, load a checkpoint, construct a sampler/DataLoader, execute training, take optimizer steps, or dispatch remote jobs. Those operations are not complete in this scaffold.

The next implementation must add a read-only loader for an already-existing dataset and an independently validated split/manifest contract before constructing the sampler/DataLoader. Do not generate or download data as part of this stage.

## Acceptance

- Notebook JSON parses.
- Static regression test checks the notebook's safety boundary and required config/capacity checks.
- CI validates the notebook file and test.
- Owner must still verify actual iPad upload/path behavior and the chosen runtime's free-tier constraints.
