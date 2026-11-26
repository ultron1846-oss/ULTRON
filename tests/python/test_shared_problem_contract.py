import unittest

from ultron_core.data_generation import generate_examples
from ultron_core.problem import Problem, ProblemVerifier, CoreExactVerifier, ReplayGeneratorVerifier
from tools.math_generators.grade1_4 import generators as g14
from tools.math_generators.grade5_8 import generators as g58
from tools.math_generators.grade8_12 import generators as g812
from tools.math_generators.university import generators as gu


class SharedProblemContractTests(unittest.TestCase):
    def test_core_adapts_to_shared_problem_and_exact_verifier(self):
        example = generate_examples(seed=91, count=1)[0]
        problem = example.to_problem()
        self.assertIsInstance(problem, Problem)
        self.assertEqual(problem.source, "ultron_core.data_generation")
        self.assertTrue(CoreExactVerifier().verify(problem))
        self.assertEqual(problem.problem_id, example.to_problem().problem_id)

    def test_grade_and_university_records_share_problem_and_verifier_interface(self):
        cases = [
            (g14, "addition", "grade1_4"),
            (g58, "ratios", "grade5_8"),
            (g812, "quadratic_equations", "grade8_12"),
            (gu, "sets_and_functions", "university"),
        ]
        for module, topic, source in cases:
            with self.subTest(source=source):
                record = module.generate(31, 2, topic)
                problem = Problem.from_generator(record, source=source)
                verifier = ReplayGeneratorVerifier(record, module.verify, source=source)
                self.assertIsInstance(verifier, ProblemVerifier)
                self.assertTrue(verifier.verify(problem))
                self.assertEqual(problem.problem_id, Problem.from_generator(record, source=source).problem_id)


if __name__ == "__main__":
    unittest.main()
