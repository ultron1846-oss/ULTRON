"""Round-trip and strict-schema contracts for ULTRON's canonical math tokenizer."""
import json
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

    def test_decode_rejects_boolean_and_out_of_range_token_ids(self):
        tokenizer = MathTokenizer()
        for token_id in (True, -1, len(tokenizer.vocabulary)):
            with self.subTest(token_id=token_id):
                with self.assertRaises((TypeError, ValueError)):
                    tokenizer.decode([token_id])


if __name__ == "__main__":
    unittest.main()
