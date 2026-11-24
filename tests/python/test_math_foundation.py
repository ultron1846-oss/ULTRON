import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from ultron_core.data_generation import (
    GENERATOR_VERSION, generate_examples, validate_example_text, write_dataset,
)
from ultron_core.math_tokenizer import MathTokenizer, MathVocabulary


class MathTokenizerTests(unittest.TestCase):
    def setUp(self):
        self.vocabulary = MathVocabulary.default()
        self.tokenizer = MathTokenizer(self.vocabulary)

    def test_default_vocabulary_has_stable_reserved_ids(self):
        self.assertEqual(self.vocabulary.token_id("<PAD>"), 0)
        self.assertEqual(self.vocabulary.token_id("<BOS>"), 1)
        self.assertEqual(self.vocabulary.token_id("<EOS>"), 2)
        self.assertEqual(len(self.vocabulary), len(set(self.vocabulary.tokens)))

    def test_lossless_round_trip_for_supported_notation(self):
        samples = (
            "2x + 3 = 7", "x <= 4", "-3/5 * (x_1 + 2)",
            r"\frac{1}{2} + \alpha", "∑_{i=1}^{n} i^2",
            "∂f/∂x", "∀x ∈ ℝ", "A × B ≠ C", "x⁽²⁾ + y₁",
        )
        for source in samples:
            with self.subTest(source=source):
                self.assertEqual(self.tokenizer.decode(self.tokenizer.encode(source)), source)

    def test_whitespace_is_preserved_not_silently_normalized(self):
        source = "x +\n\t y"
        self.assertEqual(self.tokenizer.decode(self.tokenizer.encode(source)), source)

    def test_implicit_and_explicit_multiplication_remain_distinct(self):
        implicit = self.tokenizer.encode("2x")
        explicit = self.tokenizer.encode("2*x")
        unicode = self.tokenizer.encode("2 × x")
        self.assertNotEqual(implicit, explicit)
        self.assertNotEqual(explicit, unicode)

    def test_unary_minus_and_subtraction_keep_source_tokens(self):
        self.assertNotEqual(self.tokenizer.encode("-x"), self.tokenizer.encode("x-y"))
        self.assertEqual(self.tokenizer.decode(self.tokenizer.encode("-x")), "-x")

    def test_unknown_characters_fail_with_offset(self):
        with self.assertRaisesRegex(ValueError, "offset 1"):
            self.tokenizer.encode("x🙂")

    def test_non_string_input_rejected(self):
        with self.assertRaises(TypeError):
            self.tokenizer.encode(123)

    def test_special_tokens_are_optional_and_decoding_is_safe(self):
        ids = self.tokenizer.encode("x", add_bos=True, add_eos=True)
        self.assertEqual(self.tokenizer.decode(ids), "x")
        self.assertEqual(self.tokenizer.decode(ids, skip_special_tokens=False), "<BOS>x<EOS>")
        with self.assertRaises(ValueError):
            self.tokenizer.decode([len(self.vocabulary)])
        with self.assertRaises(TypeError):
            self.tokenizer.decode([True])

    def test_vocabulary_serialization_is_deterministic(self):
        encoded = self.vocabulary.to_json()
        restored = MathVocabulary.from_json(encoded)
        self.assertEqual(restored.to_json(), encoded)
        self.assertEqual(self.tokenizer.encode(r"\alpha+x"),
                         MathTokenizer(restored).encode(r"\alpha+x"))

    def test_vocabulary_rejects_duplicate_or_reordered_reserved_tokens(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            MathVocabulary(("<PAD>", "<BOS>", "<EOS>", "x", "x"))
        with self.assertRaisesRegex(ValueError, "reserved"):
            MathVocabulary(("<BOS>", "<PAD>", "<EOS>", "x"))

    def test_vocabulary_rejects_unknown_schema(self):
        with self.assertRaisesRegex(ValueError, "version"):
            MathVocabulary(version=2)


class DeterministicDataGenerationTests(unittest.TestCase):
    def test_same_seed_and_configuration_produce_identical_examples(self):
        first = generate_examples(712, 50)
        second = generate_examples(712, 50)
        self.assertEqual(first, second)

    def test_different_seeds_change_the_generated_corpus(self):
        self.assertNotEqual(generate_examples(1, 20), generate_examples(2, 20))

    def test_example_ids_are_stable_and_unique_within_corpus(self):
        examples = generate_examples(91, 100)
        identifiers = [item.example_id for item in examples]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertTrue(all(len(item) == 64 for item in identifiers))

    def test_examples_include_provenance_and_validation(self):
        for example in generate_examples(17, 30):
            self.assertEqual(example.generator_version, GENERATOR_VERSION)
            self.assertEqual(example.validation_status, "semantically_checked")
            self.assertTrue(example.provenance)
            self.assertEqual(example.target_text, example.exact_answer)
            self.assertTrue(validate_example_text(example.input_text, example.target_text, example.topic))

    def test_validator_rejects_wrong_answers_and_malformed_text(self):
        self.assertFalse(validate_example_text("2 + 2", "5", "arithmetic"))
        self.assertFalse(validate_example_text("__import__('os')", "0", "arithmetic"))
        self.assertFalse(validate_example_text("1*x + 2 = 3", "0", "linear_equations"))

    def test_exact_rational_arithmetic(self):
        self.assertTrue(validate_example_text("1/3 + 1/6", "1/2", "rational_arithmetic"))
        self.assertFalse(validate_example_text("1/3 / 0", "0", "rational_arithmetic"))

    def test_linear_equation_validator_uses_exact_solution(self):
        self.assertTrue(validate_example_text("3*x - 2 = 7", "3", "linear_equations"))
        self.assertFalse(validate_example_text("3*x - 2 = 7", "4", "linear_equations"))

    def test_topic_and_count_validation(self):
        with self.assertRaises(ValueError):
            generate_examples(1, 0)
        with self.assertRaises(ValueError):
            generate_examples(1, 1, topics=("calculus",))
        with self.assertRaises(TypeError):
            generate_examples(True, 1)

    def test_jsonl_and_manifest_are_reproducible_and_checksummed(self):
        examples = generate_examples(101, 12)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.jsonl"
            manifest = write_dataset(path, examples, seed=101, topics=("arithmetic", "rational_arithmetic", "linear_equations"))
            content = path.read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), manifest["sha256"])
            self.assertEqual(manifest["example_count"], 12)
            self.assertEqual(sum(manifest["topic_counts"].values()), 12)
            rows = [json.loads(line) for line in content.decode("utf-8").splitlines()]
            self.assertEqual(len(rows), 12)
            path2 = Path(directory) / "fixture-copy.jsonl"
            manifest2 = write_dataset(path2, examples, seed=101, topics=("arithmetic", "rational_arithmetic", "linear_equations"))
            self.assertEqual(path.read_bytes(), path2.read_bytes())
            self.assertEqual(manifest, manifest2)


if __name__ == "__main__":
    unittest.main()
