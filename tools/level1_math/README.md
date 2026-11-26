# ULTRON Level 1 Math Generator and Verifier

Small deterministic-seed tooling for arithmetic and one-variable linear equations. This is a **tooling prototype**, not a trained model or evidence of model reasoning.

## Run

From this directory:

```bash
python -m pip install -e '.[test]'
pytest -q
python benchmark.py
python validate_benchmark.py
```

The benchmark script writes exactly 500 held-out JSONL records using fixed seed `9012026`. It is evaluation-only; do not use these records for training. The randomized regression uses separate seed `20261125` and checks 5,000 cases against SymPy, including independent exact substitution for linear equations.

## Scope

- Integer arithmetic: +, -, *, and exact division.
- One-variable linear equations with integer coefficients/constants and an integer solution.
- Difficulty changes operand ranges; it is not a calibrated human difficulty scale.
- No training, optimizer step, external AI/API, or remote execution.


## Training integration

The future authorized training entrypoint can use `ultron_core.level1_training.build_level1_training_loader(count=..., seed=..., batch_size=..., training_authorized=True)`. It creates verified prompt/working/answer sequences, tokenizes them with ULTRON's canonical math vocabulary, and returns padded batches. It defaults to a `ResumableRandomSampler`, `num_workers=0`, and `drop_last=False`; the dataset exposes `dataset_manifest_sha256`. Pass `loader.sampler` to `run_training_steps` and bind that hash into preflight/checkpoint metadata. The 500-item fixed benchmark is not used as training data.

Constructing this loader requires explicit training authorization. It does not itself run the model, optimizer, checkpointing, or remote jobs.
