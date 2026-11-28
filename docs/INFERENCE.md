# ULTRON inference API

## Public API

The public entry points are exported from `ultron_core` and implemented in
`ultron_core.inference`:

- `load_inference_engine(checkpoint_path, tokenizer=None, device="cpu")`
  selects a checkpoint only when its SHA-256 sidecar verifies (or uses the
  existing verified backup), validates the checkpoint format and model
  configuration, checks tokenizer version/vocabulary compatibility, builds
  the matching `NeuroSparseModel`, and restores model weights with
  `restore_rng=False`.
- `ULTRONInferenceEngine.generate(prompt, max_new_tokens=64)` validates the
  prompt and token IDs, runs greedy decoding in `torch.inference_mode()`,
  validates output shape and finite logits, decodes the generated IDs, and
  returns a structured result with a finish reason and explicit execution
  flags.
- `load_compressed_inference_engine(artifact_path, parent_checkpoint_path,
  parent_checkpoint_id=...)` loads the verified parent checkpoint, replays
  the compressed artifact recipe on a copy, strictly loads the artifact
  state, and exposes that model through the same inference API.

## Runtime behavior and limits

Inference is model-only. No command-tool context, external AI API, remote
service, optimizer, or training controller is invoked. Checkpoint loading
does not restore global Python/Torch RNG state. The engine temporarily enters
evaluation mode and restores the model's previous training flag after each
request. ULTRON's episodic memory is reset before and after an independent
request. `close()` resets memory, marks the engine closed, and releases its
model reference; use a context manager to ensure cleanup.

Checkpoints and compressed deployment artifacts are distinct formats.
`load_checkpoint`/ `load_inference_engine` load the parent training checkpoint;
they do not directly load a compressed artifact. The compressed inference
entry point requires the parent checkpoint and the stable parent identifier
recorded by the artifact. A compressed artifact is never substituted for the
foundation training checkpoint.

## Validation boundary

Tests use small, deterministic initialized weights and temporary checkpoint
or artifact files. They exercise tokenizer/model compatibility, checkpoint
integrity and backup selection, autoregressive invocation, output formatting,
read-only parameters, artifact reconstruction, truncation/corruption rejection,
and serialized-size reporting. These are **software-pipeline tests**, not a
trained ULTRON evaluation. An initialized random model can generate tokens
successfully while providing no demonstrated mathematical competence. No
accuracy, reasoning, proof, generalization, speed, or deployment-memory claim
follows from these tests.
