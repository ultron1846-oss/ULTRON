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

    def test_second_batch_answers_match_math_definitions(self):
        for seed in range(120):
            difficulty=1+seed%5
            item=generate(seed,difficulty,"sets_and_functions")
            v=item["ingredients"]
            self.assertEqual(int(item["answer"]),v["size_a"]+v["size_b"]-v["intersection"])

            item=generate(seed,difficulty,"propositional_logic")
            v=item["ingredients"]
            expected={"AND":v["p"] and v["q"],"OR":v["p"] or v["q"],"XOR":v["p"] != v["q"],"IMPLIES":(not v["p"]) or v["q"]}[v["operator"]]
            self.assertEqual(item["answer"],str(expected).lower())

            item=generate(seed,difficulty,"mathematical_induction")
            v=item["ingredients"]
            self.assertEqual(Fraction(v["induction_lhs"]),Fraction(v["induction_rhs"]))

            item=generate(seed,difficulty,"vectors_and_vector_spaces")
            v=item["ingredients"]
            expected=(v["alpha"]*v["u"][0]+v["beta"]*v["v"][0],v["alpha"]*v["u"][1]+v["beta"]*v["v"][1])
            self.assertEqual(item["answer"],f"({expected[0]},{expected[1]})")

            item=generate(seed,difficulty,"systems_linear_equations")
            v=item["ingredients"]
            a,b,c,e=v["coefficients"]; x,y=v["solution"]; r1,r2=v["constants"]
            self.assertEqual((a*x+b*y,c*x+e*y),(r1,r2))
            self.assertEqual(item["answer"],f"x={x}; y={y}")

            item=generate(seed,difficulty,"eigenvalues_and_eigenvectors")
            v=item["ingredients"]
            a,b=v["matrix"][0][0],v["matrix"][1][1]
            self.assertEqual(v["eigenvalues"],[a,b])
            self.assertEqual(item["answer"],f"λ1={a}; λ2={b}")

            item=generate(seed,difficulty,"Taylor_series")
            v=item["ingredients"]
            a,b,c=v["coefficients"]; h=v["center"]
            self.assertEqual(v["value_at_center"],a*h*h+b*h+c)
            self.assertEqual(v["derivative_at_center"],2*a*h+b)
            self.assertEqual(item["answer"],f"P2(x)={v['value_at_center']}+({v['derivative_at_center']})(x−{h})+({a})(x−{h})²")

            item=generate(seed,difficulty,"conditional_probability")
            v=item["ingredients"]
            self.assertEqual(Fraction(item["answer"]),Fraction(v["event_and_condition_count"],v["condition_count"]))

            item=generate(seed,difficulty,"counting_principles")
            v=item["ingredients"]
            self.assertEqual(int(item["answer"]),v["shirt_choices"]*v["pants_choices"]*v["shoe_choices"])

    def test_university_registry_declared(self):
        self.assertEqual(set(GENERATOR_METADATA),set(TOPICS))
        registry=render_registries()["university/registry.json"]
        import json
        payload=json.loads(registry)
        rows={x["topic"]:x for x in payload["topics"]}
        self.assertEqual(len(rows),197)
        generator_topics = {x["generator_topic"] for x in payload["topics"] if x.get("generator_topic")}
        self.assertEqual(generator_topics, set(TOPICS))
        mapped = [x for x in payload["topics"] if x.get("generator_topic")]
        self.assertEqual(len(mapped), len(TOPICS))
        self.assertTrue(all(x["has_generator"] for x in mapped))
        self.assertTrue(rows["conditional_probability"]["includes_word_problems"])
        self.assertTrue(rows["counting_principles"]["includes_word_problems"])
        combined = json.loads(render_registries()["registry.json"])
        combined_rows = {x["topic"]: x for x in combined["topics"] if x["grade_band"] == "University"}
        self.assertTrue(combined_rows["conditional_probability"]["word_problems"])
        self.assertTrue(combined_rows["counting_principles"]["word_problems"])
        self.assertTrue(all(x["status"] == "catalogued_not_implemented" for x in rows.values() if not x["has_generator"]))


if __name__=="__main__":
    unittest.main()
