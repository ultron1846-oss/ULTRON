import hashlib
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from fractions import Fraction

import torch
from ultron_core import NeuroSparseConfig, NeuroSparseModel
from ultron_core.math_ir import Expr, ExprKind
from ultron_core.verification import evaluate
from ultron_core.data_generation import (
    GENERATOR_VERSION, SUPPORTED_TOPICS, generate_examples, split_examples, summarize_corpus, validate_example_text, verify_dataset, write_dataset,
)
from ultron_core.math_tokenizer import MathTokenizer, MathVocabulary
from ultron_core.math_parser import MathParseError, MathParser, parse_math
from ultron_core.symbolic import simplify
from ultron_core.preflight import preflight_training_plan


class ResumableRandomSamplerTests(unittest.TestCase):
    def test_resume_cursor_replays_same_epoch_permutation_tail(self):
        from ultron_core.resumable_sampler import ResumableRandomSampler
        dataset = list(range(37))
        kwargs = {"seed": 1846, "dataset_manifest_sha256": "a" * 64}
        uninterrupted = ResumableRandomSampler(dataset, **kwargs)
        expected = list(iter(uninterrupted))
        partial = ResumableRandomSampler(dataset, **kwargs)
        # Consume a deterministic prefix using one iterator.
        iterator = iter(partial)
        prefix = [next(iterator) for _ in range(11)]
        state = partial.state_dict()
        restored = ResumableRandomSampler(dataset, **kwargs)
        restored.load_state_dict(state)
        self.assertEqual(prefix + list(restored), expected)
        self.assertEqual(len(set(expected)), len(dataset))

    def test_epoch_changes_permutation_and_state_round_trips(self):
        from ultron_core.resumable_sampler import ResumableRandomSampler
        dataset = list(range(29))
        sampler = ResumableRandomSampler(dataset, seed=19, dataset_manifest_sha256="b" * 64)
        epoch0 = list(sampler)
        sampler.set_epoch(1)
        epoch1 = list(sampler)
        self.assertNotEqual(epoch0, epoch1)
        restored = ResumableRandomSampler(dataset, seed=19, dataset_manifest_sha256="b" * 64)
        restored.load_state_dict(sampler.state_dict())
        self.assertEqual(list(restored), [])

    def test_sampler_state_rejects_dataset_hash_size_and_seed_mismatch(self):
        from ultron_core.resumable_sampler import ResumableRandomSampler
        state = ResumableRandomSampler([0, 1, 2], seed=7,
            dataset_manifest_sha256="c" * 64).state_dict()
        with self.assertRaisesRegex(ValueError, "manifest hash"):
            ResumableRandomSampler([0, 1, 2], seed=7,
                dataset_manifest_sha256="d" * 64).load_state_dict(state)
        with self.assertRaisesRegex(ValueError, "dataset size"):
            ResumableRandomSampler([0, 1, 2, 3], seed=7,
                dataset_manifest_sha256="c" * 64).load_state_dict(state)
        with self.assertRaisesRegex(ValueError, "seed"):
            ResumableRandomSampler([0, 1, 2], seed=8,
                dataset_manifest_sha256="c" * 64).load_state_dict(state)

    def test_sampler_rejects_invalid_cursor_and_boolean_state_fields(self):
        from ultron_core.resumable_sampler import ResumableRandomSampler
        with self.assertRaisesRegex(ValueError, "next_index"):
            ResumableRandomSampler([1, 2], seed=1,
                dataset_manifest_sha256="e" * 64, next_index=3)
        sampler = ResumableRandomSampler([1, 2], seed=1,
            dataset_manifest_sha256="e" * 64)
        state = sampler.state_dict()
        state["schema_version"] = True
        with self.assertRaisesRegex(ValueError, "schema"):
            sampler.load_state_dict(state)
        state = sampler.state_dict()
        state["seed"] = True
        with self.assertRaisesRegex(ValueError, "seed"):
            sampler.load_state_dict(state)


    def test_sampler_state_rejects_boolean_integer_fields(self):
        from ultron_core.resumable_sampler import ResumableRandomSampler
        sampler = ResumableRandomSampler([0], seed=1, dataset_manifest_sha256="f" * 64)
        state = sampler.state_dict()
        bad_size = dict(state)
        bad_size["dataset_size"] = True
        with self.assertRaisesRegex(ValueError, "dataset size"):
            sampler.load_state_dict(bad_size)
        bad_seed = dict(state)
        bad_seed["seed"] = True
        with self.assertRaisesRegex(ValueError, "seed"):
            sampler.load_state_dict(bad_seed)



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
    def test_corpus_summary_reports_topic_difficulty_and_validation(self):
        examples = generate_examples(812, 80)
        report = summarize_corpus(examples)
        self.assertEqual(report["example_count"], 80)
        self.assertEqual(report["unique_example_id_count"], 80)
        self.assertEqual(report["duplicate_example_id_count"], 0)
        self.assertEqual(report["validated_example_count"], 80)
        self.assertEqual(report["invalid_example_count"], 0)
        self.assertEqual(sum(report["topic_counts"].values()), 80)
        self.assertAlmostEqual(sum(report["topic_proportions"].values()), 1.0)
        self.assertFalse(report["training_performed"])
        self.assertFalse(report["data_generated"])

    def test_corpus_summary_detects_prompt_group_leakage(self):
        examples = generate_examples(813, 30)
        splits = {"train": (examples[0],), "validation": (examples[0],),
                  "test": tuple(examples[1:])}
        report = summarize_corpus(examples, splits=splits)
        self.assertFalse(report["splits_prompt_disjoint"])
        self.assertTrue(report["prompt_group_leakage"])
        self.assertEqual(report["split_counts"]["train"], 1)
        self.assertEqual(report["repeated_split_example_id_count"], 1)
        self.assertFalse(report["split_membership_valid"])


    def test_corpus_summary_detects_split_row_content_changed_under_same_id(self):
        examples = generate_examples(816, 12)
        altered = replace(examples[0], input_text=examples[0].input_text + " altered")
        splits = {"train": (altered,), "validation": tuple(examples[1:6]),
                  "test": tuple(examples[6:])}
        report = summarize_corpus(examples, splits=splits)
        self.assertEqual(report["mismatched_split_row_count"], 1)
        self.assertFalse(report["split_membership_valid"])


    def test_corpus_summary_flags_split_rows_outside_corpus(self):
        examples = generate_examples(814, 12)
        outsider = generate_examples(815, 1)[0]
        splits = {"train": (examples[0], outsider), "validation": tuple(examples[1:6]),
                  "test": tuple(examples[6:])}
        report = summarize_corpus(examples, splits=splits)
        self.assertEqual(report["unknown_split_example_id_count"], 1)
        self.assertFalse(report["split_membership_valid"])

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
        examples = generate_examples(101, 12, topics=("arithmetic", "rational_arithmetic", "linear_equations"))
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
            self.assertEqual(verify_dataset(path), manifest)
            with path.open("ab") as stream:
                stream.write(b"tamper\\n")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                verify_dataset(path)



    def test_exact_two_by_two_matrix_determinants(self):
        examples = generate_examples(722, 80, topics=("matrix_determinant_2x2",))
        self.assertTrue(all(item.validation_status == "semantically_checked" for item in examples))
        self.assertTrue(all(validate_example_text(item.input_text, item.exact_answer, item.topic)
                            for item in examples))
        self.assertTrue(validate_example_text("determinant: [[1, 2], [3, 4]]", "-2",
                                              "matrix_determinant_2x2"))
        self.assertFalse(validate_example_text("determinant: [[1, 2], [3, 4]]", "2",
                                               "matrix_determinant_2x2"))

    def test_exact_two_by_two_linear_systems(self):
        examples = generate_examples(723, 80, topics=("linear_system_2x2",))
        self.assertTrue(all(item.validation_status == "semantically_checked" for item in examples))
        self.assertTrue(all(validate_example_text(item.input_text, item.exact_answer, item.topic)
                            for item in examples))
        prompt = "solve: 2*x + 3*y = 13; 1*x - 1*y = -1"
        self.assertTrue(validate_example_text(prompt, "x=2, y=3", "linear_system_2x2"))
        self.assertFalse(validate_example_text(prompt, "x=3, y=2", "linear_system_2x2"))
        rational_prompt = "solve: 2*x + 1*y = 1; 1*x - 1*y = 0"
        self.assertTrue(validate_example_text(rational_prompt, "x=1/3, y=1/3", "linear_system_2x2"))
        self.assertFalse(validate_example_text("solve: 1*x + 2*y = 3; 2*x + 4*y = 6",
                                              "x=1, y=1", "linear_system_2x2"))

    def test_polynomial_definite_integrals_are_exactly_validated(self):
        examples = generate_examples(812, 70, topics=("polynomial_definite_integral",))
        self.assertTrue(all(validate_example_text(item.input_text, item.exact_answer, item.topic)
                            for item in examples))
        self.assertTrue(validate_example_text(
            "integrate: x^2 from x=0 to x=3", "9", "polynomial_definite_integral"))
        self.assertTrue(validate_example_text(
            "integrate: 2*x + 1 from x=-1/2 to x=3/2", "4", "polynomial_definite_integral"))
        self.assertFalse(validate_example_text(
            "integrate: x^2 from x=0 to x=3", "8", "polynomial_definite_integral"))


    def test_polynomial_derivative_examples_are_exactly_validated(self):
        examples = generate_examples(717, 80, topics=("polynomial_derivative",))
        self.assertTrue(all(item.validation_status == "semantically_checked" for item in examples))
        self.assertTrue(all(validate_example_text(item.input_text, item.exact_answer, item.topic)
                            for item in examples))
        self.assertTrue(validate_example_text(
            "differentiate: 3*x^3 - 2*x + 5", "9*x^2 - 2", "polynomial_derivative"))
        self.assertFalse(validate_example_text(
            "differentiate: 3*x^3 - 2*x + 5", "9*x^2 + 2", "polynomial_derivative"))
        self.assertFalse(validate_example_text(
            "differentiate: x^13", "13*x^12", "polynomial_derivative"))


    def test_split_examples_are_deterministic_deduplicated_and_prompt_disjoint(self):
        examples = generate_examples(4301, 500)
        first = split_examples(examples, validation_fraction=0.15, test_fraction=0.15, seed=99)
        second = split_examples(examples, validation_fraction=0.15, test_fraction=0.15, seed=99)
        self.assertEqual(first, second)
        prompts = {
            name: {" ".join(item.input_text.split()) for item in values}
            for name, values in first.items()
        }
        self.assertTrue(first["train"] and first["validation"] and first["test"])
        self.assertFalse(prompts["train"] & prompts["validation"])
        self.assertFalse(prompts["train"] & prompts["test"])
        self.assertFalse(prompts["validation"] & prompts["test"])
        self.assertEqual(sum(len(values) for values in first.values()), len(set().union(*prompts.values())))

    def test_split_examples_rejects_invalid_fractions_and_seed(self):
        examples = generate_examples(11, 30)
        with self.assertRaisesRegex(ValueError, "less than 1"):
            split_examples(examples, validation_fraction=0.6, test_fraction=0.4)
        with self.assertRaisesRegex(ValueError, "finite"):
            split_examples(examples, validation_fraction=float("nan"))
        with self.assertRaises(TypeError):
            split_examples(examples, seed=True)

    def test_dataset_verifier_recomputes_example_identity_not_only_file_hash(self):
        examples = generate_examples(909, 12)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "identity.jsonl"
            write_dataset(path, examples, seed=909, topics=SUPPORTED_TOPICS)
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            rows[0]["example_id"] = "0" * 64
            content = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False,
                                       separators=(",", ":")) + "\n" for row in rows).encode("utf-8")
            path.write_bytes(content)
            manifest_path = path.with_suffix(path.suffix + ".manifest.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["sha256"] = hashlib.sha256(content).hexdigest()
            manifest_path.write_text(json.dumps(manifest, sort_keys=True, ensure_ascii=False,
                                               separators=(",", ":")) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "example_id does not match"):
                verify_dataset(path)



class TrainingPreflightTests(unittest.TestCase):
    def setUp(self):
        self.vocabulary = MathVocabulary.default()
        self.examples = generate_examples(602, 300)
        self.splits = split_examples(self.examples, validation_fraction=0.15, test_fraction=0.15, seed=602)
        self.config = NeuroSparseConfig.foundation()

    def test_preflight_validates_plan_without_authorizing_or_training(self):
        report = preflight_training_plan(
            self.config, self.splits, batch_size=1, sequence_length=128,
            gradient_accumulation_steps=4, memory_budget_gib=0.5,
            dataset_manifest_sha256="a" * 64,
        )
        self.assertEqual(report["status"], "PREFLIGHT_ONLY")
        self.assertTrue(report["validated"])
        self.assertFalse(report["training_authorized"])
        self.assertEqual(report["optimizer_steps"], 0)
        self.assertFalse(report["remote_execution_enabled"])
        self.assertTrue(report["prompt_disjoint"])
        self.assertFalse(report["budget_covers_persistent_state"])
        self.assertEqual(report["parameter_count"], 61826048)
        self.assertEqual(report["total_parameter_count"], 63400451)
        self.assertEqual(report["dataset_size"], len(self.splits["train"]))
        self.assertEqual(report["model_weights_fp32_bytes"], 253601804)
        self.assertEqual(report["model_gradients_fp32_bytes"], 247304192)
        self.assertEqual(report["model_adamw_moments_fp32_bytes"], 494608384)
        self.assertEqual(report["model_persistent_state_fp32_bytes"], 995514380)
        self.assertEqual(report["model_grad_and_adamw_state_fp32_bytes"], 995514380)

    def test_preflight_rejects_small_model_and_vocab_mismatch(self):
        small = NeuroSparseConfig(vocab_size=len(self.vocabulary), hidden_size=32,
            num_layers=1, num_experts=4, top_k=2, max_refinements=2,
            fast_memory_slots=8, num_attention_heads=4)
        with self.assertRaisesRegex(ValueError, "minimum is 40000000"):
            preflight_training_plan(small, self.splits)
        wrong_vocab = self.config.to_dict()
        wrong_vocab["vocab_size"] += 1
        with self.assertRaisesRegex(ValueError, "does not match canonical tokenizer"):
            preflight_training_plan(NeuroSparseConfig(**wrong_vocab), self.splits)

    def test_preflight_rejects_prompt_overlap_across_splits(self):
        invalid = dict(self.splits)
        invalid["validation"] = invalid["validation"] + (invalid["train"][0],)
        with self.assertRaisesRegex(ValueError, "overlap across"):
            preflight_training_plan(self.config, invalid)

    def test_preflight_rejects_invalid_batch_and_sequence_limits(self):
        with self.assertRaisesRegex(ValueError, "batch_size"):
            preflight_training_plan(self.config, self.splits, batch_size=0)
        with self.assertRaisesRegex(ValueError, "sequence_length"):
            preflight_training_plan(self.config, self.splits, sequence_length=2049)



class ModelIntegrationTests(unittest.TestCase):
    def test_tokenizer_ids_feed_existing_causal_model(self):
        vocabulary = MathVocabulary.default()
        tokenizer = MathTokenizer(vocabulary)
        config = NeuroSparseConfig(
            vocab_size=len(vocabulary), hidden_size=32, num_layers=1,
            num_experts=4, top_k=2, fast_memory_slots=8,
            max_sequence_length=32,
        )
        model = NeuroSparseModel(config).eval()
        ids = torch.tensor([tokenizer.encode("x+1")], dtype=torch.long)
        with torch.inference_mode():
            output = model(ids)
        self.assertEqual(output["logits"].shape, (1, ids.shape[1], len(vocabulary)))

    def test_padding_tokens_cannot_change_valid_token_logits(self):
        torch.manual_seed(123)
        vocabulary = MathVocabulary.default()
        tokenizer = MathTokenizer(vocabulary)
        config = NeuroSparseConfig(
            vocab_size=len(vocabulary), hidden_size=32, num_layers=2,
            num_experts=4, top_k=2, fast_memory_slots=8,
            max_sequence_length=16,
        )
        model = NeuroSparseModel(config).eval()
        valid = tokenizer.encode("x+1")
        pad = vocabulary.token_id("<PAD>")
        alternate_padding = tokenizer.encode("z-9")
        first = torch.tensor([valid + [pad, pad]], dtype=torch.long)
        second = torch.tensor([valid + alternate_padding[:2]], dtype=torch.long)
        mask = torch.tensor([[True, True, True, False, False]], dtype=torch.bool)
        with torch.inference_mode():
            first_logits = model(first, attention_mask=mask)["logits"]
            second_logits = model(second, attention_mask=mask)["logits"]
        torch.testing.assert_close(first_logits[:, :len(valid)], second_logits[:, :len(valid)])

    def test_variable_length_batch_uses_per_example_padding_mask(self):
        vocabulary = MathVocabulary.default()
        tokenizer = MathTokenizer(vocabulary)
        config = NeuroSparseConfig(
            vocab_size=len(vocabulary), hidden_size=32, num_layers=1,
            num_experts=4, top_k=2, fast_memory_slots=8,
            max_sequence_length=16,
        )
        model = NeuroSparseModel(config).eval()
        short = tokenizer.encode("x+1")
        long = tokenizer.encode("x+1+2")
        pad = vocabulary.token_id("<PAD>")
        ids = torch.tensor([short + [pad] * (len(long) - len(short)), long])
        mask = ids.ne(pad)
        with torch.inference_mode():
            logits = model(ids, attention_mask=mask)["logits"]
            standalone = model(torch.tensor([short], dtype=torch.long))["logits"]
        self.assertEqual(tuple(logits.shape), (2, len(long), len(vocabulary)))
        torch.testing.assert_close(logits[0, :len(short)], standalone[0], atol=2e-6, rtol=2e-6)

    def test_left_padding_keeps_all_model_outputs_finite(self):
        vocabulary = MathVocabulary.default()
        tokenizer = MathTokenizer(vocabulary)
        config = NeuroSparseConfig(
            vocab_size=len(vocabulary), hidden_size=32, num_layers=2,
            num_experts=4, top_k=2, fast_memory_slots=8,
        )
        model = NeuroSparseModel(config).eval()
        ids = torch.tensor([[0, 0] + tokenizer.encode("x+1")])
        mask = torch.tensor([[False, False, True, True, True]])
        with torch.inference_mode():
            logits = model(ids, attention_mask=mask)["logits"]
        self.assertTrue(torch.isfinite(logits).all())

    def test_attention_mask_validation(self):
        vocabulary = MathVocabulary.default()
        model = NeuroSparseModel(NeuroSparseConfig(
            vocab_size=len(vocabulary), hidden_size=32, num_layers=1,
            num_experts=4, top_k=2, fast_memory_slots=8,
        ))
        ids = torch.tensor([[4, 5, 6]])
        with self.assertRaisesRegex(TypeError, "torch.bool"):
            model(ids, attention_mask=torch.ones_like(ids))
        with self.assertRaisesRegex(ValueError, "same"):
            model(ids, attention_mask=torch.ones((1, 2), dtype=torch.bool))
        with self.assertRaisesRegex(ValueError, "at least one"):
            model(ids, attention_mask=torch.zeros_like(ids, dtype=torch.bool))

    def test_padded_positions_do_not_write_to_episodic_memory(self):
        vocabulary = MathVocabulary.default()
        tokenizer = MathTokenizer(vocabulary)
        config = NeuroSparseConfig(
            vocab_size=len(vocabulary), hidden_size=32, num_layers=1,
            num_experts=4, top_k=2, fast_memory_slots=8,
        )
        model = NeuroSparseModel(config).train()
        ids = torch.tensor([tokenizer.encode("x+1") + [0, 0]])
        mask = torch.tensor([[True, True, True, False, False]])
        model(ids, write_memory=True, attention_mask=mask)
        for block in model.blocks:
            self.assertEqual(int(block.memory.valid.sum()), len(tokenizer.encode("x+1")))

    def test_math_ir_round_trip_and_structural_hash_are_deterministic(self):
        expression = Expr(
            ExprKind.ADD,
            args=(
                Expr(ExprKind.RATIONAL, value="1/3"),
                Expr(ExprKind.DIV, args=(
                    Expr(ExprKind.INTEGER, value=2),
                    Expr(ExprKind.INTEGER, value=5),
                )),
            ),
            assumptions=("x is real",),
        )
        encoded = expression.canonical_json()
        restored = Expr.from_dict(expression.to_dict())
        self.assertEqual(restored, expression)
        self.assertEqual(restored.canonical_json(), encoded)
        self.assertEqual(restored.structural_hash(), expression.structural_hash())
        self.assertEqual(len(expression.structural_hash()), 64)

    def test_math_ir_rejects_malformed_serialized_structure(self):
        with self.assertRaisesRegex(ValueError, "must contain"):
            Expr.from_dict({"kind": "integer", "value": 1})
        with self.assertRaisesRegex(ValueError, "unsupported expression kind"):
            Expr.from_dict({"kind": "unknown", "value": None, "args": [], "assumptions": []})
        with self.assertRaises(TypeError):
            Expr.from_dict({"kind": "integer", "value": 1, "args": (), "assumptions": []})

    def test_exact_subtraction_and_division_in_math_ir(self):
        two = Expr(ExprKind.INTEGER, value=2)
        six = Expr(ExprKind.INTEGER, value=6)
        subtraction = Expr(ExprKind.SUB, args=(six, two))
        division = Expr(ExprKind.DIV, args=(six, two))
        self.assertEqual(evaluate(subtraction, {}), 4)
        self.assertEqual(evaluate(division, {}), 3)
        with self.assertRaises(ZeroDivisionError):
            evaluate(Expr(ExprKind.DIV, args=(six, Expr(ExprKind.INTEGER, value=0))), {})


class MathParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = MathParser()

    def test_parse_arithmetic_and_equality_into_existing_ir(self):
        equation = self.parser.parse("2x + 3 = 7")
        self.assertEqual(equation.kind, ExprKind.EQUAL)
        self.assertEqual(evaluate(equation.args[0], {"x": Fraction(2)}), 7)
        self.assertEqual(evaluate(equation.args[1], {}), 7)

    def test_precedence_unary_sign_and_right_associative_power(self):
        self.assertEqual(evaluate(parse_math("-x^2"), {"x": Fraction(3)}), -9)
        self.assertEqual(evaluate(parse_math("2^3^2"), {}), 512)
        self.assertEqual(evaluate(parse_math("2^-2"), {}), Fraction(1, 4))
        self.assertEqual(evaluate(parse_math("-(2 + 1) * 4"), {}), -12)

    def test_implicit_and_explicit_multiplication(self):
        self.assertEqual(evaluate(parse_math("2x"), {"x": Fraction(4)}), 8)
        self.assertEqual(evaluate(parse_math("2(x + 1)"), {"x": Fraction(4)}), 10)
        self.assertEqual(evaluate(parse_math("(x + 1)(x - 1)"), {"x": Fraction(4)}), 15)
        self.assertEqual(evaluate(parse_math("2 × (x + 1)"), {"x": Fraction(4)}), 10)
        self.assertEqual(evaluate(parse_math("8 ÷ 2"), {}), 4)

    def test_contiguous_identifiers_and_spaced_products_are_distinct(self):
        self.assertEqual(parse_math("velocity").value, "velocity")
        self.assertEqual(parse_math("velocity2").value, "velocity2")
        self.assertEqual(parse_math("x_1").value, "x_1")
        self.assertEqual(parse_math("x_{12}").value, "x_12")
        spaced = parse_math("v e")
        self.assertEqual(spaced.kind, ExprKind.MUL)
        self.assertNotEqual(parse_math("ve"), spaced)

    def test_decimal_literals_are_exact_rationals(self):
        self.assertEqual(evaluate(parse_math("0.125"), {}), Fraction(1, 8))
        self.assertEqual(evaluate(parse_math(".5"), {}), Fraction(1, 2))
        self.assertEqual(evaluate(parse_math("1.25 + 0.5"), {}), Fraction(7, 4))

    def test_supported_latex_greek_symbol_alias(self):
        self.assertEqual(parse_math(r"\alpha + 1").args[0].value, "α")

    def test_unicode_superscript_powers_are_parsed_as_exponents(self):
        self.assertEqual(evaluate(parse_math("x²"), {"x": Fraction(3)}), 9)
        self.assertEqual(evaluate(parse_math("x⁻²"), {"x": Fraction(2)}), Fraction(1, 4))
        self.assertEqual(evaluate(parse_math("x²³"), {"x": Fraction(2)}), 2 ** 23)

    def test_parser_rejects_empty_and_trailing_input(self):
        for source in ("", "   ", "1 2", "x = y = z", "1.", "(x + 1"):
            with self.subTest(source=source):
                with self.assertRaises(MathParseError):
                    parse_math(source)

    def test_parser_rejects_unsupported_semantics_instead_of_guessing(self):
        for source in ("foo(x)", "x_{i,2}", "x₁", r"\frac{1}{2}", "x == 3", "x ∈ ℝ"):
            with self.subTest(source=source):
                with self.assertRaises(MathParseError):
                    parse_math(source)

    def test_typed_function_calls_are_parsed_but_not_falsely_evaluated(self):
        expression = parse_math("sin(x) + sqrt(4)")
        call = expression.args[0]
        self.assertEqual(call.kind, ExprKind.CALL)
        self.assertEqual(call.value, "sin")
        self.assertEqual(call.args[0], Expr(ExprKind.SYMBOL, value="x"))
        with self.assertRaisesRegex(ValueError, "does not implement function sin"):
            evaluate(call, {"x": Fraction(1)})

    def test_function_call_nesting_and_unknown_names(self):
        self.assertEqual(parse_math("log(abs(x))").kind, ExprKind.CALL)
        with self.assertRaisesRegex(MathParseError, "unknown or unsupported"):
            parse_math("mystery(x)")

    def test_typed_comparisons_parse_and_evaluate_exactly(self):
        cases = (
            ("1 < 2", ExprKind.LESS_THAN, True),
            ("2 <= 2", ExprKind.LESS_EQUAL, True),
            ("3 > 2", ExprKind.GREATER_THAN, True),
            ("3 >= 4", ExprKind.GREATER_EQUAL, False),
            ("1 != 2", ExprKind.NOT_EQUAL, True),
            ("1 ≠ 1", ExprKind.NOT_EQUAL, False),
            ("1 ≤ 2", ExprKind.LESS_EQUAL, True),
            ("2 ≥ 2", ExprKind.GREATER_EQUAL, True),
            ("2 = 2", ExprKind.EQUAL, True),
        )
        for source, kind, expected in cases:
            with self.subTest(source=source):
                expression = parse_math(source)
                self.assertEqual(expression.kind, kind)
                self.assertIs(evaluate(expression, {}), expected)

    def test_comparison_results_cannot_be_used_as_scalar_operands(self):
        comparison = Expr(
            ExprKind.LESS_THAN,
            args=(Expr(ExprKind.INTEGER, value=1), Expr(ExprKind.INTEGER, value=2)),
        )
        arithmetic = Expr(
            ExprKind.ADD,
            args=(comparison, Expr(ExprKind.INTEGER, value=3)),
        )
        with self.assertRaisesRegex(ValueError, "cannot be used as scalar operands"):
            evaluate(arithmetic, {})

    def test_chained_comparisons_are_rejected(self):
        for source in ("1 < 2 < 3", "1 <= 2 = 2", "1 != 2 > 0"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(MathParseError, "chained comparisons"):
                    parse_math(source)

    def test_spaced_ascii_compound_comparison_is_rejected(self):
        with self.assertRaises(MathParseError):
            parse_math("1 < = 2")

    def test_parser_errors_include_source_offsets(self):
        with self.assertRaisesRegex(MathParseError, "offset 1"):
            parse_math("x_")
        with self.assertRaisesRegex(MathParseError, "offset 1"):
            parse_math("x🙂")

    def test_parser_enforces_source_token_and_nesting_budgets(self):
        with self.assertRaisesRegex(MathParseError, "source length"):
            MathParser(max_source_chars=3).parse("1234")
        with self.assertRaisesRegex(MathParseError, "token count"):
            MathParser(max_tokens=2).parse("1 + 2")
        with self.assertRaisesRegex(MathParseError, "nesting"):
            MathParser(max_nesting=2).parse("(((x)))")
        with self.assertRaisesRegex(ValueError, "positive integer"):
            MathParser(max_tokens=0)


class ConservativeSimplificationTests(unittest.TestCase):
    def test_exact_constant_folding_and_identity_rewrites(self):
        expression = parse_math("x + 0 + 2 + 3")
        reduced = simplify(expression)
        self.assertEqual(reduced.kind, ExprKind.ADD)
        self.assertEqual(reduced.args[0], Expr(ExprKind.SYMBOL, value="x"))
        self.assertEqual(reduced.args[1], Expr(ExprKind.INTEGER, value=5))
        for sample in (Fraction(-7, 3), Fraction(-1), Fraction(0), Fraction(5, 2), Fraction(11)):
            self.assertEqual(
                evaluate(expression, {"x": sample}),
                evaluate(reduced, {"x": sample}),
            )

    def test_multiplication_division_power_and_double_negation_rewrites(self):
        self.assertEqual(simplify(parse_math("x * 1")), Expr(ExprKind.SYMBOL, value="x"))
        self.assertEqual(simplify(parse_math("x / 1")), Expr(ExprKind.SYMBOL, value="x"))
        self.assertEqual(simplify(parse_math("x ^ 1")), Expr(ExprKind.SYMBOL, value="x"))
        self.assertEqual(simplify(parse_math("-(-x)")), Expr(ExprKind.SYMBOL, value="x"))
        self.assertEqual(evaluate(simplify(parse_math("(x + 0) * (1 * 3)")), {"x": Fraction(4)}), 12)

    def test_does_not_apply_zero_product_rule_to_potentially_undefined_term(self):
        expression = parse_math("0 * (1 / 0)")
        reduced = simplify(expression)
        self.assertEqual(reduced.kind, ExprKind.MUL)
        self.assertEqual(reduced.args[0], Expr(ExprKind.INTEGER, value=0))
        with self.assertRaises(ZeroDivisionError):
            evaluate(reduced, {})

    def test_division_by_zero_remains_explicit_and_zero_to_zero_is_rejected(self):
        self.assertEqual(simplify(parse_math("1 / 0")).kind, ExprKind.DIV)
        with self.assertRaisesRegex(ValueError, "zero to the zero"):
            evaluate(parse_math("0^0"), {})

    def test_simplifier_rejects_non_expr_input(self):
        with self.assertRaises(TypeError):
            simplify("x + 1")





class ExactPolynomialTests(unittest.TestCase):
    def test_canonical_addition_and_like_term_collection(self):
        from ultron_core.polynomial import Polynomial
        first = Polynomial.from_expr(parse_math("2*x + 3*x - 4"))
        second = Polynomial.from_expr(parse_math("5*x - 4"))
        self.assertEqual(first, second)
        self.assertEqual(first.evaluate({"x": 2}), 6)
        self.assertEqual(first.canonical_key(), second.canonical_key())

    def test_exact_fraction_coefficients_and_multivariate_order(self):
        from ultron_core.polynomial import Polynomial
        first = Polynomial.from_expr(parse_math("1/2*x*y + 1/3*y*x + 2/5"))
        second = Polynomial.from_expr(parse_math("5/6*x*y + 2/5"))
        self.assertEqual(first, second)
        self.assertEqual(first.evaluate({"x": 3, "y": 6}), Fraction(77, 5))
        self.assertEqual(first.terms[0][0], ())
        self.assertEqual(first.terms[1][0], (("x", 1), ("y", 1)))

    def test_exact_expansion_and_canonical_equivalence(self):
        from ultron_core.polynomial import Polynomial
        expanded = Polynomial.from_expr(parse_math("(x + y)^2"))
        explicit = Polynomial.from_expr(parse_math("x^2 + 2*x*y + y^2"))
        self.assertEqual(expanded, explicit)
        self.assertEqual(expanded.evaluate({"x": 2, "y": 3}), 25)
        self.assertEqual(expanded.to_expr(), explicit.to_expr())

    def test_zero_polynomial_and_zero_power(self):
        from ultron_core.polynomial import Polynomial
        self.assertEqual(Polynomial.from_expr(parse_math("x - x")), Polynomial.zero())
        self.assertEqual(Polynomial.from_expr(parse_math("x^0")), Polynomial.one())
        self.assertEqual(Polynomial.from_expr(parse_math("0 * (x + 1)")), Polynomial.zero())

    def test_constant_denominator_is_exact_but_variable_denominator_is_rejected(self):
        from ultron_core.polynomial import Polynomial, PolynomialError
        self.assertEqual(Polynomial.from_expr(parse_math("x / 2")).evaluate({"x": 3}), Fraction(3, 2))
        with self.assertRaisesRegex(PolynomialError, "variable polynomial"):
            Polynomial.from_expr(parse_math("1 / x"))
        with self.assertRaisesRegex(PolynomialError, "division by zero"):
            Polynomial.from_expr(parse_math("x / 0"))

    def test_rejects_negative_fractional_and_nonliteral_powers(self):
        from ultron_core.polynomial import Polynomial, PolynomialError
        for source in ("x^-1", "x^(1/2)", "x^y"):
            with self.subTest(source=source):
                with self.assertRaises(PolynomialError):
                    Polynomial.from_expr(parse_math(source))

    def test_rejects_calls_comparisons_and_assumptions(self):
        from ultron_core.polynomial import Polynomial, PolynomialError
        for source in ("sin(x)", "x < 2"):
            with self.subTest(source=source):
                with self.assertRaises(PolynomialError):
                    Polynomial.from_expr(parse_math(source))
        assumed = Expr(ExprKind.SYMBOL, value="x", assumptions=("x > 0",))
        with self.assertRaisesRegex(PolynomialError, "assumptions"):
            Polynomial.from_expr(assumed)

    def test_polynomial_limits_bound_degree_terms_and_power(self):
        from ultron_core.polynomial import Polynomial, PolynomialError, PolynomialLimits
        with self.assertRaisesRegex(PolynomialError, "total degree"):
            Polynomial.from_expr(parse_math("x^3"), limits=PolynomialLimits(max_total_degree=2))
        with self.assertRaisesRegex(PolynomialError, "term count"):
            Polynomial.from_expr(parse_math("x + y + z"), limits=PolynomialLimits(max_terms=2))
        with self.assertRaisesRegex(PolynomialError, "max_exponent"):
            Polynomial.from_expr(parse_math("x^3"), limits=PolynomialLimits(max_exponent=2))

    def test_constructor_and_environment_validation(self):
        from ultron_core.polynomial import Polynomial
        with self.assertRaises(TypeError):
            Polynomial.constant(True)
        with self.assertRaises(ValueError):
            Polynomial.variable("not a symbol!")
        with self.assertRaises(TypeError):
            Polynomial.variable("x").evaluate({"x": True})
        with self.assertRaisesRegex(ValueError, "missing variable"):
            Polynomial.variable("x").evaluate({})

    def test_sparse_multiplication_collects_cancellation(self):
        from ultron_core.polynomial import Polynomial
        first = Polynomial.from_expr(parse_math("(x + 1)*(x - 1)"))
        second = Polynomial.from_expr(parse_math("x^2 - 1"))
        self.assertEqual(first, second)
        self.assertEqual(first.evaluate({"x": Fraction(-5, 2)}), Fraction(21, 4))


    def test_direct_construction_cannot_bypass_hard_resource_ceilings(self):
        from ultron_core.polynomial import Polynomial, PolynomialError
        with self.assertRaisesRegex(PolynomialError, "total degree"):
            Polynomial((((("x", 257),), Fraction(1)),))

class ExactRationalExpressionTests(unittest.TestCase):
    def test_x_over_x_preserves_the_original_excluded_point(self):
        from ultron_core.rational import RationalDomainError, RationalFunction
        value = RationalFunction.from_expr(parse_math("x/x"))
        self.assertEqual(value.evaluate({"x": 3}), Fraction(1))
        with self.assertRaises(RationalDomainError):
            value.evaluate({"x": 0})
        self.assertEqual(len(value.nonzero_constraints), 1)

    def test_cancelled_factor_domain_is_preserved_without_cancellation(self):
        from ultron_core.rational import RationalDomainError, RationalFunction
        value = RationalFunction.from_expr(parse_math("(x^2 - 1)/(x - 1)"))
        self.assertEqual(value.evaluate({"x": 2}), Fraction(3))
        with self.assertRaises(RationalDomainError):
            value.evaluate({"x": 1})

    def test_nested_reciprocal_preserves_inner_domain(self):
        from ultron_core.rational import RationalDomainError, RationalFunction
        value = RationalFunction.from_expr(parse_math("1/(1/x)"))
        self.assertEqual(value.evaluate({"x": 4}), Fraction(4))
        with self.assertRaises(RationalDomainError):
            value.evaluate({"x": 0})

    def test_addition_and_multiplication_union_domain_constraints(self):
        from ultron_core.rational import RationalDomainError, RationalFunction
        left = RationalFunction.from_expr(parse_math("1/x"))
        right = RationalFunction.from_expr(parse_math("1/(x - 1)"))
        added = left.add(right)
        multiplied = left.multiply(right)
        self.assertEqual(added.evaluate({"x": 2}), Fraction(3, 2))
        self.assertEqual(multiplied.evaluate({"x": 2}), Fraction(1, 2))
        for value in (added, multiplied):
            with self.subTest(value=value):
                with self.assertRaises(RationalDomainError):
                    value.evaluate({"x": 0})
                with self.assertRaises(RationalDomainError):
                    value.evaluate({"x": 1})

    def test_division_requires_divisor_to_be_nonzero(self):
        from ultron_core.rational import RationalDomainError, RationalFunction
        value = RationalFunction.from_expr(parse_math("1/(x - 2)"))
        reciprocal = RationalFunction.one().divide(value)
        self.assertEqual(reciprocal.evaluate({"x": 3}), Fraction(1))
        with self.assertRaises(RationalDomainError):
            reciprocal.evaluate({"x": 2})
        with self.assertRaisesRegex(ValueError, "zero rational function"):
            RationalFunction.one().divide(RationalFunction.zero())

    def test_negative_and_zero_powers_preserve_domain(self):
        from ultron_core.rational import RationalDomainError, RationalFunction
        reciprocal = RationalFunction.from_expr(parse_math("x^-2"))
        self.assertEqual(reciprocal.evaluate({"x": 2}), Fraction(1, 4))
        with self.assertRaises(RationalDomainError):
            reciprocal.evaluate({"x": 0})
        zero_power = RationalFunction.from_expr(parse_math("x^0"))
        self.assertEqual(zero_power.evaluate({"x": 9}), Fraction(1))
        with self.assertRaises(RationalDomainError):
            zero_power.evaluate({"x": 0})

    def test_denominator_scalar_normalization_is_deterministic(self):
        from ultron_core.rational import RationalFunction
        first = RationalFunction.from_expr(parse_math("2/x"))
        second = RationalFunction.from_expr(parse_math("4/(2*x)"))
        self.assertTrue(first.same_representation(second))
        self.assertEqual(first.evaluate({"x": 5}), Fraction(2, 5))

    def test_rejects_undefined_zero_powers_and_zero_denominators(self):
        from ultron_core.rational import RationalExpressionError, RationalFunction
        for source in ("1/0", "0^0", "0^-1"):
            with self.subTest(source=source):
                with self.assertRaises(RationalExpressionError):
                    RationalFunction.from_expr(parse_math(source))

    def test_rejects_non_integer_powers_calls_comparisons_and_assumptions(self):
        from ultron_core.rational import RationalExpressionError, RationalFunction
        for source in ("x^(1/2)", "sin(x)", "x < 2"):
            with self.subTest(source=source):
                with self.assertRaises(RationalExpressionError):
                    RationalFunction.from_expr(parse_math(source))
        assumed = Expr(ExprKind.SYMBOL, value="x", assumptions=("x > 0",))
        with self.assertRaisesRegex(RationalExpressionError, "assumptions"):
            RationalFunction.from_expr(assumed)

    def test_polynomial_budgets_bound_rational_intermediates(self):
        from ultron_core.polynomial import PolynomialLimits
        from ultron_core.rational import RationalExpressionError, RationalFunction
        with self.assertRaises((RationalExpressionError, ValueError)):
            RationalFunction.from_expr(
                parse_math("1/(x^3 - 1)"),
                limits=PolynomialLimits(max_total_degree=2),
            )

    def test_nonzero_constant_denominators_do_not_create_fake_restrictions(self):
        from ultron_core.rational import RationalFunction
        value = RationalFunction.from_expr(parse_math("x/2"))
        self.assertEqual(value.nonzero_constraints, ())
        self.assertEqual(value.evaluate({"x": 6}), Fraction(3))

    def test_rational_results_match_independent_exact_evaluator_on_sample_points(self):
        from ultron_core.rational import RationalDomainError, RationalFunction
        samples = (
            "x/2 + 1/3",
            "(x + 1)/(x - 2)",
            "1/(1/x)",
            "x^-2",
            "(x^2 + 1)/(x + 1)",
        )
        for source in samples:
            expression = parse_math(source)
            rational = RationalFunction.from_expr(expression)
            for point in range(-3, 4):
                environment = {"x": Fraction(point)}
                with self.subTest(source=source, point=point):
                    try:
                        expected = evaluate(expression, environment)
                    except ZeroDivisionError:
                        with self.assertRaises(RationalDomainError):
                            rational.evaluate(environment)
                    else:
                        self.assertEqual(rational.evaluate(environment), expected)

    def test_custom_limits_above_defaults_survive_rational_normalization(self):
        from ultron_core.polynomial import PolynomialLimits
        from ultron_core.rational import RationalFunction
        limits = PolynomialLimits(max_total_degree=128, max_terms=4096, max_exponent=128)
        value = RationalFunction.from_expr(parse_math("x^65"), limits=limits)
        self.assertEqual(value.evaluate({"x": 2}), Fraction(2**65))

class ExactUnivariatePolynomialDivisionTests(unittest.TestCase):
    def test_division_exact_quotient_and_zero_remainder(self):
        from ultron_core.polynomial import Polynomial
        dividend = Polynomial.from_expr(parse_math("x^3 - 1"))
        divisor = Polynomial.from_expr(parse_math("x - 1"))
        quotient, remainder = dividend.divide_univariate(divisor)
        self.assertEqual(quotient, Polynomial.from_expr(parse_math("x^2 + x + 1")))
        self.assertEqual(remainder, Polynomial.zero())
        self.assertEqual(
            quotient.multiply(divisor).add(remainder),
            dividend,
        )
        self.assertEqual(dividend.exact_divide_univariate(divisor), quotient)

    def test_division_returns_exact_nonzero_remainder(self):
        from ultron_core.polynomial import Polynomial, PolynomialError
        dividend = Polynomial.from_expr(parse_math("x^2 + 1"))
        divisor = Polynomial.from_expr(parse_math("x + 1"))
        quotient, remainder = dividend.divide_univariate(divisor)
        self.assertEqual(quotient, Polynomial.from_expr(parse_math("x - 1")))
        self.assertEqual(remainder, Polynomial.constant(2))
        self.assertEqual(quotient.multiply(divisor).add(remainder), dividend)
        with self.assertRaisesRegex(PolynomialError, "not exact"):
            dividend.exact_divide_univariate(divisor)

    def test_fraction_coefficients_are_divided_exactly(self):
        from ultron_core.polynomial import Polynomial
        dividend = Polynomial.from_expr(parse_math("1/2*x^2 + 1/3*x + 1/18"))
        divisor = Polynomial.from_expr(parse_math("1/2*x + 1/6"))
        quotient, remainder = dividend.divide_univariate(divisor)
        self.assertEqual(quotient, Polynomial.from_expr(parse_math("x + 1/3")))
        self.assertEqual(remainder, Polynomial.zero())

    def test_monic_univariate_gcd(self):
        from ultron_core.polynomial import Polynomial
        left = Polynomial.from_expr(parse_math("x^3 - 2*x^2 + x"))
        right = Polynomial.from_expr(parse_math("x^2 - 1"))
        expected = Polynomial.from_expr(parse_math("x - 1"))
        self.assertEqual(left.gcd_univariate(right), expected)
        self.assertEqual(right.gcd_univariate(left), expected)

    def test_coprime_and_constant_gcd(self):
        from ultron_core.polynomial import Polynomial
        left = Polynomial.from_expr(parse_math("x^2 + 1"))
        right = Polynomial.from_expr(parse_math("x + 1"))
        self.assertEqual(left.gcd_univariate(right), Polynomial.one())
        self.assertEqual(
            Polynomial.constant(6).gcd_univariate(Polynomial.constant(9)),
            Polynomial.one(),
        )

    def test_gcd_zero_polynomial_edges(self):
        from ultron_core.polynomial import Polynomial, PolynomialError
        polynomial = Polynomial.from_expr(parse_math("2*x^2 + 4*x"))
        self.assertEqual(Polynomial.zero().gcd_univariate(polynomial),
                         Polynomial.from_expr(parse_math("x^2 + 2*x")))
        with self.assertRaisesRegex(PolynomialError, "gcd"):
            Polynomial.zero().gcd_univariate(Polynomial.zero())
        with self.assertRaisesRegex(PolynomialError, "multivariate"):
            Polynomial.from_expr(parse_math("x*y")).gcd_univariate(Polynomial.zero())
        with self.assertRaisesRegex(PolynomialError, "does not match"):
            Polynomial.variable("x").gcd_univariate(Polynomial.zero(), variable="y")

    def test_division_rejects_zero_divisor_and_multivariate_inputs(self):
        from ultron_core.polynomial import Polynomial, PolynomialError
        polynomial = Polynomial.from_expr(parse_math("x + 1"))
        with self.assertRaisesRegex(PolynomialError, "division by zero"):
            polynomial.divide_univariate(Polynomial.zero())
        with self.assertRaisesRegex(PolynomialError, "multivariate"):
            Polynomial.from_expr(parse_math("x*y + 1")).divide_univariate(
                Polynomial.from_expr(parse_math("x + 1"))
            )
        with self.assertRaisesRegex(PolynomialError, "one shared variable"):
            Polynomial.from_expr(parse_math("x + 1")).divide_univariate(
                Polynomial.from_expr(parse_math("y + 1"))
            )

    def test_division_rejects_variable_mismatch_and_honors_budgets(self):
        from ultron_core.polynomial import Polynomial, PolynomialError, PolynomialLimits
        polynomial = Polynomial.from_expr(parse_math("x^3 + 1"))
        divisor = Polynomial.from_expr(parse_math("x + 1"))
        with self.assertRaisesRegex(PolynomialError, "does not match"):
            polynomial.divide_univariate(divisor, variable="y")
        with self.assertRaisesRegex(PolynomialError, "total degree"):
            polynomial.divide_univariate(
                divisor, limits=PolynomialLimits(max_total_degree=2)
            )

class DomainSafeRationalReductionTests(unittest.TestCase):
    def test_x_over_x_reduces_to_one_but_keeps_x_nonzero(self):
        from ultron_core.polynomial import Polynomial
        from ultron_core.rational import RationalDomainError, RationalFunction
        original = RationalFunction.from_expr(parse_math("x/x"))
        reduced = original.cancel_common_univariate_factors()
        self.assertEqual(reduced.numerator, Polynomial.one())
        self.assertEqual(reduced.denominator, Polynomial.one())
        self.assertEqual(reduced.evaluate({"x": 7}), Fraction(1))
        with self.assertRaises(RationalDomainError):
            reduced.evaluate({"x": 0})

    def test_common_factor_cancellation_preserves_original_denominator_domain(self):
        from ultron_core.polynomial import Polynomial
        from ultron_core.rational import RationalDomainError, RationalFunction
        original = RationalFunction.from_expr(parse_math("(x^2 - 1)/(x - 1)"))
        reduced = original.cancel_common_univariate_factors()
        self.assertEqual(reduced.numerator, Polynomial.from_expr(parse_math("x + 1")))
        self.assertEqual(reduced.denominator, Polynomial.one())
        self.assertEqual(reduced.evaluate({"x": 2}), Fraction(3))
        with self.assertRaises(RationalDomainError):
            reduced.evaluate({"x": 1})

    def test_cancellation_retains_every_original_excluded_factor(self):
        from ultron_core.rational import RationalDomainError, RationalFunction
        original = RationalFunction.from_expr(parse_math("(x*(x - 1))/(x*(x + 1))"))
        reduced = original.cancel_common_univariate_factors()
        self.assertEqual(reduced.evaluate({"x": 2}), Fraction(1, 3))
        for excluded in (0, -1):
            with self.subTest(excluded=excluded):
                with self.assertRaises(RationalDomainError):
                    reduced.evaluate({"x": excluded})

    def test_zero_numerator_reduces_but_keeps_denominator_domain(self):
        from ultron_core.polynomial import Polynomial
        from ultron_core.rational import RationalDomainError, RationalFunction
        original = RationalFunction.from_expr(parse_math("0/(x - 1)"))
        reduced = original.cancel_common_univariate_factors()
        self.assertEqual(reduced.numerator, Polynomial.zero())
        self.assertEqual(reduced.denominator, Polynomial.one())
        self.assertEqual(reduced.evaluate({"x": 3}), Fraction(0))
        with self.assertRaises(RationalDomainError):
            reduced.evaluate({"x": 1})

    def test_reduction_rejects_multivariate_inputs(self):
        from ultron_core.polynomial import PolynomialError
        from ultron_core.rational import RationalFunction
        value = RationalFunction.from_expr(parse_math("(x*y + x)/(x + 1)"))
        with self.assertRaisesRegex(PolynomialError, "multivariate"):
            value.cancel_common_univariate_factors()

    def test_reduction_is_idempotent_and_preserves_representation(self):
        from ultron_core.rational import RationalFunction
        value = RationalFunction.from_expr(parse_math("(x^2 + 1)/(x + 1)"))
        once = value.cancel_common_univariate_factors()
        twice = once.cancel_common_univariate_factors()
        self.assertTrue(once.same_representation(twice))

class ExactSturmRootCountingTests(unittest.TestCase):
    def test_univariate_derivative_is_exact(self):
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("x^3 - 3*x + 2"))
        self.assertEqual(
            polynomial.derivative_univariate(),
            Polynomial.from_expr(parse_math("3*x^2 - 3")),
        )

    def test_sturm_sequence_for_quadratic(self):
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("x^2 - 2"))
        sequence = polynomial.sturm_sequence_univariate()
        self.assertEqual(len(sequence), 3)
        self.assertEqual(sequence[0], polynomial)
        self.assertEqual(sequence[1], Polynomial.from_expr(parse_math("2*x")))
        self.assertEqual(sequence[2], Polynomial.constant(2))

    def test_exact_root_counts_for_quadratic_intervals(self):
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("x^2 - 2"))
        self.assertEqual(polynomial.real_root_count_univariate(-2, 2), 2)
        self.assertEqual(polynomial.real_root_count_univariate(-1, 1), 0)
        self.assertEqual(polynomial.real_root_count_univariate(0, 2), 1)
        self.assertEqual(polynomial.real_root_count_univariate(-2, 0), 1)

    def test_repeated_roots_are_counted_once(self):
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("(x - 1)^2*(x + 2)"))
        self.assertEqual(polynomial.real_root_count_univariate(-3, 3), 2)
        self.assertEqual(polynomial.real_root_count_univariate(-1, 2), 1)
        self.assertEqual(polynomial.real_root_count_univariate(-3, 0), 1)

    def test_polynomial_without_real_roots_and_nonzero_constant(self):
        from ultron_core.polynomial import Polynomial
        no_real_roots = Polynomial.from_expr(parse_math("x^2 + 1"))
        self.assertEqual(no_real_roots.real_root_count_univariate(-5, 5), 0)
        self.assertEqual(
            Polynomial.constant(Fraction(3, 7)).real_root_count_univariate(-2, 2),
            0,
        )

    def test_sturm_rejects_zero_polynomial_and_root_endpoints(self):
        from ultron_core.polynomial import Polynomial, PolynomialError
        with self.assertRaisesRegex(PolynomialError, "zero polynomial"):
            Polynomial.zero().sturm_sequence_univariate()
        polynomial = Polynomial.from_expr(parse_math("x^2 - 1"))
        with self.assertRaisesRegex(PolynomialError, "endpoints"):
            polynomial.real_root_count_univariate(-1, 2)
        with self.assertRaisesRegex(PolynomialError, "endpoints"):
            polynomial.real_root_count_univariate(-2, 1)

    def test_sturm_validates_interval_types_and_order(self):
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("x^2 + 1"))
        with self.assertRaises(TypeError):
            polynomial.real_root_count_univariate(0.0, 2)
        with self.assertRaises(TypeError):
            polynomial.real_root_count_univariate(False, 2)
        with self.assertRaises(ValueError):
            polynomial.real_root_count_univariate(2, 1)
        with self.assertRaises(ValueError):
            polynomial.real_root_count_univariate(1, 1)

    def test_sturm_rejects_multivariate_inputs_and_enforces_limits(self):
        from ultron_core.polynomial import Polynomial, PolynomialError, PolynomialLimits
        multivariate = Polynomial.from_expr(parse_math("x*y + 1"))
        with self.assertRaisesRegex(PolynomialError, "multivariate"):
            multivariate.sturm_sequence_univariate()
        cubic = Polynomial.from_expr(parse_math("x^3 - 1"))
        with self.assertRaisesRegex(PolynomialError, "total degree"):
            cubic.real_root_count_univariate(
                0, 2, limits=PolynomialLimits(max_total_degree=2)
            )

class ExactRealRootIsolationTests(unittest.TestCase):
    def test_irrational_roots_are_isolated_in_disjoint_rational_intervals(self):
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("x^2 - 2"))
        intervals = polynomial.isolate_real_roots_univariate(
            -2, 2, max_width=Fraction(1, 100)
        )
        self.assertEqual(len(intervals), 2)
        self.assertLess(intervals[0][1], intervals[1][0])
        for left, right in intervals:
            self.assertLess(left, right)
            self.assertLessEqual(right - left, Fraction(1, 100))
            self.assertEqual(
                polynomial.real_root_count_univariate(left, right), 1
            )
            self.assertNotEqual(polynomial.evaluate({"x": left}), 0)
            self.assertNotEqual(polynomial.evaluate({"x": right}), 0)

    def test_exact_rational_roots_are_returned_as_degenerate_intervals(self):
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("x^2 - 1"))
        self.assertEqual(
            polynomial.isolate_real_roots_univariate(-2, 2),
            ((Fraction(-1), Fraction(-1)), (Fraction(1), Fraction(1))),
        )

    def test_mixed_rational_and_irrational_roots(self):
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("(x - 1)*(x^2 - 2)"))
        intervals = polynomial.isolate_real_roots_univariate(
            -2, 2, max_width=Fraction(1, 100)
        )
        self.assertEqual(len(intervals), 3)
        self.assertIn((Fraction(1), Fraction(1)), intervals)
        for left, right in intervals:
            if left != right:
                self.assertEqual(
                    polynomial.real_root_count_univariate(left, right), 1
                )

    def test_repeated_roots_are_isolated_once_each(self):
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("(x - 1)^2*(x + 2)^3"))
        intervals = polynomial.isolate_real_roots_univariate(
            -3, 3, max_width=Fraction(1, 100)
        )
        self.assertEqual(len(intervals), 2)
        self.assertEqual(
            sum(polynomial.real_root_count_univariate(a, b)
                for a, b in intervals if a != b)
            + sum(1 for a, b in intervals if a == b),
            2,
        )

    def test_non_degenerate_intervals_never_use_removed_roots_as_endpoints(self):
        from ultron_core.polynomial import Polynomial
        # The first root is exactly the initial midpoint. The second root is
        # very close to it, so a wide requested interval exposes endpoint bugs.
        polynomial = Polynomial.from_expr(
            parse_math("(x - 1)*(10000*x - 10001)")
        )
        intervals = polynomial.isolate_real_roots_univariate(
            0, 2, max_width=2
        )
        self.assertEqual(len(intervals), 2)
        self.assertIn((Fraction(1), Fraction(1)), intervals)
        for left, right in intervals:
            if left != right:
                self.assertNotEqual(polynomial.evaluate({"x": left}), 0)
                self.assertNotEqual(polynomial.evaluate({"x": right}), 0)
                self.assertEqual(
                    polynomial.real_root_count_univariate(left, right), 1
                )
        self.assertLess(intervals[0][1], intervals[1][0])

    def test_endpoint_adjustment_detects_exact_rational_root_candidate(self):
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(
            parse_math("(x - 1)*(2*x - 3)")
        )
        intervals = polynomial.isolate_real_roots_univariate(
            0, 2, max_width=2
        )
        self.assertEqual(
            intervals,
            ((Fraction(1), Fraction(1)), (Fraction(3, 2), Fraction(3, 2))),
        )

    def test_constant_has_no_roots(self):
        from ultron_core.polynomial import Polynomial
        self.assertEqual(
            Polynomial.constant(7).isolate_real_roots_univariate(-2, 2), ()
        )

    def test_isolation_rejects_zero_polynomial_and_root_endpoints(self):
        from ultron_core.polynomial import Polynomial, PolynomialError
        with self.assertRaisesRegex(PolynomialError, "zero polynomial"):
            Polynomial.zero().isolate_real_roots_univariate(-2, 2)
        polynomial = Polynomial.from_expr(parse_math("x^2 - 1"))
        with self.assertRaisesRegex(PolynomialError, "endpoints"):
            polynomial.isolate_real_roots_univariate(-1, 2)

    def test_isolation_validates_exact_bounds_and_width(self):
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("x^2 + 1"))
        with self.assertRaises(TypeError):
            polynomial.isolate_real_roots_univariate(0.0, 2)
        with self.assertRaises(TypeError):
            polynomial.isolate_real_roots_univariate(0, 2, max_width=0.1)
        with self.assertRaises(ValueError):
            polynomial.isolate_real_roots_univariate(0, 2, max_width=0)
        with self.assertRaises(ValueError):
            polynomial.isolate_real_roots_univariate(2, 1)

    def test_isolation_enforces_depth_and_interval_budgets(self):
        from ultron_core.polynomial import Polynomial, PolynomialError
        polynomial = Polynomial.from_expr(parse_math("x^2 - 2"))
        with self.assertRaisesRegex(PolynomialError, "max_depth"):
            polynomial.isolate_real_roots_univariate(
                -2, 2, max_width=Fraction(1, 1000), max_depth=0
            )
        with self.assertRaisesRegex(PolynomialError, "max_intervals"):
            polynomial.isolate_real_roots_univariate(
                -2, 2, max_width=Fraction(1, 1000), max_intervals=1
            )

    def test_isolation_rejects_multivariate_inputs_and_variable_mismatch(self):
        from ultron_core.polynomial import Polynomial, PolynomialError
        multivariate = Polynomial.from_expr(parse_math("x*y + 1"))
        with self.assertRaisesRegex(PolynomialError, "multivariate"):
            multivariate.isolate_real_roots_univariate(-2, 2)
        polynomial = Polynomial.from_expr(parse_math("x^2 - 2"))
        with self.assertRaisesRegex(PolynomialError, "does not match"):
            polynomial.isolate_real_roots_univariate(-2, 2, variable="y")


class RealAlgebraicNumberTests(unittest.TestCase):
    def test_construct_and_refine_irrational_root_exactly(self):
        from ultron_core.algebraic import RealAlgebraicNumber
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("x^2 - 2"))
        value = RealAlgebraicNumber.from_isolating_interval(polynomial, 1, 2)
        self.assertFalse(value.is_rational)
        refined = value.refine()
        self.assertEqual(refined.lower, Fraction(1))
        self.assertEqual(refined.upper, Fraction(3, 2))
        self.assertEqual(
            polynomial.real_root_count_univariate(
                refined.lower, refined.upper
            ),
            1,
        )

    def test_refinement_detects_exact_rational_midpoint(self):
        from ultron_core.algebraic import RealAlgebraicNumber
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("x^2 - 1"))
        value = RealAlgebraicNumber.from_isolating_interval(
            polynomial, 0, 2
        )
        exact = value.refine()
        self.assertTrue(exact.is_rational)
        self.assertEqual(exact.rational_value, Fraction(1))

    def test_rational_representation_and_exact_equality(self):
        from ultron_core.algebraic import RealAlgebraicNumber
        from ultron_core.polynomial import Polynomial
        rational = RealAlgebraicNumber.from_rational(Fraction(3, 2))
        same = RealAlgebraicNumber.from_rational(Fraction(6, 4))
        self.assertTrue(rational.same_value_as(same))
        self.assertEqual(rational.compare_to(same), 0)
        polynomial = Polynomial.from_expr(parse_math("x^2 - 9/4"))
        represented = RealAlgebraicNumber.from_isolating_interval(
            polynomial, 1, 2
        )
        self.assertTrue(rational.same_value_as(represented))
        self.assertEqual(rational.compare_to(represented), 0)

    def test_equivalent_defining_polynomials_identify_same_root(self):
        from ultron_core.algebraic import RealAlgebraicNumber
        from ultron_core.polynomial import Polynomial
        first = Polynomial.from_expr(parse_math("x^2 - 2"))
        second = Polynomial.from_expr(parse_math("2*x^2 - 4"))
        a = RealAlgebraicNumber.from_isolating_interval(first, 1, 2)
        b = RealAlgebraicNumber.from_isolating_interval(second, 1, 2)
        self.assertTrue(a.same_value_as(b))
        self.assertEqual(a.compare_to(b), 0)
        nonminimal = Polynomial.from_expr(parse_math("(x^2 - 2)^2"))
        c = RealAlgebraicNumber.from_isolating_interval(nonminimal, 1, 2)
        self.assertTrue(a.same_value_as(c))
        self.assertEqual(a.compare_to(c), 0)
        negative = RealAlgebraicNumber.from_isolating_interval(first, -2, -1)
        self.assertFalse(a.same_value_as(negative))
        self.assertEqual(negative.compare_to(a), -1)

    def test_exact_comparison_of_distinct_irrational_roots(self):
        from ultron_core.algebraic import RealAlgebraicNumber
        from ultron_core.polynomial import Polynomial
        sqrt2 = RealAlgebraicNumber.from_isolating_interval(
            Polynomial.from_expr(parse_math("x^2 - 2")), 1, 2
        )
        sqrt3 = RealAlgebraicNumber.from_isolating_interval(
            Polynomial.from_expr(parse_math("x^2 - 3")), 1, 2
        )
        self.assertFalse(sqrt2.same_value_as(sqrt3))
        self.assertEqual(sqrt2.compare_to(sqrt3), -1)
        self.assertEqual(sqrt3.compare_to(sqrt2), 1)

    def test_compare_irrational_root_with_exact_rational(self):
        from ultron_core.algebraic import RealAlgebraicNumber
        from ultron_core.polynomial import Polynomial
        sqrt2 = RealAlgebraicNumber.from_isolating_interval(
            Polynomial.from_expr(parse_math("x^2 - 2")), 1, 2
        )
        seven_fifths = RealAlgebraicNumber.from_rational(Fraction(7, 5))
        three_halves = RealAlgebraicNumber.from_rational(Fraction(3, 2))
        self.assertEqual(sqrt2.compare_to(seven_fifths), 1)
        self.assertEqual(sqrt2.compare_to(three_halves), -1)

    def test_repeated_defining_polynomial_is_supported(self):
        from ultron_core.algebraic import RealAlgebraicNumber
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("(x^2 - 2)^2"))
        value = RealAlgebraicNumber.from_isolating_interval(
            polynomial, 1, 2
        )
        self.assertEqual(value.polynomial.real_root_count_univariate(1, 2), 1)

    def test_rejects_zero_roots_multiple_roots_and_root_endpoints(self):
        from ultron_core.algebraic import RealAlgebraicNumber
        from ultron_core.polynomial import Polynomial, PolynomialError
        no_roots = Polynomial.from_expr(parse_math("x^2 + 1"))
        two_roots = Polynomial.from_expr(parse_math("x^2 - 1"))
        with self.assertRaisesRegex(PolynomialError, "found 0"):
            RealAlgebraicNumber.from_isolating_interval(no_roots, 0, 2)
        with self.assertRaisesRegex(PolynomialError, "found 2"):
            RealAlgebraicNumber.from_isolating_interval(two_roots, -2, 2)
        with self.assertRaisesRegex(PolynomialError, "endpoints"):
            RealAlgebraicNumber.from_isolating_interval(two_roots, -1, 2)

    def test_rejects_invalid_types_and_variable_mismatch(self):
        from ultron_core.algebraic import RealAlgebraicNumber
        from ultron_core.polynomial import Polynomial
        polynomial = Polynomial.from_expr(parse_math("x^2 - 2"))
        with self.assertRaises(TypeError):
            RealAlgebraicNumber.from_isolating_interval(polynomial, True, 2)
        value = RealAlgebraicNumber.from_isolating_interval(polynomial, 1, 2)
        other = RealAlgebraicNumber.from_rational(1, variable="y")
        with self.assertRaisesRegex(ValueError, "same variable"):
            value.compare_to(other)

    def test_comparison_refinement_budget_is_enforced(self):
        from ultron_core.algebraic import RealAlgebraicNumber
        from ultron_core.polynomial import Polynomial, PolynomialError
        sqrt2 = RealAlgebraicNumber.from_isolating_interval(
            Polynomial.from_expr(parse_math("x^2 - 2")), 1, 2
        )
        sqrt3 = RealAlgebraicNumber.from_isolating_interval(
            Polynomial.from_expr(parse_math("x^2 - 3")), 1, 2
        )
        with self.assertRaisesRegex(PolynomialError, "max_refinements"):
            sqrt2.compare_to(sqrt3, max_refinements=0)


if __name__ == "__main__":
    unittest.main()
