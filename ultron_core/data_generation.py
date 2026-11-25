"""Original deterministic mathematical example generation (no external corpus)."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import random
import re
import tempfile
from typing import Iterable

GENERATOR_VERSION = "0.3.0"
SUPPORTED_TOPICS = ("arithmetic", "rational_arithmetic", "linear_equations", "polynomial_derivative", "polynomial_definite_integral")
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


def _parse_integer_polynomial(text: str) -> dict[int, int]:
    """Parse the bounded integer-polynomial grammar used by generated tasks."""
    if not isinstance(text, str):
        raise ValueError("polynomial must be text")
    compact = re.sub(r"\s+", "", text)
    if compact == "0":
        return {}
    terms = re.findall(r"[+-]?[^+-]+", compact)
    if not terms or "".join(terms) != compact:
        raise ValueError("polynomial terms are malformed")
    result: dict[int, int] = {}
    for term in terms:
        match = re.fullmatch(r"([+-]?)(\d+)?(\*?x(?:\^(\d+))?)?", term)
        if not match:
            raise ValueError("polynomial term is malformed")
        sign, digits, x_term, exponent_text = match.groups()
        if x_term:
            coefficient = int(digits) if digits else 1
            exponent = int(exponent_text) if exponent_text else 1
            if exponent > 12:
                raise ValueError("polynomial exponent exceeds validator limit")
        else:
            if not digits:
                raise ValueError("constant term is malformed")
            coefficient, exponent = int(digits), 0
        if sign == "-":
            coefficient = -coefficient
        result[exponent] = result.get(exponent, 0) + coefficient
    return {power: coefficient for power, coefficient in result.items() if coefficient}


def _format_integer_polynomial(coefficients: dict[int, int]) -> str:
    terms = []
    for exponent in sorted(coefficients, reverse=True):
        coefficient = coefficients[exponent]
        if coefficient == 0:
            continue
        sign = "-" if coefficient < 0 else "+"
        magnitude = abs(coefficient)
        if exponent == 0:
            body = str(magnitude)
        else:
            coefficient_text = "" if magnitude == 1 else f"{magnitude}*"
            power_text = "" if exponent == 1 else f"^{exponent}"
            body = f"{coefficient_text}x{power_text}"
        terms.append(("-" if sign == "-" else "") + body if not terms else f" {sign} {body}")
    return "".join(terms) if terms else "0"


def validate_example_text(input_text: str, expected_answer: str, topic: str) -> bool:
    """Independently parse generated text and validate exact rational/polynomial answers."""
    if not all(isinstance(item, str) for item in (input_text, expected_answer, topic)):
        return False
    if topic == "polynomial_definite_integral":
        pattern = r"^\s*integrate\s*:\s*(.*?)\s+from\s*x\s*=\s*([+-]?\d+(?:/\d+)?)\s+to\s*x\s*=\s*([+-]?\d+(?:/\d+)?)\s*$"
        match = re.fullmatch(pattern, input_text, flags=re.IGNORECASE)
        if not match:
            return False
        try:
            polynomial = _parse_integer_polynomial(match.group(1))
            lower, upper = Fraction(match.group(2)), Fraction(match.group(3))
            actual = sum(
                (Fraction(coefficient, power + 1)
                 * (upper ** (power + 1) - lower ** (power + 1))
                 for power, coefficient in polynomial.items()),
                Fraction(0),
            )
            return actual == Fraction(expected_answer)
        except (ValueError, ZeroDivisionError, TypeError):
            return False
    if topic == "polynomial_derivative":
        match = re.fullmatch(r"^\s*differentiate\s*:\s*(.*?)\s*$", input_text, flags=re.IGNORECASE)
        if not match:
            return False
        try:
            source = _parse_integer_polynomial(match.group(1))
            expected_poly = _parse_integer_polynomial(expected_answer)
            derivative = {power - 1: coefficient * power
                          for power, coefficient in source.items() if power > 0}
            derivative = {power: coefficient for power, coefficient in derivative.items() if coefficient}
            return derivative == expected_poly
        except (ValueError, TypeError):
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
    elif topic == "polynomial_derivative":
        degree = rng.randint(2, 5)
        coefficients = {power: rng.randint(-5, 5) for power in range(degree + 1)}
        if coefficients[degree] == 0:
            coefficients[degree] = rng.choice((-5, -4, -3, -2, -1, 1, 2, 3, 4, 5))
        derivative = {power - 1: coefficient * power
                     for power, coefficient in coefficients.items() if power > 0}
        prompt = "differentiate: " + _format_integer_polynomial(coefficients)
        answer = _format_integer_polynomial(derivative)
        params = {"degree": degree, "coefficients": json.dumps(sorted(coefficients.items()))}
        difficulty = degree
    elif topic == "polynomial_definite_integral":
        degree = rng.randint(1, 4)
        coefficients = {power: rng.randint(-5, 5) for power in range(degree + 1)}
        if coefficients[degree] == 0:
            coefficients[degree] = rng.choice((-5, -4, -3, -2, -1, 1, 2, 3, 4, 5))
        lower = Fraction(rng.randint(-4, 4), rng.randint(1, 3))
        upper = Fraction(rng.randint(-4, 4), rng.randint(1, 3))
        if lower == upper:
            upper += 1
        answer = sum(
            (Fraction(coefficient, power + 1)
             * (upper ** (power + 1) - lower ** (power + 1))
             for power, coefficient in coefficients.items()),
            Fraction(0),
        )
        prompt = (f"integrate: {_format_integer_polynomial(coefficients)} "
                  f"from x={_fraction_text(lower)} to x={_fraction_text(upper)}")
        params = {"degree": degree, "coefficients": json.dumps(sorted(coefficients.items())),
                  "lower": _fraction_text(lower), "upper": _fraction_text(upper)}
        difficulty = degree + 1
    else:
        raise ValueError(f"unsupported topic: {topic}")

    answer_text = answer if topic == "polynomial_derivative" else _fraction_text(answer)
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



def split_examples(
    examples: Iterable[MathExample],
    *,
    validation_fraction: float = 0.1,
    test_fraction: float = 0.1,
    seed: int = 0,
) -> dict[str, tuple[MathExample, ...]]:
    """Create deterministic prompt-disjoint train/validation/test splits.

    Duplicate normalized prompts are collapsed before assignment, and the
    SHA-256 assignment uses the prompt group so variants cannot cross splits.
    """
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("split seed must be an integer")
    for name, value in (("validation_fraction", validation_fraction), ("test_fraction", test_fraction)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if not 0.0 < value < 1.0:
            raise ValueError(f"{name} must be in (0, 1)")
    if validation_fraction + test_fraction >= 1.0:
        raise ValueError("validation_fraction + test_fraction must be less than 1")
    items = tuple(examples)
    if not items or any(not isinstance(item, MathExample) for item in items):
        raise ValueError("examples must contain at least one MathExample")
    groups: dict[str, MathExample] = {}
    for item in items:
        if (item.validation_status != "semantically_checked"
                or item.target_text != item.exact_answer
                or not validate_example_text(item.input_text, item.exact_answer, item.topic)):
            raise ValueError("split input contains an invalid or unverified example")
        prompt = " ".join(item.input_text.split())
        current = groups.get(prompt)
        if current is None or item.example_id < current.example_id:
            groups[prompt] = item
    if len(groups) < 3:
        raise ValueError("at least three unique normalized prompts are required for three splits")
    result: dict[str, list[MathExample]] = {"train": [], "validation": [], "test": []}
    for prompt, item in sorted(groups.items()):
        assignment = hashlib.sha256(
            f"ultron-split-v1\0{seed}\0{prompt}".encode("utf-8")
        ).digest()
        bucket = int.from_bytes(assignment[:8], "big") / 2**64
        if bucket < test_fraction:
            result["test"].append(item)
        elif bucket < test_fraction + validation_fraction:
            result["validation"].append(item)
        else:
            result["train"].append(item)
    if any(not result[name] for name in result):
        raise ValueError("split seed/fractions produced an empty split; increase unique prompt count")
    return {name: tuple(values) for name, values in result.items()}

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
    """Verify manifest schema, file digest, row identity and exact answers."""
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
    if (isinstance(manifest["schema_version"], bool) or manifest["schema_version"] != 1
            or manifest["generator_version"] != GENERATOR_VERSION):
        raise ValueError("unsupported dataset manifest version")
    if isinstance(manifest["seed"], bool) or not isinstance(manifest["seed"], int):
        raise ValueError("dataset manifest seed is invalid")
    topics = manifest["topics"]
    if (not isinstance(topics, list) or not topics
            or any(not isinstance(topic, str) or topic not in SUPPORTED_TOPICS for topic in topics)
            or len(set(topics)) != len(topics)):
        raise ValueError("dataset manifest topics are invalid")
    count = manifest["example_count"]
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise ValueError("dataset manifest example_count is invalid")
    topic_counts = manifest["topic_counts"]
    if (not isinstance(topic_counts, dict)
            or any(topic not in topics for topic in topic_counts)
            or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0
                   for value in topic_counts.values())
            or sum(topic_counts.values()) != count):
        raise ValueError("dataset manifest topic_counts are invalid")
    digest_expected = manifest["sha256"]
    if not isinstance(digest_expected, str) or not re.fullmatch(r"[0-9a-f]{64}", digest_expected):
        raise ValueError("dataset manifest SHA-256 is invalid")
    digest = hashlib.sha256(content).hexdigest()
    if digest != digest_expected:
        raise ValueError("dataset SHA-256 mismatch")
    if not content.endswith(b"\n"):
        raise ValueError("dataset JSONL must end with a newline")
    try:
        decoded = content.decode("utf-8")
        lines = decoded.splitlines()
        if any(not line for line in lines):
            raise ValueError("dataset JSONL contains blank rows")
        rows = [json.loads(line) for line in lines]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("dataset JSONL is malformed") from exc
    if len(rows) != count:
        raise ValueError("dataset example count does not match manifest")

    counts = Counter()
    identifiers = set()
    indexes = set()
    required_row = {"example_id", "generator_version", "topic", "difficulty",
                    "input_text", "target_text", "exact_answer", "seed", "index",
                    "generation_parameters", "validation_status", "provenance"}
    for row in rows:
        if not isinstance(row, dict) or set(row) != required_row:
            raise ValueError("dataset row schema is invalid")
        if not isinstance(row["example_id"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["example_id"]):
            raise ValueError("dataset row example_id is malformed")
        if row["example_id"] in identifiers:
            raise ValueError("dataset contains duplicate example IDs")
        identifiers.add(row["example_id"])
        if (row["generator_version"] != GENERATOR_VERSION
                or isinstance(row["seed"], bool) or not isinstance(row["seed"], int)
                or row["seed"] != manifest["seed"]):
            raise ValueError("dataset row provenance does not match manifest")
        if not isinstance(row["topic"], str) or row["topic"] not in topics:
            raise ValueError("dataset row topic is not declared in manifest")
        if (isinstance(row["difficulty"], bool) or not isinstance(row["difficulty"], int)
                or row["difficulty"] <= 0):
            raise ValueError("dataset row difficulty is invalid")
        if (not isinstance(row["index"], int) or isinstance(row["index"], bool)
                or row["index"] < 0 or row["index"] in indexes):
            raise ValueError("dataset row index is invalid or duplicated")
        indexes.add(row["index"])
        if not all(isinstance(row[key], str) for key in ("input_text", "target_text", "exact_answer", "provenance")):
            raise ValueError("dataset row text/provenance fields are invalid")
        params = row["generation_parameters"]
        if (not isinstance(params, dict)
                or any(not isinstance(key, str) or isinstance(value, bool)
                       or not isinstance(value, (int, str)) for key, value in params.items())):
            raise ValueError("dataset row generation_parameters are invalid")
        if (row["validation_status"] != "semantically_checked"
                or row["target_text"] != row["exact_answer"]
                or not validate_example_text(row["input_text"], row["exact_answer"], row["topic"])):
            raise ValueError("dataset row failed exact semantic validation")
        identity_payload = {
            "generator_version": row["generator_version"], "seed": row["seed"],
            "index": row["index"], "topic": row["topic"],
            "input_text": row["input_text"], "target_text": row["target_text"],
            "generation_parameters": params,
        }
        canonical = json.dumps(identity_payload, sort_keys=True, separators=(",", ":"),
                                ensure_ascii=False)
        expected_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(row["example_id"], expected_id):
            raise ValueError("dataset row example_id does not match its content")
        counts[row["topic"]] += 1
    if dict(sorted(counts.items())) != manifest["topic_counts"]:
        raise ValueError("dataset topic counts do not match manifest")
    return manifest
