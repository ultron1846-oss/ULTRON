"""Shared bounded resource policy for dataset verification and indexed loading."""
from __future__ import annotations

from dataclasses import dataclass

MAX_DATASET_BYTES = 1024 * 1024 * 1024
MAX_DATASET_ROWS = 100_000
MAX_LINE_BYTES = 8 * 1024 * 1024
MAX_SPLIT_MANIFEST_BYTES = 32 * 1024 * 1024
MAX_DATASET_MANIFEST_BYTES = 1024 * 1024
MAX_INDEX_BYTES = 1024 * 1024 * 1024
MAX_TEMPORARY_BYTES = 2 * 1024 * 1024 * 1024


@dataclass(frozen=True)
class DatasetResourceLimits:
    """Caller-configurable limits constrained by conservative repository ceilings."""

    max_dataset_bytes: int = MAX_DATASET_BYTES
    max_rows: int = MAX_DATASET_ROWS
    max_line_bytes: int = MAX_LINE_BYTES
    max_split_manifest_bytes: int = MAX_SPLIT_MANIFEST_BYTES
    max_dataset_manifest_bytes: int = MAX_DATASET_MANIFEST_BYTES
    max_index_bytes: int = 256 * 1024 * 1024
    max_temporary_bytes: int = MAX_DATASET_BYTES + 256 * 1024 * 1024
    snapshot_copy_chunk_bytes: int = 1024 * 1024
    sqlite_cache_kib: int = 2048
    index_build_batch_rows: int = 1024
    iterator_fetch_rows: int = 256

    def __post_init__(self) -> None:
        bounded = (
            ("max_dataset_bytes", self.max_dataset_bytes, MAX_DATASET_BYTES),
            ("max_rows", self.max_rows, MAX_DATASET_ROWS),
            ("max_line_bytes", self.max_line_bytes, MAX_LINE_BYTES),
            ("max_split_manifest_bytes", self.max_split_manifest_bytes, MAX_SPLIT_MANIFEST_BYTES),
            ("max_dataset_manifest_bytes", self.max_dataset_manifest_bytes, MAX_DATASET_MANIFEST_BYTES),
            ("max_index_bytes", self.max_index_bytes, MAX_INDEX_BYTES),
            ("max_temporary_bytes", self.max_temporary_bytes, MAX_TEMPORARY_BYTES),
            ("snapshot_copy_chunk_bytes", self.snapshot_copy_chunk_bytes, 8 * 1024 * 1024),
            ("sqlite_cache_kib", self.sqlite_cache_kib, 64 * 1024),
            ("index_build_batch_rows", self.index_build_batch_rows, 8192),
            ("iterator_fetch_rows", self.iterator_fetch_rows, 4096),
        )
        for name, value, maximum in bounded:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            minimum = 4096 if name == "max_index_bytes" else 1
            if not minimum <= value <= maximum:
                raise ValueError(f"{name} must be in [{minimum}, {maximum}]")
