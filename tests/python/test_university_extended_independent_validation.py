"""Independent mathematical checks for the university extended generators.

These assertions recompute results from generated problem ingredients rather than
calling the generator's embedded check or the replay-based verifier.
"""
import unittest
from fractions import Fraction

from tools.math_generators.university import generate
from tools.math_generators.university.extended_generators import EXTENDED_BANDS


class UniversityExtendedIndependentValidationTests(unittest.TestCase):
    def test_independent_invariants_across_all_extended_topics(self):
        for topic in EXTENDED_BANDS:
            for seed in range(100):
                with self.subTest(topic=topic, seed=seed):
                    item = generate(seed, 1 + seed % 5, topic)
                    data = item["ingredients"]

                    if topic == "proof_methods":
                        k = data["integer"]
                        self.assertEqual(data["expression"], f"2*{k}")
                        self.assertEqual(2 * k % 2, 0)
                        self.assertEqual(data["parity"], "even")
                    elif topic == "countable_and_uncountable_sets":
                        start = data["index_start"]
                        image = [3 * (start + i) + 1 for i in range(5)]
                        self.assertEqual(len(set(image)), len(image))
                        self.assertTrue(all(image[i + 1] - image[i] == 3 for i in range(4)))
                    elif topic == "axiom_of_choice_intro":
                        product = 1
                        for size in data["set_sizes"]:
                            self.assertGreater(size, 0)
                            product *= size
                        self.assertEqual(data["choice_count"], product)
                    elif topic == "spectral_theorem":
                        a, b = data["matrix"][0]
                        self.assertEqual(data["matrix"], [[a, b], [b, a]])
                        self.assertEqual(data["eigenvalues"], sorted([a + b, a - b]))
                    elif topic == "Jordan_form":
                        lam = data["eigenvalue"]
                        self.assertEqual(data["jordan_matrix"], [[lam, 1], [0, lam]])
                        self.assertEqual(data["algebraic_multiplicity"], 2)
                        self.assertLess(data["eigenspace_dimension"], data["algebraic_multiplicity"])
                        self.assertIn("not diagonalizable", item["answer"])
                    elif topic == "bilinear_and_quadratic_forms":
                        a, b = data["matrix"][0]
                        c = data["matrix"][1][1]
                        x, y = data["point"]
                        expected = a * x * x + 2 * b * x * y + c * y * y
                        self.assertEqual(data["value"], expected)
                    elif topic == "multivariable_limits":
                        x0, y0 = data["point"]
                        a, b = data["coefficients"]
                        self.assertEqual(a * (x0 - x0) + b * (y0 - y0) + data["constant"], data["constant"])
                        self.assertEqual(item["answer"], str(data["constant"]))
                    elif topic == "multiple_integrals":
                        left, right, bottom, top = data["rectangle"]
                        expected = (
                            Fraction(right**2 - left**2, 2) * (top - bottom)
                            + Fraction(top**2 - bottom**2, 2) * (right - left)
                        )
                        self.assertEqual(Fraction(data["integral"]), expected)
                        self.assertEqual(Fraction(item["answer"]), expected)
                    elif topic == "change_of_variables":
                        sx, sy = data["scale"]
                        self.assertEqual(data["jacobian"], abs(sx * sy))
                        self.assertEqual(data["transformed_area"], data["source_area"] * abs(sx * sy))
                    elif topic == "line_integrals":
                        a, b = data["vector_field"]
                        x0, y0 = data["start"]
                        x1, y1 = data["end"]
                        self.assertEqual(data["integral"], a * (x1 - x0) + b * (y1 - y0))
                    elif topic == "surface_integrals":
                        xlen, ylen = data["rectangle"]
                        self.assertEqual(data["surface_area"], xlen * ylen)
                        self.assertEqual(data["integral"], xlen * ylen)
                    elif topic == "vector_calculus":
                        a, b, c = data["field_coefficients"]
                        self.assertEqual(data["divergence"], a + b + c)
                    elif topic == "metric_spaces":
                        (x1, y1), (x2, y2) = data["points"]
                        self.assertEqual(data["squared_distance"], (x2 - x1) ** 2 + (y2 - y1) ** 2)
                    elif topic == "convergence_of_sequences":
                        ratio = Fraction(data["common_ratio"])
                        self.assertEqual(data["converges"], abs(ratio) < 1)
                        expected_limit = "0" if abs(ratio) < 1 else "does_not_converge"
                        self.assertEqual(data["limit"], expected_limit)
                    elif topic == "Cauchy_sequences":
                        k = int(data["sequence"].split("/")[0])
                        epsilon = Fraction(data["epsilon"])
                        bound = data["bound_index"]
                        self.assertGreater(bound, k / float(epsilon))
                        self.assertLess(Fraction(k, bound), epsilon)
                    elif topic == "pointwise_and_uniform_convergence":
                        index = data["index"]
                        self.assertEqual(Fraction(data["sup_norm"]), Fraction(1, index))
                        self.assertGreater(index, 0)
                    elif topic in ("compactness", "connectedness"):
                        left, right = data["interval"]
                        self.assertLessEqual(left, right)
                        self.assertIs(data[topic == "compactness" and "compact" or "connected"], True)
                    elif topic == "continuity_metric_spaces":
                        k = data["lipschitz_constant"]
                        x, y = data["points"]
                        self.assertGreaterEqual(k, 0)
                        self.assertEqual(data["distance_bound"], k * abs(x - y))
                    elif topic == "measure_intro":
                        left, right = data["interval"]
                        self.assertEqual(data["Lebesgue_measure"], right - left)
                    else:
                        self.fail(f"Independent validator missing for {topic}")

    def test_tampered_extended_problem_is_rejected(self):
        item = generate(41, 3, "spectral_theorem")
        altered = dict(item)
        altered["answer"] = "incorrect"
        from tools.math_generators.university import verify
        self.assertFalse(verify(altered))


if __name__ == "__main__":
    unittest.main()
