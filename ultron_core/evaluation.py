"""Exact-answer evaluation for ULTRON's supported generated math tasks."""
from __future__ import annotations
from collections import Counter
from typing import Mapping, Iterable
from .data_generation import MathExample, _parse_integer_polynomial, validate_example_text

def evaluate_predictions(examples: Iterable[MathExample], predictions: Mapping[str, str | None]) -> dict:
    """Score exact rational and supported polynomial-derivative answers; no model is run."""
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
    total, answered, correct, invalid = len(items), 0, 0, 0
    totals, answers, rights = Counter(), Counter(), Counter()
    for item in items:
        if (item.validation_status != "semantically_checked" or item.target_text != item.exact_answer
                or not validate_example_text(item.input_text, item.exact_answer, item.topic)):
            raise ValueError("evaluation contains an unverified reference example")
        totals[item.topic] += 1
        raw = predictions.get(item.example_id)
        if raw is None:
            continue
        if not isinstance(raw, str):
            raise TypeError("prediction values must be strings or None")
        try:
            if item.topic == "polynomial_derivative":
                _parse_integer_polynomial(raw)
            else:
                from fractions import Fraction
                Fraction(raw.strip())
        except (ValueError, ZeroDivisionError, TypeError):
            invalid += 1
            continue
        answered += 1
        answers[item.topic] += 1
        if validate_example_text(item.input_text, raw, item.topic):
            correct += 1
            rights[item.topic] += 1
    per_topic = {}
    for topic, count in sorted(totals.items()):
        n_answered, n_correct = answers[topic], rights[topic]
        per_topic[topic] = {"total": count, "answered": n_answered, "correct": n_correct,
            "coverage": n_answered / count, "exact_accuracy_all": n_correct / count,
            "exact_accuracy_answered": n_correct / n_answered if n_answered else None}
    return {"schema_version": 1, "evaluation_kind": "exact_answer",
        "total_examples": total, "answered": answered, "abstentions": total - answered,
        "invalid_predictions": invalid, "correct": correct, "coverage": answered / total,
        "exact_accuracy_all": correct / total,
        "exact_accuracy_answered": correct / answered if answered else None,
        "per_topic": per_topic, "proof_verified": False, "model_evaluated": False,
        "training_performed": False, "external_data_used": False,
        "limitations": ["Predictions are caller-supplied; no model is run or trained.",
            "Only exact answers for currently independently validated generator topics are scored.",
            "Correct answers do not validate derivations or formal proofs.",
            "No calculus, university-level coverage, or formula discovery is measured."]}
