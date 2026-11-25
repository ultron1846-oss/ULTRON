"""Paired, exact-answer comparison for Stage A math benchmarks.

This module compares caller-supplied predictions on the same validated examples.
It never invokes a model, generates a corpus, or performs training.
"""
from __future__ import annotations

import math
from typing import Mapping

from .data_generation import MathExample, validate_example_text
from .evaluation import evaluate_predictions


def exact_mcnemar_p_value(wins: int, losses: int) -> float:
    """Two-sided exact McNemar/binomial p-value for paired binary outcomes."""
    for name, value in (("wins", wins), ("losses", losses)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    discordant = wins + losses
    if discordant == 0:
        return 1.0

    tail = min(wins, losses)
    # Compute the binomial lower tail in log space. This avoids constructing
    # enormous integers or underflowing the first 2**(-n) term for large n.
    log_terms = [
        math.lgamma(discordant + 1)
        - math.lgamma(k + 1)
        - math.lgamma(discordant - k + 1)
        for k in range(tail + 1)
    ]
    maximum = max(log_terms)
    log_sum = maximum + math.log(math.fsum(math.exp(value - maximum) for value in log_terms))
    log_tail = log_sum - discordant * math.log(2.0)
    return min(1.0, 2.0 * math.exp(log_tail)) if log_tail > -745 else 0.0


def _holm_adjust(p_values: Mapping[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values, preserving topic keys."""
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    count = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (topic, p_value) in enumerate(ordered):
        candidate = min(1.0, (count - rank) * p_value)
        running = max(running, candidate)
        adjusted[topic] = running
    return adjusted


def compare_predictions(
    examples,
    ultron_predictions: Mapping[str, str | None],
    baseline_predictions: Mapping[str, str | None],
    *,
    baseline_name: str = "Fable 5.2",
    minimum_examples: int = 200,
    alpha: float = 0.05,
    maximum_coverage_drop: float = 0.02,
    maximum_validity_drop: float = 0.02,
) -> dict:
    """Compare two prediction maps on identical validated references.

    A topic passes only when ULTRON has higher exact accuracy, the paired
    exact McNemar test survives Holm correction, sample count meets the
    predeclared minimum, and coverage/valid-answer rate do not materially drop.
    Missing prediction IDs are treated as abstentions by the underlying scorer.
    """
    if not isinstance(baseline_name, str) or not baseline_name.strip():
        raise ValueError("baseline_name must be a non-empty string")
    if isinstance(minimum_examples, bool) or not isinstance(minimum_examples, int) or minimum_examples < 1:
        raise ValueError("minimum_examples must be a positive integer")
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be finite and between zero and one")
    for name, value in (
        ("maximum_coverage_drop", maximum_coverage_drop),
        ("maximum_validity_drop", maximum_validity_drop),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be finite and between zero and one")
    items = tuple(examples)
    if not items or any(not isinstance(item, MathExample) for item in items):
        raise ValueError("examples must contain at least one MathExample")
    ids = {item.example_id for item in items}
    for name, predictions in (("ULTRON", ultron_predictions), (baseline_name, baseline_predictions)):
        if not isinstance(predictions, Mapping):
            raise TypeError(f"{name} predictions must be a mapping")
        if set(predictions) - ids:
            raise ValueError(f"{name} predictions contain IDs outside the benchmark")

    ultron_report = evaluate_predictions(items, ultron_predictions)
    baseline_report = evaluate_predictions(items, baseline_predictions)
    topics = sorted({item.topic for item in items})
    topic_rows = {}
    raw_p = {}

    for topic in topics:
        topic_items = [item for item in items if item.topic == topic]
        ultron_correct = baseline_correct = wins = losses = ties = 0
        for item in topic_items:
            u = ultron_predictions.get(item.example_id)
            b = baseline_predictions.get(item.example_id)
            u_correct = u is not None and isinstance(u, str) and validate_example_text(item.input_text, u, topic)
            b_correct = b is not None and isinstance(b, str) and validate_example_text(item.input_text, b, topic)
            ultron_correct += int(u_correct)
            baseline_correct += int(b_correct)
            if u_correct and not b_correct:
                wins += 1
            elif b_correct and not u_correct:
                losses += 1
            else:
                ties += 1

        n = len(topic_items)
        u_metrics = ultron_report["per_topic"][topic]
        b_metrics = baseline_report["per_topic"][topic]
        p_value = exact_mcnemar_p_value(wins, losses)
        raw_p[topic] = p_value
        topic_rows[topic] = {
            "examples": n,
            "ultron_correct": ultron_correct,
            "baseline_correct": baseline_correct,
            "ultron_exact_accuracy": ultron_correct / n,
            "baseline_exact_accuracy": baseline_correct / n,
            "accuracy_difference": (ultron_correct - baseline_correct) / n,
            "ultron_coverage": u_metrics["coverage"],
            "baseline_coverage": b_metrics["coverage"],
            "coverage_difference": u_metrics["coverage"] - b_metrics["coverage"],
            "ultron_valid_answer_rate": u_metrics["valid_answer_rate"],
            "baseline_valid_answer_rate": b_metrics["valid_answer_rate"],
            "valid_answer_rate_difference": u_metrics["valid_answer_rate"] - b_metrics["valid_answer_rate"],
            "paired_ultron_wins": wins,
            "paired_baseline_wins": losses,
            "paired_ties": ties,
            "mcnemar_exact_p_value": p_value,
        }

    adjusted = _holm_adjust(raw_p)
    for topic, row in topic_rows.items():
        row["holm_adjusted_p_value"] = adjusted[topic]
        row["gate"] = {
            "enough_examples": row["examples"] >= minimum_examples,
            "higher_exact_accuracy": row["accuracy_difference"] > 0,
            "paired_significance": adjusted[topic] < alpha,
            "coverage_noninferior": row["coverage_difference"] >= -maximum_coverage_drop,
            "validity_noninferior": row["valid_answer_rate_difference"] >= -maximum_validity_drop,
        }
        row["passed"] = all(row["gate"].values())

    return {
        "schema_version": 1,
        "benchmark_kind": "paired_exact_math_comparison",
        "baseline_name": baseline_name,
        "minimum_examples_per_topic": minimum_examples,
        "alpha": alpha,
        "maximum_coverage_drop": maximum_coverage_drop,
        "maximum_validity_drop": maximum_validity_drop,
        "topic_count": len(topics),
        "total_examples": len(items),
        "all_topics_passed": all(row["passed"] for row in topic_rows.values()),
        "per_topic": topic_rows,
        "multiple_comparison_correction": "Holm step-down",
        "statistical_test": "two-sided exact McNemar/binomial on paired correctness",
        "prediction_scoring": {
            "ultron": ultron_report,
            "baseline": baseline_report,
        },
        "model_invoked": False,
        "training_performed": False,
        "data_generated": False,
        "external_ai_api_used": False,
        "limitations": [
            "The function compares supplied prediction files; it does not call ULTRON or the baseline model.",
            "A pass applies only to these frozen topic examples and scoring rules.",
            "The default 200 examples per topic is a minimum floor, not a substitute for prospective power analysis.",
            "This exact-answer gate does not validate derivations or formal proofs.",
        ],
    }
