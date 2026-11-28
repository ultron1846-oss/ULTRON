"""Generate committed math-generator registries from topic and evidence declarations."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from tools.math_generators.grade1_4.generators import GENERATOR_METADATA as GRADE1_4
from tools.math_generators.grade5_8.generators import GENERATOR_METADATA as GRADE5_8
from tools.math_generators.grade8_12.generators import GENERATOR_METADATA as GRADE8_12
from tools.math_generators.university.generators import GENERATOR_METADATA as UNIVERSITY

ROOT = Path(__file__).resolve().parent
from ultron_core.data_generation import SUPPORTED_TOPICS as CORE_TOPICS


@lru_cache(maxsize=1)
def _validation_manifest() -> dict:
    path = ROOT / "validation_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported curriculum validation manifest schema")
    if not isinstance(payload.get("independent_validation"), dict):
        raise ValueError("validation manifest independent_validation must be an object")
    if not isinstance(payload.get("benchmarked"), list) or not isinstance(payload.get("mastered"), list):
        raise ValueError("validation manifest benchmarked/mastered fields must be arrays")
    return payload


def _scope_slug(grade_band: str) -> str:
    return grade_band.lower().replace("-", "_").replace(" ", "_")


def _coverage_fields(catalog_id: str, generator_available: bool) -> dict:
    manifest = _validation_manifest()
    independent = manifest["independent_validation"]
    independent_validated = catalog_id in independent
    benchmarked = catalog_id in manifest["benchmarked"]
    mastered = catalog_id in manifest["mastered"]
    if independent_validated and not generator_available:
        raise ValueError(f"independent validation listed for unavailable generator {catalog_id}")
    if benchmarked and not independent_validated:
        raise ValueError(f"benchmark listed without independent validation for {catalog_id}")
    if mastered and not benchmarked:
        raise ValueError(f"mastery listed without a benchmark for {catalog_id}")
    return {
        "independent_validation_status": (
            "independently_validated" if independent_validated else "not_independently_validated"
        ),
        "benchmark_status": "benchmarked" if benchmarked else "not_benchmarked",
        "mastery_status": "mastered" if mastered else "not_mastered",
    }


def _topic_rows(metadata: dict, flag_name: str) -> list[dict]:
    rows = []
    for topic, spec in metadata.items():
        grade_band = spec["grade_band"]
        catalog_id = f"{_scope_slug(grade_band)}:{topic}"
        rows.append({
            "catalog_id": catalog_id,
            "topic": topic,
            "grade_band": grade_band,
            flag_name: bool(spec.get("word_templates", [])),
            "status": "generator_available_not_mastered",
            **_coverage_fields(catalog_id, True),
        })
    return rows


def build_grade1_4_registry() -> dict:
    return {
        "version": 1,
        "batch": "Batch 1 - Grades 1-4",
        "topics": _topic_rows(GRADE1_4, "includes_word_problems"),
    }


def build_grade5_8_registry() -> dict:
    return {
        "version": 1,
        "batch": "Batch 2 - Grades 5-8",
        "topics": _topic_rows(GRADE5_8, "includes_word_problems"),
    }


def build_grade8_12_registry() -> dict:
    return {
        "version": 1,
        "batch": "Batch 3 - Grades 8-12",
        "topics": _topic_rows(GRADE8_12, "includes_word_problems"),
    }


def _university_curriculum() -> list[dict]:
    curriculum_path = ROOT / "university" / "curriculum.json"
    return json.loads(curriculum_path.read_text(encoding="utf-8"))["topics"]


def build_university_registry() -> dict:
    implemented = set(UNIVERSITY)
    rows = []
    for topic in _university_curriculum():
        topic_id = topic["topic"]
        generator_topic = topic.get("generator_topic", topic_id)
        has_generator = topic_id in implemented or generator_topic in implemented
        catalog_id = f"university:{topic_id}"
        status = "generator_available_not_mastered" if has_generator else "catalogued_not_implemented"
        rows.append({
            **topic,
            "catalog_id": catalog_id,
            "grade_band": "University",
            "status": status,
            "includes_word_problems": bool(
                UNIVERSITY.get(generator_topic, {}).get("word_templates", [])
            ),
            "has_generator": has_generator,
            **_coverage_fields(catalog_id, has_generator),
        })
    return {
        "version": 1,
        "batch": "University mathematics curriculum map",
        "scope": "Broad undergraduate mathematics curriculum map; not an exhaustive list of every university course or specialty.",
        "topics": rows,
    }


def build_combined_registry() -> dict:
    topics = []
    for topic in CORE_TOPICS:
        catalog_id = f"core:{topic}"
        topics.append({
            "catalog_id": catalog_id,
            "topic": topic,
            "source": "ultron_core.data_generation",
            "grade_band": "Core",
            "word_problems": False,
            "status": "generator_available_not_mastered",
            **_coverage_fields(catalog_id, True),
        })
    for metadata in (GRADE1_4, GRADE5_8, GRADE8_12):
        topics.extend(_topic_rows(metadata, "word_problems"))
    for row in build_university_registry()["topics"]:
        topics.append({
            "catalog_id": row["catalog_id"],
            "topic": row["topic"],
            "grade_band": "University",
            "word_problems": row["includes_word_problems"],
            "status": row["status"],
            "independent_validation_status": row["independent_validation_status"],
            "benchmark_status": row["benchmark_status"],
            "mastery_status": row["mastery_status"],
        })
    university_topic_count = len(_university_curriculum())
    return {
        "version": 2,
        "coverage_through": f"Core + G1-12 + {university_topic_count}-topic university mathematics curriculum; scoped IDs and explicit evidence states",
        "topics": topics,
    }


def render_registries() -> dict[str, str]:
    return {
        "grade1_4/registry.json": json.dumps(build_grade1_4_registry(), indent=2) + "\n",
        "grade5_8/registry.json": json.dumps(build_grade5_8_registry(), indent=2) + "\n",
        "grade8_12/registry.json": json.dumps(build_grade8_12_registry(), indent=2) + "\n",
        "university/registry.json": json.dumps(build_university_registry(), indent=2) + "\n",
        "registry.json": json.dumps(build_combined_registry(), indent=2) + "\n",
    }


def write_registries() -> None:
    for relative_path, rendered in render_registries().items():
        target = ROOT / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")


def check_registries() -> bool:
    """Return False when any committed registry differs from topic/evidence metadata."""
    return all(
        (ROOT / path).read_text(encoding="utf-8") == content
        for path, content in render_registries().items()
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if committed registries are stale")
    args = parser.parse_args()
    if args.check:
        if not check_registries():
            raise SystemExit(
                "Committed math-generator registries are stale; run "
                "python -m tools.math_generators.build_registry"
            )
    else:
        write_registries()
