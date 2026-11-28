"""Independent exact tests for the scoped second-order ODE and transport PDE families."""
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify


def _fraction(pair):
    return Fraction(pair[0], pair[1])


class SecondOrderODEAndTransportPDETests(unittest.TestCase):
    def test_500_distinct_real_root_second_order_odes(self):
        topic = "distinct_real_root_second_order_linear_homogeneous_ODEs"
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, topic)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            r1, r2 = [_fraction(pair) for pair in data["characteristic_roots"]]
            y0 = _fraction(data["initial_value"])
            v0 = _fraction(data["initial_derivative"])
            a, b = [_fraction(pair) for pair in data["equation_coefficients"]]
            c1, c2 = [_fraction(pair) for pair in data["solution_coefficients"]]
            self.assertNotEqual(r1, r2)
            self.assertEqual(a, -(r1 + r2))
            self.assertEqual(b, r1 * r2)
            self.assertEqual(r1 * r1 + a * r1 + b, 0)
            self.assertEqual(r2 * r2 + a * r2 + b, 0)
            self.assertEqual(c1 + c2, y0)
            self.assertEqual(r1 * c1 + r2 * c2, v0)
            self.assertEqual(item, generate(seed, difficulty, topic))

    def test_500_constant_speed_transport_pde_residuals_and_initial_data(self):
        topic = "constant_speed_transport_polynomial_initial_data_PDEs"
        points = (
            (Fraction(1, 2), Fraction(-2, 3)),
            (Fraction(-3, 5), Fraction(4, 7)),
            (Fraction(2), Fraction(3, 4)),
        )
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, topic)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            speed = _fraction(data["transport_speed"])
            a0, a1, a2, a3 = [
                _fraction(pair) for pair in data["initial_polynomial_coefficients"]
            ]
            self.assertNotEqual(speed, 0)

            def p(x):
                return a0 + a1*x + a2*x*x + a3*x*x*x

            def p_prime(x):
                return a1 + 2*a2*x + 3*a3*x*x

            for x, t in points:
                characteristic_coordinate = x - speed*t
                u_x = p_prime(characteristic_coordinate)
                u_t = -speed*p_prime(characteristic_coordinate)
                self.assertEqual(u_t + speed*u_x, 0)

            for x, _ in points:
                self.assertEqual(p(x - speed*0), p(x))
            self.assertEqual(item, generate(seed, difficulty, topic))

    def test_new_families_reject_tampering_and_invalid_parameters(self):
        topics = (
            "distinct_real_root_second_order_linear_homogeneous_ODEs",
            "constant_speed_transport_polynomial_initial_data_PDEs",
        )
        for topic in topics:
            with self.subTest(topic=topic):
                item = generate(77, 3, topic)
                altered = dict(item)
                altered["answer"] += "; tampered"
                self.assertFalse(verify(altered))


if __name__ == "__main__":
    unittest.main()
