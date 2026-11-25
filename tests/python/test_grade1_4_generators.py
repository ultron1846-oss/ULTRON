import unittest
from tools.math_generators.grade1_4 import TOPICS, generate, verify

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

if __name__ == "__main__":
    unittest.main()
