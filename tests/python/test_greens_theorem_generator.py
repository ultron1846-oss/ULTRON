"""Independent mathematical and contract tests for bounded Green's theorem."""
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify
from tools.math_generators.university.green_theorem import (
    GreenTheoremInputError,
    MAX_DEGREE,
    MAX_TERMS_PER_COMPONENT,
    calculate_green_integrals,
    compute_area_integral,
    compute_boundary_integral,
)


def _f(pair):
    return Fraction(pair[0], pair[1])


def _independent_boundary(data):
    """Reference rectangle-edge calculation, separate from production helpers."""
    x0, x1 = map(_f, data["x_bounds"])
    y0, y1 = map(_f, data["y_bounds"])

    def integrate_x(terms, fixed_y, start, end):
        result = Fraction(0)
        for term in terms:
            coefficient = _f(term["coefficient"])
            power = term["x_power"]
            result += coefficient * fixed_y ** term["y_power"] * (
                end ** (power + 1) - start ** (power + 1)
            ) / (power + 1)
        return result

    def integrate_y(terms, fixed_x, start, end):
        result = Fraction(0)
        for term in terms:
            coefficient = _f(term["coefficient"])
            power = term["y_power"]
            result += coefficient * fixed_x ** term["x_power"] * (
                end ** (power + 1) - start ** (power + 1)
            ) / (power + 1)
        return result

    total = (
        integrate_x(data["P"], y0, x0, x1)
        + integrate_y(data["Q"], x1, y0, y1)
        + integrate_x(data["P"], y1, x1, x0)
        + integrate_y(data["Q"], x0, y1, y0)
    )
    return total if data["orientation"] == "counterclockwise" else -total


def _independent_area(data):
    """Independently differentiate sparse terms and integrate separated powers."""
    x0, x1 = map(_f, data["x_bounds"])
    y0, y1 = map(_f, data["y_bounds"])

    def monomial_integral(power, lower, upper):
        return (upper ** (power + 1) - lower ** (power + 1)) / (power + 1)

    total = Fraction(0)
    for term in data["Q"]:
        coefficient = _f(term["coefficient"])
        if term["x_power"]:
            total += (
                coefficient * term["x_power"]
                * monomial_integral(term["x_power"] - 1, x0, x1)
                * monomial_integral(term["y_power"], y0, y1)
            )
    for term in data["P"]:
        coefficient = _f(term["coefficient"])
        if term["y_power"]:
            total -= (
                coefficient * term["y_power"]
                * monomial_integral(term["x_power"], x0, x1)
                * monomial_integral(term["y_power"] - 1, y0, y1)
            )
    return total if data["orientation"] == "counterclockwise" else -total


def _problem_for(orientation="counterclockwise"):
    return {
        "topic": "greens_theorem_rectangles",
        "P": [{"coefficient": [2, 3], "x_power": 1, "y_power": 1}],
        "Q": [{"coefficient": [3, 4], "x_power": 2, "y_power": 2}],
        "x_bounds": [[-1, 2], [5, 3]],
        "y_bounds": [[1, 3], [7, 2]],
        "orientation": orientation,
    }


class GreenTheoremGeneratorTests(unittest.TestCase):
    def test_seeded_determinism_and_independent_integrals(self):
        orientations = set()
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, "greens_theorem_rectangles")
            self.assertEqual(item, generate(seed, difficulty, "greens_theorem_rectangles"))
            self.assertTrue(verify(item), (seed, difficulty))
            data = item["ingredients"]
            orientations.add(data["orientation"])
            self.assertEqual(compute_boundary_integral(data), _independent_boundary(data))
            self.assertEqual(compute_area_integral(data), _independent_area(data))
            self.assertEqual(_independent_boundary(data), _independent_area(data))
            for component in ("P", "Q"):
                self.assertLessEqual(len(data[component]), MAX_TERMS_PER_COMPONENT)
                self.assertTrue(all(term["x_power"] + term["y_power"] <= difficulty for term in data[component]))
        self.assertEqual(orientations, {"counterclockwise", "clockwise"})

    def test_clockwise_is_exact_sign_reverse_of_counterclockwise(self):
        ccw = _problem_for("counterclockwise")
        cw = _problem_for("clockwise")
        ccw_boundary, ccw_area = calculate_green_integrals(ccw)
        cw_boundary, cw_area = calculate_green_integrals(cw)
        self.assertEqual(cw_boundary, -ccw_boundary)
        self.assertEqual(cw_area, -ccw_area)

    def test_independent_hand_computable_field_and_gradient_invariant(self):
        field = {
            "topic": "greens_theorem_rectangles",
            "P": [],
            "Q": [{"coefficient": [1, 1], "x_power": 1, "y_power": 0}],
            "x_bounds": [[0, 1], [2, 1]],
            "y_bounds": [[0, 1], [3, 1]],
            "orientation": "counterclockwise",
        }
        self.assertEqual(calculate_green_integrals(field), (Fraction(6), Fraction(6)))

        # F = grad(x^2*y): its curl and circulation around a closed rectangle are zero.
        gradient = {
            "topic": "greens_theorem_rectangles",
            "P": [{"coefficient": [2, 1], "x_power": 1, "y_power": 1}],
            "Q": [{"coefficient": [1, 1], "x_power": 2, "y_power": 0}],
            "x_bounds": [[-2, 1], [3, 1]],
            "y_bounds": [[-1, 1], [4, 1]],
            "orientation": "counterclockwise",
        }
        self.assertEqual(calculate_green_integrals(gradient), (Fraction(0), Fraction(0)))

    def test_tampered_answers_and_ingredients_are_rejected(self):
        item = generate(71, 4, "greens_theorem_rectangles")
        altered_answer = dict(item)
        altered_answer["answer"] = "boundary=0; area=0"
        self.assertFalse(verify(altered_answer))
        altered_ingredients = dict(item)
        altered_ingredients["ingredients"] = dict(item["ingredients"])
        altered_ingredients["ingredients"]["orientation"] = (
            "clockwise" if item["ingredients"]["orientation"] == "counterclockwise" else "counterclockwise"
        )
        self.assertFalse(verify(altered_ingredients))
        altered_field = dict(item)
        altered_field["ingredients"] = dict(item["ingredients"])
        altered_field["ingredients"]["Q"] = []
        self.assertFalse(verify(altered_field))

        over_difficulty = dict(item)
        over_difficulty["ingredients"] = dict(item["ingredients"])
        over_difficulty["ingredients"]["P"] = [
            {"coefficient": [1, 1], "x_power": 5, "y_power": 0}
        ]
        over_difficulty["ingredients"]["Q"] = []
        over_difficulty["answer"] = "boundary=0; area=0"
        self.assertFalse(verify(over_difficulty))

    def test_rejects_malformed_polynomial_and_rectangle_inputs(self):
        invalid = [
            ({"coefficient": [1, 1], "x_power": True, "y_power": 0}, "bool power"),
            ({"coefficient": [1.5, 1], "x_power": 0, "y_power": 0}, "float coefficient"),
            ({"coefficient": [1, 0], "x_power": 0, "y_power": 0}, "zero denominator"),
            ({"coefficient": [1, -2], "x_power": 0, "y_power": 0}, "negative denominator"),
            ({"coefficient": [0, 1], "x_power": 0, "y_power": 0}, "zero coefficient"),
            ({"coefficient": [1, 1], "x_power": -1, "y_power": 0}, "negative power"),
            ({"coefficient": [1, 1], "x_power": MAX_DEGREE + 1, "y_power": 0}, "degree"),
            ({"coefficient": [1, 1], "x_power": 0, "y_power": 0, "extra": 1}, "extra key"),
            ({"coefficient": [1001, 1], "x_power": 0, "y_power": 0}, "coefficient numerator budget"),
            ({"coefficient": [1, 101], "x_power": 0, "y_power": 0}, "coefficient denominator budget"),
        ]
        for term, label in invalid:
            with self.subTest(label=label):
                data = _problem_for()
                data["P"] = [term]
                with self.assertRaises(GreenTheoremInputError):
                    calculate_green_integrals(data)

        duplicate = _problem_for()
        duplicate["P"] = [duplicate["P"][0], dict(duplicate["P"][0])]
        with self.assertRaisesRegex(GreenTheoremInputError, "duplicate"):
            calculate_green_integrals(duplicate)

        too_many = _problem_for()
        too_many["P"] = [
            {"coefficient": [index + 1, 1], "x_power": index, "y_power": 0}
            for index in range(MAX_TERMS_PER_COMPONENT + 1)
        ]
        with self.assertRaises(GreenTheoremInputError):
            calculate_green_integrals(too_many)

        combined_too_many = _problem_for()
        p_powers = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (0, 1), (0, 2)]
        q_powers = [(0, 0), (1, 0), (2, 0), (3, 0), (0, 1)]
        combined_too_many["P"] = [
            {"coefficient": [index + 1, 1], "x_power": x, "y_power": y}
            for index, (x, y) in enumerate(p_powers)
        ]
        combined_too_many["Q"] = [
            {"coefficient": [index + 1, 1], "x_power": x, "y_power": y}
            for index, (x, y) in enumerate(q_powers)
        ]
        with self.assertRaisesRegex(GreenTheoremInputError, "combined polynomial term count"):
            calculate_green_integrals(combined_too_many)

        operation_budget = _problem_for()
        operation_budget["P"] = [
            {"coefficient": [index + 1, 1], "x_power": x, "y_power": y}
            for index, (x, y) in enumerate(
                [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (0, 1), (1, 1)]
            )
        ]
        operation_budget["Q"] = [
            {"coefficient": [index + 1, 1], "x_power": 0, "y_power": y}
            for index, y in enumerate((0, 1, 2))
        ]
        with self.assertRaisesRegex(GreenTheoremInputError, "operation budget"):
            calculate_green_integrals(operation_budget)

        for mutation in (
            lambda value: value.update(x_bounds=[[1, 1], [1, 1]]),
            lambda value: value.update(y_bounds=[[2, 1], [1, 1]]),
            lambda value: value.update(x_bounds=[[101, 1], [102, 1]]),
            lambda value: value.update(x_bounds=[[1, 21], [2, 1]]),
            lambda value: value.update(x_bounds=[[0, 0], [1, 1]]),
            lambda value: value.update(orientation="diagonal"),
            lambda value: value.update(unsupported="sin(x)"),
        ):
            data = _problem_for()
            mutation(data)
            with self.assertRaises(GreenTheoremInputError):
                calculate_green_integrals(data)

    def test_generator_rejects_invalid_seed_difficulty_and_topic(self):
        with self.assertRaises(TypeError):
            generate(True, 1, "greens_theorem_rectangles")
        with self.assertRaises(ValueError):
            generate(0, 0, "greens_theorem_rectangles")
        with self.assertRaises(ValueError):
            generate(0, True, "greens_theorem_rectangles")
        with self.assertRaises(ValueError):
            generate(0, 6, "greens_theorem_rectangles")
        with self.assertRaises(ValueError):
            generate(0, 1, "stokes_theorem")

    def test_fractional_rectangle_and_zero_field_boundary_cases(self):
        zero = {
            "topic": "greens_theorem_rectangles",
            "P": [],
            "Q": [],
            "x_bounds": [[-5, 4], [7, 3]],
            "y_bounds": [[-2, 5], [11, 7]],
            "orientation": "clockwise",
        }
        self.assertEqual(calculate_green_integrals(zero), (Fraction(0), Fraction(0)))


if __name__ == "__main__":
    unittest.main()
