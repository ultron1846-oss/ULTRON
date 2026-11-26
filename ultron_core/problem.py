"""Shared canonical problem contract and verifier interface for ULTRON generators."""
from __future__ import annotations

from abc import ABC, abstractmethod
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
        if not isinstance(record, Mapping) or not isinstance(source, str) or not source:
            raise TypeError("record and source are required")
        prompt = record.get("problem", record.get("input_text"))
        answer = record.get("answer", record.get("target_text", record.get("exact_answer")))
        topic, seed = record.get("topic"), record.get("seed")
        difficulty = record.get("difficulty", 1)
        if not isinstance(prompt, str) or not isinstance(answer, str) or not isinstance(topic, str):
            raise ValueError("generator record is missing prompt, answer, or topic")
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
        if not isinstance(steps, (tuple, list)) or any(not isinstance(x, str) for x in steps):
            steps = ()
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProblemVerifier(ABC):
    """Common interface for source-specific exact or replay verifiers."""
    @abstractmethod
    def verify(self, problem: Problem) -> bool:
        raise NotImplementedError


class CoreExactVerifier(ProblemVerifier):
    def verify(self, problem: Problem) -> bool:
        from ultron_core.data_generation import validate_example_text
        return (problem.source == "ultron_core.data_generation"
                and validate_example_text(problem.prompt, problem.answer, problem.topic))


class ReplayGeneratorVerifier(ProblemVerifier):
    def __init__(self, source_record: Mapping[str, Any],
                 verify_fn: Callable[[dict], bool], *, source: str):
        self._record = dict(source_record)
        self._verify_fn = verify_fn
        self._source = source

    def verify(self, problem: Problem) -> bool:
        try:
            return (problem.source == self._source
                    and Problem.from_generator(self._record, source=self._source) == problem
                    and bool(self._verify_fn(self._record)))
        except (KeyError, TypeError, ValueError, ArithmeticError, ZeroDivisionError):
            return False
