"""Strict validation for resumable training data cursors.

This module is intentionally pure: it validates metadata only and never reads a
checkpoint file, creates a model/optimizer, consumes a batch, or starts training.
"""
from __future__ import annotations

import copy
import re
from typing import Any

_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_SAMPLER_REQUIRED_FIELDS = {
    "schema_version", "dataset_size", "dataset_manifest_sha256",
    "seed", "epoch", "next_index",
}


def _integer(value: Any, *, name: str, minimum: int, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return value


def validate_training_data_state(
    data_state: dict[str, Any],
    *,
    dataset_manifest_sha256: str,
    dataset_size: int,
    batch_size: int,
    seed: int,
    gradient_accumulation_steps: int,
) -> dict[str, Any]:
    """Validate and return a detached copy of a complete resumable data cursor.

    The sampler cursor is measured in samples; the trainer cursor is measured
    in batches. For a non-dropping DataLoader their positions must satisfy:
    next_sample_index == min(next_batch_index * batch_size, dataset_size).
    Both positions are bound to the same dataset digest, split size, seed, and
    epoch. No runtime state is mutated.
    """
    if not isinstance(data_state, dict):
        raise TypeError("data_state must be a dictionary")
    if not isinstance(dataset_manifest_sha256, str) or not _SHA256_RE.fullmatch(
        dataset_manifest_sha256
    ):
        raise ValueError("dataset_manifest_sha256 must be a lowercase SHA-256 hex digest")
    dataset_size = _integer(dataset_size, name="dataset_size", minimum=1)
    batch_size = _integer(batch_size, name="batch_size", minimum=1, maximum=1024)
    seed = _integer(seed, name="seed", minimum=0, maximum=2**63 - 1)
    gradient_accumulation_steps = _integer(
        gradient_accumulation_steps,
        name="gradient_accumulation_steps",
        minimum=1,
        maximum=128,
    )

    required = {
        "epoch", "next_batch_index", "next_sample_index",
        "dataset_manifest_sha256", "dataset_size", "seed",
        "gradient_accumulation_steps", "sampler_state",
    }
    missing = required - data_state.keys()
    if missing:
        raise ValueError(f"data_state is missing required fields: {sorted(missing)}")

    epoch = _integer(data_state["epoch"], name="data_state epoch", minimum=0)
    next_batch_index = _integer(
        data_state["next_batch_index"], name="next_batch_index", minimum=0
    )
    next_sample_index = _integer(
        data_state["next_sample_index"], name="next_sample_index",
        minimum=0, maximum=dataset_size,
    )

    saved_hash = data_state["dataset_manifest_sha256"]
    if not isinstance(saved_hash, str) or not _SHA256_RE.fullmatch(saved_hash):
        raise ValueError("data_state dataset manifest hash is malformed")
    if saved_hash != dataset_manifest_sha256:
        raise ValueError("data_state dataset manifest hash does not match")

    saved_size = _integer(
        data_state["dataset_size"], name="data_state dataset_size", minimum=1
    )
    if saved_size != dataset_size:
        raise ValueError("data_state dataset size does not match")

    saved_seed = _integer(
        data_state["seed"], name="data_state seed", minimum=0, maximum=2**63 - 1
    )
    if saved_seed != seed:
        raise ValueError("data_state seed does not match training settings")

    saved_accumulation = _integer(
        data_state["gradient_accumulation_steps"],
        name="data_state gradient_accumulation_steps",
        minimum=1,
        maximum=128,
    )
    if saved_accumulation != gradient_accumulation_steps:
        raise ValueError("data_state accumulation does not match training settings")

    batch_count = (dataset_size + batch_size - 1) // batch_size
    if next_batch_index > batch_count:
        raise ValueError("data_state next_batch_index exceeds the training split")
    expected_sample_index = min(next_batch_index * batch_size, dataset_size)
    if next_sample_index != expected_sample_index:
        raise ValueError("data_state sample cursor does not align with its batch cursor")

    sampler_state = data_state["sampler_state"]
    if not isinstance(sampler_state, dict):
        raise ValueError("data_state sampler_state must be a dictionary")
    missing_sampler = _SAMPLER_REQUIRED_FIELDS - sampler_state.keys()
    if missing_sampler:
        raise ValueError(
            f"sampler_state is missing required fields: {sorted(missing_sampler)}"
        )

    version = _integer(
        sampler_state["schema_version"], name="sampler schema_version", minimum=1
    )
    if version != 1:
        raise ValueError("unsupported sampler state schema_version")

    sampler_size = _integer(
        sampler_state["dataset_size"], name="sampler dataset_size", minimum=1
    )
    if sampler_size != dataset_size:
        raise ValueError("sampler dataset size does not match data_state")

    sampler_hash = sampler_state["dataset_manifest_sha256"]
    if not isinstance(sampler_hash, str) or not _SHA256_RE.fullmatch(sampler_hash):
        raise ValueError("sampler dataset manifest hash is malformed")
    if sampler_hash != dataset_manifest_sha256:
        raise ValueError("sampler dataset manifest hash does not match")

    sampler_seed = _integer(
        sampler_state["seed"], name="sampler seed", minimum=0, maximum=2**63 - 1
    )
    if sampler_seed != seed:
        raise ValueError("sampler seed does not match training settings")
    sampler_epoch = _integer(sampler_state["epoch"], name="sampler epoch", minimum=0)
    if sampler_epoch != epoch:
        raise ValueError("sampler epoch does not match data_state")

    sampler_next_index = _integer(
        sampler_state["next_index"],
        name="sampler next_index",
        minimum=0,
        maximum=dataset_size,
    )
    if sampler_next_index != next_sample_index:
        raise ValueError("sampler sample cursor does not match data_state")
    if sampler_next_index != expected_sample_index:
        raise ValueError("sampler sample cursor does not align with batch cursor")

    training_settings = data_state.get("training_settings")
    if training_settings is not None:
        if not isinstance(training_settings, dict):
            raise ValueError("data_state training_settings must be a dictionary")
        if "seed" in training_settings:
            settings_seed = _integer(
                training_settings["seed"],
                name="training_settings seed",
                minimum=0,
                maximum=2**63 - 1,
            )
            if settings_seed != seed:
                raise ValueError("data_state training_settings seed does not match")
        if "gradient_accumulation_steps" in training_settings:
            settings_accumulation = _integer(
                training_settings["gradient_accumulation_steps"],
                name="training_settings gradient_accumulation_steps",
                minimum=1,
                maximum=128,
            )
            if settings_accumulation != gradient_accumulation_steps:
                raise ValueError("data_state training_settings accumulation does not match")

    return copy.deepcopy(data_state)
