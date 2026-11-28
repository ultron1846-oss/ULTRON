"""Deterministic math-generator/curriculum coverage audit (no data generation)."""
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


def _validate_manifest_and_evidence(catalog_ids: set[str]) -> tuple[set[str], set[str], set[str]]:
    manifest = _read_json(ROOT / "validation_manifest.json")
    independent = manifest.get("independent_validation")
    benchmarked = manifest.get("benchmarked")
    mastered = manifest.get("mastered")
    if not isinstance(independent, dict) or not isinstance(benchmarked, list) or not isinstance(mastered, list):
        raise ValueError("validation manifest has invalid state collections")

    for catalog_id, evidence_items in independent.items():
        if catalog_id not in catalog_ids:
            raise ValueError(f"validation evidence references unknown catalog ID {catalog_id!r}")
        if not isinstance(evidence_items, list) or not evidence_items:
            raise ValueError(f"validation evidence for {catalog_id!r} must be a non-empty array")
        for evidence in evidence_items:
            if not isinstance(evidence, dict):
                raise ValueError(f"validation evidence item for {catalog_id!r} must be an object")
            path_text, test_name, validator = (
                evidence.get("path"), evidence.get("test"), evidence.get("validator")
            )
            if not all(isinstance(value, str) and value for value in (path_text, test_name, validator)):
                raise ValueError(f"validation evidence for {catalog_id!r} is incomplete")
            test_path = REPOSITORY_ROOT / path_text
            try:
                source = test_path.read_text(encoding="utf-8")
            except OSError as exc:
                raise ValueError(f"validation evidence test file is missing: {path_text}") from exc
            if f"def {test_name}(" not in source:
                raise ValueError(f"validation test {test_name!r} is not present in {path_text}")

    benchmark_set, mastered_set = set(benchmarked), set(mastered)
    independent_set = set(independent)
    if len(benchmark_set) != len(benchmarked) or len(mastered_set) != len(mastered):
        raise ValueError("benchmark/mastery manifest entries must be unique")
    if not benchmark_set.issubset(catalog_ids) or not mastered_set.issubset(catalog_ids):
        raise ValueError("benchmark/mastery manifest references an unknown catalog ID")
    if not benchmark_set.issubset(independent_set):
        raise ValueError("a benchmarked topic must have independent mathematical validation")
    if not mastered_set.issubset(benchmark_set):
        raise ValueError("a mastered topic must have a benchmark record")
    return independent_set, benchmark_set, mastered_set


def build_coverage_audit() -> dict:
    """Validate committed coverage metadata and compute distinct implementation states."""
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

    catalog_ids = []
    raw_topic_ids = []
    grade_counts = Counter()
    word_problem_counts = Counter()
    generator_count = 0
    independent_status_count = 0
    benchmark_status_count = 0
    mastery_status_count = 0
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("combined registry contains a non-object topic")
        topic, grade_band, catalog_id = row.get("topic"), row.get("grade_band"), row.get("catalog_id")
        if not all(isinstance(value, str) and value for value in (topic, grade_band, catalog_id)):
            raise ValueError("combined registry topic, grade_band, and catalog_id are required")
        if row.get("status") not in ("generator_available_not_mastered", "catalogued_not_implemented"):
            raise ValueError(f"generator status is missing or invalid for {catalog_id!r}")
        if row["status"] == "generator_available_not_mastered":
            generator_count += 1
        if row.get("independent_validation_status") not in (
            "independently_validated", "not_independently_validated"
        ):
            raise ValueError(f"independent validation state is invalid for {catalog_id!r}")
        if row.get("benchmark_status") not in ("benchmarked", "not_benchmarked"):
            raise ValueError(f"benchmark state is invalid for {catalog_id!r}")
        if row.get("mastery_status") not in ("mastered", "not_mastered"):
            raise ValueError(f"mastery state is invalid for {catalog_id!r}")
        independent_status_count += row["independent_validation_status"] == "independently_validated"
        benchmark_status_count += row["benchmark_status"] == "benchmarked"
        mastery_status_count += row["mastery_status"] == "mastered"
        raw_topic_ids.append(topic)
        catalog_ids.append(catalog_id)
        grade_counts[grade_band] += 1
        if row.get("word_problems") is True:
            word_problem_counts[grade_band] += 1
        elif row.get("word_problems") not in (False, None):
            raise ValueError(f"word_problems flag is invalid for {catalog_id!r}")

    scope_id_counts = Counter(catalog_ids)
    scope_id_collisions = {
        catalog_id: count
        for catalog_id, count in sorted(scope_id_counts.items())
        if count > 1
    }
    if scope_id_collisions:
        raise ValueError(
            "combined registry contains duplicate scope-qualified catalog IDs: "
            + repr(scope_id_collisions)
        )

    catalog_id_set = set(catalog_ids)
    independent_set, benchmark_set, mastered_set = _validate_manifest_and_evidence(catalog_id_set)
    if independent_status_count != len(independent_set):
        raise ValueError("registry independent-validation states differ from the evidence manifest")
    if benchmark_status_count != len(benchmark_set) or mastery_status_count != len(mastered_set):
        raise ValueError("registry benchmark/mastery states differ from the evidence manifest")
    if independent_set - {
        row["catalog_id"] for row in rows if row["status"] == "generator_available_not_mastered"
    }:
        raise ValueError("independent validation cannot be claimed for an unavailable generator")

    university_status = Counter()
    university_ids = set()
    university_generated = 0
    for row in university_rows:
        topic, has_generator, status = row.get("topic"), row.get("has_generator"), row.get("status")
        if not isinstance(topic, str) or not topic or topic in university_ids:
            raise ValueError("university registry has invalid or duplicate topic IDs")
        if not isinstance(has_generator, bool):
            raise ValueError(f"university generator flag is invalid for {topic!r}")
        expected_status = "generator_available_not_mastered" if has_generator else "catalogued_not_implemented"
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
    raw_topic_counts = Counter(raw_topic_ids)
    collisions = {topic: count for topic, count in sorted(raw_topic_counts.items()) if count > 1}

    return {
        "schema_version": 2,
        "registry_sync_valid": True,
        "catalogued_topic_count": len(rows),
        "generator_available_topic_count": generator_count,
        "independently_validated_topic_count": len(independent_set),
        "benchmarked_topic_count": len(benchmark_set),
        "mastered_topic_count": len(mastered_set),
        "unique_catalog_id_count": len(catalog_ids),
        "unique_raw_topic_id_count": len(raw_topic_counts),
        "scope_qualified_identifier_collision_count": len(scope_id_collisions),
        "raw_topic_identifier_collision_count": len(collisions),
        "raw_topic_identifier_collisions": collisions,
        "combined_registry_entry_count": len(rows),
        "unique_topic_id_count": len(raw_topic_counts),
        "unique_source_topic_entry_count": len(catalog_ids),
        "entries_by_grade_band": dict(sorted(grade_counts.items())),
        "word_problem_entries_by_grade_band": dict(sorted(word_problem_counts.items())),
        "university_curriculum_topic_count": len(university_rows),
        "university_generator_available_count": university_generated,
        "university_catalogued_not_implemented_count": university_status["catalogued_not_implemented"],
        "university_generator_status_counts": dict(sorted(university_status.items())),
        "university_prerequisite_mapped_topic_count": prerequisites.mapped_topic_count,
        "university_prerequisite_edge_count": edge_count,
        "university_prerequisite_root_topic_count": roots,
        "university_prerequisite_graph_acyclic": True,
        "data_generated": False,
        "training_performed": False,
        "model_mastery_claimed": False,
        "interpretation": (
            "Generator availability, independent exercise validation, measured model benchmarks, "
            "and model mastery are separate states. Independent exercise checks do not establish "
            "a trained model's competence; no benchmark or mastery is inferred from metadata."
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
