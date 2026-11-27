# ULTRON compression toolkit and policy

## Foundation checkpoint parameter floor

The requirement of **at least 60,000,000 trainable parameters** applies only to the
ULTRON **foundation training checkpoint**. The foundation configuration remains
63,400,451 total parameters and 61,826,048 trainable parameters.

A compressed model is a separate, versioned **deployment artifact**. Every
compressed artifact records its parent foundation checkpoint (a stable
checkpoint identifier or version), the ordered compression steps, the resulting
model configuration, and an artifact version.

A compressed deployment artifact never replaces, overwrites, or becomes the
foundation training checkpoint. The 60M trainable-parameter floor is not a
requirement for compressed deployment artifacts, and compressed artifacts must
never be described as meeting that foundation floor. The floor remains attached
to the uncompressed foundation training checkpoint only.

## Implemented operations

The public Python API is exported from `ultron_core.compress`. Each transform
returns a **new model plus a report**; the supplied model is not edited in
place.

### Expert usage counter

`ExpertUsageCounter(model)` installs reversible forward pre-hooks on each
expert. Each hook counts the number of token rows actually passed to that
expert. `snapshot()` returns JSON-compatible per-layer counts and totals;
`reset()` clears counts; `close()` removes hooks. The counter is intended for
an explicitly scoped inference/analysis pass, not training.

The measurement is dispatch frequency only. It does not indicate expert
quality, mathematical competence, or future utility.

### Expert pruning

`prune_experts(model, usage, keep_experts=N)` returns a copied model with the
least-used experts removed. Usage can be an `ExpertUsageCounter` or its
`snapshot()` mapping. Per-expert usage is summed across layers, then the same
expert indices are retained in every layer so the model's uniform expert-count
configuration remains valid. Router projection rows are sliced to match the
retained experts. `keep_experts` must be at least the router's `top_k`.

### Expert merging

`merge_experts(model, groups, usage=None)` requires `groups` to partition all
original expert indices exactly once. For each group and each layer, it retains
the real expert with the highest observed usage in that layer; ties select the
lowest original index. Router rows are selected from the same representative.
**No parameters are averaged. Ridge refit is not implemented and is OFF.**

Without usage data, all counts tie and the lowest index in each group is kept.
The resulting routing distribution is recomputed over the retained router
outputs; no quality preservation is implied.

### SVD low-rank factorization

`factorize_linear(linear, max_relative_error=...)` returns a `LowRankLinear`
and a report. `factorize_model(model, ...)` applies that conversion to chosen
module paths on a copied model. Without `target_modules`, all non-tied
`nn.Linear` modules are candidates. Tied weights are skipped rather than
silently breaking parameter sharing.

The rank is the smallest singular-value truncation rank meeting the requested
relative Frobenius weight error:

```
||W - W_hat||_F / ||W||_F <= max_relative_error
```

This bound is measured on the weight tensor only. It is not an output
distribution bound, model-quality score, benchmark result, or proof of retained
math capability. The report includes the selected rank and parameter delta.
For strict error limits, the required factors can contain as many or more
parameters than the original dense layer; inspect the report rather than
assuming every factorization reduces parameter count.

### Simulated int8 quantization and sensitivity

`simulate_int8_quantization(model, sensitivity_inputs=None)` returns a copied
model and per-linear-layer report. It uses symmetric per-layer scaling to map
weights to signed int8 values, then dequantizes those values back into the
original floating dtype. The returned model therefore contains floating-point
weights: this is a **simulation**, not packed-int8 storage, an int8 runtime, or
evidence of speed or memory savings. Tied parameters are skipped.

Every processed layer reports weight reconstruction sensitivity. Optional
output sensitivity is calculated only for module paths with explicitly
caller-supplied `sensitivity_inputs`. A zero-norm baseline output has no
defined relative output error, so the relative field is `null` and the
absolute maximum output error is reported separately. This API never creates
calibration data or samples.

### Pipeline, rollback, and artifact format

`run_compression_pipeline(model, steps, parent_checkpoint_id=...)` supports
the following step names:

- `prune_experts` — options passed to `prune_experts`.
- `merge_experts` — options passed to `merge_experts`.
- `factorize` — options passed to `factorize_model`.
- `quantize_int8` — options passed to `simulate_int8_quantization`.

Use expert pruning/merging before factorization: these expert operations expect
the original router projection to be an `nn.Linear`. Quantization may follow
factorization and will process the remaining `nn.Linear` factors. Every stage
works on a copy. If any step or artifact write fails, the function returns a
fresh copy of the original model and a report with `success=false` and
`rolled_back=true`; no partial result is returned as successful.

When `artifact_path` is supplied, the pipeline writes an immutable artifact
only after every transformation succeeds. Existing files are never overwritten.
The version 1 format is named `ultron.compressed-model` and includes:

- `artifact_version`, `parent_checkpoint_id`, and `model_scope`.
- The updated model configuration and ordered compression-step manifests.
- CPU `state_dict` tensors and a SHA-256 digest of the serialized model state.
- `foundation_parameter_floor_applies=false`, preventing the deployment
  artifact from being described as the foundation training checkpoint.

`load_compression_artifact(path)` validates the format metadata and state
digest and returns the artifact payload. It is not a universal model factory:
a consumer must construct the compatible module layout (including any
`LowRankLinear` replacements) before loading the returned state. Keep the
parent checkpoint and artifact provenance together.

## Safe use example

```python
import torch

from ultron_core.compress import (
    ExpertUsageCounter,
    prune_experts,
    run_compression_pipeline,
)

counter = ExpertUsageCounter(model)
try:
    with torch.inference_mode():
        model(example_token_ids)
    usage = counter.snapshot()
finally:
    counter.close()

pruned, pruning_report = prune_experts(model, usage, keep_experts=4)
compressed, pipeline_report = run_compression_pipeline(
    pruned,
    [{"name": "factorize", "options": {"max_relative_error": 0.05}}],
    parent_checkpoint_id="foundation-checkpoint-sha-or-version",
    artifact_version="1.0.0",
    artifact_path="artifacts/ultron-1.0.0.pt",
)
if not pipeline_report["success"]:
    raise RuntimeError(pipeline_report["error"])
```

The example assumes the model, token IDs, and checkpoint identifier already
exist. It does not create data or initiate training. Choose the operation order
and tolerances deliberately; inspect each returned report before accepting an
artifact.

## Compression quality and calibration

Compression quality can only be judged on a **trained model** using a
**verified benchmark** with a documented baseline and evaluation procedure.
Parameter counts, synthetic smoke checks, successful software tests, or
weight-tensor reconstruction errors from an untrained model are not evidence
of compression quality or retained mathematical capability.

**No calibration corpus has been generated.** No calibration quality,
calibration coverage, or calibrated compression result is claimed. Optional
sensitivity inputs must be explicitly supplied by a caller and are not
generated or stored by these tools.

Until a trained checkpoint and verified benchmark are available, compression
quality remains unmeasured. No quality, speed, or memory improvement is
claimed by this implementation.

## Scope and safety boundary

The parameter-reporting utility may construct the model on the PyTorch
meta-device to inspect real module structure without allocating foundation
weights. If meta-device construction is unavailable, it falls back to existing
analytical configuration counters and explicitly reports that the
category/module breakdown is unavailable.

The compression transforms and tests in this PR do not train a model, perform
optimizer steps, generate corpora or calibration data, use pretrained weights,
call external AI APIs, or run cloud/remote training. New compression
regressions use fixed-seed small CPU models. The foundation model count
implementation and configuration are unchanged. No website, Supabase,
authentication, or GitHub Pages files are part of this change.


## Reconstructing a compressed deployment artifact

`load_compressed_model_artifact(path, parent_model, parent_checkpoint_id=...)`
validates the immutable artifact, verifies the supplied parent checkpoint identifier,
replays its ordered transformation recipe on a copy of the parent model, checks the
resulting configuration, and strictly loads the integrity-checked compressed state.
The supplied parent model is never modified.

The artifact stores layer paths for optional quantization sensitivity inputs, not
the calibration tensors themselves. Those tensors affect sensitivity reporting,
not the quantized weights, so they are not needed for reconstruction. This loader
does not claim quality, speed, or memory improvements; the caller must supply the
correct parent checkpoint and validate the deployment artifact in its target
runtime.
