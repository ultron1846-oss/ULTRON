"""Independent parameter-to-prompt and exact-answer verification tests."""
import unittest
from ultron_core.data_generation import SUPPORTED_TOPICS, generate_examples
from ultron_core.dataset_math_validation import validate_generated_math_sample


class IndependentDatasetMathValidationTests(unittest.TestCase):
    def test_every_supported_generator_topic_reconstructs_exactly(self):
        for topic_index, topic in enumerate(SUPPORTED_TOPICS):
            examples = generate_examples(seed=8100 + topic_index, count=25, topics=(topic,))
            for example in examples:
                with self.subTest(topic=topic, index=example.index):
                    self.assertTrue(validate_generated_math_sample(example.to_dict()))

    def test_parameter_tampering_is_rejected_even_when_identity_is_not_considered(self):
        example = generate_examples(8123, 1, topics=("arithmetic",))[0]
        row = example.to_dict()
        changed_parameter = dict(row)
        changed_parameter["generation_parameters"] = dict(row["generation_parameters"])
        changed_parameter["generation_parameters"]["a"] += 1
        self.assertFalse(validate_generated_math_sample(changed_parameter))
        self.assertFalse(validate_generated_math_sample(dict(row, input_text=row["input_text"] + " + 0")))
        changed_answer = dict(row, target_text=str(int(row["target_text"]) + 1))
        changed_answer["exact_answer"] = changed_answer["target_text"]
        self.assertFalse(validate_generated_math_sample(changed_answer))
        self.assertFalse(validate_generated_math_sample(dict(row, difficulty=row["difficulty"] + 1)))

    def test_arithmetic_recheck_accepts_valid_values_outside_sampler_range(self):
        example = generate_examples(8125, 1, topics=("arithmetic",))[0]
        row = example.to_dict()
        row["generation_parameters"] = {"a": 90, "operator": "+", "b": 2}
        row["input_text"] = "90 + 2"
        row["target_text"] = "92"
        row["exact_answer"] = "92"
        row["difficulty"] = 2
        self.assertTrue(validate_generated_math_sample(row))

    def test_unknown_or_ambiguous_parameter_schema_fails_closed(self):
        example = generate_examples(8124, 1, topics=("matrix_determinant_2x2",))[0]
        row = example.to_dict()
        parameters = dict(row["generation_parameters"])
        parameters["unexpected"] = 1
        row["generation_parameters"] = parameters
        self.assertFalse(validate_generated_math_sample(row))


if __name__ == "__main__":
    unittest.main()
