import json
import unittest
from pathlib import Path

from ultron_core.curriculum_prerequisites import (
    load_curriculum_prerequisites,
    validate_prerequisite_data,
)


CURRICULUM_PATH = Path("tools/math_generators/university/curriculum.json")
PREREQUISITES_PATH = Path("tools/math_generators/university/prerequisites.json")


class UniversityPrerequisiteTests(unittest.TestCase):
    def test_curated_map_covers_all_declared_curriculum_fields(self):
        curriculum = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
        data = json.loads(PREREQUISITES_PATH.read_text(encoding="utf-8"))
        mapping = load_curriculum_prerequisites()

        expected = {
            item["topic"] for item in curriculum["topics"]
            if item["field"] in data["coverage_fields"]
        }
        self.assertEqual(set(mapping.prerequisites), expected)
        self.assertEqual(mapping.mapped_topic_count, 218)
        self.assertEqual(mapping.source_topic_count, 218)
        self.assertEqual(mapping.source_topic_count - mapping.mapped_topic_count, 0)

    def test_prerequisite_edges_are_ordered_and_queryable(self):
        mapping = load_curriculum_prerequisites()
        self.assertTrue(mapping.is_prerequisite("eigenvalues_and_eigenvectors", "spectral_theorem"))
        self.assertTrue(mapping.is_prerequisite("inner_product_spaces", "spectral_theorem"))
        self.assertFalse(mapping.is_prerequisite("sets_and_functions", "spectral_theorem"))
        positions = {topic: index for index, topic in enumerate(mapping.topological_order)}
        for topic, parents in mapping.prerequisites.items():
            for parent in parents:
                self.assertLess(positions[parent], positions[topic])


    def test_calculus_and_real_analysis_edges_are_present(self):
        mapping = load_curriculum_prerequisites()
        self.assertTrue(mapping.is_prerequisite("greens_theorem_rectangles", "stokes_theorem"))
        self.assertTrue(mapping.is_prerequisite("vector_calculus", "greens_theorem_rectangles"))
        self.assertTrue(mapping.is_prerequisite("surface_integrals", "divergence_theorem"))
        self.assertTrue(mapping.is_prerequisite("stokes_theorem", "stokes_theorem_horizontal_rectangles"))
        self.assertTrue(mapping.is_prerequisite("greens_theorem_rectangles", "stokes_theorem_horizontal_rectangles"))
        self.assertTrue(mapping.is_prerequisite("divergence_theorem", "divergence_theorem_axis_aligned_boxes"))
        self.assertTrue(mapping.is_prerequisite("diagonal_linear_vector_field_divergence", "divergence_theorem_axis_aligned_boxes"))
        self.assertNotIn("Green_stokes_divergence_theorems", mapping.prerequisites)
        self.assertTrue(mapping.is_prerequisite("power_series", "Taylor_series"))
        self.assertTrue(mapping.is_prerequisite("derivative_theory", "Taylor_series"))
        self.assertTrue(mapping.is_prerequisite("Cauchy_sequences", "pointwise_and_uniform_convergence"))
        self.assertTrue(mapping.is_prerequisite("Lebesgue_measure", "Lebesgue_integral"))
        self.assertTrue(mapping.is_prerequisite("multiple_integrals", "rectangular_linear_polynomial_double_integrals"))
        self.assertTrue(mapping.is_prerequisite("multiple_integrals", "diagonal_linear_change_of_variables_rectangles"))
        self.assertTrue(mapping.is_prerequisite("Riemann_integral", "flat_rectangular_surface_area_integrals"))
        self.assertTrue(mapping.is_prerequisite("partial_derivatives", "diagonal_linear_vector_field_divergence"))
        self.assertTrue(mapping.is_prerequisite("vectors_and_vector_spaces", "constant_vector_field_segment_line_integrals"))
        self.assertTrue(mapping.is_prerequisite("derivative_theory", "quadratic_Taylor_polynomials"))


    def test_complex_algebra_and_number_theory_edges_are_present(self):
        mapping = load_curriculum_prerequisites()
        self.assertTrue(mapping.is_prerequisite("Laurent_series", "residues"))
        self.assertTrue(mapping.is_prerequisite("complex_number_arithmetic", "holomorphic_functions"))
        self.assertTrue(mapping.is_prerequisite("complex_topology", "holomorphic_functions"))
        self.assertTrue(mapping.is_prerequisite("Cauchy_integral_formula", "complex_Taylor_series"))
        self.assertTrue(mapping.is_prerequisite("Cauchy_integral_formula", "Laurent_series"))
        self.assertTrue(mapping.is_prerequisite("groups_and_subgroups", "cyclic_groups"))
        self.assertTrue(mapping.is_prerequisite("fields_and_extensions", "Galois_theory_intro"))
        self.assertTrue(mapping.is_prerequisite("congruences", "Chinese_remainder_theorem"))


    def test_topology_discrete_probability_and_statistics_edges(self):
        mapping = load_curriculum_prerequisites()
        self.assertTrue(mapping.is_prerequisite("fundamental_group_intro", "covering_spaces_intro"))
        self.assertTrue(mapping.is_prerequisite("mathematical_induction", "recurrence_relations"))
        self.assertTrue(mapping.is_prerequisite("law_of_large_numbers", "central_limit_theorem"))
        self.assertTrue(mapping.is_prerequisite("Bayes_theorem", "Bayesian_statistics_intro"))
        self.assertTrue(mapping.is_prerequisite("expectation_and_variance", "finite_discrete_distribution_expectation_variance"))
        self.assertTrue(mapping.is_prerequisite("probability_spaces", "finite_discrete_distribution_expectation_variance"))
        self.assertTrue(mapping.is_prerequisite("discrete_distributions", "binomial_distribution_point_probabilities"))
        self.assertTrue(mapping.is_prerequisite("probability_spaces", "binomial_distribution_point_probabilities"))
        self.assertTrue(mapping.is_prerequisite("counting_principles", "binomial_distribution_point_probabilities"))


    def test_ode_optimization_and_numerical_edges(self):
        mapping = load_curriculum_prerequisites()
        self.assertTrue(mapping.is_prerequisite("homogeneous_constant_coefficient_first_order_ODEs", "Laplace_transforms_applications"))
        self.assertTrue(mapping.is_prerequisite("homogeneous_constant_coefficient_first_order_ODEs", "homogeneous_variable_coefficient_linear_first_order_ODEs"))
        self.assertTrue(mapping.is_prerequisite("Riemann_integral", "homogeneous_variable_coefficient_linear_first_order_ODEs"))
        self.assertTrue(mapping.is_prerequisite("linear_first_order_variable_coefficient_ODEs", "second_order_linear_ODEs"))
        self.assertTrue(mapping.is_prerequisite("separable_first_order_ODEs", "ODE_numerical_methods"))
        self.assertTrue(mapping.is_prerequisite("partial_derivatives", "exact_first_order_ODEs"))
        self.assertTrue(mapping.is_prerequisite("exact_first_order_ODEs", "quadratic_potential_exact_first_order_ODEs"))
        self.assertTrue(mapping.is_prerequisite("partial_derivatives", "quadratic_potential_exact_first_order_ODEs"))
        self.assertNotIn("first_order_ODEs", mapping.prerequisites)
        self.assertTrue(mapping.is_prerequisite("Lagrange_multipliers", "KKT_conditions"))
        self.assertTrue(mapping.is_prerequisite("root_finding", "Newton_and_secant_methods"))
        self.assertTrue(mapping.is_prerequisite("numerical_integration", "ODE_numerical_methods"))
        self.assertTrue(mapping.is_prerequisite("probability_spaces", "Monte_Carlo_methods"))
        self.assertTrue(mapping.is_prerequisite("second_order_linear_ODEs", "distinct_real_root_second_order_linear_homogeneous_ODEs"))
        self.assertTrue(mapping.is_prerequisite("homogeneous_constant_coefficient_first_order_ODEs", "distinct_real_root_second_order_linear_homogeneous_ODEs"))
        self.assertTrue(mapping.is_prerequisite("characteristics_PDE", "constant_speed_transport_polynomial_initial_data_PDEs"))
        self.assertTrue(mapping.is_prerequisite("partial_derivatives", "constant_speed_transport_polynomial_initial_data_PDEs"))

    def test_unknown_topic_does_not_get_inferred_prerequisites(self):
        mapping = load_curriculum_prerequisites()
        with self.assertRaisesRegex(ValueError, "no curated prerequisite mapping"):
            mapping.prerequisites_for("not_a_curriculum_topic")

    def test_geometry_applied_and_advanced_edges(self):
        mapping = load_curriculum_prerequisites()
        self.assertTrue(mapping.is_prerequisite("topological_spaces", "manifolds_intro"))
        self.assertTrue(mapping.is_prerequisite("sequences_and_series", "Fourier_series_and_transforms"))
        self.assertTrue(mapping.is_prerequisite("systems_of_ODEs", "control_theory_intro"))
        self.assertTrue(mapping.is_prerequisite("Lp_spaces", "functional_analysis_intro"))
        self.assertTrue(mapping.is_prerequisite("proof_methods", "mathematical_logic_advanced"))

    def test_validator_rejects_cycles(self):
        curriculum = {"topics": [{"topic": "a", "field": "F"}, {"topic": "b", "field": "F"}]}
        data = {
            "schema_version": 1,
            "source_topic_count": 2,
            "mapped_topic_count": 2,
            "coverage_fields": ["F"],
            "prerequisites": {"a": ["b"], "b": ["a"]},
        }
        with self.assertRaisesRegex(ValueError, "contains a cycle"):
            validate_prerequisite_data(data, curriculum)

    def test_validator_rejects_unknown_prerequisite(self):
        curriculum = {"topics": [{"topic": "a", "field": "F"}]}
        data = {
            "schema_version": 1,
            "source_topic_count": 1,
            "mapped_topic_count": 1,
            "coverage_fields": ["F"],
            "prerequisites": {"a": ["missing"]},
        }
        with self.assertRaisesRegex(ValueError, "unmapped topic"):
            validate_prerequisite_data(data, curriculum)


if __name__ == "__main__":
    unittest.main()
