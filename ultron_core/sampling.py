"""Deterministic, checkpointable batch sampler for local training."""
from __future__ import annotations

import math

import torch


class ResumableBatchSampler:
    """Yield deterministic batches and serialize an exact next-batch cursor.

    Pass this object as a DataLoader batch_sampler and restore its state before
    creating or iterating the resumed DataLoader.
    """
    _STATE_KEYS = {
        "schema_version", "dataset_size", "batch_size", "seed", "epoch",
        "next_batch_index", "shuffle", "drop_last",
    }

    def __init__(self, dataset_size: int, batch_size: int, *, seed: int = 0,
                 epoch: int = 0, next_batch_index: int = 0,
                 shuffle: bool = True, drop_last: bool = False):
        for name, value in (("dataset_size", dataset_size), ("batch_size", batch_size),
                            ("seed", seed), ("epoch", epoch),
                            ("next_batch_index", next_batch_index)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
        if dataset_size < 1 or batch_size < 1:
            raise ValueError("dataset_size and batch_size must be positive")
        if not 0 <= seed < 2**63:
            raise ValueError("seed must be in [0, 2**63)")
        if epoch < 0:
            raise ValueError("epoch must be non-negative")
        if not isinstance(shuffle, bool) or not isinstance(drop_last, bool):
            raise TypeError("shuffle and drop_last must be boolean")
        self.dataset_size = dataset_size
        self.batch_size = batch_size
        self.seed = seed
        self.epoch = epoch
        self.shuffle = shuffle
        self.drop_last = drop_last
        self.next_batch_index = 0
        self._validate_cursor(next_batch_index)
        self.next_batch_index = next_batch_index

    @property
    def total_batches(self) -> int:
        if self.drop_last:
            return self.dataset_size // self.batch_size
        return math.ceil(self.dataset_size / self.batch_size)

    def _validate_cursor(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("next_batch_index must be an integer")
        if not 0 <= value <= self.total_batches:
            raise ValueError("next_batch_index is outside the sampler epoch")

    def set_epoch(self, epoch: int) -> None:
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise ValueError("epoch must be a non-negative integer")
        self.epoch = epoch
        self.next_batch_index = 0

    def __iter__(self):
        if self.shuffle:
            generator = torch.Generator()
            generator.manual_seed((self.seed + self.epoch) % (2**63))
            indices = torch.randperm(self.dataset_size, generator=generator).tolist()
        else:
            indices = list(range(self.dataset_size))
        for batch_index in range(self.next_batch_index, self.total_batches):
            start = batch_index * self.batch_size
            batch = indices[start:start + self.batch_size]
            if self.drop_last and len(batch) < self.batch_size:
                break
            # Set before yield so state is the next batch when checkpointed.
            self.next_batch_index = batch_index + 1
            yield batch

    def __len__(self) -> int:
        return self.total_batches - self.next_batch_index

    def state_dict(self, *, next_batch_index: int | None = None) -> dict:
        cursor = self.next_batch_index if next_batch_index is None else next_batch_index
        self._validate_cursor(cursor)
        return {
            "schema_version": 1,
            "dataset_size": self.dataset_size,
            "batch_size": self.batch_size,
            "seed": self.seed,
            "epoch": self.epoch,
            "next_batch_index": cursor,
            "shuffle": self.shuffle,
            "drop_last": self.drop_last,
        }

    def load_state_dict(self, state: dict) -> None:
        if not isinstance(state, dict) or set(state) != self._STATE_KEYS:
            raise ValueError("sampler state schema is invalid")
        if state.get("schema_version") != 1:
            raise ValueError("sampler state version is unsupported")
        expected = {
            "dataset_size": self.dataset_size,
            "batch_size": self.batch_size,
            "seed": self.seed,
            "shuffle": self.shuffle,
            "drop_last": self.drop_last,
        }
        for key, value in expected.items():
            if state.get(key) != value:
                raise ValueError(f"sampler state {key} does not match configured sampler")
        epoch, cursor = state.get("epoch"), state.get("next_batch_index")
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise ValueError("sampler state epoch is invalid")
        self.epoch = epoch
        self._validate_cursor(cursor)
        self.next_batch_index = cursor
