import unittest
from fractions import Fraction
from tools.math_generators.university import TOPICS, generate, verify
from tools.math_generators.university.generators import GENERATOR_METADATA
from tools.math_generators.build_registry import render_registries


class UniversityFoundationTests(unittest.TestCase):
    def test_300_seeded_verified_items_per_topic(self):
        for topic in TOPICS:
            for seed in range(300):
                item=generate(seed,1+seed%5,topic)
                self.assertTrue(verify(item),(topic,seed,item))
                self.assertEqual(item["topic"],topic)

    def test_replay_variation_and_tamper_detection(self):
        for topic in TOPICS:
            self.assertEqual(generate(100,3,topic),generate(100,3,topic))
            problems={generate(seed,2,topic)["problem"] for seed in range(80)}
            self.assertGreater(len(problems),10,topic)
        item=generate(8,2,"linear_algebra")
        item["answer"]="tampered"
        self.assertFalse(verify(item))

    def test_bayes_posterior_matches_count_definition(self):
        for seed in range(300):
            item=generate(seed,1+seed%5,"probability_theory")
            values=item["ingredients"]
            positives=values["positive_given_case"]+values["positive_given_noncase"]
            expected=Fraction(values["positive_given_case"],positives)
            self.assertEqual(Fraction(item["answer"]),expected)
            self.assertLessEqual(expected,1)

    def test_university_registry_declared(self):
        self.assertEqual(set(GENERATOR_METADATA),set(TOPICS))
        registry=render_registries()["university/registry.json"]
        import json
        payload=json.loads(registry)
        self.assertEqual({x["topic"] for x in payload["topics"]},set(TOPICS))
        self.assertTrue(all(x["grade_band"]=="University Foundation" for x in payload["topics"]))


if __name__=="__main__":
    unittest.main()
