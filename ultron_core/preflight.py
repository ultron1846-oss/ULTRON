"""Training readiness validation only; this module never trains or allocates a model."""
from __future__ import annotations

import math
import re
from typing import Iterable, Mapping

from .config import (MIN_FOUNDATION_TRAINABLE_PARAMETERS, NeuroSparseConfig,
                     count_parameters, count_total_parameters)
from .data_generation import MathExample, validate_example_text
from .math_tokenizer import MathVocabulary

_REQUIRED_SPLITS = ("train", "validation", "test")

def preflight_training_plan(config, splits, *, batch_size=1, sequence_length=256,
                            gradient_accumulation_steps=1, memory_budget_gib=None, dataset_manifest_sha256=None):
    """Validate a proposed plan; this never authorizes or executes training."""
    if not isinstance(config, NeuroSparseConfig):
        raise TypeError("config must be a NeuroSparseConfig")
    for name, value in (("batch_size", batch_size), ("sequence_length", sequence_length),
                         ("gradient_accumulation_steps", gradient_accumulation_steps)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if sequence_length < 2 or sequence_length > config.max_sequence_length:
        raise ValueError("sequence_length must be between 2 and config.max_sequence_length")
    if memory_budget_gib is not None:
        if (isinstance(memory_budget_gib, bool) or not isinstance(memory_budget_gib, (int, float))
                or not math.isfinite(memory_budget_gib) or memory_budget_gib <= 0):
            raise ValueError("memory_budget_gib must be a finite positive number or None")
    if dataset_manifest_sha256 is not None and (
            not isinstance(dataset_manifest_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", dataset_manifest_sha256)):
        raise ValueError("dataset_manifest_sha256 must be a lowercase SHA-256 hex digest")
    vocab = MathVocabulary.default()
    if config.vocab_size != len(vocab):
        raise ValueError(f"config vocab_size={config.vocab_size} does not match canonical tokenizer size={len(vocab)}")
    parameter_count = count_parameters(config)
    total_parameter_count = count_total_parameters(config)
    if parameter_count < MIN_FOUNDATION_TRAINABLE_PARAMETERS:
        raise ValueError(
            f"model has {parameter_count} trainable parameters; minimum is "
            f"{MIN_FOUNDATION_TRAINABLE_PARAMETERS} (at least 60M)"
        )
    if not isinstance(splits, Mapping) or set(splits) != set(_REQUIRED_SPLITS):
        raise ValueError("splits must contain exactly train, validation, and test")
    seen_prompts, seen_ids = set(), set()
    split_counts = {}
    for split_name in _REQUIRED_SPLITS:
        examples = tuple(splits[split_name])
        if not examples or any(not isinstance(item, MathExample) for item in examples):
            raise ValueError(f"{split_name} split must contain at least one MathExample")
        split_counts[split_name] = len(examples)
        local_prompts = set()
        for item in examples:
            prompt = " ".join(item.input_text.split())
            if prompt in local_prompts:
                raise ValueError(f"{split_name} split contains a duplicate normalized prompt")
            local_prompts.add(prompt)
            if prompt in seen_prompts:
                raise ValueError("normalized prompts overlap across train/validation/test splits")
            seen_prompts.add(prompt)
            if item.example_id in seen_ids:
                raise ValueError("example IDs overlap across dataset splits")
            seen_ids.add(item.example_id)
            if (item.validation_status != "semantically_checked" or item.target_text != item.exact_answer
                    or not validate_example_text(item.input_text, item.exact_answer, item.topic)):
                raise ValueError(f"{split_name} contains an unverified mathematical example")
    weight_bytes = total_parameter_count * 4
    # All parameters occupy weight memory; only trainable parameters need gradients
    # and AdamW's two moment tensors.
    persistent_bytes = weight_bytes + parameter_count * 4 * 3
    budget_bytes = None if memory_budget_gib is None else int(memory_budget_gib * (1024 ** 3))
    fits = None if budget_bytes is None else budget_bytes >= persistent_bytes
    return {
        "status": "PREFLIGHT_ONLY", "validated": True, "training_authorized": False,
        "optimizer_steps": 0, "remote_execution_enabled": False,
        "parameter_count": parameter_count, "trainable_parameter_count": parameter_count,
        "total_parameter_count": total_parameter_count,
        "minimum_parameter_count": MIN_FOUNDATION_TRAINABLE_PARAMETERS,
        "minimum_trainable_parameter_count": MIN_FOUNDATION_TRAINABLE_PARAMETERS,
        "vocabulary_size": len(vocab), "split_counts": split_counts, "prompt_disjoint": True,
        "batch_size": batch_size, "sequence_length": sequence_length,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "model_weights_fp32_bytes": weight_bytes,
        "model_gradients_fp32_bytes": parameter_count * 4,
        "model_adamw_moments_fp32_bytes": parameter_count * 8,
        "model_persistent_state_fp32_bytes": persistent_bytes,
        # Backward-compatible alias; includes weights as well as gradient/optimizer state.
        "model_grad_and_adamw_state_fp32_bytes": persistent_bytes,
        "memory_budget_bytes": budget_bytes, "budget_covers_persistent_state": fits,
        "dataset_manifest_sha256": dataset_manifest_sha256,
        "limitations": [
            "Persistent-state estimate excludes activations, attention workspace, temporary tensors, runtime overhead and allocator fragmentation.",
            "A budget that covers persistent state does not guarantee the workload fits.",
            "This is not a training authorization or a training run.",
        ],
    }



def preflight_verified_indexed_dataset(
    config,
    indexed_store,
    runtime_config,
):
    """Create a non-authorizing report from a semantically verified indexed store.

    The store's constructor has already verified exact-answer semantics,
    content-derived identities, duplicate constraints, and prompt-disjoint
    split membership. This function uses only its digest and split counts;
    it does not materialize MathExample objects or dataset rows.
    """
    from .runtime_config import RuntimeConfig

    if not isinstance(config, NeuroSparseConfig):
        raise TypeError("config must be a NeuroSparseConfig")
    if not isinstance(runtime_config, RuntimeConfig):
        raise TypeError("runtime_config must be a validated RuntimeConfig")
    digest = getattr(indexed_store, "dataset_manifest_sha256", None)
    split_counts = getattr(indexed_store, "split_counts", None)
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("indexed store must carry a verified dataset SHA-256")
    if not isinstance(split_counts, Mapping) or set(split_counts) != set(_REQUIRED_SPLITS):
        raise ValueError("indexed store must expose verified train/validation/test counts")
    counts = {}
    for split_name in _REQUIRED_SPLITS:
        count = split_counts[split_name]
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ValueError(f"verified {split_name} split must be non-empty")
        counts[split_name] = count

    kwargs = runtime_config.preflight_kwargs()
    batch_size = kwargs["batch_size"]
    sequence_length = kwargs["sequence_length"]
    gradient_accumulation_steps = kwargs["gradient_accumulation_steps"]
    vocab = MathVocabulary.default()
    if config.vocab_size != len(vocab):
        raise ValueError(
            f"config vocab_size={config.vocab_size} does not match canonical tokenizer size={len(vocab)}"
        )
    parameter_count = count_parameters(config)
    total_parameter_count = count_total_parameters(config)
    if parameter_count < MIN_FOUNDATION_TRAINABLE_PARAMETERS:
        raise ValueError(
            f"model has {parameter_count} trainable parameters; minimum is "
            f"{MIN_FOUNDATION_TRAINABLE_PARAMETERS} (at least 60M)"
        )
    weight_bytes = total_parameter_count * 4
    persistent_bytes = weight_bytes + parameter_count * 4 * 3
    memory_budget_gib = kwargs.get("memory_budget_gib")
    budget_bytes = None if memory_budget_gib is None else int(memory_budget_gib * (1024 ** 3))
    fits = None if budget_bytes is None else budget_bytes >= persistent_bytes
    return {
        "status": "PREFLIGHT_ONLY",
        "validated": True,
        "training_authorized": False,
        "optimizer_steps": 0,
        "remote_execution_enabled": False,
        "parameter_count": parameter_count,
        "trainable_parameter_count": parameter_count,
        "total_parameter_count": total_parameter_count,
        "minimum_parameter_count": MIN_FOUNDATION_TRAINABLE_PARAMETERS,
        "minimum_trainable_parameter_count": MIN_FOUNDATION_TRAINABLE_PARAMETERS,
        "vocabulary_size": len(vocab),
        "split_counts": counts,
        "prompt_disjoint": True,
        "batch_size": batch_size,
        "sequence_length": sequence_length,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "model_weights_fp32_bytes": weight_bytes,
        "model_gradients_fp32_bytes": parameter_count * 4,
        "model_adamw_moments_fp32_bytes": parameter_count * 8,
        "model_persistent_state_fp32_bytes": persistent_bytes,
        "model_grad_and_adamw_state_fp32_bytes": persistent_bytes,
        "memory_budget_bytes": budget_bytes,
        "budget_covers_persistent_state": fits,
        "dataset_manifest_sha256": digest,
        "dataset_rows_materialized_for_report": False,
        "limitations": [
            "Dataset rows are streamed from a verified disk snapshot; the split-ID manifest and SQLite index still occupy bounded memory/disk.",
            "Persistent-state estimate excludes activations, attention workspace, temporary tensors, runtime overhead and allocator fragmentation.",
            "A budget that covers persistent state does not guarantee the workload fits.",
            "This is not a training authorization or a training run.",
        ],
    }


def preflight_training_plan_from_runtime_config(
    config,
    splits,
    runtime_config,
    *,
    dataset_manifest_sha256=None,
):
    """Run the existing non-authorizing preflight with validated runtime settings.

    The runtime config supplies only workload bounds and the requested memory
    budget. It cannot authorize training or enable remote execution.
    """
    from .runtime_config import RuntimeConfig

    if not isinstance(runtime_config, RuntimeConfig):
        raise TypeError("runtime_config must be a validated RuntimeConfig")
    return preflight_training_plan(
        config,
        splits,
        **runtime_config.preflight_kwargs(),
        dataset_manifest_sha256=dataset_manifest_sha256,
    )
