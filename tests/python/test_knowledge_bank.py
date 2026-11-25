import unittest

from ultron_core.agent_tools import execute_tool, get_tool_specs
from ultron_core.knowledge_bank import load_knowledge_bank, search_knowledge


class KnowledgeBankTests(unittest.TestCase):
    def test_bank_has_at_least_one_hundred_unique_entries(self):
        bank = load_knowledge_bank()
        self.assertGreaterEqual(bank["entry_count"], 100)
        self.assertEqual(len({entry["id"] for entry in bank["entries"]}), bank["entry_count"])

    def test_bank_covers_multiple_subjects_and_levels(self):
        bank = load_knowledge_bank()
        subjects = {entry["subject"] for entry in bank["entries"]}
        levels = {entry["level"] for entry in bank["entries"]}
        self.assertGreaterEqual(len(subjects), 5)
        self.assertTrue(any("Grade 1" in level for level in levels))
        self.assertTrue(any("University" in level for level in levels))

    def test_search_returns_ranked_math_entries(self):
        result = search_knowledge("Newton force acceleration", subject="science", limit=3)
        self.assertEqual(result["status"], "results")
        self.assertLessEqual(len(result["results"]), 3)
        self.assertTrue(any("Newton" in entry["statement"] for entry in result["results"]))

    def test_agent_tool_dispatch(self):
        result = execute_tool("knowledge_search", {"query": "Pythagorean theorem", "limit": 2})
        self.assertEqual(result["tool"], "knowledge_search")
        self.assertTrue(result["results"])
        self.assertIn("knowledge_search", [spec["name"] for spec in get_tool_specs()])

    def test_rejects_invalid_limit_and_unknown_arguments(self):
        with self.assertRaises(ValueError):
            search_knowledge("math", limit=0)
        with self.assertRaises(ValueError):
            execute_tool("knowledge_search", {"query": "math", "shell": "no"})


if __name__ == "__main__":
    unittest.main()
