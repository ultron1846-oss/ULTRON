"""Round-trip and strict-schema contracts for ULTRON's canonical math tokenizer."""
import json
import random
import tempfile
import unittest
from pathlib import Path

from ultron_core.math_tokenizer import MathTokenizer, MathVocabulary, SPECIAL_TOKENS
from ultron_core.config import NeuroSparseConfig


class MathTokenizerContractTests(unittest.TestCase):
    def test_vocabulary_size_version_and_special_token_ids_are_stable(self):
        vocab = MathVocabulary.default()
        self.assertEqual(vocab.version, 1)
        self.assertEqual(len(vocab), 240)
        self.assertEqual(vocab.tokens[:3], SPECIAL_TOKENS)
        self.assertEqual([vocab.token_id(token) for token in SPECIAL_TOKENS], [0, 1, 2])

    def test_every_canonical_lexical_token_round_trips(self):
        tokenizer = MathTokenizer()
        for token in tokenizer.vocabulary.tokens[3:]:
            with self.subTest(token=token):
                self.assertEqual(tokenizer.decode(tokenizer.encode(token)), token)

    def test_math_unicode_and_whitespace_round_trip_losslessly(self):
        tokenizer = MathTokenizer()
        examples = (
            "∀x∈ℝ: x²≥0",
            r"\frac{a+b}{c} \Rightarrow a\neq0",
            "f(x) = α·x + β\n\t",
            "∫₀¹ x² dx = 1/3",
        )
        for text in examples:
            with self.subTest(text=text):
                self.assertEqual(tokenizer.decode(tokenizer.encode(text)), text)

    def test_bos_eos_and_special_token_decoding_contract(self):
        tokenizer = MathTokenizer()
        ids = tokenizer.encode("x+y", add_bos=True, add_eos=True)
        self.assertEqual(ids[0], 1)
        self.assertEqual(ids[-1], 2)
        self.assertEqual(tokenizer.decode(ids), "x+y")
        self.assertEqual(tokenizer.decode(ids, skip_special_tokens=False), "<BOS>x+y<EOS>")

    def test_unknown_unicode_reports_exact_character_offset(self):
        tokenizer = MathTokenizer()
        with self.assertRaisesRegex(ValueError, "offset 2"):
            tokenizer.encode("x+🙂")

    def test_vocabulary_json_rejects_duplicate_keys_and_noncanonical_assets(self):
        vocab = MathVocabulary.default()
        document = vocab.to_dict()
        duplicate = (
            '{"schema_version":1,"schema_version":1,"tokens":'
            + json.dumps(document["tokens"], ensure_ascii=False)
            + "}"
        )
        with self.assertRaisesRegex(ValueError, "duplicate vocabulary JSON key"):
            MathVocabulary.from_json(duplicate)
        document["tokens"][3], document["tokens"][4] = document["tokens"][4], document["tokens"][3]
        with self.assertRaisesRegex(ValueError, "canonical version-1 order"):
            MathVocabulary.from_dict(document)

    def test_vocabulary_asset_round_trips_through_disk(self):
        vocab = MathVocabulary.default()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vocab.json"
            vocab.save(path)
            loaded = MathVocabulary.load(path)
            self.assertEqual(loaded.to_json(), vocab.to_json())
            self.assertEqual(loaded.tokens, vocab.tokens)


    def test_foundation_config_is_bound_to_canonical_tokenizer(self):
        tokenizer = MathTokenizer()
        config = NeuroSparseConfig.foundation()
        tokenizer.assert_compatible_config(config)
        self.assertEqual(config.tokenizer_version, tokenizer.vocabulary.version)
        self.assertEqual(config.vocab_size, len(tokenizer.vocabulary))

    def test_tokenizer_rejects_model_config_vocab_size_mismatch(self):
        tokenizer = MathTokenizer()
        config = NeuroSparseConfig(vocab_size=len(tokenizer.vocabulary) + 1)
        with self.assertRaisesRegex(ValueError, "vocabulary size"):
            tokenizer.assert_compatible_config(config)

    def test_model_config_rejects_unsupported_tokenizer_version(self):
        with self.assertRaisesRegex(ValueError, "unsupported tokenizer version"):
            NeuroSparseConfig(tokenizer_version=2)

    def test_default_model_config_matches_the_canonical_vocabulary_and_pad_id(self):
        tokenizer = MathTokenizer()
        config = NeuroSparseConfig()
        tokenizer.assert_compatible_config(config)
        self.assertEqual(config.vocab_size, 240)
        self.assertEqual(config.pad_token_id, 0)

    def test_model_config_with_wrong_reserved_padding_id_is_rejected(self):
        tokenizer = MathTokenizer()
        config = NeuroSparseConfig(pad_token_id=1)
        with self.assertRaisesRegex(ValueError, "padding token ID"):
            tokenizer.assert_compatible_config(config)


    def test_trie_longest_match_matches_reference_scanner_on_mixed_input(self):
        tokenizer = MathTokenizer()
        lexical_tokens = tokenizer.vocabulary.tokens[3:]
        ordered_tokens = sorted(lexical_tokens, key=lambda token: (-len(token), token))
        rng = random.Random(20261128)
        examples = [
            "".join(rng.choice(lexical_tokens) for _ in range(400)),
            r"\subseteq\subset\supseteq\supset\Rightarrow\to\Leftrightarrow\notin",
            "x + α·y = ∫₀¹ x² dx\n",
        ]

        for source in examples:
            with self.subTest(source_prefix=source[:40]):
                expected = []
                offset = 0
                while offset < len(source):
                    match = next(
                        (token for token in ordered_tokens if source.startswith(token, offset)),
                        None,
                    )
                    self.assertIsNotNone(match, f"reference scanner failed at offset {offset}")
                    expected.append((tokenizer.vocabulary.token_id(match), match, offset))
                    offset += len(match)

                actual = [
                    (token.token_id, token.value, token.offset)
                    for token in tokenizer.tokenize(source)
                ]
                self.assertEqual(actual, expected)
                self.assertEqual(
                    tokenizer.decode(token_id for token_id, _value, _offset in actual),
                    source,
                )

    def test_longest_match_and_boundary_sequences_are_deterministic(self):
        tokenizer = MathTokenizer()
        for token in (r"\subseteq", r"\supseteq", r"\Rightarrow", r"\Leftrightarrow", r"\notin"):
            with self.subTest(token=token):
                ids = tokenizer.encode(token)
                self.assertEqual(ids, [tokenizer.vocabulary.token_id(token)])
                self.assertEqual(tokenizer.decode(ids), token)
        self.assertEqual(tokenizer.encode(""), [])
        self.assertEqual(tokenizer.decode([]), "")
        pad_id = tokenizer.vocabulary.token_id("<PAD>")
        self.assertEqual(tokenizer.decode([pad_id]), "")
        self.assertEqual(tokenizer.decode([pad_id], skip_special_tokens=False), "<PAD>")

    def test_unicode_error_offsets_are_python_codepoint_offsets(self):
        tokenizer = MathTokenizer()
        for text, offset in (("x+🙂", 2), ("x\u0301", 1), ("x\u00a0y", 1)):
            with self.subTest(text=text):
                with self.assertRaisesRegex(ValueError, f"offset {offset}"):
                    tokenizer.encode(text)

    def test_non_text_input_and_non_integer_decode_ids_are_rejected(self):
        tokenizer = MathTokenizer()
        with self.assertRaises(TypeError):
            tokenizer.encode(b"x+y")
        for token_ids in ([1.0], ["1"], [None]):
            with self.subTest(token_ids=token_ids), self.assertRaises(TypeError):
                tokenizer.decode(token_ids)

    def test_vocab_is_fixed_and_does_not_assign_unknown_characters(self):
        tokenizer = MathTokenizer()
        before = tokenizer.vocabulary.to_json()
        with self.assertRaisesRegex(ValueError, "unsupported mathematical character"):
            tokenizer.encode("x+🧮")
        self.assertEqual(tokenizer.vocabulary.to_json(), before)

    def test_decode_rejects_boolean_and_out_of_range_token_ids(self):
        tokenizer = MathTokenizer()
        for token_id in (True, -1, len(tokenizer.vocabulary)):
            with self.subTest(token_id=token_id):
                with self.assertRaises((TypeError, ValueError)):
                    tokenizer.decode([token_id])


if __name__ == "__main__":
    unittest.main()
