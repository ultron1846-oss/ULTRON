"""Independent exact checks for a bounded variable-coefficient linear ODE family."""
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify
from tools.math_generators.university.ode_variable_coefficient import TOPIC


def _read(pair):
    return Fraction(pair[0], pair[1])


class VariableCoefficientFirstOrderODETests(unittest.TestCase):
    def test_500_seeded_log_derivative_and_initial_value(self):
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, TOPIC)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            coefficient = _read(data["coefficient"])
            initial_point = _read(data["initial_point"])
            initial_value = _read(data["initial_value"])
            exponent_coefficient = _read(data["exponent_coefficient"])
            power = data["coefficient_power"]
            self.assertIn(power, range(1, min(2, difficulty) + 1))
            self.assertNotEqual(coefficient, 0)
            self.assertGreater(initial_value, 0)
            # The derivative of C*(x^(m+1)-x0^(m+1)) has coefficient -a*x^m.
            self.assertEqual(exponent_coefficient * (power + 1), -coefficient)
            exponent_at_initial_point = exponent_coefficient * (
                initial_point ** (power + 1) - initial_point ** (power + 1)
            )
            self.assertEqual(exponent_at_initial_point, 0)
            self.assertEqual(item, generate(seed, difficulty, TOPIC))

    def test_tampered_solution_and_invalid_parameter_are_rejected(self):
        item = generate(71, 4, TOPIC)
        altered = dict(item)
        altered["answer"] = "y(x)=0"
        self.assertFalse(verify(altered))
        malformed = dict(item)
        malformed["ingredients"] = dict(item["ingredients"])
        malformed["ingredients"]["coefficient"] = [0, 1]
        self.assertFalse(verify(malformed))


if __name__ == "__main__":
    unittest.main()
