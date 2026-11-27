"""Versioned, non-authorizing runtime configuration handoff.

This schema is suitable for exporting a browser preference and loading it into
future local tooling. It does not create a runtime, authorize training, or
enable remote execution.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping

SCHEMA_VERSION = 1
MIN_MEMORY_BUDGET_GIB = 2
MAX_MEMORY_BUDGET_GIB = 10
MAX_CONFIG_JSON_BYTES = 16 * 1024

_REQUIRED_KEYS = frozenset({
    "schema_version",
    "memory_budget_gib",
    "batch_size",
    "sequence_length",
    "gradient_accumulation_steps",
    "training_authorized",
    "remote_execution_enabled",
})


def _require_bounded_int(name: str, value: Any, minimum: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be in [{minimum}, {maximum}]")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


@dataclass(frozen=True)
class RuntimeConfig:
    """Validated settings only; authorization is deliberately not configurable."""

    schema_version: int = SCHEMA_VERSION
    memory_budget_gib: int = 6
    batch_size: int = 1
    sequence_length: int = 256
    gradient_accumulation_steps: int = 1
    training_authorized: bool = False
    remote_execution_enabled: bool = False

    def __post_init__(self) -> None:
        _require_bounded_int("schema_version", self.schema_version, SCHEMA_VERSION, SCHEMA_VERSION)
        _require_bounded_int(
            "memory_budget_gib", self.memory_budget_gib,
            MIN_MEMORY_BUDGET_GIB, MAX_MEMORY_BUDGET_GIB,
        )
        _require_bounded_int("batch_size", self.batch_size, 1, 16)
        _require_bounded_int("sequence_length", self.sequence_length, 2, 2048)
        _require_bounded_int(
            "gradient_accumulation_steps", self.gradient_accumulation_steps, 1, 128
        )
        if self.training_authorized is not False:
            raise ValueError("runtime config cannot authorize training")
        if self.remote_execution_enabled is not False:
            raise ValueError("runtime config cannot enable remote execution")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RuntimeConfig":
        if not isinstance(value, Mapping):
            raise TypeError("runtime config must be a mapping")
        if any(not isinstance(key, str) for key in value):
            raise TypeError("runtime config keys must be strings")
        keys = set(value)
        missing = _REQUIRED_KEYS - keys
        extra = keys - _REQUIRED_KEYS
        if missing:
            raise ValueError(f"runtime config missing keys: {', '.join(sorted(missing))}")
        if extra:
            raise ValueError(f"runtime config has unknown keys: {', '.join(sorted(extra))}")
        return cls(**dict(value))

    @classmethod
    def from_json(cls, source: str) -> "RuntimeConfig":
        if not isinstance(source, str):
            raise TypeError("runtime config JSON must be a string")
        try:
            encoded_size = len(source.encode("utf-8"))
        except UnicodeEncodeError as error:
            raise ValueError("runtime config JSON contains invalid Unicode") from error
        if encoded_size > MAX_CONFIG_JSON_BYTES:
            raise ValueError(f"runtime config JSON exceeds {MAX_CONFIG_JSON_BYTES} bytes")
        try:
            value = json.loads(source, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, UnicodeError) as error:
            raise ValueError(f"invalid runtime config JSON: {error}") from error
        if not isinstance(value, dict):
            raise TypeError("runtime config JSON root must be an object")
        return cls.from_mapping(value)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=2) + "\n"

    def preflight_kwargs(self) -> dict[str, int]:
        """Return the validated workload/budget fields accepted by preflight."""
        return {
            "memory_budget_gib": self.memory_budget_gib,
            "batch_size": self.batch_size,
            "sequence_length": self.sequence_length,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
        }
