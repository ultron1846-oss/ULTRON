"""Deterministic math-generator/curriculum coverage audit (no data generation).

Run from repository root:
    python -m tools.math_generators.coverage_audit
    python -m tools.math_generators.coverage_audit --output docs/MATH_COVERAGE_AUDIT.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ultron_core.curriculum_prerequisites import load_curriculum_prerequisites
from tools.math_generators.build_registry import check_registries

ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parent.parent


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"coverage registry missing or malformed: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"coverage registry must be a JSON object: {path}")
    return value


def build_coverage_audit() -> dict:
    """Validate committed coverage metadata and return a deterministic summary."""
    if not check_registries():
        raise ValueError(
            "committed math-generator registries are stale; run "
            "python -m tools.math_generators.build_registry"
        )

    combined = _read_json(ROOT / "registry.json")
    university = _read_json(ROOT / "university" / "registry.json")
    rows = combined.get("topics")
    university_rows = university.get("topics")
    if not isinstance(rows, list) or not isinstance(university_rows, list):
        raise ValueError("coverage registries must contain topic arrays")

    entry_keys = []
    grade_counts = Counter()
    word_problem_counts = Counter()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("combined registry contains a non-object topic")
        topic = row.get("topic")
        grade_band = row.get("grade_band")
        if not isinstance(topic, str) or not topic or not isinstance(grade_band, str) or not grade_band:
            raise ValueError("combined registry topic or grade_band is invalid")
        source = row.get("source", grade_band)
        if not isinstance(source, str) or not source:
            raise ValueError("combined registry source must be a non-empty string")
        entry_keys.append((source, topic))
        grade_counts[grade_band] += 1
        if row.get("word_problems") is True:
            word_problem_counts[grade_band] += 1
        elif row.get("word_problems") not in (False, None):
            raise ValueError(f"word_problems flag is invalid for {topic!r}")

    if len(entry_keys) != len(set(entry_keys)):
        raise ValueError("combined registry contains duplicate source/topic entries")

    university_status = Counter()
    university_generated = 0
    university_ids = set()
    for row in university_rows:
        if not isinstance(row, dict):
            raise ValueError("university registry contains a non-object topic")
        topic = row.get("topic")
        has_generator = row.get("has_generator")
        status = row.get("status")
        if not isinstance(topic, str) or not topic or topic in university_ids:
            raise ValueError("university registry has invalid or duplicate topic IDs")
        if not isinstance(has_generator, bool):
            raise ValueError(f"university generator flag is invalid for {topic!r}")
        expected_status = (
            "generator_available_not_mastered"
            if has_generator
            else "catalogued_not_implemented"
        )
        if status != expected_status:
            raise ValueError(f"university status/generator mismatch for {topic!r}")
        university_ids.add(topic)
        university_status[status] += 1
        university_generated += int(has_generator)

    prerequisites = load_curriculum_prerequisites()
    if prerequisites.source_topic_count != len(university_rows):
        raise ValueError("prerequisite map and university registry topic counts differ")
    edge_count = sum(len(parents) for parents in prerequisites.prerequisites.values())
    roots = sum(not parents for parents in prerequisites.prerequisites.values())

    return {
        "schema_version": 1,
        "registry_sync_valid": True,
        "combined_registry_entry_count": len(rows),
        "unique_topic_id_count": len({topic for _, topic in entry_keys}),
        "unique_source_topic_entry_count": len(entry_keys),
        "entries_by_grade_band": dict(sorted(grade_counts.items())),
        "word_problem_entries_by_grade_band": dict(sorted(word_problem_counts.items())),
        "university_curriculum_topic_count": len(university_rows),
        "university_generator_available_count": university_generated,
        "university_catalogued_not_implemented_count": university_status[
            "catalogued_not_implemented"
        ],
        "university_generator_status_counts": dict(sorted(university_status.items())),
        "university_prerequisite_mapped_topic_count": prerequisites.mapped_topic_count,
        "university_prerequisite_edge_count": edge_count,
        "university_prerequisite_root_topic_count": roots,
        "university_prerequisite_graph_acyclic": True,
        "data_generated": False,
        "training_performed": False,
        "model_mastery_claimed": False,
        "interpretation": (
            "Generator availability and curriculum catalog coverage are engineering "
            "metadata only; they do not establish dataset quality, model mastery, "
            "or mathematical capability."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="optional JSON report destination")
    args = parser.parse_args()
    report = build_coverage_audit()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        destination = args.output.expanduser()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
