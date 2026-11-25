"""Generate committed math-generator coverage registries from generator declarations.

Run from the repository root:
    python -m tools.math_generators.build_registry
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.math_generators.grade1_4.generators import GENERATOR_METADATA as GRADE1_4
from tools.math_generators.grade5_8.generators import GENERATOR_METADATA as GRADE5_8

ROOT = Path(__file__).resolve().parent


def _has_context(spec: dict) -> bool:
    return bool(spec.get("word_templates", []))


def build_grade5_8_registry() -> dict:
    return {
        "version": 1,
        "batch": "Batch 2 - Grades 5-8",
        "topics": [
            {
                "topic": topic,
                "grade_band": spec["grade_band"],
                "includes_word_problems": _has_context(spec),
            }
            for topic, spec in GRADE5_8.items()
        ],
    }


def build_combined_registry() -> dict:
    topics = [
        {
            "topic": topic,
            "grade_band": spec["grade_band"],
            "word_problems": _has_context(spec),
        }
        for topic, spec in GRADE1_4.items()
    ]
    topics.extend(
        {
            "topic": topic,
            "grade_band": spec["grade_band"],
            "word_problems": _has_context(spec),
        }
        for topic, spec in GRADE5_8.items()
    )
    return {"version": 1, "coverage_through": "G5-8", "topics": topics}


def render_registries() -> dict[str, str]:
    return {
        "grade5_8/registry.json": json.dumps(build_grade5_8_registry(), indent=2) + "\n",
        "registry.json": json.dumps(build_combined_registry(), indent=2) + "\n",
    }


def write_registries() -> None:
    for relative_path, rendered in render_registries().items():
        target = ROOT / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    write_registries()
