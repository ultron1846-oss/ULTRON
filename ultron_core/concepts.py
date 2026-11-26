"""Concept taxonomy and leakage-aware concept sampling for ULTRON's core tasks.

The registry is metadata only: it does not generate examples or run training.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import random
import re
from typing import Iterable, Mapping

from .data_generation import SUPPORTED_TOPICS


@dataclass(frozen=True)
class MathConcept:
    concept_id: str
    title: str
    principle: str
    prerequisites: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    misconceptions: tuple[str, ...] = ()


CONCEPTS: dict[str, MathConcept] = {
    "concept.integer_operations": MathConcept(
        "concept.integer_operations", "Integer operations",
        "Use exact addition, subtraction, multiplication, and defined division.",
        assumptions=("Operands are integers.", "Division by zero is excluded."),
        misconceptions=("Integer division is not always closed over integers.",),
    ),
    "concept.rational_operations": MathConcept(
        "concept.rational_operations", "Rational arithmetic",
        "Represent fractions exactly and preserve equality under rational operations.",
        prerequisites=("concept.integer_operations",),
        assumptions=("Denominators are nonzero.",),
        misconceptions=("A fraction is not changed by multiplying numerator and denominator by the same nonzero value.",),
    ),
    "concept.linear_equation_balance": MathConcept(
        "concept.linear_equation_balance", "Linear equation balance",
        "Apply the same valid operation to both sides of an equality to isolate the variable.",
        prerequisites=("concept.integer_operations", "concept.rational_operations"),
        assumptions=("The coefficient of the variable is nonzero for a unique solution.",),
        misconceptions=("Dividing by a zero coefficient is invalid.",),
    ),
    "concept.polynomial_term_operations": MathConcept(
        "concept.polynomial_term_operations", "Polynomial term operations",
        "Combine like powers and preserve each coefficient and exponent.",
        prerequisites=("concept.integer_operations", "concept.rational_operations"),
        assumptions=("Expressions are finite polynomials.",),
        misconceptions=("Unlike powers cannot be combined by adding coefficients alone.",),
    ),
    "concept.polynomial_derivative_power_rule": MathConcept(
        "concept.polynomial_derivative_power_rule", "Polynomial derivative power rule",
        "Differentiate termwise using d(x^n)/dx = n*x^(n-1).",
        prerequisites=("concept.polynomial_term_operations",),
        assumptions=("The inputs are polynomials over the supported coefficient domain.",),
        misconceptions=("The exponent decreases by one; it is not the new coefficient.",),
    ),
    "concept.polynomial_antiderivative_power_rule": MathConcept(
        "concept.polynomial_antiderivative_power_rule", "Polynomial antiderivative power rule",
        "Integrate termwise using integral x^n dx = x^(n+1)/(n+1).",
        prerequisites=("concept.polynomial_term_operations", "concept.rational_operations"),
        assumptions=("For the power rule, n is not -1.",),
        misconceptions=("Integration increases the exponent and divides by the new exponent.",),
    ),
    "concept.definite_integral_polynomial": MathConcept(
        "concept.definite_integral_polynomial", "Definite polynomial integral",
        "Evaluate an antiderivative at the upper endpoint and subtract its lower-endpoint value.",
        prerequisites=("concept.polynomial_antiderivative_power_rule", "concept.rational_operations"),
        assumptions=("The polynomial is continuous on the interval.",),
        misconceptions=("Endpoint order matters: F(b)-F(a), not F(a)-F(b).",),
    ),
    "concept.determinant_2x2": MathConcept(
        "concept.determinant_2x2", "Two-by-two determinant",
        "For [[a,b],[c,d]], compute ad-bc; a zero determinant signals singularity.",
        prerequisites=("concept.integer_operations",),
        assumptions=("Matrix entries belong to the supported exact number domain.",),
        misconceptions=("The determinant is not the product of all four entries.",),
    ),
    "concept.linear_system_2x2": MathConcept(
        "concept.linear_system_2x2", "Two-by-two linear system",
        "Find a pair that satisfies both equations; a nonzero coefficient determinant gives a unique solution.",
        prerequisites=("concept.linear_equation_balance", "concept.rational_operations"),
        assumptions=("The system is consistent; uniqueness requires nonzero determinant.",),
        misconceptions=("Solving one equation alone does not guarantee satisfying the second.",),
    ),
    "concept.matrix_inverse_2x2": MathConcept(
        "concept.matrix_inverse_2x2", "Two-by-two matrix inverse",
        "Use the adjugate divided by the determinant; an inverse exists only when the determinant is nonzero.",
        prerequisites=("concept.determinant_2x2", "concept.rational_operations"),
        assumptions=("The matrix is nonsingular.",),
        misconceptions=("A singular matrix has no inverse.",),
    ),
}

TOPIC_TO_CONCEPT: dict[str, str] = {
    "arithmetic": "concept.integer_operations",
    "rational_arithmetic": "concept.rational_operations",
    "linear_equations": "concept.linear_equation_balance",
    "polynomial_derivative": "concept.polynomial_derivative_power_rule",
    "polynomial_definite_integral": "concept.definite_integral_polynomial",
    "matrix_determinant_2x2": "concept.determinant_2x2",
    "linear_system_2x2": "concept.linear_system_2x2",
    "matrix_inverse_2x2": "concept.matrix_inverse_2x2",
}

CONCEPT_TRANSFER_CATEGORIES = (
    "unseen_surface_form",
    "unseen_numeric_values",
    "multi_concept_composition",
    "prerequisite_sensitive",
    "unseen_concept",
)


def validate_concept_registry() -> bool:
    """Fail closed on missing topic mappings, dangling edges, or cycles."""
    if set(TOPIC_TO_CONCEPT) != set(SUPPORTED_TOPICS):
        raise ValueError("every supported generator topic must map to exactly one concept")
    if any(concept_id not in CONCEPTS for concept_id in TOPIC_TO_CONCEPT.values()):
        raise ValueError("topic mapping references an unknown concept")
    for key, concept in CONCEPTS.items():
        if key != concept.concept_id:
            raise ValueError("concept registry key does not match concept_id")
        if any(parent not in CONCEPTS for parent in concept.prerequisites):
            raise ValueError(f"{key} references an unknown prerequisite")
        if len(set(concept.prerequisites)) != len(concept.prerequisites):
            raise ValueError(f"{key} has duplicate prerequisites")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(concept_id: str) -> None:
        if concept_id in visiting:
            raise ValueError("concept prerequisite graph contains a cycle")
        if concept_id in visited:
            return
        visiting.add(concept_id)
        for parent in CONCEPTS[concept_id].prerequisites:
            visit(parent)
        visiting.remove(concept_id)
        visited.add(concept_id)

    for concept_id in CONCEPTS:
        visit(concept_id)
    return True


def concept_id_for_topic(topic: str) -> str:
    try:
        return TOPIC_TO_CONCEPT[topic]
    except KeyError as exc:
        raise ValueError(f"unsupported concept topic: {topic!r}") from exc


def _example_id(example) -> str:
    value = getattr(example, "example_id", None)
    if not isinstance(value, str) or not value:
        raise ValueError("each example must have a non-empty example_id")
    return value


def _example_topic(example) -> str:
    topic = getattr(example, "topic", None)
    if not isinstance(topic, str) or topic not in TOPIC_TO_CONCEPT:
        raise ValueError("each example must have a supported topic")
    return topic


def sample_concept_balanced(
    examples: Iterable,
    *,
    max_per_concept: int,
    seed: int = 0,
) -> tuple:
    """Deterministically cap examples per concept; never create new examples."""
    if isinstance(max_per_concept, bool) or not isinstance(max_per_concept, int) or max_per_concept < 1:
        raise ValueError("max_per_concept must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    items = tuple(examples)
    if not items:
        raise ValueError("examples must be non-empty")
    ids = [_example_id(item) for item in items]
    if len(set(ids)) != len(ids):
        raise ValueError("examples contain duplicate IDs")

    groups: dict[str, list] = {}
    for item in items:
        concept_id = concept_id_for_topic(_example_topic(item))
        groups.setdefault(concept_id, []).append(item)

    rng = random.Random(seed)
    selected = []
    for concept_id in sorted(groups):
        group = sorted(groups[concept_id], key=_example_id)
        if len(group) > max_per_concept:
            group = rng.sample(group, max_per_concept)
        selected.extend(sorted(group, key=_example_id))
    return tuple(selected)


def concept_coverage_report(examples: Iterable) -> dict:
    """Summarize supplied examples by concept without generating or sampling."""
    items = tuple(examples)
    counts = Counter(concept_id_for_topic(_example_topic(item)) for item in items)
    return {
        "schema_version": 1,
        "example_count": len(items),
        "concept_counts": dict(sorted(counts.items())),
        "concept_count_present": len(counts),
        "concept_count_registry": len(CONCEPTS),
        "missing_concepts": sorted(set(CONCEPTS) - set(counts)),
        "data_generated": False,
        "training_performed": False,
    }


def _concept_ids(example) -> set[str]:
    explicit = getattr(example, "concept_ids", None)
    if explicit is None:
        return {concept_id_for_topic(_example_topic(example))}
    if not isinstance(explicit, (tuple, list, set)) or not explicit:
        raise ValueError("concept_ids must be a non-empty sequence when supplied")
    values = set(explicit)
    if any(not isinstance(value, str) or value not in CONCEPTS for value in values):
        raise ValueError("concept_ids contains an unknown concept")
    return values


def _prompt(example) -> str:
    value = getattr(example, "input_text", getattr(example, "prompt", None))
    if not isinstance(value, str) or not value.strip():
        raise ValueError("each transfer example must have non-empty prompt text")
    return " ".join(value.split()).casefold()


_NUMBER_PATTERN = re.compile(r"(?<![A-Za-z_])[-+]?\d+(?:/\d+)?(?:\.\d+)?(?![A-Za-z_])")


def validate_concept_transfer_split(
    train_examples: Iterable,
    test_examples: Iterable,
    *,
    test_categories: Mapping[str, str],
) -> dict:
    """Validate prompt/ID isolation and category-specific concept-transfer claims.

    Category labels are curation metadata; numeric/prerequisite/composition
    checks below verify the concrete properties that can be checked locally.
    """
    train, test = tuple(train_examples), tuple(test_examples)
    if not train or not test:
        raise ValueError("train and test examples must both be non-empty")
    if not isinstance(test_categories, Mapping):
        raise TypeError("test_categories must map test example IDs to transfer categories")

    train_ids = [_example_id(item) for item in train]
    test_ids = [_example_id(item) for item in test]
    if len(set(train_ids)) != len(train_ids) or len(set(test_ids)) != len(test_ids):
        raise ValueError("train/test examples contain duplicate IDs")
    if set(train_ids) & set(test_ids):
        raise ValueError("train and test example IDs overlap")
    if set(test_categories) != set(test_ids):
        raise ValueError("every test example must have exactly one transfer category")

    train_prompts = {_prompt(item) for item in train}
    test_prompts = {_prompt(item) for item in test}
    if train_prompts & test_prompts:
        raise ValueError("train/test normalized prompts overlap")

    train_concepts = set().union(*(_concept_ids(item) for item in train))
    train_numbers = set().union(*(
        set(_NUMBER_PATTERN.findall(_prompt(item))) for item in train
    ))
    category_counts = Counter()
    test_concepts = set()
    for item in test:
        example_id = _example_id(item)
        category = test_categories[example_id]
        if category not in CONCEPT_TRANSFER_CATEGORIES:
            raise ValueError(f"unsupported transfer category: {category!r}")
        concepts = _concept_ids(item)
        test_concepts.update(concepts)
        category_counts[category] += 1
        if category == "unseen_concept" and concepts & train_concepts:
            raise ValueError("unseen_concept example uses a concept present in training")
        if category == "unseen_numeric_values":
            values = set(_NUMBER_PATTERN.findall(_prompt(item)))
            if not values or values & train_numbers:
                raise ValueError("unseen_numeric_values example reuses a training numeric value")
        if category == "multi_concept_composition" and len(concepts) < 2:
            raise ValueError("multi_concept_composition example must contain at least two concepts")
        if category == "prerequisite_sensitive" and not any(
            CONCEPTS[concept_id].prerequisites for concept_id in concepts
        ):
            raise ValueError("prerequisite_sensitive example must reference a concept with prerequisites")

    return {
        "schema_version": 1,
        "protocol": "ultron_concept_transfer_v1",
        "train_example_count": len(train),
        "test_example_count": len(test),
        "train_concept_count": len(train_concepts),
        "test_concept_count": len(test_concepts),
        "test_category_counts": dict(sorted(category_counts.items())),
        "normalized_prompt_overlap_count": 0,
        "example_id_overlap_count": 0,
        "split_valid": True,
        "training_performed": False,
        "data_generated": False,
        "limitations": [
            "Surface-form novelty is enforced by exact normalized-prompt disjointness; semantic near-duplicate review remains a curation responsibility.",
            "Transfer category labels must be recorded by curators and are not inferred by a command tool.",
            "The protocol validates split properties; it does not establish model capability or run evaluation.",
        ],
    }


validate_concept_registry()
