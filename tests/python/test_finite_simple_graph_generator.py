"""Independent graph-theoretic validation of finite simple graph exercises."""
import unittest

from tools.math_generators.university import generate, verify
from tools.math_generators.university.finite_graph import TOPIC


def _independent_degrees(vertex_count, edges):
    result = [0] * vertex_count
    adjacency = [[] for _ in range(vertex_count)]
    for left, right in edges:
        result[left] += 1
        result[right] += 1
        adjacency[left].append(right)
        adjacency[right].append(left)
    seen = {0}
    stack = [0]
    while stack:
        node = stack.pop()
        for neighbour in adjacency[node]:
            if neighbour not in seen:
                seen.add(neighbour)
                stack.append(neighbour)
    return result, len(seen) == vertex_count


class FiniteSimpleGraphTests(unittest.TestCase):
    def test_500_seeded_graphs_handshaking_and_connectivity(self):
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, TOPIC)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            n = data["vertex_count"]
            edges = [tuple(edge) for edge in data["edges"]]
            degrees, connected = _independent_degrees(n, edges)
            self.assertEqual(len(edges), len(set(edges)))
            self.assertTrue(all(0 <= u < v < n for u, v in edges))
            self.assertTrue(connected)
            self.assertEqual(data["degree_sequence"], degrees)
            self.assertEqual(sum(degrees), 2 * len(edges))
            self.assertEqual(data["edge_count"], len(edges))
            self.assertEqual(data["degree_sum"], 2 * len(edges))
            self.assertEqual(item, generate(seed, difficulty, TOPIC))

    def test_loop_and_parallel_edge_tampering_are_rejected(self):
        item = generate(17, 5, TOPIC)
        for bad_edges in ([[0, 0]] + item["ingredients"]["edges"][1:],
                          item["ingredients"]["edges"] + [item["ingredients"]["edges"][0]]):
            altered = dict(item)
            altered["ingredients"] = dict(item["ingredients"])
            altered["ingredients"]["edges"] = bad_edges
            self.assertFalse(verify(altered))


if __name__ == "__main__":
    unittest.main()
