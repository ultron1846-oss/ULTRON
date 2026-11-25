import json
import unittest
from fractions import Fraction
from pathlib import Path

from tools.math_generators.grade5_8 import TOPICS, WORD_TOPICS, generate, verify
from tools.math_generators.grade5_8.generators import GENERATOR_METADATA, semantic_check
from tools.math_generators.build_registry import render_registries


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_WORD_TOPICS = {
    "ratios", "percentages", "integers", "order_of_operations",
    "linear_equations", "inequalities", "basic_geometry", "angles",
    "statistics_basics", "simple_probability",
}


class Grade5To8GeneratorTests(unittest.TestCase):
    def test_1000_verified_per_topic(self):
        for topic in TOPICS:
            for seed in range(1000):
                p = generate(seed, 1 + seed % 5, topic)
                self.assertTrue(verify(p), (topic, seed, p))
                self.assertEqual(p["seed"], seed)

    def test_deterministic_and_tamper_rejected(self):
        for topic in TOPICS:
            self.assertEqual(generate(123, 4, topic), generate(123, 4, topic))
        p = generate(19, 2, "percentages")
        p["answer"] = "999"
        self.assertFalse(verify(p))
        self.assertGreater(
            len({(generate(seed, 1 + seed % 5, "percentages")["problem"],
                  generate(seed, 1 + seed % 5, "percentages")["answer"])
                 for seed in range(100)}),
            50,
        )

    def test_complete_word_problem_topic_set_and_declarations(self):
        declared = {
            topic for topic, spec in GENERATOR_METADATA.items()
            if spec["word_templates"]
        }
        self.assertEqual(WORD_TOPICS, EXPECTED_WORD_TOPICS)
        self.assertEqual(declared, EXPECTED_WORD_TOPICS)
        self.assertEqual(set(GENERATOR_METADATA), set(TOPICS))
        for topic in WORD_TOPICS:
            self.assertTrue(generate(7, 3, topic)["problem"])

    def test_committed_registries_match_generator_output(self):
        rendered = render_registries()
        registry_root = ROOT / "tools" / "math_generators"
        for relative, expected_text in rendered.items():
            with self.subTest(registry=relative):
                self.assertEqual(
                    (registry_root / relative).read_text(encoding="utf-8"),
                    expected_text,
                )
        grade5 = json.loads(rendered["grade5_8/registry.json"])
        topic_flags = {
            item["topic"]: item["includes_word_problems"]
            for item in grade5["topics"]
        }
        self.assertTrue(topic_flags["integers"])
        self.assertTrue(topic_flags["order_of_operations"])
        combined = json.loads(rendered["registry.json"])
        combined_flags = {
            item["topic"]: item["word_problems"]
            for item in combined["topics"]
        }
        self.assertTrue(combined_flags["integers"])
        self.assertTrue(combined_flags["order_of_operations"])

    def test_percentage_semantics_across_2500_seeds_and_difficulties(self):
        for seed in range(2500):
            difficulty = 1 + seed % 5
            p = generate(seed, difficulty, "percentages")
            ingredients = p["ingredients"]
            pct = ingredients["percent"]
            amount = ingredients["amount"]
            exact = Fraction(pct * amount, 100)
            self.assertTrue(verify(p), (seed, p))
            self.assertTrue(semantic_check(ingredients, p["answer"]), (seed, p))
            if ingredients["quantity_type"] == "count":
                divisor = 100 // __import__("math").gcd(pct, 100)
                self.assertEqual(amount % divisor, 0, (seed, p))
                self.assertEqual(exact.denominator, 1, (seed, p))
                self.assertEqual(Fraction(p["answer"]).denominator, 1, (seed, p))
                self.assertIn("students", p["problem"].lower())
                self.assertNotRegex(p["problem"].lower(), r"\\b(dollars?|kilometers?|litres?|liters?)\\b")
            else:
                self.assertEqual(ingredients["quantity_type"], "continuous")
                self.assertEqual(Fraction(p["answer"]), exact, (seed, p))
                decimal_places = len(p["answer"].partition(".")[2])
                self.assertLessEqual(decimal_places, 2, (seed, p))
                self.assertNotRegex(p["problem"].lower(), r"\\b(students?|people|children|items|animals)\\b")

    def test_semantic_checks_reject_invalid_contextual_values(self):
        p = generate(14, 3, "percentages")
        bad = dict(p["ingredients"])
        bad["quantity_type"] = "count"
        bad["amount"] = 23
        self.assertFalse(semantic_check(bad, "3.91"))
        p = generate(18, 3, "basic_geometry")
        bad = dict(p["ingredients"])
        bad["values"] = [-2, 4]
        self.assertFalse(semantic_check(bad, p["answer"]))


if __name__ == "__main__":
    unittest.main()
