"""Disk-backed, lazy access to integrity-verified JSONL split records."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from .dataset_split_manifest import (
    _MAX_DATA,
    _MAX_LINE_BYTES,
    _MAX_ROWS,
    _read_bound_split_payload,
    validate_dataset_split_manifest,
    _strict_object,
)
from .dataset_resource_limits import DatasetResourceLimits

# Backward-compatible import name used by the benchmark CLI and stress tests.
IndexedDatasetResourceLimits = DatasetResourceLimits



class VerifiedIndexedSplitStore:
    """Verified read-only snapshot plus disk-backed byte-offset index.

    The source is copied in bounded chunks into a private temporary snapshot.
    The copy must match the verified dataset digest before it is indexed.
    SQLite stores selected IDs and row offsets on disk; full records are
    decoded only when requested. The snapshot is removed by close().
    """

    def __init__(self, dataset_path, split_manifest_path, *, resource_limits=None):
        self.dataset_path = Path(dataset_path)
        self.split_manifest_path = Path(split_manifest_path)
        if resource_limits is None:
            resource_limits = DatasetResourceLimits()
        if not isinstance(resource_limits, DatasetResourceLimits):
            raise TypeError("resource_limits must be DatasetResourceLimits")
        self.resource_limits = resource_limits
        self._temporary = tempfile.TemporaryDirectory(prefix="ultron-indexed-dataset-")
        self._closed = False
        self._connection = None
        self._snapshot_path = Path(self._temporary.name) / "verified.jsonl"
        self._index_path = Path(self._temporary.name) / "records.sqlite3"

        try:
            self._check_input_file_limits()
            verified = validate_dataset_split_manifest(
                self.dataset_path, self.split_manifest_path,
                resource_limits=self.resource_limits,
            )
            # Re-check after semantic validation in case an input was replaced
            # or grew between the initial stat and parser open.
            self._check_input_file_limits()
            payload = _read_bound_split_payload(
                self.split_manifest_path, verified, resource_limits=self.resource_limits
            )
            self.dataset_manifest_sha256 = verified.dataset_sha256
            self.split_manifest_sha256 = verified.split_manifest_sha256
            self.split_counts = dict(verified.split_counts)
            self.dataset_example_count = verified.dataset_example_count

            self._copy_verified_snapshot()
            self._build_index(payload["split_ids"], verified)
        except Exception:
            self.close()
            raise

    def _check_input_file_limits(self):
        """Reject oversized inputs before JSON parsing or snapshot copying."""
        try:
            if not self.dataset_path.is_file():
                raise ValueError("dataset path is not a file")
            if not self.split_manifest_path.is_file():
                raise ValueError("split manifest path is not a file")
            if self.dataset_path.stat().st_size > self.resource_limits.max_dataset_bytes:
                raise ValueError("dataset exceeds configured max_dataset_bytes")
            if self.split_manifest_path.stat().st_size > self.resource_limits.max_split_manifest_bytes:
                raise ValueError("split manifest exceeds configured max_split_manifest_bytes")
        except OSError as exc:
            raise ValueError("dataset or split manifest is missing or inaccessible") from exc

    def _check_disk_usage(self):
        """Enforce configured index and combined temporary-disk ceilings."""
        try:
            snapshot_bytes = self._snapshot_path.stat().st_size if self._snapshot_path.exists() else 0
            index_bytes = self._index_path.stat().st_size if self._index_path.exists() else 0
            temporary_bytes = sum(
                entry.stat().st_size
                for entry in Path(self._temporary.name).rglob("*")
                if entry.is_file()
            )
        except OSError as exc:
            raise ValueError("temporary dataset storage could not be inspected") from exc
        if index_bytes > self.resource_limits.max_index_bytes:
            raise ValueError("SQLite index exceeds configured max_index_bytes")
        if temporary_bytes > self.resource_limits.max_temporary_bytes:
            raise ValueError("temporary dataset directory exceeds configured max_temporary_bytes")

    def _copy_verified_snapshot(self):
        digest = hashlib.sha256()
        bytes_seen = 0
        try:
            with self.dataset_path.open("rb") as source, self._snapshot_path.open("xb") as target:
                while True:
                    chunk = source.read(self.resource_limits.snapshot_copy_chunk_bytes)
                    if not chunk:
                        break
                    bytes_seen += len(chunk)
                    if bytes_seen > self.resource_limits.max_dataset_bytes:
                        raise ValueError("dataset exceeds configured max_dataset_bytes")
                    digest.update(chunk)
                    target.write(chunk)
                    target.flush()
                    self._check_disk_usage()
                target.flush()
                os.fsync(target.fileno())
        except OSError as exc:
            raise ValueError("verified dataset snapshot could not be created") from exc
        if digest.hexdigest() != self.dataset_manifest_sha256:
            raise ValueError("dataset changed while the verified snapshot was copied")
        try:
            self._snapshot_path.chmod(0o400)
        except OSError as exc:
            raise ValueError("verified dataset snapshot could not be made read-only") from exc
        self._check_disk_usage()

    def _build_index(self, split_ids, verified):
        connection = sqlite3.connect(self._index_path)
        self._connection = connection
        try:
            connection.execute("PRAGMA temp_store=FILE")
            connection.execute(f"PRAGMA cache_size=-{self.resource_limits.sqlite_cache_kib}")
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
            page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
            snapshot_bytes = self._snapshot_path.stat().st_size
            available_index_bytes = min(
                self.resource_limits.max_index_bytes,
                self.resource_limits.max_temporary_bytes - snapshot_bytes,
            )
            if available_index_bytes < page_size:
                raise ValueError("configured temporary-disk budget cannot hold one SQLite index page")
            maximum_pages = available_index_bytes // page_size
            connection.execute(f"PRAGMA max_page_count={maximum_pages}")
            connection.execute(
                "CREATE TABLE selected_ids (example_id TEXT PRIMARY KEY, split_name TEXT NOT NULL) WITHOUT ROWID"
            )
            connection.execute(
                "CREATE TABLE records (example_id TEXT PRIMARY KEY, split_name TEXT NOT NULL, "
                "byte_offset INTEGER NOT NULL, byte_length INTEGER NOT NULL, row_sha256 TEXT NOT NULL) WITHOUT ROWID"
            )
            for split_name in ("train", "validation", "test"):
                ids = split_ids.get(split_name)
                if not isinstance(ids, list):
                    raise ValueError("split manifest IDs are malformed")
                connection.executemany(
                    "INSERT INTO selected_ids(example_id, split_name) VALUES (?, ?)",
                    ((example_id, split_name) for example_id in ids),
                )
            connection.commit()
            self._check_disk_usage()

            digest = hashlib.sha256()
            bytes_seen = 0
            rows_seen = 0
            selected_seen = {"train": 0, "validation": 0, "test": 0}
            offset = 0
            with self._snapshot_path.open("rb") as stream:
                while True:
                    line = stream.readline(self.resource_limits.max_line_bytes + 1)
                    if not line:
                        break
                    rows_seen += 1
                    if rows_seen > self.resource_limits.max_rows or rows_seen > verified.dataset_example_count:
                        raise ValueError("dataset row count exceeds configured max_rows or verified manifest")
                    if len(line) > self.resource_limits.max_line_bytes:
                        raise ValueError("dataset JSONL row exceeds configured max_line_bytes")
                    bytes_seen += len(line)
                    if bytes_seen > self.resource_limits.max_dataset_bytes:
                        raise ValueError("dataset exceeds configured max_dataset_bytes")
                    if not line.endswith(b"\n"):
                        raise ValueError("dataset JSONL must end with a newline")
                    digest.update(line)
                    try:
                        row = json.loads(
                            line[:-1].decode("utf-8"),
                            object_pairs_hook=_strict_object,
                        )
                    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                        raise ValueError("dataset JSONL malformed or contains duplicate keys") from exc
                    if not isinstance(row, dict) or not isinstance(row.get("example_id"), str):
                        raise ValueError("dataset example ID is malformed")
                    selected = connection.execute(
                        "SELECT split_name FROM selected_ids WHERE example_id = ?",
                        (row["example_id"],),
                    ).fetchone()
                    if selected is not None:
                        split_name = selected[0]
                        connection.execute(
                            "INSERT INTO records(example_id, split_name, byte_offset, byte_length, row_sha256) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (
                                row["example_id"],
                                split_name,
                                offset,
                                len(line),
                                hashlib.sha256(line).hexdigest(),
                            ),
                        )
                        selected_seen[split_name] += 1
                    offset += len(line)

            if (rows_seen != verified.dataset_example_count
                    or bytes_seen != self._snapshot_path.stat().st_size
                    or digest.hexdigest() != self.dataset_manifest_sha256):
                raise ValueError("verified snapshot changed during index construction")
            if selected_seen != self.split_counts:
                raise ValueError("indexed split counts differ from verified manifest")

            connection.execute(
                "CREATE TABLE ordered_records (split_name TEXT NOT NULL, seq INTEGER NOT NULL, "
                "example_id TEXT NOT NULL UNIQUE, byte_offset INTEGER NOT NULL, "
                "byte_length INTEGER NOT NULL, row_sha256 TEXT NOT NULL, "
                "PRIMARY KEY(split_name, seq)) WITHOUT ROWID"
            )
            for split_name in ("train", "validation", "test"):
                cursor = connection.execute(
                    "SELECT example_id, byte_offset, byte_length, row_sha256 "
                    "FROM records WHERE split_name = ? ORDER BY example_id",
                    (split_name,),
                )
                seq = 0
                while True:
                    batch = cursor.fetchmany(self.resource_limits.index_build_batch_rows)
                    if not batch:
                        break
                    connection.executemany(
                        "INSERT INTO ordered_records(split_name, seq, example_id, byte_offset, byte_length, row_sha256) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            (split_name, seq + index, *record)
                            for index, record in enumerate(batch)
                        ),
                    )
                    seq += len(batch)
                if seq != self.split_counts[split_name]:
                    raise ValueError("ordered index count differs from verified split")
            connection.execute("DROP TABLE records")
            connection.execute("DROP TABLE selected_ids")
            connection.commit()
            self._check_disk_usage()
        except sqlite3.OperationalError as exc:
            connection.rollback()
            message = str(exc).lower()
            if "full" in message or "maximum page count" in message:
                raise ValueError(
                    "SQLite index exceeded configured max_index_bytes or max_temporary_bytes"
                ) from exc
            raise
        except Exception:
            connection.rollback()
            raise

    def iter_records(self, split_name):
        """Yield integrity-checked records in stable split order with bounded memory."""
        self._ensure_open()
        if split_name not in self.split_counts:
            raise ValueError("invalid split name")
        cursor = self._connection.execute(
            "SELECT example_id, byte_offset, byte_length, row_sha256 "
            "FROM ordered_records WHERE split_name = ? ORDER BY seq",
            (split_name,),
        )
        try:
            with self._snapshot_path.open("rb") as stream:
                while True:
                    batch = cursor.fetchmany(self.resource_limits.iterator_fetch_rows)
                    if not batch:
                        break
                    for example_id, offset, length, row_digest in batch:
                        stream.seek(offset)
                        line = stream.read(length)
                        if len(line) != length or hashlib.sha256(line).hexdigest() != row_digest:
                            raise ValueError("verified snapshot record integrity check failed")
                        if not line.endswith(b"\n"):
                            raise ValueError("verified snapshot record newline is malformed")
                        try:
                            row = json.loads(
                                line[:-1].decode("utf-8"),
                                object_pairs_hook=_strict_object,
                            )
                        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                            raise ValueError("verified snapshot record is malformed") from exc
                        if (not isinstance(row, dict)
                                or row.get("example_id") != example_id
                                or not isinstance(row.get("input_text"), str)
                                or not isinstance(row.get("target_text"), str)):
                            raise ValueError("verified snapshot record identity or text is malformed")
                        yield example_id, row["input_text"], row["target_text"]
        except OSError as exc:
            raise ValueError("verified snapshot records could not be streamed") from exc
        finally:
            cursor.close()

    def __len_for_split__(self, split_name):
        self._ensure_open()
        if split_name not in self.split_counts:
            raise ValueError("invalid split name")
        return self.split_counts[split_name]

    def get_record(self, split_name, index):
        self._ensure_open()
        if split_name not in self.split_counts:
            raise ValueError("invalid split name")
        if isinstance(index, bool) or not isinstance(index, int):
            raise TypeError("dataset index must be an integer")
        if not 0 <= index < self.split_counts[split_name]:
            raise IndexError(index)
        record = self._connection.execute(
            "SELECT example_id, byte_offset, byte_length, row_sha256 "
            "FROM ordered_records WHERE split_name = ? AND seq = ?",
            (split_name, index),
        ).fetchone()
        if record is None:
            raise ValueError("verified index record is missing")
        example_id, byte_offset, byte_length, row_digest = record
        try:
            with self._snapshot_path.open("rb") as stream:
                stream.seek(byte_offset)
                line = stream.read(byte_length)
        except OSError as exc:
            raise ValueError("verified snapshot record could not be read") from exc
        if len(line) != byte_length or hashlib.sha256(line).hexdigest() != row_digest:
            raise ValueError("verified snapshot record integrity check failed")
        try:
            row = json.loads(line[:-1].decode("utf-8"), object_pairs_hook=_strict_object)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("verified snapshot record is malformed") from exc
        if not isinstance(row, dict) or row.get("example_id") != example_id:
            raise ValueError("verified snapshot record identity mismatch")
        if not isinstance(row.get("input_text"), str) or not isinstance(row.get("target_text"), str):
            raise ValueError("verified snapshot record text is malformed")
        return example_id, row["input_text"], row["target_text"]

    def _ensure_open(self):
        if self._closed:
            raise RuntimeError("verified indexed dataset store is closed")

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._connection is not None:
            try:
                self._connection.close()
            finally:
                self._connection = None
        self._temporary.cleanup()

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
