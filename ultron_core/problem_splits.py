"""Disjoint seed allocation and benchmark-overlap guards."""
from __future__ import annotations
from typing import Iterable
from ultron_core.problem import Problem

TRAIN_SEED_RANGE = (0, 1_000_000)       # inclusive start, exclusive end
BENCHMARK_SEED_RANGE = (1_000_000, 2_000_000)


def seed_in_range(seed: int, seed_range: tuple[int, int]) -> bool:
    return isinstance(seed, int) and not isinstance(seed, bool) and seed_range[0] <= seed < seed_range[1]


def seed_split(seed: int) -> str:
    if seed_in_range(seed, TRAIN_SEED_RANGE):
        return "train"
    if seed_in_range(seed, BENCHMARK_SEED_RANGE):
        return "benchmark"
    raise ValueError("seed is outside reserved train/benchmark ranges")


def filter_benchmark_overlaps(training: Iterable[Problem], candidates: Iterable[Problem]) -> tuple[Problem, ...]:
    """Drop candidates sharing normalized prompt OR ingredients hash with training."""
    training = tuple(training)
    known_text = {item.normalized_text for item in training}
    known_ingredients = {item.ingredients_sha256 for item in training}
    accepted = []
    seen_text, seen_ingredients = set(), set()
    for item in candidates:
        if (item.normalized_text in known_text or item.ingredients_sha256 in known_ingredients
                or item.normalized_text in seen_text or item.ingredients_sha256 in seen_ingredients):
            continue
        accepted.append(item)
        seen_text.add(item.normalized_text)
        seen_ingredients.add(item.ingredients_sha256)
    return tuple(accepted)


def assert_benchmark_disjoint(training: Iterable[Problem], benchmark: Iterable[Problem]) -> None:
    training, benchmark = tuple(training), tuple(benchmark)
    if any(not seed_in_range(item.seed, TRAIN_SEED_RANGE) for item in training):
        raise ValueError("training problems must use reserved training seed range")
    if any(not seed_in_range(item.seed, BENCHMARK_SEED_RANGE) for item in benchmark):
        raise ValueError("benchmark problems must use reserved benchmark seed range")
    train_text = {item.normalized_text for item in training}
    train_ingredients = {item.ingredients_sha256 for item in training}
    for item in benchmark:
        if item.normalized_text in train_text or item.ingredients_sha256 in train_ingredients:
            raise ValueError("benchmark overlaps training by normalized text or ingredients hash")
