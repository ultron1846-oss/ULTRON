import unittest

from ultron_core.data_generation import generate_examples
from ultron_core.problem import Problem, ProblemVerifier, CoreExactVerifier, ReplayGeneratorVerifier
from ultron_core.task_schema import MathTaskRecord
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
        self.assertEqual(Problem.from_dict(problem.to_dict()), problem)
        task = MathTaskRecord.from_verifier(
            problem, CoreExactVerifier(),
            verifier_id="ultron_core.CoreExactVerifier",
            verifier_version="1",
        )
        restored = MathTaskRecord.from_json(task.to_json())
        self.assertEqual(restored.task_id, task.task_id)
        self.assertEqual(restored.verification.verified_fields, ("problem", "answer"))
        self.assertFalse(restored.target_export_eligible)

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
                restored_problem = Problem.from_dict(problem.to_dict())
                self.assertEqual(restored_problem, problem)
                task = MathTaskRecord.from_verifier(
                    problem, verifier, verifier_id=f"{source}.replay", verifier_version="1"
                )
                restored_task = MathTaskRecord.from_json(task.to_json())
                self.assertEqual(restored_task.task_id, task.task_id)
                self.assertEqual(
                    restored_task.verification.verified_fields, ("problem", "answer")
                )
                self.assertFalse(restored_task.target_export_eligible)


if __name__ == "__main__":
    unittest.main()
