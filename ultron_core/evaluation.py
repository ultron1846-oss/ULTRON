"""Exact-answer evaluation for ULTRON's supported generated math tasks."""
from __future__ import annotations
from collections import Counter
from typing import Mapping, Iterable
from .data_generation import MathExample, _parse_integer_polynomial, validate_example_text

def evaluate_predictions(examples: Iterable[MathExample], predictions: Mapping[str, str | None]) -> dict:
    """Score exact rational and supported polynomial answers; no model is run."""
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

    total, attempted, answered, correct, invalid = len(items), 0, 0, 0, 0
    totals, attempts, answers, rights, invalid_by_topic = (
        Counter(), Counter(), Counter(), Counter(), Counter()
    )
    error_classes = Counter()
    topic_error_classes = {}
    for item in items:
        if (item.validation_status != "semantically_checked" or item.target_text != item.exact_answer
                or not validate_example_text(item.input_text, item.exact_answer, item.topic)):
            raise ValueError("evaluation contains an unverified reference example")
        totals[item.topic] += 1
        topic_errors = topic_error_classes.setdefault(item.topic, Counter())
        raw = predictions.get(item.example_id)
        if raw is None:
            error_classes["abstention"] += 1
            topic_errors["abstention"] += 1
            continue
        attempted += 1
        attempts[item.topic] += 1
        if not isinstance(raw, str):
            invalid += 1
            invalid_by_topic[item.topic] += 1
            error_classes["malformed_output"] += 1
            topic_errors["malformed_output"] += 1
            continue
        try:
            if item.topic == "polynomial_derivative":
                _parse_integer_polynomial(raw)
            else:
                from fractions import Fraction
                Fraction(raw.strip())
        except (ValueError, ZeroDivisionError, TypeError):
            invalid += 1
            invalid_by_topic[item.topic] += 1
            continue
        answered += 1
        answers[item.topic] += 1
        if validate_example_text(item.input_text, raw, item.topic):
            correct += 1
            rights[item.topic] += 1
            error_classes["correct_answer"] += 1
            topic_errors["correct_answer"] += 1
        else:
            error_classes["incorrect_answer"] += 1
            topic_errors["incorrect_answer"] += 1

    per_topic = {}
    for topic, count in sorted(totals.items()):
        n_attempted = attempts[topic]
        n_answered, n_correct = answers[topic], rights[topic]
        per_topic[topic] = {
            "total": count,
            "attempted": n_attempted,
            "answered": n_answered,
            "abstentions": count - n_attempted,
            "invalid_predictions": invalid_by_topic[topic],
            "incorrect_valid_predictions": n_answered - n_correct,
            "coverage": n_attempted / count,
            "valid_answer_rate": n_answered / count,
            "exact_accuracy_all": n_correct / count,
            "exact_accuracy_answered": n_correct / n_answered if n_answered else None,
            "error_class_counts": dict(sorted(topic_error_classes[topic].items())),
        }
    return {
        "schema_version": 3,
        "evaluation_kind": "exact_answer",
        "total_examples": total,
        "attempted": attempted,
        "answered": answered,
        "abstentions": total - attempted,
        "invalid_predictions": invalid,
        "incorrect_valid_predictions": answered - correct,
        "correct": correct,
        "coverage": attempted / total,
        "valid_answer_rate": answered / total,
        "exact_accuracy_all": correct / total,
        "exact_accuracy_answered": correct / answered if answered else None,
        "per_topic": per_topic,
        "error_class_counts": dict(sorted(error_classes.items())),
        "proof_verified": False,
        "model_evaluated": False,
        "training_performed": False,
        "external_data_used": False,
        "limitations": [
            "Predictions are caller-supplied; no model is run or trained.",
            "Only exact answers for currently independently validated generator topics are scored.",
            "Correct answers do not validate derivations or formal proofs.",
            "No broad calculus, university-level coverage, or formula discovery is measured.",
        ],
    }
