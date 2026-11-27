"""Verified-dataset readiness report construction; never trains or allocates weights."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from torch.utils.data import DataLoader

from .config import NeuroSparseConfig
from .data_generation import MathExample
from .dataset_split_manifest import (
    VerifiedSplitManifest,
    load_verified_split_rows_by_split,
)
from .math_tokenizer import MathTokenizer, MathVocabulary
from .preflight import preflight_training_plan_from_runtime_config
from .runtime_config import RuntimeConfig
from .verified_dataset import _build_verified_split_loaders_from_rows

_SPLITS = ("train", "validation", "test")


@dataclass(frozen=True)
class VerifiedTrainingPreflight:
    """Non-authorizing report plus loaders built from the same verified snapshot."""

    report: dict[str, Any]
    train_loader: DataLoader
    validation_loader: DataLoader
    test_loader: DataLoader
    initial_data_state: dict[str, Any]


def _to_math_example(row: dict[str, Any]) -> MathExample:
    parameters = row.get("generation_parameters")
    if not isinstance(parameters, dict):
        raise ValueError("verified dataset generation_parameters must be an object")
    try:
        immutable_parameters = tuple(sorted(parameters.items()))
        return MathExample(
            example_id=row["example_id"],
            generator_version=row["generator_version"],
            topic=row["topic"],
            difficulty=row["difficulty"],
            input_text=row["input_text"],
            target_text=row["target_text"],
            exact_answer=row["exact_answer"],
            seed=row["seed"],
            index=row["index"],
            generation_parameters=immutable_parameters,
            validation_status=row["validation_status"],
            provenance=row["provenance"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("verified dataset row cannot be adapted to MathExample") from exc


def build_verified_training_preflight(
    dataset_path,
    split_manifest_path,
    runtime_config: RuntimeConfig,
    *,
    model_config: NeuroSparseConfig | None = None,
    sampler_seed: int = 0,
    tokenizer: MathTokenizer | None = None,
) -> VerifiedTrainingPreflight:
    """Verify the existing dataset and build a non-authorizing readiness package.

    It validates dataset rows, prompt-disjoint splits, model capacity formulas,
    runtime settings, and tokenized sequence limits. It then constructs all
    three DataLoaders from the same verified row snapshot. It never iterates a
    DataLoader, instantiates model weights or an optimizer, restores a
    checkpoint, performs optimizer steps, or dispatches remote work.
    """
    if not isinstance(runtime_config, RuntimeConfig):
        raise TypeError("runtime_config must be a validated RuntimeConfig")
    if isinstance(sampler_seed, bool) or not isinstance(sampler_seed, int) or not 0 <= sampler_seed < 2**63:
        raise ValueError("sampler_seed must be an integer in [0, 2**63)")
    config = model_config or NeuroSparseConfig.foundation()
    if not isinstance(config, NeuroSparseConfig):
        raise TypeError("model_config must be NeuroSparseConfig")
    active_tokenizer = tokenizer or MathTokenizer(MathVocabulary.default())
    if not isinstance(active_tokenizer, MathTokenizer):
        raise TypeError("tokenizer must be MathTokenizer")
    if len(active_tokenizer.vocabulary) != config.vocab_size:
        raise ValueError("model vocabulary size does not match the verified dataset tokenizer")

    verified, rows_by_split = load_verified_split_rows_by_split(
        dataset_path, split_manifest_path
    )
    examples_by_split = {
        name: tuple(_to_math_example(row) for row in rows_by_split[name])
        for name in _SPLITS
    }
    report = preflight_training_plan_from_runtime_config(
        config,
        examples_by_split,
        runtime_config,
        dataset_manifest_sha256=verified.dataset_sha256,
    )

    token_counts = {}
    maximum_sequence_length = 0
    total_tokens = 0
    for split_name in _SPLITS:
        count = 0
        for row in rows_by_split[split_name]:
            example_id = row["example_id"]
            text = f"Question: {row['input_text']}\nAnswer: {row['target_text']}"
            try:
                token_length = len(
                    active_tokenizer.encode(text, add_bos=True, add_eos=True)
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"{split_name} example {example_id} cannot be tokenized: {exc}"
                ) from exc
            if token_length > runtime_config.sequence_length:
                raise ValueError(
                    f"{split_name} example {example_id} requires {token_length} tokens; "
                    f"runtime sequence limit is {runtime_config.sequence_length}. "
                    "Truncation is disabled."
                )
            if token_length < 3:
                raise ValueError(
                    f"{split_name} example {example_id} has an invalid token sequence"
                )
            count += token_length
            maximum_sequence_length = max(maximum_sequence_length, token_length)
        token_counts[split_name] = count
        total_tokens += count

    loaders = _build_verified_split_loaders_from_rows(
        verified,
        rows_by_split,
        batch_size=runtime_config.batch_size,
        seed=sampler_seed,
        max_sequence_length=runtime_config.sequence_length,
        tokenizer=active_tokenizer,
    )
    train_sampler = loaders["train"].sampler
    initial_data_state = {
        "epoch": 0,
        "next_batch_index": 0,
        "next_sample_index": 0,
        "dataset_manifest_sha256": verified.dataset_sha256,
        "dataset_size": len(loaders["train"].dataset),
        "seed": sampler_seed,
        "gradient_accumulation_steps": runtime_config.gradient_accumulation_steps,
        "sampler_state": train_sampler.state_dict(),
    }

    report.update({
        "dataset_example_count": verified.dataset_example_count,
        "selected_unique_prompt_examples": verified.selected_example_count,
        "split_manifest_sha256": verified.split_manifest_sha256,
        "tokenizer_version": active_tokenizer.vocabulary.version,
        "tokenizer_vocabulary_size": len(active_tokenizer.vocabulary),
        "tokenized_tokens_by_split": token_counts,
        "tokenized_token_count": total_tokens,
        "maximum_tokenized_sequence_length": maximum_sequence_length,
        "sampler_seed": sampler_seed,
        "sampler_seed_must_match_training_settings_seed": True,
        "data_loaders_constructed": True,
        "batches_consumed": False,
        "model_weights_allocated": False,
        "optimizer_created": False,
        "checkpoint_restored": False,
        "resource_estimate_complete": False,
    })
    report["limitations"].extend([
        "The memory estimate covers persistent FP32 model weights, gradients, and AdamW moments only.",
        "Dataset Python-object residency, DataLoader batches, activations, attention workspaces, temporary tensors, runtime overhead, and allocator fragmentation are not fully estimated.",
        "The sampler seed must match TrainingSettings.seed when the bounded trainer is eventually invoked.",
    ])
    return VerifiedTrainingPreflight(
        report=report,
        train_loader=loaders["train"],
        validation_loader=loaders["validation"],
        test_loader=loaders["test"],
        initial_data_state=initial_data_state,
    )
