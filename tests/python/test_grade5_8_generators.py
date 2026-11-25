import unittest
from tools.math_generators.grade5_8 import TOPICS, WORD_TOPICS, generate, verify

class Grade5To8GeneratorTests(unittest.TestCase):
    def test_1000_verified_per_topic(self):
        for topic in TOPICS:
            for seed in range(1000):
                p=generate(seed,1+seed%5,topic)
                self.assertTrue(verify(p),(topic,seed,p))
                self.assertEqual(p["seed"],seed)
    def test_deterministic_and_tamper_rejected(self):
        for topic in TOPICS:
            self.assertEqual(generate(123,4,topic),generate(123,4,topic))
        p=generate(19,2,"percentages"); p["answer"]="999"
        self.assertFalse(verify(p))
    def test_word_problem_coverage_registry(self):
        self.assertTrue({"ratios","percentages","linear_equations","inequalities","basic_geometry","angles","statistics_basics","simple_probability"}.issubset(WORD_TOPICS))
        for topic in WORD_TOPICS:
            self.assertTrue(generate(7,3,topic)["problem"])

if __name__=="__main__": unittest.main()
