import json
import unittest
from pathlib import Path

from tools.math_generators.build_registry import render_registries

ROOT = Path(__file__).resolve().parents[2] / "tools" / "math_generators"


class MathGeneratorRegistrySyncTests(unittest.TestCase):
    def test_committed_registries_match_generator_declarations(self):
        for relative, expected in render_registries().items():
            with self.subTest(registry=relative):
                actual = (ROOT / relative).read_text(encoding="utf-8")
                self.assertEqual(actual, expected)

    def test_combined_registry_includes_core_topics_and_source_keys(self):
        payload = json.loads(render_registries()["registry.json"])
        rows = payload["topics"]
        core = [row for row in rows if row.get("source") == "ultron_core.data_generation"]
        self.assertEqual(len(core), 8)
        self.assertTrue(all(row["status"] == "generator_available_not_mastered" for row in core))
        source_topic_keys = [(row.get("source", row["grade_band"]), row["topic"]) for row in rows]
        self.assertEqual(len(source_topic_keys), len(set(source_topic_keys)))


if __name__ == "__main__":
    unittest.main()
