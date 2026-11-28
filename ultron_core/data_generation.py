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

from .dataset_resource_limits import DatasetResourceLimits

GENERATOR_VERSION = "0.5.0"
SUPPORTED_TOPICS = ("arithmetic", "rational_arithmetic", "linear_equations", "polynomial_derivative", "polynomial_definite_integral", "matrix_determinant_2x2", "linear_system_2x2", "matrix_inverse_2x2")
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
        if len({item[0] for item in self.generation_parameters}) != len(self.generation_parameters):
            raise ValueError("generation_parameters keys must be unique")
        if self.validation_status not in ("semantically_checked", "rejected"):
            raise ValueError("unsupported validation status")

    def to_dict(self) -> dict:
        value = asdict(self)
        value["generation_parameters"] = dict(self.generation_parameters)
        return value

    def to_problem(self):
        """Adapt this legacy core record to the shared Problem schema."""
        from ultron_core.problem import Problem
        return Problem.from_core(self)


def _example_identity_digest(row: dict) -> str:
    """Hash the canonical identity fields shared by generation, writing and verification."""
    identity_payload = {
        "generator_version": row["generator_version"],
        "seed": row["seed"],
        "index": row["index"],
        "topic": row["topic"],
        "input_text": row["input_text"],
        "target_text": row["target_text"],
        "generation_parameters": row["generation_parameters"],
    }
    canonical = json.dumps(
        identity_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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


def _parse_linear_system_answer(text: str) -> tuple[Fraction, Fraction]:
    """Parse an exact x/y solution pair for the bounded 2x2 system topic."""
    if not isinstance(text, str):
        raise ValueError("linear-system answer must be text")
    match = re.fullmatch(
        r"\s*x\s*=\s*([+-]?\d+(?:/\d+)?)\s*,\s*y\s*=\s*([+-]?\d+(?:/\d+)?)\s*",
        text, flags=re.IGNORECASE,
    )
    if not match:
        raise ValueError("linear-system answer must be 'x=<rational>, y=<rational>'")
    return Fraction(match.group(1)), Fraction(match.group(2))


def _parse_matrix_inverse_answer(text: str) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    """Parse a 2x2 exact-rational matrix answer."""
    if not isinstance(text, str):
        raise ValueError("matrix answer must be text")
    pattern = (
        r"^\s*\[\[\s*([+-]?\d+(?:/\d+)?)\s*,\s*"
        r"([+-]?\d+(?:/\d+)?)\s*\]\s*,\s*"
        r"\[\s*([+-]?\d+(?:/\d+)?)\s*,\s*"
        r"([+-]?\d+(?:/\d+)?)\s*\]\]\s*$"
    )
    match = re.fullmatch(pattern, text)
    if not match:
        raise ValueError("matrix answer must be a 2x2 rational matrix")
    return tuple(Fraction(value) for value in match.groups())


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
    if topic == "matrix_determinant_2x2":
        match = re.fullmatch(
            r"^\s*determinant\s*:\s*\[\[\s*([+-]?\d+)\s*,\s*([+-]?\d+)\s*\]\s*,\s*\[\s*([+-]?\d+)\s*,\s*([+-]?\d+)\s*\]\s*\]\s*$",
            input_text, flags=re.IGNORECASE,
        )
        if not match:
            return False
        try:
            a, b, c, d = map(int, match.groups())
            return Fraction(a * d - b * c) == Fraction(expected_answer)
        except (ValueError, ZeroDivisionError, TypeError):
            return False
    if topic == "matrix_inverse_2x2":
        match = re.fullmatch(
            r"^\s*inverse\s*:\s*\[\[\s*([+-]?\d+)\s*,\s*([+-]?\d+)\s*\]\s*,\s*\[\s*([+-]?\d+)\s*,\s*([+-]?\d+)\s*\]\s*\]\s*$",
            input_text, flags=re.IGNORECASE,
        )
        if not match:
            return False
        try:
            a, b, c, d = map(int, match.groups())
            determinant = a * d - b * c
            if determinant == 0:
                return False
            expected = _parse_matrix_inverse_answer(expected_answer)
            actual = (
                Fraction(d, determinant), Fraction(-b, determinant),
                Fraction(-c, determinant), Fraction(a, determinant),
            )
            return actual == expected
        except (ValueError, ZeroDivisionError, TypeError):
            return False
    if topic == "linear_system_2x2":
        match = re.fullmatch(
            r"^\s*solve\s*:\s*([+-]?\d+)\s*\*\s*x\s*([+-])\s*(\d+)\s*\*\s*y\s*=\s*([+-]?\d+)\s*;\s*([+-]?\d+)\s*\*\s*x\s*([+-])\s*(\d+)\s*\*\s*y\s*=\s*([+-]?\d+)\s*$",
            input_text, flags=re.IGNORECASE,
        )
        if not match:
            return False
        try:
            a_text, sign_b, b_text, c_text, d_text, sign_e, e_text, f_text = match.groups()
            a, b, c, d, e, f = (
                int(a_text),
                int(b_text) * (1 if sign_b == "+" else -1),
                int(c_text), int(d_text),
                int(e_text) * (1 if sign_e == "+" else -1),
                int(f_text),
            )
            determinant = a * e - b * d
            if determinant == 0:
                return False
            expected_x, expected_y = _parse_linear_system_answer(expected_answer)
            actual_x = Fraction(c * e - b * f, determinant)
            actual_y = Fraction(a * f - c * d, determinant)
            return (actual_x, actual_y) == (expected_x, expected_y)
        except (ValueError, ZeroDivisionError, TypeError):
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
    elif topic == "matrix_determinant_2x2":
        a, b, c, d = (rng.randint(-9, 9) for _ in range(4))
        answer = a * d - b * c
        prompt = f"determinant: [[{a}, {b}], [{c}, {d}]]"
        params = {"a": a, "b": b, "c": c, "d": d}
        difficulty = 3
    elif topic == "matrix_inverse_2x2":
        while True:
            a, b, c, d = (rng.randint(-6, 6) for _ in range(4))
            determinant = a * d - b * c
            if determinant != 0:
                break
        inverse_values = (
            Fraction(d, determinant), Fraction(-b, determinant),
            Fraction(-c, determinant), Fraction(a, determinant),
        )
        prompt = f"inverse: [[{a}, {b}], [{c}, {d}]]"
        answer = (
            f"[[{_fraction_text(inverse_values[0])}, {_fraction_text(inverse_values[1])}], "
            f"[{_fraction_text(inverse_values[2])}, {_fraction_text(inverse_values[3])}]]"
        )
        params = {"a": a, "b": b, "c": c, "d": d, "determinant": determinant}
        difficulty = 4
    elif topic == "linear_system_2x2":
        while True:
            a, b, d, e = (rng.randint(-5, 5) for _ in range(4))
            determinant = a * e - b * d
            if determinant != 0:
                break
        x, y = rng.randint(-5, 5), rng.randint(-5, 5)
        c, f = a * x + b * y, d * x + e * y
        prompt = (f"solve: {a}*x {'+' if b >= 0 else '-'} {abs(b)}*y = {c}; "
                  f"{d}*x {'+' if e >= 0 else '-'} {abs(e)}*y = {f}")
        answer = (f"x={_fraction_text(Fraction(c * e - b * f, determinant))}, "
                  f"y={_fraction_text(Fraction(a * f - c * d, determinant))}")
        params = {"a": a, "b": b, "c": c, "d": d, "e": e, "f": f,
                  "determinant": determinant}
        difficulty = 4
    else:
        raise ValueError(f"unsupported topic: {topic}")

    answer_text = answer if topic in ("polynomial_derivative", "linear_system_2x2", "matrix_inverse_2x2") else _fraction_text(answer)
    valid = validate_example_text(prompt, answer_text, topic)
    payload = {
        "generator_version": GENERATOR_VERSION, "seed": seed, "index": index,
        "topic": topic, "input_text": prompt, "target_text": answer_text,
        "generation_parameters": params,
    }
    identifier = _example_identity_digest(payload)
    return MathExample(
        example_id=identifier, generator_version=GENERATOR_VERSION, topic=topic,
        difficulty=difficulty, input_text=prompt, target_text=answer_text,
        exact_answer=answer_text, seed=seed, index=index,
        generation_parameters=tuple(sorted(params.items())),
        validation_status="semantically_checked" if valid else "rejected",
        provenance="ultron_core.data_generation deterministic generator; exact Fraction text validator",
    )


def generate_examples(
    seed: int,
    count: int,
    topics: Iterable[str] = SUPPORTED_TOPICS,
    *,
    resource_limits: DatasetResourceLimits | None = None,
) -> tuple[MathExample, ...]:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    resource_limits = resource_limits or DatasetResourceLimits()
    if not isinstance(resource_limits, DatasetResourceLimits):
        raise TypeError("resource_limits must be DatasetResourceLimits")
    maximum_count = min(_MAX_EXAMPLES, resource_limits.max_rows)
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= maximum_count:
        raise ValueError(f"count must be between 1 and {maximum_count}")
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




def summarize_corpus(examples: Iterable[MathExample], *, splits=None) -> dict:
    """Report topic/difficulty coverage and duplicate/invalid rows without generating data."""
    items = tuple(examples)
    if not items or any(not isinstance(item, MathExample) for item in items):
        raise ValueError("examples must contain at least one MathExample")
    ids = [item.example_id for item in items]
    prompt_groups = [re.sub(r"\s+", " ", item.input_text).strip().casefold() for item in items]
    topic_counts = Counter(item.topic for item in items)
    difficulty_counts = Counter(str(item.difficulty) for item in items)
    topic_difficulty = {
        topic: dict(sorted(Counter(str(item.difficulty) for item in items if item.topic == topic).items(),
                           key=lambda pair: int(pair[0])))
        for topic in sorted(topic_counts)
    }
    valid_count = sum(
        item.validation_status == "semantically_checked"
        and item.target_text == item.exact_answer
        and validate_example_text(item.input_text, item.exact_answer, item.topic)
        for item in items
    )
    result = {
        "schema_version": 1,
        "example_count": len(items),
        "unique_example_id_count": len(set(ids)),
        "duplicate_example_id_count": len(ids) - len(set(ids)),
        "unique_prompt_count": len(set(prompt_groups)),
        "duplicate_prompt_count": len(prompt_groups) - len(set(prompt_groups)),
        "validated_example_count": valid_count,
        "invalid_example_count": len(items) - valid_count,
        "topic_counts": dict(sorted(topic_counts.items())),
        "topic_proportions": {
            topic: count / len(items) for topic, count in sorted(topic_counts.items())
        },
        "difficulty_counts": dict(sorted(difficulty_counts.items(), key=lambda pair: int(pair[0]))),
        "topic_difficulty_counts": topic_difficulty,
        "training_performed": False,
        "data_generated": False,
    }
    if splits is not None:
        if not isinstance(splits, dict) or set(splits) != {"train", "validation", "test"}:
            raise ValueError("splits must contain exactly train, validation, and test")
        split_prompt_groups = {}
        split_counts = {}
        split_id_counts = Counter()
        for name, rows in splits.items():
            rows = tuple(rows)
            if any(not isinstance(item, MathExample) for item in rows):
                raise TypeError(f"{name} split contains a non-MathExample row")
            split_counts[name] = len(rows)
            split_prompt_groups[name] = {
                re.sub(r"\s+", " ", item.input_text).strip().casefold() for item in rows
            }
            split_id_counts.update(item.example_id for item in rows)
        unknown_split_ids = set(split_id_counts) - set(ids)
        corpus_by_id = {item.example_id: item for item in items}
        mismatched_split_rows = sum(
            item != corpus_by_id.get(item.example_id)
            for rows in splits.values() for item in rows
        )
        repeated_split_ids = sum(count - 1 for count in split_id_counts.values() if count > 1)
        names = ("train", "validation", "test")
        leakage = []
        for i, left in enumerate(names):
            for right in names[i + 1:]:
                overlap = split_prompt_groups[left] & split_prompt_groups[right]
                if overlap:
                    leakage.append({"left": left, "right": right, "overlap_count": len(overlap)})
        result["split_counts"] = split_counts
        result["prompt_group_leakage"] = leakage
        result["splits_prompt_disjoint"] = not leakage
        result["unknown_split_example_id_count"] = len(unknown_split_ids)
        result["repeated_split_example_id_count"] = repeated_split_ids
        result["mismatched_split_row_count"] = mismatched_split_rows
        result["split_membership_valid"] = (
            not unknown_split_ids and repeated_split_ids == 0 and mismatched_split_rows == 0
        )
    return result


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

def write_dataset(
    path: str | Path,
    examples: Iterable[MathExample],
    *,
    seed: int,
    topics: Iterable[str],
    resource_limits: DatasetResourceLimits | None = None,
) -> dict:
    """Stream a validated JSONL dataset and sidecar under explicit byte/row caps.

    The data file and sidecar are each fsynced and atomically replaced, but the
    pair is not a multi-file transaction. A mismatched pair always fails later
    verification. Rows and the encoded full dataset are never accumulated.
    """
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("dataset seed must be an integer")
    topics = tuple(topics)
    if (
        not topics
        or any(topic not in SUPPORTED_TOPICS for topic in topics)
        or len(set(topics)) != len(topics)
    ):
        raise ValueError("dataset topics must be a non-empty unique supported-topic sequence")
    resource_limits = resource_limits or DatasetResourceLimits()
    if not isinstance(resource_limits, DatasetResourceLimits):
        raise TypeError("resource_limits must be DatasetResourceLimits")

    target = Path(path)
    manifest_path = target.with_suffix(target.suffix + ".manifest.json")
    if target.resolve() == manifest_path.resolve():
        raise ValueError("dataset path and sidecar path must be distinct")
    target.parent.mkdir(parents=True, exist_ok=True)

    dataset_fd, dataset_temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    manifest_temp_name = None
    identifiers: set[str] = set()
    indexes: set[int] = set()
    topic_counts: Counter[str] = Counter()
    digest = hashlib.sha256()
    examples_seen = 0
    bytes_seen = 0
    try:
        with os.fdopen(dataset_fd, "wb") as stream:
            for item in examples:
                if examples_seen >= resource_limits.max_rows:
                    raise ValueError("dataset exceeds configured max_rows")
                if not isinstance(item, MathExample):
                    raise TypeError("dataset rows must be MathExample instances")
                if item.example_id in identifiers:
                    raise ValueError("dataset contains duplicate example IDs")
                if item.index in indexes:
                    raise ValueError("dataset contains duplicate example indices")
                if item.seed != seed or item.topic not in topics:
                    raise ValueError("example seed/topic does not match dataset manifest configuration")
                if item.validation_status != "semantically_checked" or not validate_example_text(
                    item.input_text, item.target_text, item.topic
                ) or item.exact_answer != item.target_text:
                    raise ValueError("dataset contains an example that failed exact semantic validation")

                row = item.to_dict()
                if not hmac.compare_digest(item.example_id, _example_identity_digest(row)):
                    raise ValueError("dataset example ID does not match its canonical content")
                row_bytes = (
                    json.dumps(
                        row,
                        sort_keys=True,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode("utf-8")
                    + b"\n"
                )
                if len(row_bytes) > resource_limits.max_line_bytes:
                    raise ValueError("dataset row exceeds configured max_line_bytes")
                if bytes_seen + len(row_bytes) > resource_limits.max_dataset_bytes:
                    raise ValueError("dataset exceeds configured max_dataset_bytes")
                if bytes_seen + len(row_bytes) > resource_limits.max_temporary_bytes:
                    raise ValueError("dataset temporary output exceeds configured max_temporary_bytes")

                stream.write(row_bytes)
                digest.update(row_bytes)
                bytes_seen += len(row_bytes)
                examples_seen += 1
                identifiers.add(item.example_id)
                indexes.add(item.index)
                topic_counts[item.topic] += 1

            if examples_seen == 0:
                raise ValueError("dataset must contain at least one MathExample")
            stream.flush()
            os.fsync(stream.fileno())

        manifest = {
            "schema_version": 1,
            "generator_version": GENERATOR_VERSION,
            "seed": seed,
            "topics": list(topics),
            "example_count": examples_seen,
            "topic_counts": dict(sorted(topic_counts.items())),
            "sha256": digest.hexdigest(),
        }
        manifest_bytes = (
            json.dumps(
                manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
        if len(manifest_bytes) > resource_limits.max_dataset_manifest_bytes:
            raise ValueError("dataset sidecar manifest exceeds configured max_dataset_manifest_bytes")
        if bytes_seen + len(manifest_bytes) > resource_limits.max_temporary_bytes:
            raise ValueError("dataset and sidecar temporary outputs exceed configured max_temporary_bytes")

        manifest_fd, manifest_temp_name = tempfile.mkstemp(
            prefix=f".{manifest_path.name}.", suffix=".tmp", dir=manifest_path.parent
        )
        with os.fdopen(manifest_fd, "wb") as stream:
            stream.write(manifest_bytes)
            stream.flush()
            os.fsync(stream.fileno())

        os.replace(dataset_temp_name, target)
        dataset_temp_name = None
        os.replace(manifest_temp_name, manifest_path)
        manifest_temp_name = None
        return manifest
    finally:
        if dataset_temp_name is not None and os.path.exists(dataset_temp_name):
            os.unlink(dataset_temp_name)
        if manifest_temp_name is not None and os.path.exists(manifest_temp_name):
            os.unlink(manifest_temp_name)


_MAX_DATASET_BYTES = 1024 * 1024 * 1024
_MAX_DATASET_ROWS = 100_000
_MAX_DATASET_LINE_BYTES = 8 * 1024 * 1024
_MAX_DATASET_MANIFEST_BYTES = 1024 * 1024


def _strict_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value):
    raise ValueError(f"non-standard JSON constant is not allowed: {value}")


def verify_dataset(
    path: str | Path,
    *,
    max_bytes: int = _MAX_DATASET_BYTES,
    max_rows: int = _MAX_DATASET_ROWS,
    max_line_bytes: int = _MAX_DATASET_LINE_BYTES,
    max_manifest_bytes: int = _MAX_DATASET_MANIFEST_BYTES,
) -> dict:
    """Verify a dataset incrementally with strict byte, row, and line bounds.

    Exact answer, row identity, duplicate-ID/index, topic-count, and SHA-256
    validation remain authoritative. The raw dataset and parsed rows are never
    retained as a full-file byte/string/list copy.
    """
    for name, value, maximum in (
        ("max_bytes", max_bytes, _MAX_DATASET_BYTES),
        ("max_rows", max_rows, _MAX_DATASET_ROWS),
        ("max_line_bytes", max_line_bytes, _MAX_DATASET_LINE_BYTES),
        ("max_manifest_bytes", max_manifest_bytes, _MAX_DATASET_MANIFEST_BYTES),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
        if not 1 <= value <= maximum:
            raise ValueError(f"{name} must be in [1, {maximum}]")

    target = Path(path)
    manifest_path = target.with_suffix(target.suffix + ".manifest.json")
    try:
        with manifest_path.open("rb") as manifest_stream:
            manifest_bytes = manifest_stream.read(max_manifest_bytes + 1)
    except OSError as exc:
        raise ValueError("dataset or manifest is missing or malformed") from exc
    if len(manifest_bytes) > max_manifest_bytes:
        raise ValueError(f"dataset manifest exceeds byte limit ({max_manifest_bytes} bytes)")
    try:
        manifest = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_strict_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError("dataset manifest is missing or malformed") from exc

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
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= max_rows:
        raise ValueError("dataset manifest example_count is invalid or exceeds row limit")
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

    try:
        before = target.stat()
    except OSError as exc:
        raise ValueError("dataset file is missing or inaccessible") from exc
    if not target.is_file():
        raise ValueError("dataset path is not a file")
    if before.st_size > max_bytes:
        raise ValueError(f"dataset exceeds byte limit ({max_bytes} bytes)")

    # Preserve integrity-error precedence without materializing the file: hash
    # a bounded first pass before semantic parsing. The second pass below also
    # hashes, so a concurrent rewrite between passes is detected.
    pre_digest = hashlib.sha256()
    pre_bytes = 0
    pre_rows = 0
    ends_with_newline = True
    try:
        with target.open("rb") as stream:
            while True:
                line = stream.readline(max_line_bytes + 1)
                if not line:
                    break
                pre_rows += 1
                if pre_rows > max_rows:
                    raise ValueError(f"dataset exceeds row limit ({max_rows})")
                if len(line) > max_line_bytes:
                    raise ValueError(f"dataset row {pre_rows} exceeds line byte limit")
                pre_bytes += len(line)
                if pre_bytes > max_bytes:
                    raise ValueError(f"dataset exceeds byte limit ({max_bytes} bytes)")
                pre_digest.update(line)
                ends_with_newline = line.endswith(b"\n")
    except OSError as exc:
        raise ValueError("dataset could not be read during integrity scan") from exc
    if pre_bytes != before.st_size:
        raise ValueError("dataset changed during integrity scan")
    if pre_digest.hexdigest() != digest_expected:
        raise ValueError("dataset SHA-256 mismatch")
    if not ends_with_newline:
        raise ValueError("dataset JSONL must end with a newline")

    digest = hashlib.sha256()
    counts = Counter()
    identifiers = set()
    indexes = set()
    required_row = {"example_id", "generator_version", "topic", "difficulty",
                    "input_text", "target_text", "exact_answer", "seed", "index",
                    "generation_parameters", "validation_status", "provenance"}
    rows_seen = 0
    bytes_seen = 0
    try:
        with target.open("rb") as stream:
            while True:
                line = stream.readline(max_line_bytes + 1)
                if not line:
                    break
                rows_seen += 1
                if rows_seen > max_rows:
                    raise ValueError(f"dataset exceeds row limit ({max_rows})")
                if len(line) > max_line_bytes:
                    raise ValueError(f"dataset row {rows_seen} exceeds line byte limit")
                bytes_seen += len(line)
                if bytes_seen > max_bytes:
                    raise ValueError(f"dataset exceeds byte limit ({max_bytes} bytes)")
                digest.update(line)
                if not line.endswith(b"\n"):
                    raise ValueError("dataset JSONL must end with a newline")
                encoded = line[:-1]
                if not encoded:
                    raise ValueError(f"dataset JSONL contains blank rows at line {rows_seen}")
                try:
                    row = json.loads(
                        encoded.decode("utf-8"),
                        object_pairs_hook=_strict_json_object,
                        parse_constant=_reject_json_constant,
                    )
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                    raise ValueError(f"dataset JSONL row {rows_seen} is malformed: {exc}") from exc

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
                expected_id = _example_identity_digest(row)
                if not hmac.compare_digest(row["example_id"], expected_id):
                    raise ValueError("dataset row example_id does not match its content")
                counts[row["topic"]] += 1
    except OSError as exc:
        raise ValueError("dataset could not be read during streaming verification") from exc

    try:
        after = target.stat()
    except OSError as exc:
        raise ValueError("dataset changed during verification") from exc
    if (bytes_seen != before.st_size or after.st_size != before.st_size
            or after.st_mtime_ns != before.st_mtime_ns):
        raise ValueError("dataset changed while being verified")
    if rows_seen != count:
        raise ValueError("dataset example count does not match manifest")
    if digest.hexdigest() != digest_expected:
        raise ValueError("dataset SHA-256 mismatch")
    if dict(sorted(counts.items())) != manifest["topic_counts"]:
        raise ValueError("dataset topic counts do not match manifest")
    return manifest
