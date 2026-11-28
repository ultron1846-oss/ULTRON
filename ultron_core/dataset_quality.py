"""Read-only, reproducible quality audit for an existing verified dataset.

This module never generates rows, changes the input dataset, or trains a model.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile

from .data_generation import validate_example_text
from .dataset_resource_limits import DatasetResourceLimits
from .dataset_split_manifest import (
    _read_bound_split_payload,
    _strict_object,
    validate_dataset_split_manifest,
)

_SHA256 = re.compile(r"[0-9a-f]{64}")
_NUMBER = re.compile(r"(?<![A-Za-z_])[+-]?\d+(?:/\d+)?(?![A-Za-z_])")
_INTEGER = re.compile(r"[+-]?\d+")
_RATIONAL = re.compile(r"[+-]?\d+/\d+")
_MATRIX = re.compile(r"^\s*\[\[")
_ASSIGNMENT_PAIR = re.compile(r"^\s*x\s*=", re.IGNORECASE)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalized_text(value: str) -> str:
    return " ".join(value.split()).casefold()


def _template_signature(prompt: str) -> str:
    """Return a deliberately lexical template signature, not semantic equivalence."""
    return _NUMBER.sub("<num>", _normalized_text(prompt))


def _answer_format(answer: str) -> str:
    value = answer.strip()
    if _MATRIX.match(value):
        return "matrix"
    if _ASSIGNMENT_PAIR.match(value):
        return "assignment_pair"
    if _INTEGER.fullmatch(value):
        return "integer"
    if _RATIONAL.fullmatch(value):
        return "rational"
    if re.search(r"\b[xyz]\b", value, flags=re.IGNORECASE):
        return "symbolic_or_polynomial"
    return "other"


def _pairwise_overlap(connection: sqlite3.Connection, table: str, first: str, second: str) -> int:
    # Table names are internal constants at call sites, never user input.
    query = (
        f"SELECT COUNT(*) FROM (SELECT a.value_hash FROM {table} a "
        f"JOIN {table} b ON a.value_hash = b.value_hash "
        "WHERE a.split_name = ? AND b.split_name = ?)"
    )
    return int(connection.execute(query, (first, second)).fetchone()[0])


def _reject_output_aliases(output_path: Path, input_paths: tuple[Path, ...]) -> None:
    output = output_path.expanduser().resolve()
    resolved_inputs = tuple(path.expanduser().resolve() for path in input_paths)
    if output in resolved_inputs:
        raise ValueError("quality report output must not overwrite an input or dataset sidecar")
    if output.exists():
        for input_path in resolved_inputs:
            if input_path.exists() and os.path.samefile(output, input_path):
                raise ValueError("quality report output must not overwrite an input or dataset sidecar")


def audit_dataset_quality(dataset_path, split_manifest_path, *, resource_limits=None) -> dict:
    """Audit an existing dataset and frozen split manifest without modifying either."""
    resource_limits = resource_limits or DatasetResourceLimits()
    if not isinstance(resource_limits, DatasetResourceLimits):
        raise TypeError("resource_limits must be DatasetResourceLimits")
    dataset = Path(dataset_path).expanduser()
    split_path = Path(split_manifest_path).expanduser()
    dataset_sidecar = dataset.with_suffix(dataset.suffix + ".manifest.json")

    verified = validate_dataset_split_manifest(
        dataset, split_path, resource_limits=resource_limits
    )
    split_payload = _read_bound_split_payload(
        split_path, verified, resource_limits=resource_limits
    )
    try:
        before = dataset.stat()
    except OSError as exc:
        raise ValueError("dataset is missing or inaccessible before quality audit") from exc

    topic_counts = {name: Counter() for name in ("train", "validation", "test")}
    difficulty_counts = {name: Counter() for name in ("train", "validation", "test")}
    answer_formats = {name: Counter() for name in ("train", "validation", "test")}
    template_counts = {name: Counter() for name in ("train", "validation", "test")}
    seed_counts = {name: Counter() for name in ("train", "validation", "test")}
    validation_status = Counter()
    generator_versions = Counter()
    prompt_duplicate_rows = 0
    prompt_duplicate_groups = 0
    unassigned_rows = 0
    rechecked_rows = 0
    invalid_reference_answers = 0
    rows_seen = 0

    with tempfile.TemporaryDirectory(prefix="ultron-quality-audit-") as temp_dir:
        db_path = Path(temp_dir) / "quality.sqlite3"
        connection = sqlite3.connect(db_path)
        try:
            connection.execute("PRAGMA temp_store=FILE")
            main_cache_kib = max(1, resource_limits.sqlite_cache_kib // 2)
            temp_cache_kib = max(1, resource_limits.sqlite_cache_kib - main_cache_kib)
            connection.execute(f"PRAGMA main.cache_size=-{main_cache_kib}")
            connection.execute(f"PRAGMA temp.cache_size=-{temp_cache_kib}")
            main_page_size = int(connection.execute("PRAGMA main.page_size").fetchone()[0])
            temp_page_size = int(connection.execute("PRAGMA temp.page_size").fetchone()[0])
            main_index_budget = min(
                resource_limits.max_index_bytes,
                resource_limits.max_temporary_bytes // 2,
            )
            temp_database_budget = resource_limits.max_temporary_bytes - main_index_budget
            if main_index_budget < main_page_size or temp_database_budget < temp_page_size:
                raise ValueError(
                    "quality audit budget exceeds configured max_index_bytes or max_temporary_bytes (insufficient SQLite main/temp page budget)"
                )
            connection.execute(
                f"PRAGMA main.max_page_count={main_index_budget // main_page_size}"
            )
            connection.execute(
                f"PRAGMA temp.max_page_count={temp_database_budget // temp_page_size}"
            )
            connection.execute("CREATE TABLE selected_ids (example_id TEXT PRIMARY KEY, split_name TEXT NOT NULL) WITHOUT ROWID")
            for split_name in ("train", "validation", "test"):
                connection.executemany(
                    "INSERT INTO selected_ids(example_id, split_name) VALUES (?, ?)",
                    ((example_id, split_name) for example_id in split_payload["split_ids"][split_name]),
                )

            connection.execute(
                "CREATE TABLE prompt_groups (value_hash TEXT PRIMARY KEY, row_count INTEGER NOT NULL, "
                "assigned_split TEXT, first_example_id TEXT NOT NULL) WITHOUT ROWID"
            )
            for table in ("prompt_values", "answer_values", "generator_ingredients", "template_values", "seed_values"):
                connection.execute(
                    f"CREATE TABLE {table} (value_hash TEXT NOT NULL, split_name TEXT NOT NULL, "
                    "PRIMARY KEY(value_hash, split_name)) WITHOUT ROWID"
                )

            digest = hashlib.sha256()
            bytes_seen = 0
            try:
                with dataset.open("rb") as stream:
                    while True:
                        line = stream.readline(resource_limits.max_line_bytes + 1)
                        if not line:
                            break
                        rows_seen += 1
                        if rows_seen > resource_limits.max_rows:
                            raise ValueError("dataset exceeds configured max_rows during quality audit")
                        if len(line) > resource_limits.max_line_bytes or not line.endswith(b"\n"):
                            raise ValueError("dataset row exceeds configured max_line_bytes during quality audit")
                        bytes_seen += len(line)
                        if bytes_seen > resource_limits.max_dataset_bytes:
                            raise ValueError("dataset exceeds configured max_dataset_bytes during quality audit")
                        digest.update(line)
                        try:
                            row = json.loads(
                                line[:-1].decode("utf-8"), object_pairs_hook=_strict_object
                            )
                        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                            raise ValueError("dataset row is malformed during quality audit") from exc
                        if not isinstance(row, dict):
                            raise ValueError("dataset row is not an object")

                        example_id = row.get("example_id")
                        if not isinstance(example_id, str) or not _SHA256.fullmatch(example_id):
                            raise ValueError("dataset row example ID is malformed during quality audit")
                        selected = connection.execute(
                            "SELECT split_name FROM selected_ids WHERE example_id = ?", (example_id,)
                        ).fetchone()
                        split_name = selected[0] if selected else None
                        if split_name is None:
                            unassigned_rows += 1
                        else:
                            topic_counts[split_name][row["topic"]] += 1
                            difficulty_counts[split_name][str(row["difficulty"])] += 1
                            answer_formats[split_name][_answer_format(row["target_text"])] += 1
                            seed_counts[split_name][str(row["seed"])] += 1
                            connection.execute(
                                "INSERT OR IGNORE INTO seed_values(value_hash, split_name) VALUES (?, ?)",
                                (_sha256_text(str(row["seed"])), split_name),
                            )

                        validation_status[str(row.get("validation_status"))] += 1
                        generator_versions[str(row.get("generator_version"))] += 1
                        if validate_example_text(row["input_text"], row["exact_answer"], row["topic"]):
                            rechecked_rows += 1
                        else:
                            invalid_reference_answers += 1

                        normalized_prompt = _normalized_text(row["input_text"])
                        prompt_hash = _sha256_text(normalized_prompt)
                        prior_prompt = connection.execute(
                            "SELECT row_count, assigned_split FROM prompt_groups WHERE value_hash = ?",
                            (prompt_hash,),
                        ).fetchone()
                        if prior_prompt is None:
                            connection.execute(
                                "INSERT INTO prompt_groups(value_hash, row_count, assigned_split, first_example_id) "
                                "VALUES (?, 1, ?, ?)",
                                (prompt_hash, split_name, example_id),
                            )
                        else:
                            prompt_duplicate_rows += 1
                            if prior_prompt[0] == 1:
                                prompt_duplicate_groups += 1
                            connection.execute(
                                "UPDATE prompt_groups SET row_count = row_count + 1 WHERE value_hash = ?",
                                (prompt_hash,),
                            )

                        template_hash = _sha256_text(_template_signature(row["input_text"]))
                        if split_name is not None:
                            connection.execute(
                                "INSERT OR IGNORE INTO prompt_values(value_hash, split_name) VALUES (?, ?)",
                                (prompt_hash, split_name),
                            )
                            normalized_answer = _normalized_text(row["target_text"])
                            connection.execute(
                                "INSERT OR IGNORE INTO answer_values(value_hash, split_name) VALUES (?, ?)",
                                (_sha256_text(normalized_answer), split_name),
                            )
                            template_counts[split_name][(row["topic"], template_hash)] += 1
                            connection.execute(
                                "INSERT OR IGNORE INTO template_values(value_hash, split_name) VALUES (?, ?)",
                                (f"{row['topic']}:{template_hash}", split_name),
                            )

                            ingredients = {
                                "generator_version": row["generator_version"],
                                "topic": row["topic"],
                                "seed": row["seed"],
                                "index": row["index"],
                                "generation_parameters": row["generation_parameters"],
                            }
                            ingredients_hash = hashlib.sha256(_canonical_json(ingredients)).hexdigest()
                            connection.execute(
                                "INSERT OR IGNORE INTO generator_ingredients(value_hash, split_name) "
                                "VALUES (?, ?)",
                                (ingredients_hash, split_name),
                            )
            except OSError as exc:
                raise ValueError("dataset could not be read during quality audit") from exc

            connection.commit()
            try:
                after = dataset.stat()
            except OSError as exc:
                raise ValueError("dataset changed during quality audit") from exc
            if (
                bytes_seen != before.st_size
                or after.st_size != before.st_size
                or after.st_mtime_ns != before.st_mtime_ns
                or digest.hexdigest() != verified.dataset_sha256
            ):
                raise ValueError("dataset changed during quality audit")
            if rows_seen != verified.dataset_example_count:
                raise ValueError("dataset row count changed during quality audit")
            index_bytes = db_path.stat().st_size
            temp_bytes = (
                int(connection.execute("PRAGMA temp.page_count").fetchone()[0])
                * int(connection.execute("PRAGMA temp.page_size").fetchone()[0])
            )
            if index_bytes > resource_limits.max_index_bytes:
                raise ValueError("quality index exceeds configured max_index_bytes")
            if index_bytes + temp_bytes > resource_limits.max_temporary_bytes:
                raise ValueError("quality SQLite main/temp storage exceeds configured max_temporary_bytes")

            pair_names = (("train", "validation"), ("train", "test"), ("validation", "test"))
            pairwise = {}
            for first, second in pair_names:
                pairwise[f"{first}_vs_{second}"] = {
                    "normalized_prompt_groups": _pairwise_overlap(connection, "prompt_values", first, second),
                    "answer_values_shared": _pairwise_overlap(connection, "answer_values", first, second),
                    "template_signatures_shared": _pairwise_overlap(connection, "template_values", first, second),
                    "generation_ingredients_shared": _pairwise_overlap(connection, "generator_ingredients", first, second),
                    "generation_seed_values_shared": _pairwise_overlap(connection, "seed_values", first, second),
                }

            prompt_cross_split_groups = int(connection.execute(
                "SELECT COUNT(*) FROM (SELECT value_hash FROM prompt_values "
                "GROUP BY value_hash HAVING COUNT(DISTINCT split_name) > 1)"
            ).fetchone()[0])
            shared_answer_values = int(connection.execute(
                "SELECT COUNT(*) FROM (SELECT value_hash FROM answer_values "
                "GROUP BY value_hash HAVING COUNT(DISTINCT split_name) > 1)"
            ).fetchone()[0])
            shared_template_signatures = int(connection.execute(
                "SELECT COUNT(*) FROM (SELECT value_hash FROM template_values "
                "GROUP BY value_hash HAVING COUNT(DISTINCT split_name) > 1)"
            ).fetchone()[0])
            shared_ingredients = int(connection.execute(
                "SELECT COUNT(*) FROM (SELECT value_hash FROM generator_ingredients "
                "GROUP BY value_hash HAVING COUNT(DISTINCT split_name) > 1)"
            ).fetchone()[0])
            prompt_groups_total = int(connection.execute(
                "SELECT COUNT(*) FROM prompt_groups"
            ).fetchone()[0])
            duplicate_prompt_rows = max(
                prompt_duplicate_rows,
                int(connection.execute("SELECT COALESCE(SUM(row_count - 1), 0) FROM prompt_groups").fetchone()[0]),
            )
        except sqlite3.OperationalError as exc:
            connection.rollback()
            message = str(exc).lower()
            if "full" in message or "maximum page count" in message:
                raise ValueError(
                    "quality audit SQLite storage exceeded configured max_index_bytes or max_temporary_bytes"
                ) from exc
            raise
        finally:
            connection.close()

    split_counts = dict(verified.split_counts)
    per_split = {}
    for split_name in ("train", "validation", "test"):
        topic_total = sum(topic_counts[split_name].values())
        template_totals = defaultdict(int)
        for (topic, _template_hash), count in template_counts[split_name].items():
            template_totals[topic] += count
        dominant_templates = []
        for topic, topic_total_count in sorted(template_totals.items()):
            ranked = sorted(
                (
                    (count, template_hash)
                    for (template_topic, template_hash), count in template_counts[split_name].items()
                    if template_topic == topic
                ),
                reverse=True,
            )
            if ranked:
                top_count, top_hash = ranked[0]
                dominant_templates.append({
                    "topic": topic,
                    "top_template_sha256": top_hash,
                    "top_template_count": top_count,
                    "topic_sample_count": topic_total_count,
                    "top_template_share": top_count / topic_total_count,
                })
        per_split[split_name] = {
            "manifest_selected_count": split_counts[split_name],
            "audited_selected_count": topic_total,
            "topic_counts": dict(sorted(topic_counts[split_name].items())),
            "difficulty_counts": dict(sorted(difficulty_counts[split_name].items())),
            "answer_format_counts": dict(sorted(answer_formats[split_name].items())),
            "unique_seed_count": len(seed_counts[split_name]),
            "seed_use_counts": dict(sorted(seed_counts[split_name].items())),
            "topic_coverage_count": len(topic_counts[split_name]),
            "difficulty_levels_present": sorted(difficulty_counts[split_name]),
            "dominant_templates_by_topic": dominant_templates,
        }

    answer_leakage = {
        "distinct_normalized_answer_values_shared_across_any_splits": shared_answer_values,
        "interpretation": (
            "Diagnostic only: common exact answers can occur independently and are not, "
            "by themselves, proof of leakage."
        ),
    }
    template_leakage = {
        "distinct_lexical_template_signatures_shared_across_any_splits": shared_template_signatures,
        "interpretation": (
            "Diagnostic only: broad generator templates are expected to recur. "
            "This lexical signature is not semantic equivalence."
        ),
    }
    report = {
        "schema_version": 1,
        "report_type": "ultron_dataset_quality_audit",
        "resource_limits": dict(vars(resource_limits)),
        "dataset_manifest_sha256": verified.dataset_sha256,
        "split_manifest_sha256": verified.split_manifest_sha256,
        "source_dataset_example_count": verified.dataset_example_count,
        "selected_split_counts": split_counts,
        "audited_selected_example_count": sum(split_counts.values()),
        "unassigned_source_rows": unassigned_rows,
        "normalized_prompt_duplicate_groups": prompt_duplicate_groups,
        "normalized_prompt_duplicate_rows_after_first": duplicate_prompt_rows,
        "normalized_prompt_group_count": prompt_groups_total,
        "generator_versions": dict(sorted(generator_versions.items())),
        "validation_status_counts": dict(sorted(validation_status.items())),
        "reference_answer_recheck": {
            "rows_rechecked": rechecked_rows,
            "invalid_reference_answers": invalid_reference_answers,
            "method": "repository exact per-topic validate_example_text recheck after manifest verification",
        },
        "per_split": per_split,
        "split_pairwise_leakage_diagnostics": pairwise,
        "answer_leakage": answer_leakage,
        "template_leakage": template_leakage,
        "generation_ingredient_overlap": {
            "distinct_ingredient_hashes_shared_across_any_splits": shared_ingredients,
            "interpretation": "Any non-zero overlap is a hard split-integrity warning.",
        },
        "semantic_near_duplicates": {
            "status": "not_assessed",
            "reason": "No defensible semantic-equivalence method is implemented for the full mixed-topic corpus.",
            "owner_review_required": True,
        },
        "prerequisite_coverage": {
            "status": "not_assessed",
            "reason": "Sample schema v1 has no prerequisite identifiers or curriculum prerequisite links; topic counts are not a prerequisite-coverage measurement.",
        },
        "boundary_sample_coverage": {
            "status": "not_annotated_in_schema_v1",
            "count": 0,
            "note": "Current row schema has no explicit boundary/adversarial-case annotation.",
        },
        "quality_gate_summary": {
            "manifest_and_split_verified": True,
            "all_reference_answers_rechecked": invalid_reference_answers == 0 and rechecked_rows == rows_seen,
            "normalized_prompt_cross_split_groups": prompt_cross_split_groups,
            "generation_ingredient_cross_split_hashes": shared_ingredients,
            "prompt_group_split_separation": prompt_cross_split_groups == 0,
            "production_readiness": False,
            "reason": "A deterministic audit report is not owner-curated semantic review or a production corpus acceptance.",
        },
        "reproducibility": {
            "report_is_deterministic_for_identical_inputs": True,
            "canonical_encoding": "UTF-8 JSON; sorted keys; compact separators; ensure_ascii=false",
            "dataset_manifest_sha256": verified.dataset_sha256,
            "split_manifest_sha256": verified.split_manifest_sha256,
            "input_data_modified": False,
            "corpus_generated": False,
            "training_performed": False,
        },
    }
    report["report_sha256"] = hashlib.sha256(_canonical_json(report)).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--split-manifest", required=True, type=Path)
    defaults = DatasetResourceLimits()
    parser.add_argument("--max-dataset-bytes", type=int, default=defaults.max_dataset_bytes)
    parser.add_argument("--max-rows", type=int, default=defaults.max_rows)
    parser.add_argument("--max-line-bytes", type=int, default=defaults.max_line_bytes)
    parser.add_argument("--max-split-manifest-bytes", type=int, default=defaults.max_split_manifest_bytes)
    parser.add_argument("--max-dataset-manifest-bytes", type=int, default=defaults.max_dataset_manifest_bytes)
    parser.add_argument("--max-index-bytes", type=int, default=defaults.max_index_bytes)
    parser.add_argument("--max-temporary-bytes", type=int, default=defaults.max_temporary_bytes)
    parser.add_argument("--sqlite-cache-kib", type=int, default=defaults.sqlite_cache_kib)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output:
        sidecar = args.dataset.with_suffix(args.dataset.suffix + ".manifest.json")
        _reject_output_aliases(args.output, (args.dataset, args.split_manifest, sidecar))
    resource_limits = DatasetResourceLimits(
        max_dataset_bytes=args.max_dataset_bytes,
        max_rows=args.max_rows,
        max_line_bytes=args.max_line_bytes,
        max_split_manifest_bytes=args.max_split_manifest_bytes,
        max_dataset_manifest_bytes=args.max_dataset_manifest_bytes,
        max_index_bytes=args.max_index_bytes,
        max_temporary_bytes=args.max_temporary_bytes,
        sqlite_cache_kib=args.sqlite_cache_kib,
    )
    report = audit_dataset_quality(
        args.dataset, args.split_manifest, resource_limits=resource_limits
    )
    rendered = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        destination = args.output.expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(rendered)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, destination)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
