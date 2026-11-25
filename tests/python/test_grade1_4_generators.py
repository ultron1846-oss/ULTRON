import json
import unittest
from pathlib import Path

from tools.math_generators.grade1_4 import TOPICS, WORD_TOPICS, generate, verify, semantic_check
from tools.math_generators.grade1_4.generators import GENERATOR_METADATA
from tools.math_generators.build_registry import render_registries

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_WORD_TOPICS = {
    "multiplication", "division", "fractions_basics", "simple_word_problems",
    "time_and_money", "perimeter_and_area",
}


class Grade1To4GeneratorTests(unittest.TestCase):
    def test_1000_verified_per_topic(self):
        for topic in TOPICS:
            for seed in range(1000):
                p = generate(seed, 1 + seed % 5, topic)
                self.assertTrue(verify(p), (topic, seed, p))
                self.assertEqual(p["seed"], seed)
                self.assertEqual(p["topic"], topic)

    def test_same_seed_same_problem(self):
        for topic in TOPICS:
            self.assertEqual(generate(41, 4, topic), generate(41, 4, topic))

    def test_tampering_is_rejected(self):
        p = generate(91, 3, "addition")
        p["answer"] = str(int(p["answer"]) + 1)
        self.assertFalse(verify(p))

    def test_complete_contextual_declarations(self):
        declared = {topic for topic, spec in GENERATOR_METADATA.items() if spec["word_templates"]}
        self.assertEqual(WORD_TOPICS, EXPECTED_WORD_TOPICS)
        self.assertEqual(declared, EXPECTED_WORD_TOPICS)
        self.assertEqual(set(GENERATOR_METADATA), set(TOPICS))

    def test_contextual_topics_emit_word_problems(self):
        markers = {
            "multiplication": ("groups",),
            "division": ("share",),
            "fractions_basics": ("receive", "you have"),
            "simple_word_problems": ("sam has", "basket", "bags", "tables"),
            "time_and_money": ("journey", "minutes", "cents", "pencil"),
            "perimeter_and_area": ("rectangle",),
        }
        for topic, phrases in markers.items():
            self.assertTrue(any(
                any(phrase in generate(seed, 3, topic)["problem"].lower() for phrase in phrases)
                for seed in range(500)
            ), topic)

    def test_registry_files_match_generator_metadata(self):
        rendered = render_registries()
        root = ROOT / "tools" / "math_generators"
        for relative, expected in rendered.items():
            with self.subTest(path=relative):
                self.assertEqual((root / relative).read_text(encoding="utf-8"), expected)
        grade1 = json.loads(rendered["grade1_4/registry.json"])
        flags = {row["topic"]: row["includes_word_problems"] for row in grade1["topics"]}
        self.assertEqual({t for t,v in flags.items() if v}, EXPECTED_WORD_TOPICS)

    def test_semantic_hook_rejects_invalid_quantities(self):
        self.assertFalse(semantic_check("multiplication", "-3", "There are 2 groups."))
        self.assertFalse(semantic_check("time_and_money", "$1.2", "money"))
        self.assertFalse(semantic_check("time_and_money", "1 hour 70 minutes", "time"))
        self.assertFalse(semantic_check("perimeter_and_area", "perimeter=-2; area=4", "rectangle"))
        self.assertTrue(semantic_check("time_and_money", "$1.20", "money"))


if __name__ == "__main__":
    unittest.main()
