"""Shared canonical problem contract and verifier interface for ULTRON generators."""
from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Callable, Mapping

PROBLEM_SCHEMA_VERSION = 1


def normalize_problem_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("problem text must be a string")
    return re.sub(r"\s+", " ", text).strip().casefold()


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Problem:
    schema_version: int
    problem_id: str
    source: str
    topic: str
    prompt: str
    answer: str
    seed: int
    difficulty: int
    normalized_text: str
    ingredients_sha256: str
    steps: tuple[str, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_generator(cls, record: Mapping[str, Any], *, source: str) -> "Problem":
        if not isinstance(record, Mapping) or not isinstance(source, str) or not source.strip():
            raise TypeError("record and non-empty source are required")
        if any(not isinstance(key, str) or not key for key in record):
            raise ValueError("generator record keys must be non-empty strings")
        prompt = record.get("problem", record.get("input_text"))
        answer = record.get("answer", record.get("target_text", record.get("exact_answer")))
        topic, seed = record.get("topic"), record.get("seed")
        difficulty = record.get("difficulty", 1)
        if (not isinstance(prompt, str) or not prompt.strip()
                or not isinstance(answer, str) or not answer.strip()
                or not isinstance(topic, str) or not topic.strip()):
            raise ValueError("generator record is missing non-empty prompt, answer, or topic")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("generator record seed must be an integer")
        if isinstance(difficulty, bool) or not isinstance(difficulty, int) or difficulty < 1:
            raise ValueError("generator record difficulty must be positive")
        normalized = normalize_problem_text(prompt)
        ingredients = record.get("ingredients", record.get("generation_parameters"))
        if ingredients is None:
            ingredients = {"normalized_prompt": normalized}
        ingredients_hash = canonical_hash(ingredients)
        identity = {
            "schema_version": PROBLEM_SCHEMA_VERSION, "source": source, "topic": topic,
            "seed": seed, "difficulty": difficulty, "normalized_text": normalized,
            "ingredients_sha256": ingredients_hash,
        }
        steps = record.get("steps", ())
        if (not isinstance(steps, (tuple, list))
                or any(not isinstance(item, str) or not item.strip() for item in steps)):
            raise ValueError("generator steps must be a sequence of non-empty strings")
        metadata = tuple(sorted((str(k), str(v)) for k, v in record.items()
            if k not in {"id", "problem", "input_text", "answer", "target_text",
                          "exact_answer", "seed", "difficulty", "steps",
                          "ingredients", "generation_parameters"}))
        return cls(PROBLEM_SCHEMA_VERSION, canonical_hash(identity), source, topic,
                   prompt, answer, seed, difficulty, normalized, ingredients_hash,
                   tuple(steps), metadata)

    @classmethod
    def from_core(cls, example: Any) -> "Problem":
        record = {
            "topic": example.topic, "input_text": example.input_text,
            "target_text": example.target_text, "exact_answer": example.exact_answer,
            "seed": example.seed, "difficulty": example.difficulty,
            "generation_parameters": dict(example.generation_parameters),
            "validation_status": example.validation_status,
        }
        return cls.from_generator(record, source="ultron_core.data_generation")

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Problem":
        """Restore a problem document and verify its content-derived identity."""
        required = {
            "schema_version", "problem_id", "source", "topic", "prompt", "answer",
            "seed", "difficulty", "normalized_text", "ingredients_sha256",
            "steps", "metadata",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise ValueError("problem document fields do not match schema version 1")

        version = value["schema_version"]
        if isinstance(version, bool) or not isinstance(version, int) or version != PROBLEM_SCHEMA_VERSION:
            raise ValueError("unsupported problem schema version")
        problem_id = value["problem_id"]
        source, topic = value["source"], value["topic"]
        prompt, answer = value["prompt"], value["answer"]
        seed, difficulty = value["seed"], value["difficulty"]
        normalized, ingredients_hash = value["normalized_text"], value["ingredients_sha256"]
        if not isinstance(problem_id, str) or not re.fullmatch(r"[0-9a-f]{64}", problem_id):
            raise ValueError("problem_id must be a lowercase SHA-256 digest")
        if (not isinstance(source, str) or not source.strip()
                or not isinstance(topic, str) or not topic.strip()
                or not isinstance(prompt, str) or not prompt.strip()
                or not isinstance(answer, str) or not answer.strip()):
            raise ValueError("problem source, topic, prompt, and answer must be non-empty strings")
        if normalized != normalize_problem_text(prompt):
            raise ValueError("normalized_text does not match the problem prompt")
        if not isinstance(ingredients_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", ingredients_hash):
            raise ValueError("ingredients_sha256 must be a lowercase SHA-256 digest")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("problem seed must be an integer")
        if isinstance(difficulty, bool) or not isinstance(difficulty, int) or difficulty < 1:
            raise ValueError("problem difficulty must be a positive integer")

        raw_steps = value["steps"]
        if (not isinstance(raw_steps, (list, tuple))
                or any(not isinstance(item, str) or not item.strip() for item in raw_steps)):
            raise ValueError("problem steps must be a sequence of non-empty strings")
        raw_metadata = value["metadata"]
        if not isinstance(raw_metadata, (list, tuple)):
            raise ValueError("problem metadata must be a sequence of string pairs")
        metadata = []
        for pair in raw_metadata:
            if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                    or not all(isinstance(item, str) for item in pair)):
                raise ValueError("problem metadata must contain only string pairs")
            metadata.append((pair[0], pair[1]))
        if tuple(metadata) != tuple(sorted(metadata)) or len({key for key, _ in metadata}) != len(metadata):
            raise ValueError("problem metadata keys must be unique and sorted")

        identity = {
            "schema_version": PROBLEM_SCHEMA_VERSION,
            "source": source,
            "topic": topic,
            "seed": seed,
            "difficulty": difficulty,
            "normalized_text": normalized,
            "ingredients_sha256": ingredients_hash,
        }
        if canonical_hash(identity) != problem_id:
            raise ValueError("problem_id does not match the serialized problem identity")
        return cls(
            version, problem_id, source, topic, prompt, answer, seed, difficulty,
            normalized, ingredients_hash, tuple(raw_steps), tuple(metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProblemVerifier(ABC):
    """Common interface for source-specific exact or replay verifiers."""

    @abstractmethod
    def verify(self, problem: Problem) -> bool:
        raise NotImplementedError

    def verified_fields(self, problem: Problem) -> tuple[str, ...]:
        """Return the task fields actually checked by this verifier.

        The conservative default covers the problem and final answer only.
        Implementations must override this to claim derivation verification.
        """
        return ("problem", "answer")


class CoreExactVerifier(ProblemVerifier):
    def verify(self, problem: Problem) -> bool:
        if not isinstance(problem, Problem):
            return False
        from ultron_core.data_generation import validate_example_text
        return (problem.source == "ultron_core.data_generation"
                and validate_example_text(problem.prompt, problem.answer, problem.topic))


class ReplayGeneratorVerifier(ProblemVerifier):
    def __init__(
        self,
        source_record: Mapping[str, Any],
        verify_fn: Callable[[dict], bool],
        *,
        source: str,
        verified_fields: tuple[str, ...] = ("problem", "answer"),
    ):
        if not isinstance(source_record, Mapping):
            raise TypeError("source_record must be a mapping")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source must be non-empty text")
        if not callable(verify_fn):
            raise TypeError("verify_fn must be callable")
        if not isinstance(verified_fields, (tuple, list)):
            raise TypeError("verified_fields must be a tuple or list")
        fields = tuple(verified_fields)
        allowed = ("problem", "derivation", "answer")
        if (any(not isinstance(field, str) or field not in allowed for field in fields)
                or len(set(fields)) != len(fields)
                or fields != tuple(field for field in allowed if field in fields)
                or not {"problem", "answer"} <= set(fields)):
            raise ValueError(
                "verified_fields must be an ordered subset containing problem and answer"
            )
        self._record = deepcopy(dict(source_record))
        self._verify_fn = verify_fn
        self._source = source
        self._verified_fields = fields

    def verified_fields(self, problem: Problem) -> tuple[str, ...]:
        if not isinstance(problem, Problem):
            raise TypeError("problem must be a Problem")
        if "derivation" in self._verified_fields and not problem.steps:
            raise ValueError("derivation scope requires non-empty problem steps")
        return self._verified_fields

    def verify(self, problem: Problem) -> bool:
        if not isinstance(problem, Problem):
            return False
        try:
            expected = Problem.from_generator(self._record, source=self._source)
            if expected != problem:
                return False
            # Give custom verifier callbacks an isolated copy so they cannot
            # mutate the stored source record used for identity comparisons.
            verifier_result = self._verify_fn(deepcopy(self._record))
            return type(verifier_result) is bool and verifier_result is True
        except (KeyError, TypeError, ValueError, ArithmeticError, ZeroDivisionError):
            return False
