"""Bounded-memory structural scan for an existing ULTRON JSONL dataset.

This utility deliberately does not replace the exact semantic dataset verifier.
It streams bytes and parses one bounded row at a time to report file integrity,
row structure, and topic counts without retaining the full corpus in memory.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import re
from pathlib import Path

_SHA256 = re.compile(r"[0-9a-f]{64}")
_MAX_BYTES = 1024 * 1024 * 1024
_MAX_ROWS = 100_000
_MAX_LINE_BYTES = 8 * 1024 * 1024
_ROW_KEYS = {
    "example_id", "generator_version", "topic", "difficulty",
    "input_text", "target_text", "exact_answer", "seed", "index",
    "generation_parameters", "validation_status", "provenance",
}


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"non-standard JSON constant is not allowed: {value}")


def _bounded_integer(name: str, value: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if not 1 <= value <= maximum:
        raise ValueError(f"{name} must be in [1, {maximum}]")
    return value


def scan_jsonl_structure(
    path,
    *,
    expected_sha256: str | None = None,
    max_bytes: int = _MAX_BYTES,
    max_rows: int = _MAX_ROWS,
    max_line_bytes: int = _MAX_LINE_BYTES,
) -> dict:
    """Stream-scan an existing JSONL file with strict row-shape checks.

    The scan computes a SHA-256 digest and verifies newline-delimited JSON,
    duplicate-key rejection, the exact row-key set, and basic field types.
    It does not check answer correctness, content-derived IDs, prompt leakage,
    split membership, or duplicate IDs; use verify_dataset and split preflight
    for those semantic/integrity contracts.
    """
    max_bytes = _bounded_integer("max_bytes", max_bytes, _MAX_BYTES)
    max_rows = _bounded_integer("max_rows", max_rows, _MAX_ROWS)
    max_line_bytes = _bounded_integer("max_line_bytes", max_line_bytes, _MAX_LINE_BYTES)
    if expected_sha256 is not None and (
        not isinstance(expected_sha256, str) or not _SHA256.fullmatch(expected_sha256)
    ):
        raise ValueError("expected_sha256 must be a lowercase SHA-256 hex digest")

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"dataset file not found: {source}")
    before = source.stat()
    if before.st_size > max_bytes:
        raise ValueError(f"dataset exceeds scan byte limit ({max_bytes} bytes)")

    digest = hashlib.sha256()
    topic_counts = Counter()
    bytes_scanned = 0
    row_count = 0
    maximum_line_seen = 0

    with source.open("rb") as stream:
        line_number = 0
        while True:
            line = stream.readline(max_line_bytes + 1)
            if not line:
                break
            line_number += 1
            if len(line) > max_line_bytes:
                raise ValueError(f"JSONL row {line_number} exceeds line byte limit")
            bytes_scanned += len(line)
            if bytes_scanned > max_bytes:
                raise ValueError(f"dataset exceeds scan byte limit ({max_bytes} bytes)")
            digest.update(line)
            maximum_line_seen = max(maximum_line_seen, len(line))
            if not line.endswith(b"\n"):
                raise ValueError("dataset JSONL must end every row with a newline")
            encoded = line[:-1]
            if not encoded:
                raise ValueError(f"dataset JSONL contains a blank row at line {line_number}")
            try:
                row = json.loads(
                    encoded.decode("utf-8"),
                    object_pairs_hook=_strict_object,
                    parse_constant=_reject_constant,
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError(f"dataset JSONL row {line_number} is malformed: {exc}") from exc
            if not isinstance(row, dict) or set(row) != _ROW_KEYS:
                raise ValueError(f"dataset JSONL row {line_number} has an invalid schema")
            if not isinstance(row.get("example_id"), str) or not _SHA256.fullmatch(row["example_id"]):
                raise ValueError(f"dataset JSONL row {line_number} has an invalid example_id")
            topic = row.get("topic")
            if not isinstance(topic, str) or not topic:
                raise ValueError(f"dataset JSONL row {line_number} has an invalid topic")
            index = row.get("index")
            if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                raise ValueError(f"dataset JSONL row {line_number} has an invalid index")
            if not isinstance(row.get("generation_parameters"), dict):
                raise ValueError(f"dataset JSONL row {line_number} has invalid generation_parameters")
            row_count += 1
            if row_count > max_rows:
                raise ValueError(f"dataset exceeds scan row limit ({max_rows})")
            topic_counts[topic] += 1

    after = source.stat()
    if (bytes_scanned != before.st_size or after.st_size != before.st_size
            or after.st_mtime_ns != before.st_mtime_ns):
        raise ValueError("dataset changed while streaming the structural scan")
    actual_sha256 = digest.hexdigest()
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ValueError("dataset SHA-256 does not match expected manifest")

    return {
        "schema_version": 1,
        "path": str(source),
        "bytes_scanned": bytes_scanned,
        "example_count": row_count,
        "sha256": actual_sha256,
        "topic_counts": dict(sorted(topic_counts.items())),
        "maximum_line_bytes": maximum_line_seen,
        "structural_validation_only": True,
        "semantic_answers_checked": False,
        "duplicate_example_ids_checked": False,
        "prompt_split_leakage_checked": False,
        "training_performed": False,
        "data_generated": False,
    }
