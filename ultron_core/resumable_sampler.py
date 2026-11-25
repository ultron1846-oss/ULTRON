"""Deterministic, dataset-bound sampler with a resumable sample cursor."""
from __future__ import annotations

import re
from typing import Iterator

import torch
from torch.utils.data import Sampler

_HASH_RE = re.compile(r"[0-9a-f]{64}")


class ResumableRandomSampler(Sampler[int]):
    """Random permutation sampler whose position can be saved/restored.

    For exact mid-epoch resume, use DataLoader(num_workers=0) so worker
    prefetching cannot advance the sampler beyond batches consumed by training.
    The dataset manifest digest binds sampler state to the exact corpus.
    """

    def __init__(self, data_source, *, seed: int, dataset_manifest_sha256: str,
                 epoch: int = 0, next_index: int = 0):
        if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
            raise ValueError("seed must be an integer in [0, 2**63)")
        if not isinstance(dataset_manifest_sha256, str) or not _HASH_RE.fullmatch(dataset_manifest_sha256):
            raise ValueError("dataset_manifest_sha256 must be a lowercase SHA-256 hex digest")
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise ValueError("epoch must be a non-negative integer")
        size = len(data_source)
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise ValueError("data_source must be non-empty")
        if isinstance(next_index, bool) or not isinstance(next_index, int) or not 0 <= next_index <= size:
            raise ValueError("next_index must be an integer within the dataset")
        self.data_source = data_source
        self.seed = seed
        self.dataset_manifest_sha256 = dataset_manifest_sha256
        self.epoch = epoch
        self.next_index = next_index
        self._permutation: list[int] | None = None

    def _get_permutation(self) -> list[int]:
        if self._permutation is None:
            generator = torch.Generator(device="cpu")
            generator.manual_seed((self.seed + self.epoch) % (2**63))
            self._permutation = torch.randperm(len(self.data_source), generator=generator).tolist()
        return self._permutation

    def __iter__(self) -> Iterator[int]:
        permutation = self._get_permutation()
        while self.next_index < len(permutation):
            index = permutation[self.next_index]
            self.next_index += 1
            yield index

    def __len__(self) -> int:
        return len(self.data_source) - self.next_index

    def set_epoch(self, epoch: int) -> None:
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise ValueError("epoch must be a non-negative integer")
        self.epoch = epoch
        self.next_index = 0
        self._permutation = None

    def state_dict(self) -> dict:
        return {
            "schema_version": 1,
            "dataset_size": len(self.data_source),
            "dataset_manifest_sha256": self.dataset_manifest_sha256,
            "seed": self.seed,
            "epoch": self.epoch,
            "next_index": self.next_index,
        }

    def load_state_dict(self, state: dict) -> None:
        version = state.get("schema_version") if isinstance(state, dict) else None
        if isinstance(version, bool) or not isinstance(version, int) or version != 1:
            raise ValueError("sampler state schema is invalid")
        size = state.get("dataset_size")
        if isinstance(size, bool) or not isinstance(size, int) or size != len(self.data_source):
            raise ValueError("sampler state dataset size does not match")
        if state.get("dataset_manifest_sha256") != self.dataset_manifest_sha256:
            raise ValueError("sampler state dataset manifest hash does not match")
        saved_seed = state.get("seed")
        if isinstance(saved_seed, bool) or not isinstance(saved_seed, int) or saved_seed != self.seed:
            raise ValueError("sampler state seed does not match")
        epoch, next_index = state.get("epoch"), state.get("next_index")
        if (isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0
                or isinstance(next_index, bool) or not isinstance(next_index, int)
                or not 0 <= next_index <= len(self.data_source)):
            raise ValueError("sampler state cursor is invalid")
        self.epoch = epoch
        self.next_index = next_index
        self._permutation = None
