"""Generate committed math-generator coverage registries from topic declarations.

Run from the repository root:
    python -m tools.math_generators.build_registry
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.math_generators.grade1_4.generators import GENERATOR_METADATA as GRADE1_4
from tools.math_generators.grade5_8.generators import GENERATOR_METADATA as GRADE5_8
from tools.math_generators.grade8_12.generators import GENERATOR_METADATA as GRADE8_12
from tools.math_generators.university.generators import GENERATOR_METADATA as UNIVERSITY

ROOT = Path(__file__).resolve().parent


def _topic_rows(metadata: dict, flag_name: str) -> list[dict]:
    return [
        {
            "topic": topic,
            "grade_band": spec["grade_band"],
            flag_name: bool(spec.get("word_templates", [])),
        }
        for topic, spec in metadata.items()
    ]


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
        rows.append({
            **topic,
            "grade_band": "University",
            "includes_word_problems": bool(UNIVERSITY.get(topic.get("generator_topic", topic["topic"]), {}).get("word_templates", [])),
            "has_generator": topic["topic"] in implemented or topic.get("generator_topic") in implemented,
        })
    return {
        "version": 1,
        "batch": "University mathematics curriculum map",
        "scope": "Broad undergraduate mathematics curriculum map; not an exhaustive list of every university course or specialty.",
        "topics": rows,
    }

def build_combined_registry() -> dict:
    topics = []
    for metadata in (GRADE1_4, GRADE5_8, GRADE8_12):
        topics.extend(_topic_rows(metadata, "word_problems"))
    topics.extend([
        {"topic": row["topic"], "grade_band": "University",
         "word_problems": bool(UNIVERSITY.get(row.get("generator_topic", row["topic"]), {}).get("word_templates", [])),
         "status": row["status"]}
        for row in _university_curriculum()
    ])
    return {
        "version": 1,
        "coverage_through": "G1-12 + university mathematics curriculum catalog (generator status explicit)",
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


if __name__ == "__main__":
    write_registries()
