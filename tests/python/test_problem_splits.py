import unittest

from ultron_core.problem import Problem
from ultron_core.problem_splits import (
    TRAIN_SEED_RANGE, BENCHMARK_SEED_RANGE, seed_split,
    filter_benchmark_overlaps, assert_benchmark_disjoint,
)


def make_problem(seed, prompt, ingredients):
    return Problem.from_generator({
        "topic": "test_topic", "problem": prompt, "answer": "1", "seed": seed,
        "difficulty": 1, "ingredients": ingredients,
    }, source="test")


class ProblemSplitTests(unittest.TestCase):
    def test_seed_ranges_are_disjoint_and_classified(self):
        self.assertEqual(TRAIN_SEED_RANGE[1], BENCHMARK_SEED_RANGE[0])
        self.assertEqual(seed_split(TRAIN_SEED_RANGE[0]), "train")
        self.assertEqual(seed_split(BENCHMARK_SEED_RANGE[0]), "benchmark")
        with self.assertRaises(ValueError):
            seed_split(BENCHMARK_SEED_RANGE[1])

    def test_benchmark_filter_and_assert_reject_text_or_ingredient_overlap(self):
        training = [make_problem(7, "Calculate 2 + 2", {"a": 2, "b": 2})]
        candidates = [
            make_problem(1_000_007, " calculate 2 + 2 ", {"a": 3, "b": 1}),
            make_problem(1_000_008, "Different prompt", {"a": 2, "b": 2}),
            make_problem(1_000_009, "Unique prompt", {"a": 8, "b": 9}),
        ]
        filtered = filter_benchmark_overlaps(training, candidates)
        self.assertEqual([x.seed for x in filtered], [1_000_009])
        assert_benchmark_disjoint(training, filtered)
        with self.assertRaisesRegex(ValueError, "overlaps"):
            assert_benchmark_disjoint(training, candidates)


if __name__ == "__main__":
    unittest.main()
