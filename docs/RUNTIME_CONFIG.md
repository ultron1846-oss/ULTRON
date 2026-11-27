# ULTRON runtime configuration handoff

**Status:** schema-v1 configuration export and validation; not a runtime connection or training authorization.

## Browser export

Settings → Training RAM preference → **Export runtime config (JSON)** downloads `ultron-runtime-config.json`. The selected memory value is the existing browser-local 2–10 GiB preference. The export also includes conservative workload defaults:

```json
{
  "schema_version": 1,
  "memory_budget_gib": 6,
  "batch_size": 1,
  "sequence_length": 256,
  "gradient_accumulation_steps": 1,
  "training_authorized": false,
  "remote_execution_enabled": false
}
```

The memory value is a requested budget, not a promise that a provider/device has that much memory. GiB is interpreted as 1,073,741,824 bytes by preflight.

## Python validation

`ultron_core.runtime_config.RuntimeConfig` validates the complete schema independently of the browser. The `preflight_training_plan_from_runtime_config(...)` adapter forwards the validated workload fields into the existing preflight. It rejects missing or unknown keys, duplicate JSON keys, invalid JSON, inputs over 16 KiB, booleans masquerading as integers, out-of-range values, unsupported schema versions, and any config attempting to set either authorization flag to true.

Supported ranges:
- Memory budget: 2–10 GiB
- Batch size: 1–16
- Sequence length: 2–2,048
- Gradient accumulation: 1–128

Use `RuntimeConfig.from_json(text)` to parse a downloaded/configured JSON string, then call `preflight_training_plan_from_runtime_config(model_config, splits, runtime_config, dataset_manifest_sha256=...)`. This adapter forwards only validated `memory_budget_gib`, `batch_size`, `sequence_length`, and `gradient_accumulation_steps` into the existing non-authorizing preflight. It does not bypass any model, dataset, split, or verifier checks.

## Security and limitations

- This file is untrusted input and must be validated again wherever consumed.
- The config is not a credential, a job request, or an authorization token.
- It does not connect GitHub Pages to Python, Supabase, Colab, or any provider.
- It does not allocate physical RAM or VRAM, select a device, run preflight, start a process, create data, or train.
- `run_training_steps` still requires its separate explicit `training_authorized=True` argument and a valid preflight report.
- A later runtime integration must check actual available memory, reserve headroom for activations/temporary allocations, and fail closed when device capability is unknown. The requested budget alone cannot establish that a workload fits.
- Actual iPad Safari export/download acceptance remains a manual device test.
