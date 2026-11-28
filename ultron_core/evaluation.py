"""Reproducible evaluation primitives for ULTRON's supported math tasks."""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from typing import Iterable, Mapping

from .data_generation import (
    MathExample,
    SUPPORTED_TOPICS,
    _parse_integer_polynomial,
    _parse_linear_system_answer,
    _parse_matrix_inverse_answer,
    generate_examples,
    validate_example_text,
)

_NUMERIC_SCALAR_TOPICS = frozenset({
    "arithmetic",
    "rational_arithmetic",
    "linear_equations",
    "polynomial_definite_integral",
    "matrix_determinant_2x2",
})


def _validate_tolerance(name: str, value: float) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite non-negative number")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return Fraction(str(value))


def _valid_numeric_tolerance(
    prediction: str,
    expected: str,
    absolute_tolerance: Fraction,
    relative_tolerance: Fraction,
) -> bool:
    try:
        actual_value = Fraction(prediction.strip())
        expected_value = Fraction(expected.strip())
    except (ValueError, ZeroDivisionError, TypeError):
        return False
    allowed = max(
        absolute_tolerance,
        relative_tolerance * abs(expected_value),
    )
    return abs(actual_value - expected_value) <= allowed


def build_deterministic_math_task_suite(
    *,
    seed: int,
    examples_per_topic: int = 8,
    topics: Iterable[str] | None = None,
) -> dict:
    """Build a bounded, deterministic evaluation-only suite from existing generators.

    The function returns in-memory examples and a reproducible manifest. It
    writes no corpus, does not add rows to a training split, and does not run a
    model. The default suite covers every currently supported exact generator
    topic; callers may request a documented subset for focused regression runs.
    """
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
        raise ValueError("seed must be an integer in [0, 2**63)")
    if (
        isinstance(examples_per_topic, bool)
        or not isinstance(examples_per_topic, int)
        or not 1 <= examples_per_topic <= 100
    ):
        raise ValueError("examples_per_topic must be in [1, 100]")
    selected_topics = tuple(sorted(SUPPORTED_TOPICS if topics is None else topics))
    if not selected_topics or len(selected_topics) != len(set(selected_topics)):
        raise ValueError("topics must be a non-empty sequence of unique supported topics")
    if any(not isinstance(topic, str) or topic not in SUPPORTED_TOPICS for topic in selected_topics):
        raise ValueError("topics contains an unsupported generator topic")

    examples = tuple(
        item
        for topic in selected_topics
        for item in generate_examples(seed, examples_per_topic, topics=(topic,))
    )
    if len({item.example_id for item in examples}) != len(examples):
        raise ValueError("deterministic task suite contains duplicate example IDs")
    if any(
        item.validation_status != "semantically_checked"
        or item.target_text != item.exact_answer
        or not validate_example_text(item.input_text, item.exact_answer, item.topic)
        for item in examples
    ):
        raise ValueError("deterministic task suite contains an invalid reference answer")

    ids = sorted(item.example_id for item in examples)
    id_payload = {
        "schema_version": 1,
        "suite_id": "ultron_core_math_v1",
        "seed": seed,
        "examples_per_topic": examples_per_topic,
        "topics": list(selected_topics),
        "example_ids": ids,
        "topic_counts": {topic: examples_per_topic for topic in selected_topics},
        "generator_versions": sorted({item.generator_version for item in examples}),
    }
    digest = hashlib.sha256(
        json.dumps(id_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "examples": examples,
        "manifest": {
            **id_payload,
            "manifest_sha256": digest,
            "evaluation_only": True,
            "training_performed": False,
            "corpus_written": False,
            "independent_reference_validation": True,
        },
    }


def evaluate_predictions(
    examples: Iterable[MathExample],
    predictions: Mapping[str, str | None],
    *,
    absolute_tolerance: float = 0.0,
    relative_tolerance: float = 0.0,
) -> dict:
    """Score exact answers and opt-in scalar numeric tolerance; no model is run.

    Exact matching remains the default. A positive tolerance applies only to
    supported scalar numeric topics and is reported separately from exact
    correctness. The evaluator scores final answers, not derivations/reasoning.
    """
    absolute = _validate_tolerance("absolute_tolerance", absolute_tolerance)
    relative = _validate_tolerance("relative_tolerance", relative_tolerance)
    if not isinstance(predictions, Mapping):
        raise TypeError("predictions must map example IDs to strings or None")
    items = tuple(examples)
    if not items or any(not isinstance(item, MathExample) for item in items):
        raise ValueError("examples must contain at least one MathExample")
    ids = [item.example_id for item in items]
    if len(set(ids)) != len(ids):
        raise ValueError("evaluation examples contain duplicate IDs")
    if set(predictions) - set(ids):
        raise ValueError("predictions contain IDs not present in evaluation examples")

    total = len(items)
    attempted = answered = exact_correct = tolerance_correct = invalid = 0
    totals, attempts, answers, exact_right, accepted_right, invalid_by_topic = (
        Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
    )
    error_classes = Counter()
    detailed_classes = Counter()
    topic_error_classes = {}
    topic_detailed_classes = {}
    for item in items:
        if (
            item.validation_status != "semantically_checked"
            or item.target_text != item.exact_answer
            or not validate_example_text(item.input_text, item.exact_answer, item.topic)
        ):
            raise ValueError("evaluation contains an unverified reference example")
        totals[item.topic] += 1
        topic_errors = topic_error_classes.setdefault(item.topic, Counter())
        topic_detailed = topic_detailed_classes.setdefault(item.topic, Counter())
        raw = predictions.get(item.example_id)
        if raw is None:
            error_classes["abstention"] += 1
            detailed_classes["abstention"] += 1
            topic_errors["abstention"] += 1
            topic_detailed["abstention"] += 1
            continue

        attempted += 1
        attempts[item.topic] += 1
        if not isinstance(raw, str):
            invalid += 1
            invalid_by_topic[item.topic] += 1
            error_classes["malformed_output"] += 1
            detailed_classes["malformed_output"] += 1
            topic_errors["malformed_output"] += 1
            topic_detailed["malformed_output"] += 1
            continue

        try:
            if item.topic == "polynomial_derivative":
                _parse_integer_polynomial(raw)
            elif item.topic == "linear_system_2x2":
                _parse_linear_system_answer(raw)
            elif item.topic == "matrix_inverse_2x2":
                _parse_matrix_inverse_answer(raw)
            else:
                Fraction(raw.strip())
        except ZeroDivisionError:
            invalid += 1
            invalid_by_topic[item.topic] += 1
            error_classes["malformed_output"] += 1
            detailed_classes["domain_invalid_output"] += 1
            topic_errors["malformed_output"] += 1
            topic_detailed["domain_invalid_output"] += 1
            continue
        except (ValueError, TypeError, OverflowError):
            invalid += 1
            invalid_by_topic[item.topic] += 1
            error_classes["malformed_output"] += 1
            detailed_classes["malformed_output"] += 1
            topic_errors["malformed_output"] += 1
            topic_detailed["malformed_output"] += 1
            continue

        answered += 1
        answers[item.topic] += 1
        exact_match = validate_example_text(item.input_text, raw, item.topic)
        within_tolerance = (
            not exact_match
            and item.topic in _NUMERIC_SCALAR_TOPICS
            and (absolute > 0 or relative > 0)
            and _valid_numeric_tolerance(raw, item.exact_answer, absolute, relative)
        )
        if exact_match:
            exact_correct += 1
            exact_right[item.topic] += 1
            accepted_right[item.topic] += 1
            error_classes["correct_answer"] += 1
            detailed_classes["exact_correct_answer"] += 1
            topic_errors["correct_answer"] += 1
            topic_detailed["exact_correct_answer"] += 1
        elif within_tolerance:
            tolerance_correct += 1
            accepted_right[item.topic] += 1
            error_classes["within_numeric_tolerance"] += 1
            detailed_classes["within_numeric_tolerance"] += 1
            topic_errors["within_numeric_tolerance"] += 1
            topic_detailed["within_numeric_tolerance"] += 1
        else:
            error_classes["incorrect_answer"] += 1
            detailed_classes["mathematically_incorrect_answer"] += 1
            topic_errors["incorrect_answer"] += 1
            topic_detailed["mathematically_incorrect_answer"] += 1

    accepted_correct = exact_correct + tolerance_correct
    per_topic = {}
    for topic, count in sorted(totals.items()):
        n_attempted = attempts[topic]
        n_answered = answers[topic]
        n_exact = exact_right[topic]
        n_accepted = accepted_right[topic]
        per_topic[topic] = {
            "total": count,
            "attempted": n_attempted,
            "answered": n_answered,
            "abstentions": count - n_attempted,
            "invalid_predictions": invalid_by_topic[topic],
            "incorrect_valid_predictions": n_answered - n_accepted,
            "exact_correct": n_exact,
            "within_numeric_tolerance": topic_error_classes[topic]["within_numeric_tolerance"],
            "coverage": n_attempted / count,
            "valid_answer_rate": n_answered / count,
            "exact_accuracy_all": n_exact / count,
            "accepted_accuracy_all": n_accepted / count,
            "exact_accuracy_answered": n_exact / n_answered if n_answered else None,
            "accepted_accuracy_answered": n_accepted / n_answered if n_answered else None,
            "error_class_counts": dict(sorted(topic_error_classes[topic].items())),
            "detailed_error_class_counts": dict(sorted(topic_detailed_classes[topic].items())),
        }
    return {
        "schema_version": 4,
        "evaluation_kind": "exact_answer_with_opt_in_numeric_tolerance",
        "total_examples": total,
        "attempted": attempted,
        "answered": answered,
        "abstentions": total - attempted,
        "invalid_predictions": invalid,
        "incorrect_valid_predictions": answered - accepted_correct,
        "exact_correct": exact_correct,
        "within_numeric_tolerance": tolerance_correct,
        "correct": accepted_correct,
        "coverage": attempted / total,
        "valid_answer_rate": answered / total,
        "exact_accuracy_all": exact_correct / total,
        "accepted_accuracy_all": accepted_correct / total,
        "exact_accuracy_answered": exact_correct / answered if answered else None,
        "accepted_accuracy_answered": accepted_correct / answered if answered else None,
        "absolute_tolerance": float(absolute),
        "relative_tolerance": float(relative),
        "per_topic": per_topic,
        "error_class_counts": dict(sorted(error_classes.items())),
        "detailed_error_class_counts": dict(sorted(detailed_classes.items())),
        "reasoning_trace_scored": False,
        "proof_verified": False,
        "model_evaluated": False,
        "training_performed": False,
        "external_data_used": False,
        "limitations": [
            "Predictions are caller-supplied; no model is run or trained.",
            "Only exact answers for currently independently validated generator topics are scored.",
            "Numeric tolerances are opt-in and apply only to documented scalar numeric topics; exact correctness is reported separately.",
            "Answer validity does not evaluate intermediate derivations, explanation quality, or reasoning traces.",
            "Correct answers do not validate formal proofs.",
            "No broad calculus, university-level coverage, or formula discovery is measured.",
        ],
    }
