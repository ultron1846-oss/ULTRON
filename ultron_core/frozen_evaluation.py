"""Frozen, leakage-checked evaluation split manifests for ULTRON.

This module validates caller-supplied fixtures or curated examples. It does not
create a training corpus, mutate splits, run a model, or execute training.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Iterable

from .concepts import (
    CONCEPTS,
    CONCEPT_TRANSFER_CATEGORIES,
    concept_id_for_topic,
    validate_concept_transfer_split,
)
from .data_generation import MathExample, validate_example_text

_SPLITS = ("train", "validation", "evaluation")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _normalized_prompt(example: MathExample) -> str:
    return " ".join(example.input_text.split()).casefold()


def _concept_ids(example: MathExample) -> tuple[str, ...]:
    supplied = getattr(example, "concept_ids", None)
    if supplied is None:
        return (concept_id_for_topic(example.topic),)
    if not isinstance(supplied, (tuple, list, set)) or not supplied:
        raise ValueError("concept_ids must be a non-empty sequence when supplied")
    values = set(supplied)
    if any(not isinstance(value, str) or value not in CONCEPTS for value in values):
        raise ValueError("concept_ids contains an unknown concept")
    return tuple(sorted(values))


def _generation_ingredient_sha256(example: MathExample) -> str:
    """Hash generator inputs independently of the emitted prompt and answer."""
    parameters = example.generation_parameters
    if not isinstance(parameters, tuple):
        raise ValueError("generation_parameters must be an immutable tuple")
    if any(
        not isinstance(pair, tuple) or len(pair) != 2
        or not isinstance(pair[0], str)
        or not isinstance(pair[1], (int, str))
        or isinstance(pair[1], bool)
        for pair in parameters
    ):
        raise ValueError("generation_parameters contains malformed values")
    identity = {
        "generator_version": example.generator_version,
        "topic": example.topic,
        "difficulty": example.difficulty,
        "seed": example.seed,
        "index": example.index,
        "generation_parameters": sorted(parameters),
    }
    return _sha256(_canonical(identity))


def _validated_records(examples: Iterable[MathExample], split_name: str) -> tuple[tuple[MathExample, ...], list[dict]]:
    items = tuple(examples)
    if not items:
        raise ValueError(f"{split_name} split must be non-empty")
    records = []
    for item in items:
        if not isinstance(item, MathExample):
            raise TypeError(f"{split_name} split must contain MathExample records")
        if (
            item.validation_status != "semantically_checked"
            or item.target_text != item.exact_answer
            or not validate_example_text(item.input_text, item.exact_answer, item.topic)
        ):
            raise ValueError(f"{split_name} contains an independently invalid reference answer")
        prompt = _normalized_prompt(item)
        if not prompt:
            raise ValueError(f"{split_name} contains an empty normalized prompt")
        records.append({
            "example_id": item.example_id,
            "topic": item.topic,
            "generator_version": item.generator_version,
            "difficulty": item.difficulty,
            "seed": item.seed,
            "index": item.index,
            "generation_ingredient_sha256": _generation_ingredient_sha256(item),
            "normalized_prompt_sha256": _sha256(prompt.encode("utf-8")),
            "reference_answer_sha256": _sha256(item.exact_answer.encode("utf-8")),
            "concept_ids": list(_concept_ids(item)),
        })
    records.sort(key=lambda record: record["example_id"])
    return items, records


def build_frozen_evaluation_manifest(
    train_examples: Iterable[MathExample],
    validation_examples: Iterable[MathExample],
    evaluation_examples: Iterable[MathExample],
    *,
    evaluation_categories: Mapping[str, str],
    benchmark_revision: str,
) -> dict:
    """Build a deterministic manifest for train/validation/final-evaluation isolation.

    The final evaluation split is checked against the union of train and
    validation examples for concept-transfer claims. Prompt hashes, generation
    ingredients, reference-answer hashes, concept IDs, and the concept registry
    are fingerprinted; raw prompts and answers are not copied into the manifest.
    """
    if not isinstance(benchmark_revision, str) or not benchmark_revision.strip():
        raise ValueError("benchmark_revision must be a non-empty immutable identifier")
    if not isinstance(evaluation_categories, Mapping):
        raise TypeError("evaluation_categories must map evaluation IDs to categories")

    examples_by_split = {}
    records_by_split = {}
    for split_name, values in (
        ("train", train_examples),
        ("validation", validation_examples),
        ("evaluation", evaluation_examples),
    ):
        examples_by_split[split_name], records_by_split[split_name] = _validated_records(
            values, split_name
        )

    all_ids = []
    prompt_owners = {}
    ingredient_owners = {}
    for split_name in _SPLITS:
        for record in records_by_split[split_name]:
            example_id = record["example_id"]
            all_ids.append(example_id)
            prompt_hash = record["normalized_prompt_sha256"]
            ingredient_hash = record["generation_ingredient_sha256"]
            previous_prompt = prompt_owners.get(prompt_hash)
            if previous_prompt is not None:
                raise ValueError(
                    f"normalized prompt leakage between {previous_prompt} and {split_name}"
                )
            prompt_owners[prompt_hash] = split_name
            previous_ingredient = ingredient_owners.get(ingredient_hash)
            if previous_ingredient is not None:
                raise ValueError(
                    f"generation ingredient leakage between {previous_ingredient} and {split_name}"
                )
            ingredient_owners[ingredient_hash] = split_name

    if len(all_ids) != len(set(all_ids)):
        raise ValueError("train/validation/evaluation example IDs overlap")

    evaluation_ids = {
        item.example_id for item in examples_by_split["evaluation"]
    }
    if set(evaluation_categories) != evaluation_ids:
        raise ValueError("every evaluation example must have exactly one transfer category")
    if any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in evaluation_categories.items()
    ):
        raise TypeError("evaluation category keys and values must be strings")
    if any(value not in CONCEPT_TRANSFER_CATEGORIES for value in evaluation_categories.values()):
        raise ValueError("evaluation_categories contains an unsupported transfer category")

    # Validation concepts count as previously seen: "unseen concept" must be
    # absent from both train and validation, not merely absent from train.
    transfer_report = validate_concept_transfer_split(
        examples_by_split["train"] + examples_by_split["validation"],
        examples_by_split["evaluation"],
        test_categories=evaluation_categories,
    )

    concept_registry_payload = [
        {
            "concept_id": concept.concept_id,
            "title": concept.title,
            "principle": concept.principle,
            "prerequisites": list(concept.prerequisites),
            "assumptions": list(concept.assumptions),
            "misconceptions": list(concept.misconceptions),
        }
        for _, concept in sorted(CONCEPTS.items())
    ]
    registry_digest = _sha256(_canonical(concept_registry_payload))
    manifest = {
        "schema_version": 1,
        "protocol": "ultron_frozen_evaluation_v1",
        "benchmark_revision": benchmark_revision,
        "splits": records_by_split,
        "evaluation_categories": dict(sorted(evaluation_categories.items())),
        "concept_registry_sha256": registry_digest,
        "transfer_report": transfer_report,
        "split_counts": {
            name: len(records_by_split[name]) for name in _SPLITS
        },
        "generator_versions": sorted({
            record["generator_version"]
            for records in records_by_split.values()
            for record in records
        }),
        "training_performed": False,
        "corpus_written": False,
        "model_evaluated": False,
        "limitations": [
            "Prompt and generation-ingredient fingerprints enforce exact protocol leakage checks, not semantic paraphrase detection.",
            "Human/independent review of mathematical near-duplicates and category labels remains required.",
            "A frozen manifest fingerprints supplied references; it does not itself prove verifier independence or model capability.",
        ],
    }
    return {**manifest, "manifest_sha256": _sha256(_canonical(manifest))}


def verify_frozen_evaluation_manifest(
    manifest: Mapping,
    train_examples: Iterable[MathExample],
    validation_examples: Iterable[MathExample],
    evaluation_examples: Iterable[MathExample],
    *,
    evaluation_categories: Mapping[str, str],
    benchmark_revision: str,
) -> dict:
    """Rebuild and compare a frozen manifest without running a model."""
    if not isinstance(manifest, Mapping):
        raise TypeError("manifest must be a mapping")
    rebuilt = build_frozen_evaluation_manifest(
        train_examples,
        validation_examples,
        evaluation_examples,
        evaluation_categories=evaluation_categories,
        benchmark_revision=benchmark_revision,
    )
    if dict(manifest) != rebuilt:
        raise ValueError("frozen evaluation manifest does not match supplied examples or protocol")
    digest = manifest.get("manifest_sha256")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise ValueError("frozen evaluation manifest digest is malformed")
    return {
        "valid": True,
        "manifest_sha256": digest,
        "split_counts": dict(rebuilt["split_counts"]),
        "training_performed": False,
        "model_evaluated": False,
    }
