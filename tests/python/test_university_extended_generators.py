import unittest\nimport math
from fractions import Fraction

from tools.math_generators.university import generate, verify
from tools.math_generators.university.extended_generators import EXTENDED_BANDS

class UniversityExtendedBatchTests(unittest.TestCase):
    def test_all_extended_topics_seed_replay_and_verification(self):
        for topic in EXTENDED_BANDS:
            for seed in range(100):
                item=generate(seed,1+seed%5,topic)
                self.assertTrue(verify(item),(topic,seed,item))
                self.assertEqual(item,generate(seed,1+seed%5,topic))
                self.assertEqual(item["grade_band"],"University")

    def test_independent_formula_regressions(self):
        for seed in range(150):
            difficulty=1+seed%5
            item=generate(seed,difficulty,"spectral_theorem")
            v=item["ingredients"];a,b=v["matrix"][0]
            self.assertEqual(v["eigenvalues"],sorted([a+b,a-b]))

            item=generate(seed,difficulty,"bilinear_and_quadratic_forms")
            v=item["ingredients"];a,b=v["matrix"][0];c=v["matrix"][1][1];x,y=v["point"]
            self.assertEqual(v["value"],a*x*x+2*b*x*y+c*y*y)

            item=generate(seed,difficulty,"multiple_integrals")
            v=item["ingredients"];left,right,bottom,top=v["rectangle"]
            expected=Fraction(right**2-left**2,2)*(top-bottom)+Fraction(top**2-bottom**2,2)*(right-left)
            self.assertEqual(Fraction(item["answer"]),expected)

            item=generate(seed,difficulty,"change_of_variables")
            v=item["ingredients"];sx,sy=v["scale"]
            self.assertEqual(v["jacobian"],sx*sy)
            self.assertEqual(v["transformed_area"],v["source_area"]*sx*sy)

            item=generate(seed,difficulty,"line_integrals")
            v=item["ingredients"];a,b=v["vector_field"];x0,y0=v["start"];x1,y1=v["end"]
            self.assertEqual(v["integral"],a*(x1-x0)+b*(y1-y0))

            item=generate(seed,difficulty,"vector_calculus")
            self.assertEqual(item["ingredients"]["divergence"],sum(item["ingredients"]["field_coefficients"]))

            item=generate(seed,difficulty,"convergence_of_sequences")
            ratio=Fraction(item["ingredients"]["common_ratio"])
            self.assertEqual(item["ingredients"]["converges"],abs(ratio)<1)

            item=generate(seed,difficulty,"pointwise_and_uniform_convergence")
            self.assertEqual(Fraction(item["ingredients"]["sup_norm"]),Fraction(1,item["ingredients"]["index"]))

            item=generate(seed,difficulty,"measure_intro")
            left,right=item["ingredients"]["interval"]
            self.assertEqual(item["ingredients"]["Lebesgue_measure"],right-left)

    def test_ten_new_analysis_topics_have_independent_exact_checks(self):
        topics = (
            "Lebesgue_measure", "Lebesgue_integral", "Lp_spaces",
            "complex_numbers_and_topology", "holomorphic_functions",
            "Cauchy_Riemann_equations", "contour_integrals", "singularities",
            "conformal_maps", "groups_and_subgroups",
        )
        for topic in topics:
            for seed in range(200):
                item = generate(seed, 1 + seed % 5, topic)
                self.assertTrue(verify(item), (topic, seed, item))
                self.assertEqual(item, generate(seed, 1 + seed % 5, topic))
                v = item["ingredients"]
                with self.subTest(topic=topic, seed=seed):
                    if topic == "Lebesgue_measure":
                        left, right = v["interval"]
                        self.assertEqual(v["Lebesgue_measure"], right - left)
                    elif topic == "Lebesgue_integral":
                        left, right = v["interval"]
                        self.assertEqual(v["integral"], v["constant_value"] * (right - left))
                    elif topic == "Lp_spaces":
                        self.assertEqual(v["lp_norm"], sum(abs(x) for x in v["values"]))
                        self.assertEqual(v["p"], 1)
                    elif topic == "complex_numbers_and_topology":
                        dx, dy = v["coordinate_difference"]
                        self.assertEqual(v["distance"] ** 2, dx * dx + dy * dy)
                    elif topic in ("holomorphic_functions", "Cauchy_Riemann_equations"):
                        x, y = v["point"]
                        self.assertEqual(v["partials"]["u_x"], 2 * x) if topic == "holomorphic_functions" else self.assertEqual(v["u_x"], 2 * x)
                        if topic == "holomorphic_functions":
                            p = v["partials"]
                            self.assertEqual(p["u_x"], p["v_y"])
                            self.assertEqual(p["u_y"], -p["v_x"])
                            self.assertEqual(v["derivative"], f"{2*x}+{2*y}i")
                        else:
                            self.assertEqual(v["u_x"], v["v_y"])
                            self.assertEqual(v["u_y"], -v["v_x"])
                    elif topic == "contour_integrals":
                        x0, y0 = v["start"]
                        x1, y1 = v["end"]
                        self.assertEqual(v["integral"], [
                            (x1*x1-y1*y1)-(x0*x0-y0*y0),
                            2*x1*y1-2*x0*y0,
                        ])
                    elif topic == "singularities":
                        self.assertEqual(v["singularity_type"], "pole")
                        self.assertGreaterEqual(v["pole_order"], 1)
                    elif topic == "conformal_maps":
                        a, b = v["derivative"]
                        self.assertGreater(a*a+b*b, 0)
                    elif topic == "groups_and_subgroups":
                        n, k = v["group_order"], v["generator"]
                        self.assertEqual(v["subgroup_order"], n // math.gcd(n, k))

    def test_cauchy_bound_is_strictly_sufficient(self):
        for seed in range(100):
            item=generate(seed,1+seed%5,"Cauchy_sequences")
            v=item["ingredients"]
            k=int(v["sequence"].split("/")[0])
            epsilon=Fraction(v["epsilon"])
            self.assertGreater(v["bound_index"],k/float(epsilon))
            self.assertLess(Fraction(k,v["bound_index"]),epsilon)

if __name__=="__main__":
    unittest.main()
