"""Finite simple connected graph degree sequences and the handshaking identity."""
from __future__ import annotations

import random
from typing import Any

TOPIC = "finite_simple_graph_handshaking"
VERIFIER = "independent_simple_graph_degree_and_handshaking_check"


def _degrees(vertex_count: int, edges: tuple[tuple[int, int], ...]) -> tuple[int, ...]:
    values = [0] * vertex_count
    for left, right in edges:
        values[left] += 1
        values[right] += 1
    return tuple(values)


def _connected(vertex_count: int, edges: tuple[tuple[int, int], ...]) -> bool:
    adjacency = [[] for _ in range(vertex_count)]
    for left, right in edges:
        adjacency[left].append(right)
        adjacency[right].append(left)
    seen = {0}
    pending = [0]
    while pending:
        node = pending.pop()
        for neighbour in adjacency[node]:
            if neighbour not in seen:
                seen.add(neighbour)
                pending.append(neighbour)
    return len(seen) == vertex_count


def _canonical(seed: int, difficulty: int, vertex_count: int, edges: tuple[tuple[int, int], ...]) -> dict:
    ordered_edges = tuple(sorted(edges))
    degree_sequence = _degrees(vertex_count, ordered_edges)
    degree_sum = sum(degree_sequence)
    edge_count = len(ordered_edges)
    return {
        "id": f"university-{TOPIC}-{seed}-{difficulty}",
        "seed": seed,
        "grade_band": "University",
        "topic": TOPIC,
        "subtopic": "degree sequences of finite connected simple graphs and the handshaking lemma",
        "difficulty": difficulty,
        "problem": (
            f"A finite simple connected graph has vertices 0 through {vertex_count - 1} "
            f"and edge set {list(ordered_edges)}. Find the vertex degree sequence and verify "
            "that the sum of all degrees equals twice the number of edges."
        ),
        "steps": [
            "Count one incident edge at each endpoint to obtain every vertex degree.",
            "Sum the degrees; each undirected edge contributes exactly two incidences.",
            f"The degree sum is {degree_sum}, equal to 2*{edge_count}.",
        ],
        "answer": f"degrees={list(degree_sequence)}; degree_sum={degree_sum}=2*{edge_count}",
        "answer_type": "expression",
        "ingredients": {
            "topic": TOPIC,
            "vertex_count": vertex_count,
            "edges": [list(edge) for edge in ordered_edges],
            "degree_sequence": list(degree_sequence),
            "edge_count": edge_count,
            "degree_sum": degree_sum,
            "connected": True,
        },
        "verifier": VERIFIER,
    }


def build_finite_graph_fields(rng: random.Random, difficulty: int):
    d = difficulty
    vertex_count = rng.randint(3, min(12, 2 * d + 4))
    edges = {(index, index + 1) for index in range(vertex_count - 1)}
    candidates = [
        (left, right)
        for left in range(vertex_count)
        for right in range(left + 2, vertex_count)
        if (left, right) not in edges
    ]
    rng.shuffle(candidates)
    extra_limit = min(len(candidates), d + 1)
    extra_count = rng.randint(0, extra_limit)
    edges.update(candidates[:extra_count])
    fields = _canonical(0, d, vertex_count, tuple(sorted(edges)))
    fields.pop("id")
    fields.pop("seed")
    return fields, lambda: verify_finite_graph({
        **fields, "id": f"university-{TOPIC}-0-{d}", "seed": 0
    })


def verify_finite_graph(problem: dict) -> bool:
    try:
        if not isinstance(problem, dict) or problem.get("topic") != TOPIC:
            return False
        seed = problem.get("seed")
        difficulty = problem.get("difficulty")
        if not isinstance(seed, int) or isinstance(seed, bool):
            return False
        if not isinstance(difficulty, int) or isinstance(difficulty, bool) or difficulty not in (1, 2, 3, 4, 5):
            return False
        data = problem.get("ingredients")
        if not isinstance(data, dict) or data.get("topic") != TOPIC:
            return False
        vertex_count = data.get("vertex_count")
        if (
            not isinstance(vertex_count, int)
            or isinstance(vertex_count, bool)
            or not 3 <= vertex_count <= min(12, 2 * difficulty + 4)
        ):
            return False
        raw_edges = data.get("edges")
        if not isinstance(raw_edges, list) or not vertex_count - 1 <= len(raw_edges) <= vertex_count * (vertex_count - 1) // 2:
            return False
        normalized = []
        for edge in raw_edges:
            if (
                not isinstance(edge, list)
                or len(edge) != 2
                or any(not isinstance(v, int) or isinstance(v, bool) for v in edge)
            ):
                return False
            left, right = edge
            if not 0 <= left < right < vertex_count:
                return False
            normalized.append((left, right))
        edges = tuple(normalized)
        if edges != tuple(sorted(set(edges))):
            return False
        if any((index, index + 1) not in edges for index in range(vertex_count - 1)):
            return False
        if not _connected(vertex_count, edges):
            return False
        expected = _canonical(seed, difficulty, vertex_count, edges)
        return problem == expected
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
