"""Read-only Dataset/DataLoader adapters for verified ULTRON JSONL splits."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import torch
from torch.utils.data import DataLoader, Dataset, SequentialSampler

from .dataset_split_manifest import (
    VerifiedSplitManifest,
    load_verified_split_rows,
    load_verified_split_rows_by_split,
)
from .math_tokenizer import MathTokenizer, MathVocabulary
from .resumable_sampler import ResumableRandomSampler

_SPLITS = ("train", "validation", "test")


class VerifiedMathDataset(Dataset):
    """Tokenize selected records from an integrity-verified existing dataset."""

    def __init__(
        self,
        dataset_path,
        split_manifest_path,
        *,
        split_name: str,
        tokenizer: MathTokenizer | None = None,
        max_sequence_length: int = 2048,
    ):
        verified, rows = load_verified_split_rows(
            dataset_path, split_manifest_path, split_name=split_name
        )
        self._initialize(
            verified,
            rows,
            split_name=split_name,
            tokenizer=tokenizer,
            max_sequence_length=max_sequence_length,
        )

    @classmethod
    def from_verified_rows(
        cls,
        verified: VerifiedSplitManifest,
        rows,
        *,
        split_name: str,
        tokenizer: MathTokenizer | None = None,
        max_sequence_length: int = 2048,
    ) -> "VerifiedMathDataset":
        """Build from an already verified split snapshot without re-reading files."""
        instance = cls.__new__(cls)
        instance._initialize(
            verified,
            rows,
            split_name=split_name,
            tokenizer=tokenizer,
            max_sequence_length=max_sequence_length,
        )
        return instance

    def _initialize(
        self,
        verified: VerifiedSplitManifest,
        rows,
        *,
        split_name: str,
        tokenizer: MathTokenizer | None,
        max_sequence_length: int,
    ) -> None:
        if not isinstance(verified, VerifiedSplitManifest):
            raise TypeError("verified must be a VerifiedSplitManifest")
        if split_name not in _SPLITS:
            raise ValueError("split_name must be train, validation, or test")
        if (
            isinstance(max_sequence_length, bool)
            or not isinstance(max_sequence_length, int)
            or not 2 <= max_sequence_length <= 2048
        ):
            raise ValueError("max_sequence_length must be in [2, 2048]")
        if not isinstance(rows, (tuple, list)):
            raise TypeError("verified rows must be a tuple or list")
        normalized = []
        for row in rows:
            if not isinstance(row, Mapping):
                raise TypeError("each verified row must be a mapping")
            for key in ("example_id", "input_text", "target_text"):
                if not isinstance(row.get(key), str):
                    raise ValueError(f"verified row {key} is malformed")
            normalized.append((row["example_id"], row["input_text"], row["target_text"]))

        self.dataset_manifest_sha256 = verified.dataset_sha256
        self.split_manifest_sha256 = verified.split_manifest_sha256
        self.split_name = split_name
        self.tokenizer = tokenizer or MathTokenizer(MathVocabulary.default())
        if not isinstance(self.tokenizer, MathTokenizer):
            raise TypeError("tokenizer must be MathTokenizer")
        self.max_sequence_length = max_sequence_length
        self._records = tuple(normalized)

    def __len__(self) -> int:
        return len(self._records)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("dataset index must be an integer")
        if not 0 <= index < len(self._records):
            raise IndexError(index)
        example_id, prompt, answer = self._records[index]
        token_ids = self.tokenizer.encode(
            f"Question: {prompt}\nAnswer: {answer}",
            add_bos=True,
            add_eos=True,
        )
        if len(token_ids) > self.max_sequence_length:
            raise ValueError(
                f"example {example_id} exceeds {self.max_sequence_length} tokens; "
                "truncation is disabled"
            )
        if len(token_ids) < 3:
            raise ValueError(f"example {example_id} token sequence is too short")
        return {"input_ids": torch.tensor(token_ids, dtype=torch.long)}


def collate_verified_math_batch(
    items: list[dict[str, Any]], *, pad_token_id: int = 0
) -> dict[str, torch.Tensor]:
    """Right-pad verified token sequences and return a boolean attention mask."""
    if not items:
        raise ValueError("cannot collate an empty batch")
    if (
        isinstance(pad_token_id, bool)
        or not isinstance(pad_token_id, int)
        or pad_token_id != 0
    ):
        raise ValueError("canonical ULTRON padding token ID must be 0")
    sequences = [
        item.get("input_ids") if isinstance(item, dict) else None
        for item in items
    ]
    if any(
        not isinstance(value, torch.Tensor)
        or value.ndim != 1
        or value.dtype != torch.long
        or value.numel() < 2
        for value in sequences
    ):
        raise ValueError("each item must contain a 1D int64 input_ids sequence")
    width = max(value.numel() for value in sequences)
    batch = torch.full((len(sequences), width), pad_token_id, dtype=torch.long)
    for row, value in enumerate(sequences):
        batch[row, : value.numel()] = value
    return {"input_ids": batch, "attention_mask": batch.ne(pad_token_id)}


def _build_loader(
    dataset: VerifiedMathDataset,
    *,
    batch_size: int,
    seed: int,
    shuffle: bool,
) -> DataLoader:
    sampler = (
        ResumableRandomSampler(
            dataset,
            seed=seed,
            dataset_manifest_sha256=dataset.dataset_manifest_sha256,
        )
        if shuffle
        else SequentialSampler(dataset)
    )
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        sampler=sampler,
        num_workers=0,
        drop_last=False,
        collate_fn=collate_verified_math_batch,
    )
    loader.dataset_manifest_sha256 = dataset.dataset_manifest_sha256
    loader.split_manifest_sha256 = dataset.split_manifest_sha256
    loader.split_name = dataset.split_name
    return loader


def build_verified_split_loaders_from_rows(
    verified: VerifiedSplitManifest,
    rows_by_split: Mapping[str, tuple[dict, ...]],
    *,
    batch_size: int,
    seed: int,
    max_sequence_length: int = 2048,
    tokenizer: MathTokenizer | None = None,
) -> dict[str, DataLoader]:
    """Construct all three loaders from one verified in-memory split snapshot."""
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not 1 <= batch_size <= 1024:
        raise ValueError("batch_size must be in [1, 1024]")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
        raise ValueError("seed must be in [0, 2**63)")
    if not isinstance(rows_by_split, Mapping) or set(rows_by_split) != set(_SPLITS):
        raise ValueError("rows_by_split must contain exactly train, validation, and test")

    shared_tokenizer = tokenizer or MathTokenizer(MathVocabulary.default())
    loaders = {}
    for split_name in _SPLITS:
        dataset = VerifiedMathDataset.from_verified_rows(
            verified,
            rows_by_split[split_name],
            split_name=split_name,
            tokenizer=shared_tokenizer,
            max_sequence_length=max_sequence_length,
        )
        loaders[split_name] = _build_loader(
            dataset,
            batch_size=batch_size,
            seed=seed,
            shuffle=(split_name == "train"),
        )
    return loaders


def build_verified_split_loaders(
    dataset_path,
    split_manifest_path,
    *,
    batch_size: int,
    seed: int,
    max_sequence_length: int = 2048,
    tokenizer: MathTokenizer | None = None,
) -> dict[str, DataLoader]:
    """Verify/load the corpus once and construct train/validation/test loaders."""
    verified, rows_by_split = load_verified_split_rows_by_split(
        dataset_path, split_manifest_path
    )
    return build_verified_split_loaders_from_rows(
        verified,
        rows_by_split,
        batch_size=batch_size,
        seed=seed,
        max_sequence_length=max_sequence_length,
        tokenizer=tokenizer,
    )


def build_verified_split_loader(
    dataset_path,
    split_manifest_path,
    *,
    split_name: str,
    batch_size: int,
    seed: int,
    max_sequence_length: int = 2048,
    tokenizer: MathTokenizer | None = None,
    shuffle: bool | None = None,
) -> DataLoader:
    """Construct one verified split loader without creating a model or training."""
    if split_name not in _SPLITS:
        raise ValueError("invalid split_name")
    if shuffle is None:
        shuffle = split_name == "train"
    if not isinstance(shuffle, bool):
        raise TypeError("shuffle must be boolean")
    if split_name != "train" and shuffle:
        raise ValueError("validation/test loaders must not shuffle")
    loaders = build_verified_split_loaders(
        dataset_path,
        split_manifest_path,
        batch_size=batch_size,
        seed=seed,
        max_sequence_length=max_sequence_length,
        tokenizer=tokenizer,
    )
    if split_name == "train" and not shuffle:
        # Explicit deterministic ordering is allowed for diagnostics but not for
        # the standard combined loader. Build the alternate train sampler here.
        dataset = loaders["train"].dataset
        return _build_loader(dataset, batch_size=batch_size, seed=seed, shuffle=False)
    return loaders[split_name]
