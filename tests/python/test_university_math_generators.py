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

            item=generate(seed,difficulty,"quadratic_Taylor_polynomials")
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


    def test_batch3_independent_math_checks(self):
        for seed in range(250):
            difficulty=1+seed%5
            item=generate(seed,difficulty,"predicate_logic")
            v=item["ingredients"]
            expected=(v["threshold"]==len(v["domain"])) if v["quantifier"]=="forall" else bool(v["threshold"])
            self.assertEqual(item["answer"],str(expected).lower())

            item=generate(seed,difficulty,"relations_and_equivalence")
            v=item["ingredients"]
            self.assertEqual(v["equivalence_class"],[x for x in v["domain"] if x%v["modulus"]==v["element"]%v["modulus"]])

            item=generate(seed,difficulty,"subspaces_and_span")
            v=item["ingredients"]
            self.assertEqual(v["coefficients"],v["target"])

            item=generate(seed,difficulty,"linear_independence")
            v=item["ingredients"]
            a,b=v["vectors"][0]; c,e=v["vectors"][1]
            self.assertEqual(v["determinant"],a*e-b*c)
            self.assertEqual(item["answer"],"independent" if v["determinant"]!=0 else "dependent")

            item=generate(seed,difficulty,"basis_and_dimension")
            v=item["ingredients"]
            a,b=v["vectors"][0]; c,e=v["vectors"][1]
            self.assertNotEqual(a*e-b*c,0)
            self.assertEqual(v["dimension"],2)

            item=generate(seed,difficulty,"matrix_rank")
            v=item["ingredients"]
            a,b=v["matrix"][0]; c,e=v["matrix"][1]
            determinant=a*e-b*c
            rank=2 if determinant else (1 if any((a,b,c,e)) else 0)
            self.assertEqual(v["rank"],rank)
            self.assertEqual(item["answer"],str(rank))

            item=generate(seed,difficulty,"limits_and_continuity")
            v=item["ingredients"]
            self.assertEqual(int(item["answer"]),v["constant"])

            item=generate(seed,difficulty,"derivative_theory")
            v=item["ingredients"]
            a,b,_=v["coefficients"]
            self.assertEqual(int(item["answer"]),2*a*v["point"]+b)


    def test_batch3_math_regressions(self):
        for seed in range(180):
            difficulty=1+seed%5
            item=generate(seed,difficulty,"quantifiers")
            v=item["ingredients"]
            expected=v["threshold"]==len(v["domain"]) if v["quantifier"]=="forall" else v["threshold"]>0
            self.assertEqual(item["answer"],str(expected).lower())

            item=generate(seed,difficulty,"cardinality")
            v=item["ingredients"]
            self.assertEqual(v["cardinality"],min(v["set_size"],v["modulus"]))

            item=generate(seed,difficulty,"linear_transformations")
            v=item["ingredients"]; a,b,c,e=v["matrix"]; x,y=v["vector"]
            self.assertEqual(v["image"],[a*x+b*y,c*x+e*y])

            item=generate(seed,difficulty,"diagonalization")
            self.assertTrue(item["ingredients"]["diagonalizable"])

            item=generate(seed,difficulty,"inner_product_spaces")
            v=item["ingredients"]
            self.assertEqual(v["inner_product"],v["vector"][0]*v["other"][0]+v["vector"][1]*v["other"][1])

            item=generate(seed,difficulty,"orthogonality_and_projection")
            self.assertEqual(item["ingredients"]["projection"],[item["ingredients"]["vector"][0],0])

            item=generate(seed,difficulty,"least_squares")
            v=item["ingredients"]
            self.assertEqual(Fraction(item["answer"]),Fraction(v["column"][0]*v["target"][0],v["squared_norm"]))

            item=generate(seed,difficulty,"mean_value_theorems")
            v=item["ingredients"]; a,b,_=v["coefficients"]; c=Fraction(v["mean_value_point"])
            self.assertEqual(2*a*c+b,Fraction(v["secant_slope"]))

            item=generate(seed,difficulty,"Riemann_integral")
            v=item["ingredients"]; a,b=v["linear_coefficients"]; left,right=v["interval"]
            expected=Fraction(a*(right**2-left**2),2)+b*(right-left)
            self.assertEqual(Fraction(item["answer"]),expected)

            item=generate(seed,difficulty,"improper_integrals")
            self.assertEqual(Fraction(item["answer"]),Fraction(1,item["ingredients"]["power"]-1))

            item=generate(seed,difficulty,"sequences_and_series")
            v=item["ingredients"]
            self.assertEqual(Fraction(item["answer"]),Fraction(v["first_term"],1)/(1-Fraction(v["common_ratio"])))

            item=generate(seed,difficulty,"power_series")
            v=item["ingredients"]
            self.assertEqual(item["answer"],"converges" if abs(v["test_point"]-v["center"])<v["radius"] else "diverges")

            item=generate(seed,difficulty,"gradient_and_directional_derivatives")
            v=item["ingredients"]; a,b=v["coefficients"]; x,y=v["point"]; u,w=v["direction"]
            self.assertEqual(int(item["answer"]),2*a*x*u+2*b*y*w)

            item=generate(seed,difficulty,"chain_rule_multivariable")
            v=item["ingredients"]; a,b=v["coefficients"]; t=v["parameter"]
            self.assertEqual(int(item["answer"]),4*a*t**3+3*b)

    def test_university_registry_declared(self):
        self.assertEqual(set(GENERATOR_METADATA),set(TOPICS))
        registry=render_registries()["university/registry.json"]
        import json
        payload=json.loads(registry)
        rows={x["topic"]:x for x in payload["topics"]}
        self.assertEqual(len(rows),214)
        self.assertFalse(rows["Taylor_series"]["has_generator"])
        self.assertTrue(rows["quadratic_Taylor_polynomials"]["has_generator"])
        self.assertFalse(rows["multiple_integrals"]["has_generator"])
        self.assertTrue(rows["rectangular_linear_polynomial_double_integrals"]["has_generator"])
        self.assertTrue(rows["complex_number_arithmetic"]["has_generator"])
        self.assertFalse(rows["complex_topology"]["has_generator"])
        self.assertFalse(rows["complex_Taylor_series"]["has_generator"])
        self.assertFalse(rows["Laurent_series"]["has_generator"])
        self.assertFalse(rows["change_of_variables"]["has_generator"])
        self.assertTrue(rows["diagonal_linear_change_of_variables_rectangles"]["has_generator"])
        self.assertFalse(rows["line_integrals"]["has_generator"])
        self.assertTrue(rows["constant_vector_field_segment_line_integrals"]["has_generator"])
        self.assertFalse(rows["surface_integrals"]["has_generator"])
        self.assertTrue(rows["flat_rectangular_surface_area_integrals"]["has_generator"])
        self.assertFalse(rows["vector_calculus"]["has_generator"])
        self.assertTrue(rows["diagonal_linear_vector_field_divergence"]["has_generator"])
        self.assertTrue(rows["homogeneous_variable_coefficient_linear_first_order_ODEs"]["has_generator"])
        self.assertTrue(rows["quadratic_potential_exact_first_order_ODEs"]["has_generator"])
        self.assertFalse(rows["exact_first_order_ODEs"]["has_generator"])
        self.assertFalse(rows["linear_first_order_variable_coefficient_ODEs"]["has_generator"])
        generator_topics = {x["generator_topic"] for x in payload["topics"] if x.get("generator_topic")}
        self.assertEqual(generator_topics, set(TOPICS))
        mapped = [x for x in payload["topics"] if x.get("generator_topic")]
        self.assertEqual(len(mapped), len(TOPICS))
        self.assertTrue(all(x["has_generator"] for x in mapped))
        self.assertTrue(rows["homogeneous_constant_coefficient_first_order_ODEs"]["has_generator"])
        self.assertEqual(rows["homogeneous_constant_coefficient_first_order_ODEs"]["status"], "generator_available_not_mastered")
        self.assertTrue(rows["separable_first_order_ODEs"]["has_generator"])
        self.assertFalse(rows["linear_first_order_variable_coefficient_ODEs"]["has_generator"])
        self.assertFalse(rows["exact_first_order_ODEs"]["has_generator"])
        self.assertEqual(rows["separable_first_order_ODEs"]["status"], "generator_available_not_mastered")
        self.assertEqual(rows["linear_first_order_variable_coefficient_ODEs"]["status"], "catalogued_not_implemented")
        self.assertEqual(rows["exact_first_order_ODEs"]["status"], "catalogued_not_implemented")
        self.assertTrue(rows["greens_theorem_rectangles"]["has_generator"])
        self.assertTrue(rows["stokes_theorem_horizontal_rectangles"]["has_generator"])
        self.assertTrue(rows["divergence_theorem_axis_aligned_boxes"]["has_generator"])
        self.assertEqual(rows["greens_theorem_rectangles"]["status"], "generator_available_not_mastered")
        self.assertFalse(rows["stokes_theorem"]["has_generator"])
        self.assertEqual(rows["stokes_theorem"]["status"], "catalogued_not_implemented")
        self.assertFalse(rows["divergence_theorem"]["has_generator"])
        self.assertEqual(rows["divergence_theorem"]["status"], "catalogued_not_implemented")
        self.assertTrue(rows["conditional_probability"]["includes_word_problems"])
        self.assertTrue(rows["counting_principles"]["includes_word_problems"])
        combined = json.loads(render_registries()["registry.json"])
        combined_rows = {x["topic"]: x for x in combined["topics"] if x["grade_band"] == "University"}
        self.assertTrue(combined_rows["conditional_probability"]["word_problems"])
        self.assertTrue(combined_rows["counting_principles"]["word_problems"])
        self.assertTrue(all(x["status"] == "catalogued_not_implemented" for x in rows.values() if not x["has_generator"]))


if __name__=="__main__":
    unittest.main()
