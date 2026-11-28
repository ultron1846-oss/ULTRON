"""Independent exact tests for bounded Stokes and divergence theorem families."""
import unittest
from fractions import Fraction

from tools.math_generators.university import generate, verify


def _fraction(pair):
    return Fraction(pair[0], pair[1])


class VectorCalculusTheoremTests(unittest.TestCase):
    def test_500_stokes_rectangle_boundary_and_curl_surface_integrals(self):
        topic = "stokes_theorem_horizontal_rectangles"
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, topic)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            px, py, pz, qx, qy, qz = [
                _fraction(pair) for pair in data["field_coefficients"]
            ]
            left, right, bottom, top, z0 = data["rectangle_and_height"]
            width = right - left
            height = top - bottom

            # Independently integrate each oriented edge of the counter-clockwise boundary.
            bottom_edge = (
                px * Fraction(right**2 - left**2, 2)
                + (py * bottom + pz * z0) * width
            )
            right_edge = (
                qy * Fraction(top**2 - bottom**2, 2)
                + (qx * right + qz * z0) * height
            )
            top_edge = -(
                px * Fraction(right**2 - left**2, 2)
                + (py * top + pz * z0) * width
            )
            left_edge = -(
                qy * Fraction(top**2 - bottom**2, 2)
                + (qx * left + qz * z0) * height
            )
            boundary = bottom_edge + right_edge + top_edge + left_edge
            curl_surface = (qx - py) * width * height

            self.assertEqual(boundary, curl_surface)
            self.assertEqual(_fraction(data["curl_z"]), qx - py)
            self.assertEqual(Fraction(data["boundary_integral"]), boundary)
            self.assertEqual(Fraction(data["surface_integral"]), curl_surface)
            self.assertEqual(item, generate(seed, difficulty, topic))

    def test_500_divergence_box_outward_flux_equals_volume_integral(self):
        topic = "divergence_theorem_axis_aligned_boxes"
        for seed in range(500):
            difficulty = 1 + seed % 5
            item = generate(seed, difficulty, topic)
            self.assertTrue(verify(item), (seed, item))
            data = item["ingredients"]
            a, b, c = [_fraction(pair) for pair in data["field_coefficients"]]
            x0, x1, y0, y1, z0, z1 = data["box_bounds"]
            dx, dy, dz = x1 - x0, y1 - y0, z1 - z0

            # Recompute outward flux face by face, preserving each face's normal sign.
            x_right = a * x1 * dy * dz
            x_left = -a * x0 * dy * dz
            y_right = b * y1 * dx * dz
            y_left = -b * y0 * dx * dz
            z_right = c * z1 * dx * dy
            z_left = -c * z0 * dx * dy
            face_fluxes = [x_right, x_left, y_right, y_left, z_right, z_left]
            outward_flux = sum(face_fluxes, Fraction(0))
            divergence = a + b + c
            volume_integral = divergence * dx * dy * dz

            self.assertEqual([_fraction(pair) for pair in data["face_fluxes"]], face_fluxes)
            self.assertEqual(_fraction(data["divergence"]), divergence)
            self.assertEqual(outward_flux, volume_integral)
            self.assertEqual(Fraction(data["boundary_flux"]), outward_flux)
            self.assertEqual(Fraction(data["volume_integral"]), volume_integral)
            self.assertEqual(item, generate(seed, difficulty, topic))

    def test_both_theorem_verifiers_reject_tampered_or_malformed_items(self):
        for topic in (
            "stokes_theorem_horizontal_rectangles",
            "divergence_theorem_axis_aligned_boxes",
        ):
            with self.subTest(topic=topic):
                item = generate(73, 4, topic)
                altered = dict(item)
                altered["answer"] += "; tampered"
                self.assertFalse(verify(altered))
                malformed = dict(item)
                malformed["ingredients"] = dict(item["ingredients"])
                if topic == "stokes_theorem_horizontal_rectangles":
                    malformed["ingredients"]["field_coefficients"] = [[1, 0]] * 6
                else:
                    malformed["ingredients"]["box_bounds"] = [0, 0, 0, 1, 0, 1]
                self.assertFalse(verify(malformed))


if __name__ == "__main__":
    unittest.main()
