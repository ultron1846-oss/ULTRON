"""Validated prerequisite graph loader for the university curriculum catalog."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CURRICULUM = _REPOSITORY_ROOT / "tools/math_generators/university/curriculum.json"
_DEFAULT_PREREQUISITES = _REPOSITORY_ROOT / "tools/math_generators/university/prerequisites.json"


@dataclass(frozen=True)
class CurriculumPrerequisiteMap:
    prerequisites: Mapping[str, tuple[str, ...]]
    topological_order: tuple[str, ...]
    mapped_topic_count: int
    source_topic_count: int
    coverage_fields: tuple[str, ...]

    def prerequisites_for(self, topic: str) -> tuple[str, ...]:
        try:
            return self.prerequisites[topic]
        except KeyError as exc:
            raise ValueError(f"topic has no curated prerequisite mapping: {topic!r}") from exc

    def is_prerequisite(self, prerequisite: str, topic: str) -> bool:
        """Return whether prerequisite is a direct edge, not transitive closure."""
        return prerequisite in self.prerequisites_for(topic)


def _topological_order(prerequisites: Mapping[str, tuple[str, ...]]) -> tuple[str, ...]:
    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(topic: str) -> None:
        if topic in visiting:
            raise ValueError("curriculum prerequisite graph contains a cycle")
        if topic in visited:
            return
        visiting.add(topic)
        for parent in prerequisites[topic]:
            visit(parent)
        visiting.remove(topic)
        visited.add(topic)
        order.append(topic)

    for topic in prerequisites:
        visit(topic)
    return tuple(order)


def validate_prerequisite_data(data: dict, curriculum: dict) -> CurriculumPrerequisiteMap:
    """Validate coverage, edge references, and acyclicity against the source catalog."""
    if not isinstance(data, dict) or not isinstance(curriculum, dict):
        raise TypeError("prerequisite data and curriculum must be JSON objects")
    if data.get("schema_version") != 1 or isinstance(data.get("schema_version"), bool):
        raise ValueError("unsupported prerequisite map schema version")
    topics = curriculum.get("topics")
    if not isinstance(topics, list) or not topics:
        raise ValueError("curriculum topics must be a non-empty list")
    topic_by_id = {}
    for item in topics:
        if not isinstance(item, dict) or not isinstance(item.get("topic"), str):
            raise ValueError("curriculum contains an invalid topic entry")
        topic_id = item["topic"]
        if topic_id in topic_by_id:
            raise ValueError("curriculum contains duplicate topic IDs")
        topic_by_id[topic_id] = item

    source_count = data.get("source_topic_count")
    if isinstance(source_count, bool) or not isinstance(source_count, int) or source_count != len(topics):
        raise ValueError("prerequisite map source topic count does not match curriculum")
    fields = data.get("coverage_fields")
    if (not isinstance(fields, list) or not fields
            or any(not isinstance(field, str) or not field for field in fields)
            or len(set(fields)) != len(fields)):
        raise ValueError("coverage_fields must be a unique non-empty string list")
    expected = {
        topic_id for topic_id, item in topic_by_id.items()
        if item.get("field") in set(fields)
    }
    raw = data.get("prerequisites")
    if not isinstance(raw, dict) or set(raw) != expected:
        raise ValueError("prerequisite map must cover exactly the declared curriculum fields")
    mapped_count = data.get("mapped_topic_count")
    if isinstance(mapped_count, bool) or not isinstance(mapped_count, int) or mapped_count != len(raw):
        raise ValueError("mapped_topic_count does not match prerequisite map")
    parsed: dict[str, tuple[str, ...]] = {}
    for topic, parents in raw.items():
        if not isinstance(topic, str) or topic not in topic_by_id:
            raise ValueError("prerequisite map contains an unknown topic")
        if not isinstance(parents, list) or any(not isinstance(parent, str) for parent in parents):
            raise ValueError(f"prerequisites for {topic!r} must be a string list")
        if len(set(parents)) != len(parents):
            raise ValueError(f"prerequisites for {topic!r} contain duplicates")
        if topic in parents:
            raise ValueError(f"topic {topic!r} cannot be its own prerequisite")
        if any(parent not in raw for parent in parents):
            raise ValueError(f"prerequisites for {topic!r} reference an unmapped topic")
        parsed[topic] = tuple(parents)

    order = _topological_order(parsed)
    return CurriculumPrerequisiteMap(
        prerequisites=MappingProxyType(parsed),
        topological_order=order,
        mapped_topic_count=len(parsed),
        source_topic_count=len(topics),
        coverage_fields=tuple(fields),
    )


def load_curriculum_prerequisites(
    *,
    curriculum_path: str | Path = _DEFAULT_CURRICULUM,
    prerequisites_path: str | Path = _DEFAULT_PREREQUISITES,
) -> CurriculumPrerequisiteMap:
    """Load and validate the committed prerequisite map; performs no data generation."""
    try:
        curriculum = json.loads(Path(curriculum_path).read_text(encoding="utf-8"))
        data = json.loads(Path(prerequisites_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("curriculum or prerequisite JSON is missing or malformed") from exc
    return validate_prerequisite_data(data, curriculum)
