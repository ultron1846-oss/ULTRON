"""Original deterministic mathematical example generation (no external corpus)."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import random
import re
import tempfile
from typing import Iterable

GENERATOR_VERSION = "0.1.0"
SUPPORTED_TOPICS = ("arithmetic", "rational_arithmetic", "linear_equations")
_MAX_EXAMPLES = 100_000


def _fraction_text(value: Fraction | int) -> str:
    return str(Fraction(value))


@dataclass(frozen=True)
class MathExample:
    example_id: str
    generator_version: str
    topic: str
    difficulty: int
    input_text: str
    target_text: str
    exact_answer: str
    seed: int
    index: int
    generation_parameters: tuple[tuple[str, int | str], ...]
    validation_status: str
    provenance: str

    def __post_init__(self) -> None:
        if not isinstance(self.example_id, str) or not re.fullmatch(r"[0-9a-f]{64}", self.example_id):
            raise ValueError("example_id must be a lowercase SHA-256 hex digest")
        if self.generator_version != GENERATOR_VERSION:
            raise ValueError("unsupported generator version")
        if self.topic not in SUPPORTED_TOPICS:
            raise ValueError("unsupported example topic")
        if isinstance(self.difficulty, bool) or not isinstance(self.difficulty, int) or self.difficulty <= 0:
            raise ValueError("difficulty must be a positive integer")
        if not all(isinstance(value, str) for value in (self.input_text, self.target_text, self.exact_answer, self.provenance)):
            raise TypeError("example text, answer and provenance fields must be strings")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("example seed must be an integer")
        if isinstance(self.index, bool) or not isinstance(self.index, int) or self.index < 0:
            raise ValueError("example index must be a non-negative integer")
        if not isinstance(self.generation_parameters, tuple) or any(
            not isinstance(item, tuple) or len(item) != 2 or not isinstance(item[0], str)
            or not isinstance(item[1], (int, str)) or isinstance(item[1], bool)
            for item in self.generation_parameters
        ):
            raise TypeError("generation_parameters must be an immutable tuple of string/value pairs")
        if self.validation_status not in ("semantically_checked", "rejected"):
            raise ValueError("unsupported validation status")

    def to_dict(self) -> dict:
        value = asdict(self)
        value["generation_parameters"] = dict(self.generation_parameters)
        return value


def validate_example_text(input_text: str, expected_answer: str, topic: str) -> bool:
    """Independently parse the emitted text and check it using exact Fractions."""
    if not all(isinstance(item, str) for item in (input_text, expected_answer, topic)):
        return False
    try:
        expected = Fraction(expected_answer)
        if topic in ("arithmetic", "rational_arithmetic"):
            pattern = r"^\s*([+-]?\d+(?:/\d+)?)\s*([+\-*/])\s*([+-]?\d+(?:/\d+)?)\s*$"
            match = re.fullmatch(pattern, input_text)
            if not match:
                return False
            left, operator, right = match.groups()
            a, b = Fraction(left), Fraction(right)
            if operator == "+":
                actual = a + b
            elif operator == "-":
                actual = a - b
            elif operator == "*":
                actual = a * b
            else:
                if b == 0:
                    return False
                actual = a / b
            return actual == expected
        if topic == "linear_equations":
            pattern = r"^\s*([+-]?\d+)\s*\*\s*x\s*([+-])\s*(\d+)\s*=\s*([+-]?\d+)\s*$"
            match = re.fullmatch(pattern, input_text)
            if not match:
                return False
            coefficient, sign, magnitude, rhs = match.groups()
            a = Fraction(coefficient)
            b = Fraction(magnitude) * (1 if sign == "+" else -1)
            if a == 0:
                return False
            return (Fraction(rhs) - b) / a == expected
    except (ValueError, ZeroDivisionError, TypeError):
        return False
    return False


def _make_one(rng: random.Random, seed: int, index: int, topic: str) -> MathExample:
    params: dict[str, int | str]
    if topic == "arithmetic":
        a, b = rng.randint(-50, 50), rng.randint(-50, 50)
        operator = rng.choice(("+", "-", "*"))
        answer = a + b if operator == "+" else a - b if operator == "-" else a * b
        prompt = f"{a} {operator} {b}"
        params = {"a": a, "operator": operator, "b": b}
        difficulty = 1 if max(abs(a), abs(b)) < 10 else 2
    elif topic == "rational_arithmetic":
        a = Fraction(rng.randint(-12, 12), rng.randint(1, 12))
        b = Fraction(rng.randint(-12, 12), rng.randint(1, 12))
        operator = rng.choice(("+", "-", "*", "/"))
        if operator == "/" and b == 0:
            b = Fraction(1, 1)
        answer = a + b if operator == "+" else a - b if operator == "-" else a * b if operator == "*" else a / b
        prompt = f"{a} {operator} {b}"
        params = {"a": str(a), "operator": operator, "b": str(b)}
        difficulty = 2
    elif topic == "linear_equations":
        a = rng.choice(tuple(value for value in range(-9, 10) if value != 0))
        b, solution = rng.randint(-20, 20), rng.randint(-12, 12)
        rhs = a * solution + b
        sign = "+" if b >= 0 else "-"
        prompt = f"{a}*x {sign} {abs(b)} = {rhs}"
        answer = Fraction(solution)
        params = {"coefficient": a, "constant": b, "rhs": rhs}
        difficulty = 2
    else:
        raise ValueError(f"unsupported topic: {topic}")

    answer_text = _fraction_text(answer)
    valid = validate_example_text(prompt, answer_text, topic)
    payload = {
        "generator_version": GENERATOR_VERSION, "seed": seed, "index": index,
        "topic": topic, "input_text": prompt, "target_text": answer_text,
        "generation_parameters": params,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    identifier = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return MathExample(
        example_id=identifier, generator_version=GENERATOR_VERSION, topic=topic,
        difficulty=difficulty, input_text=prompt, target_text=answer_text,
        exact_answer=answer_text, seed=seed, index=index,
        generation_parameters=tuple(sorted(params.items())),
        validation_status="semantically_checked" if valid else "rejected",
        provenance="ultron_core.data_generation deterministic generator; exact Fraction text validator",
    )


def generate_examples(seed: int, count: int,
                      topics: Iterable[str] = SUPPORTED_TOPICS) -> tuple[MathExample, ...]:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= _MAX_EXAMPLES:
        raise ValueError(f"count must be between 1 and {_MAX_EXAMPLES}")
    topics = tuple(topics)
    if not topics or any(topic not in SUPPORTED_TOPICS for topic in topics):
        raise ValueError("topics must be a non-empty subset of supported topics")
    rng = random.Random(seed)
    result = []
    for index in range(count):
        topic = topics[rng.randrange(len(topics))]
        result.append(_make_one(rng, seed, index, topic))
    if any(example.validation_status != "semantically_checked" for example in result):
        raise ArithmeticError("generated example failed independent semantic validation")
    return tuple(result)


def write_dataset(path: str | Path, examples: Iterable[MathExample],
                  *, seed: int, topics: Iterable[str]) -> dict:
    """Write deterministic JSONL and a deterministic SHA-256 manifest atomically."""
    examples = tuple(examples)
    if not examples or any(not isinstance(item, MathExample) for item in examples):
        raise ValueError("dataset must contain at least one MathExample")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("dataset seed must be an integer")
    topics = tuple(topics)
    if not topics or any(topic not in SUPPORTED_TOPICS for topic in topics):
        raise ValueError("dataset topics must be a non-empty supported-topic sequence")
    if len({item.example_id for item in examples}) != len(examples):
        raise ValueError("dataset contains duplicate example IDs")
    for item in examples:
        if item.seed != seed or item.topic not in topics:
            raise ValueError("example seed/topic does not match dataset manifest configuration")
        if item.validation_status != "semantically_checked" or not validate_example_text(
            item.input_text, item.target_text, item.topic
        ) or item.exact_answer != item.target_text:
            raise ValueError("dataset contains an example that failed exact semantic validation")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    rows = "".join(json.dumps(item.to_dict(), sort_keys=True, ensure_ascii=False,
                              separators=(",", ":")) + "\n" for item in examples)
    encoded = rows.encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    counts = dict(sorted(Counter(item.topic for item in examples).items()))
    manifest = {
        "schema_version": 1, "generator_version": GENERATOR_VERSION,
        "seed": seed, "topics": list(topics), "example_count": len(examples),
        "topic_counts": counts, "sha256": digest,
    }
    manifest_text = json.dumps(manifest, sort_keys=True, ensure_ascii=False,
                               separators=(",", ":")) + "\n"
    for output, content in (
        (target, encoded),
        (target.with_suffix(target.suffix + ".manifest.json"), manifest_text.encode("utf-8")),
    ):
        fd, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, output)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
    return manifest


def verify_dataset(path: str | Path) -> dict:
    """Verify the on-disk manifest, JSONL digest, row count and exact answers."""
    target = Path(path)
    manifest_path = target.with_suffix(target.suffix + ".manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        content = target.read_bytes()
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("dataset or manifest is missing or malformed") from exc
    required = {"schema_version", "generator_version", "seed", "topics",
                "example_count", "topic_counts", "sha256"}
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ValueError("dataset manifest schema is invalid")
    if manifest["schema_version"] != 1 or manifest["generator_version"] != GENERATOR_VERSION:
        raise ValueError("unsupported dataset manifest version")
    digest = hashlib.sha256(content).hexdigest()
    if digest != manifest["sha256"]:
        raise ValueError("dataset SHA-256 mismatch")
    try:
        rows = [json.loads(line) for line in content.decode("utf-8").splitlines() if line]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("dataset JSONL is malformed") from exc
    if len(rows) != manifest["example_count"]:
        raise ValueError("dataset example count does not match manifest")
    counts = Counter()
    identifiers = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("dataset row must be an object")
        required_row = {"example_id", "generator_version", "topic", "difficulty",
                        "input_text", "target_text", "exact_answer", "seed", "index",
                        "generation_parameters", "validation_status", "provenance"}
        if set(row) != required_row:
            raise ValueError("dataset row schema is invalid")
        if row["generator_version"] != GENERATOR_VERSION or row["seed"] != manifest["seed"]:
            raise ValueError("dataset row provenance does not match manifest")
        if row["topic"] not in manifest["topics"]:
            raise ValueError("dataset row topic is not declared in manifest")
        if row["example_id"] in identifiers:
            raise ValueError("dataset contains duplicate example IDs")
        identifiers.add(row["example_id"])
        if row["validation_status"] != "semantically_checked" or row["target_text"] != row["exact_answer"]:
            raise ValueError("dataset row has an invalid validation status or answer")
        if not validate_example_text(row["input_text"], row["exact_answer"], row["topic"]):
            raise ValueError("dataset row failed exact semantic validation")
        counts[row["topic"]] += 1
    if dict(sorted(counts.items())) != manifest["topic_counts"]:
        raise ValueError("dataset topic counts do not match manifest")
    return manifest
