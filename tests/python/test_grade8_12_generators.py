import json
import unittest
from fractions import Fraction
from pathlib import Path

from tools.math_generators.grade8_12 import TOPICS, WORD_TOPICS, generate, verify, semantic_check
from tools.math_generators.grade8_12.generators import GENERATOR_METADATA
from tools.math_generators.build_registry import render_registries

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_WORD_TOPICS = {
    "linear_equations", "systems_of_equations", "polynomial_factoring",
    "functions", "coordinate_geometry", "triangle_geometry", "trigonometry",
    "sequences_series", "derivatives", "definite_integrals", "combinatorics",
    "number_theory", "vectors", "statistics", "probability",
}


class Grade8To12GeneratorTests(unittest.TestCase):
    def test_500_verified_examples_per_topic(self):
        for topic in TOPICS:
            for seed in range(500):
                p = generate(seed, 1 + seed % 5, topic)
                self.assertTrue(verify(p), (topic, seed, p))
                self.assertEqual(p["seed"], seed)
                self.assertEqual(p["topic"], topic)

    def test_seed_replay_and_variation(self):
        for topic in TOPICS:
            self.assertEqual(generate(2025, 4, topic), generate(2025, 4, topic))
        for topic in TOPICS:
            samples = {
                (generate(seed, 1 + seed % 5, topic)["problem"],
                 generate(seed, 1 + seed % 5, topic)["answer"])
                for seed in range(80)
            }
            self.assertGreater(len(samples), 25, topic)

    def test_complete_word_problem_topic_declarations(self):
        declared = {topic for topic, spec in GENERATOR_METADATA.items() if spec["word_templates"]}
        self.assertEqual(WORD_TOPICS, EXPECTED_WORD_TOPICS)
        self.assertEqual(declared, EXPECTED_WORD_TOPICS)
        self.assertEqual(set(GENERATOR_METADATA), set(TOPICS))

    def test_contextual_topics_emit_context(self):
        markers = {
            "linear_equations": ("school buys",),
            "systems_of_equations": ("two items cost",),
            "polynomial_factoring": ("rectangle",),
            "functions": ("distance model",),
            "coordinate_geometry": ("map",),
            "triangle_geometry": ("triangle",),
            "trigonometry": ("vertical rise", "evaluate"),
            "sequences_series": ("savings plan",),
            "derivatives": ("position function", "instantaneous rate"),
            "definite_integrals": ("accumulates", "definite integral"),
            "combinatorics": ("committee",),
            "number_theory": ("schedules",),
            "vectors": ("dot product",),
            "statistics": ("sample measurements",),
            "probability": ("bag contains",),
        }
        for topic, phrases in markers.items():
            emitted = any(
                any(phrase in generate(seed, 2, topic)["problem"].lower() for phrase in phrases)
                for seed in range(250)
            )
            self.assertTrue(emitted, topic)

    def test_registry_files_match_metadata(self):
        rendered = render_registries()
        registry_root = ROOT / "tools" / "math_generators"
        for relative, expected in rendered.items():
            with self.subTest(path=relative):
                self.assertEqual((registry_root / relative).read_text(encoding="utf-8"), expected)
        grade8 = json.loads(rendered["grade8_12/registry.json"])
        flags = {row["topic"]: row["includes_word_problems"] for row in grade8["topics"]}
        self.assertEqual({topic for topic, enabled in flags.items() if enabled}, EXPECTED_WORD_TOPICS)
        combined = json.loads(rendered["registry.json"])
        self.assertEqual(combined["coverage_through"], "G1-12 + university mathematics curriculum catalog (generator status explicit)")

    def test_semantic_domains(self):
        self.assertFalse(semantic_check(
            {"topic":"probability","red":-1,"blue":4,"total":3,"value":"-1/3"}, "-1/3"
        ))
        self.assertFalse(semantic_check(
            {"topic":"triangle_geometry","a":100,"b":90,"third":-10}, "-10"
        ))
        self.assertFalse(semantic_check(
            {"topic":"combinatorics","choose":8,"total":5}, "0"
        ))
        self.assertTrue(semantic_check(
            {"topic":"probability","red":2,"blue":3,"total":5,"value":"2/5"}, "2/5"
        ))

    def test_tampering_rejected(self):
        p = generate(71, 3, "matrices")
        p["answer"] = "999"
        self.assertFalse(verify(p))


if __name__ == "__main__":
    unittest.main()
