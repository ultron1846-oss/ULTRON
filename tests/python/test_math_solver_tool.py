import unittest
from fractions import Fraction

from ultron_core.agent_tools import execute_tool, get_tool_specs
from ultron_core.math_solver_tool import run_math_solver, solve_linear


class MathSolverToolTests(unittest.TestCase):
    def test_exact_evaluation(self):
        result = run_math_solver({"operation": "evaluate", "expression": "1/3 + 1/6"})
        self.assertEqual(result["value"], "1/2")
        self.assertTrue(result["exact"])

    def test_evaluation_with_exact_variable_binding(self):
        result = run_math_solver({
            "operation": "evaluate",
            "expression": "2x + 1",
            "variables": {"x": "3/2"},
        })
        self.assertEqual(result["value"], "4")

    def test_symbolic_simplification(self):
        result = run_math_solver({"operation": "simplify", "expression": "x + 0"})
        self.assertEqual(result["expression"], "x")

    def test_linear_equation_solution(self):
        result = solve_linear("2x + 3 = 7")
        self.assertEqual(result["status"], "solved")
        self.assertEqual(result["value"], "2")
        self.assertEqual(result["variable"], "x")

    def test_linear_equation_fraction_solution(self):
        result = solve_linear("3x = 1")
        self.assertEqual(result["value"], "1/3")

    def test_identity_and_no_solution(self):
        self.assertEqual(solve_linear("x = x")["status"], "identity")
        self.assertEqual(solve_linear("x + 1 = x")["status"], "no_solution")

    def test_rejects_nonlinear_equations(self):
        with self.assertRaisesRegex(ValueError, "nonlinear"):
            solve_linear("x^2 = 4")

    def test_rejects_unknown_functions_for_exact_evaluation(self):
        with self.assertRaisesRegex(ValueError, "exact evaluator"):
            run_math_solver({"operation": "evaluate", "expression": "sqrt(4)"})

    def test_rejects_extra_arguments(self):
        with self.assertRaisesRegex(ValueError, "unknown argument"):
            run_math_solver({"operation": "simplify", "expression": "x", "shell": "no"})

    def test_agent_registry_is_allow_listed(self):
        self.assertEqual(get_tool_specs()[0]["name"], "math_solver")
        self.assertEqual(execute_tool("math_solver", {"operation": "solve", "expression": "x + 2 = 5"})["value"], "3")
        with self.assertRaisesRegex(ValueError, "unknown or unavailable"):
            execute_tool("shell", {})


if __name__ == "__main__":
    unittest.main()
