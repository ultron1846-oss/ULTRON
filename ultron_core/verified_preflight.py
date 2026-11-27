"""Verified-dataset readiness report construction; never trains or allocates weights."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from torch.utils.data import DataLoader

from .config import NeuroSparseConfig
from .data_state import validate_training_data_state
from .math_tokenizer import MathTokenizer, MathVocabulary
from .preflight import preflight_verified_indexed_dataset
from .runtime_config import RuntimeConfig
from .verified_dataset import (
    build_verified_split_loaders,
    close_verified_split_loaders,
)

_SPLITS = ("train", "validation", "test")


@dataclass(frozen=True)
class VerifiedTrainingPreflight:
    """Non-authorizing report plus loaders sharing one verified disk snapshot."""

    report: dict[str, Any]
    train_loader: DataLoader
    validation_loader: DataLoader
    test_loader: DataLoader
    initial_data_state: dict[str, Any]

    def close(self) -> None:
        """Release the temporary verified snapshot and SQLite index."""
        close_verified_split_loaders({
            "train": self.train_loader,
            "validation": self.validation_loader,
            "test": self.test_loader,
        })


def build_verified_training_preflight(
    dataset_path,
    split_manifest_path,
    runtime_config: RuntimeConfig,
    *,
    model_config: NeuroSparseConfig | None = None,
    sampler_seed: int = 0,
    tokenizer: MathTokenizer | None = None,
) -> VerifiedTrainingPreflight:
    """Verify an existing dataset and stream its token checks from disk.

    The indexed loader constructor performs semantic dataset and split
    validation, then binds a private snapshot to the verified dataset digest.
    This preflight streams selected rows from that snapshot to check token
    limits without retaining all row dictionaries or MathExample objects.
    It never iterates a DataLoader, allocates model weights or an optimizer,
    restores a checkpoint, performs optimizer steps, or dispatches remote work.
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

    loaders = build_verified_split_loaders(
        dataset_path,
        split_manifest_path,
        batch_size=runtime_config.batch_size,
        seed=sampler_seed,
        max_sequence_length=runtime_config.sequence_length,
        tokenizer=active_tokenizer,
    )
    try:
        store = loaders["train"].dataset._store
        report = preflight_verified_indexed_dataset(config, store, runtime_config)

        token_counts = {}
        maximum_sequence_length = 0
        total_tokens = 0
        for split_name in _SPLITS:
            count = 0
            for example_id, prompt, answer in store.iter_records(split_name):
                text = f"Question: {prompt}\nAnswer: {answer}"
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

        train_sampler = loaders["train"].sampler
        initial_data_state = validate_training_data_state(
            {
                "epoch": 0,
                "next_batch_index": 0,
                "next_sample_index": 0,
                "dataset_manifest_sha256": store.dataset_manifest_sha256,
                "dataset_size": len(loaders["train"].dataset),
                "batch_size": runtime_config.batch_size,
                "seed": sampler_seed,
                "gradient_accumulation_steps": runtime_config.gradient_accumulation_steps,
                "sampler_state": train_sampler.state_dict(),
            },
            dataset_manifest_sha256=store.dataset_manifest_sha256,
            dataset_size=len(loaders["train"].dataset),
            batch_size=runtime_config.batch_size,
            seed=sampler_seed,
            gradient_accumulation_steps=runtime_config.gradient_accumulation_steps,
        )

        report.update({
            "dataset_example_count": store.dataset_example_count,
            "selected_unique_prompt_examples": sum(store.split_counts.values()),
            "split_manifest_sha256": store.split_manifest_sha256,
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
            "Dataset rows are streamed from a verified temporary snapshot; split-ID metadata and SQLite index still use memory/disk.",
            "The persistent-state estimate excludes activations, attention workspaces, temporary tensors, runtime overhead, and allocator fragmentation.",
            "The sampler seed must match TrainingSettings.seed when the bounded trainer is eventually invoked.",
        ])
        return VerifiedTrainingPreflight(
            report=report,
            train_loader=loaders["train"],
            validation_loader=loaders["validation"],
            test_loader=loaders["test"],
            initial_data_state=initial_data_state,
        )
    except Exception:
        close_verified_split_loaders(loaders)
        raise
