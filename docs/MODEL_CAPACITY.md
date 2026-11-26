# ULTRON model capacity and expansion

## Hard requirement

The foundation configuration must have **at least 60,000,000 trainable parameters**. The lower bound is checked with the parameter-count formula in `ultron_core/config.py`; a comment or model name is not sufficient.

## Expansion controls

`NeuroSparseConfig.expanded()` provides a larger configuration. Capacity can be increased by changing:

- `hidden_size` — representation width
- `num_layers` — depth
- `num_experts` — expert count
- `expert_multiplier` — expert feed-forward width multiplier

The configuration validates shape constraints and rejects an expanded variant that does not exceed foundation capacity. Parameter counting does not allocate weights or run training.

## Verification boundary

The foundation and expanded counts are architecture calculations. They are not evidence of successful model instantiation, memory fit, training, or mathematical capability. Before training, CI should compare the formula with the instantiated model's parameter count; larger variants require resource profiling on the intended execution hardware. No model training or optimizer step is authorized by this specification.
