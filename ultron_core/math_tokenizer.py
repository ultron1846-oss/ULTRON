"""Deterministic, lossless lexical tokenization for a documented math subset.

This is a lexer, not a parser or a symbolic algebra system. Numeric literals are
represented as stable digit/operator tokens, avoiding per-number vocabulary growth.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

TOKENIZER_VERSION = 1
SPECIAL_TOKENS = ("<PAD>", "<BOS>", "<EOS>")

# Longest-match operators are listed explicitly; their order is canonicalized below.
MULTI_TOKENS = (
    r"\notin", r"\subseteq", r"\supseteq", r"\rightarrow", r"\Rightarrow",
    r"\Leftrightarrow", r"\forall", r"\exists", r"\partial", r"\nabla",
    r"\sqrt", r"\sum", r"\prod", r"\int", r"\lim", r"\infty", r"\alpha",
    r"\beta", r"\gamma", r"\delta", r"\theta", r"\lambda", r"\mu",
    r"\pi", r"\sigma", r"\phi", r"\omega", r"\in", r"\subset",
    r"\supset", r"\cup", r"\cap", r"\land", r"\lor", r"\neg",
    r"\cdot", r"\times", r"\leq", r"\geq", r"\neq", r"\approx",
    r"\equiv", r"\pm", r"\to", r"\mapsto", r"\frac",
)

SINGLE_TOKENS = tuple(
    list("0123456789")
    + list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    + [" ", "\t", "\n", "\r"]
    + list("+-*/=<>!^_()[]{}.,:;|&%")
    + list("±×÷≤≥≠≈∑∏∫∂∇√∞∈∉⊂⊆⊃⊇∪∩∀∃→⇒⇔∧∨¬∥‖·πℝℤℚℂℕ")
    + list("αβγδεζηθικλμνξοπρστυφχψωΓΔΘΛΞΠΣΦΨΩ")
    + list("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎")
)
CANONICAL_TOKENS = SPECIAL_TOKENS + tuple(dict.fromkeys(
    sorted(MULTI_TOKENS, key=lambda item: (-len(item), item))
    + list(dict.fromkeys(SINGLE_TOKENS))
))
VOCAB_SIZE = len(CANONICAL_TOKENS)


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate vocabulary JSON key: {key}")
        result[key] = value
    return result


@dataclass(frozen=True)
class MathToken:
    token_id: int
    kind: str
    value: str
    offset: int


class MathVocabulary:
    """Versioned immutable token-to-ID mapping with strict JSON validation."""

    def __init__(self, tokens: Iterable[str] = CANONICAL_TOKENS, version: int = TOKENIZER_VERSION):
        tokens = tuple(tokens)
        if isinstance(version, bool) or not isinstance(version, int) or version != TOKENIZER_VERSION:
            raise ValueError("unsupported tokenizer vocabulary version")
        if not tokens or any(not isinstance(token, str) or not token for token in tokens):
            raise ValueError("vocabulary tokens must be non-empty strings")
        if len(set(tokens)) != len(tokens):
            raise ValueError("vocabulary tokens must be unique")
        if tokens[:len(SPECIAL_TOKENS)] != SPECIAL_TOKENS:
            raise ValueError("reserved special tokens must occupy the first vocabulary IDs")
        if tokens != CANONICAL_TOKENS:
            raise ValueError("vocabulary tokens do not match the canonical version-1 order")
        self.version = version
        self.tokens = tokens
        self._ids = {token: index for index, token in enumerate(tokens)}
        self._lexer_tokens = tuple(sorted(tokens[len(SPECIAL_TOKENS):],
                                           key=lambda item: (-len(item), item)))

    @classmethod
    def default(cls) -> "MathVocabulary":
        return cls()

    def __len__(self) -> int:
        return len(self.tokens)

    def token_id(self, token: str) -> int:
        try:
            return self._ids[token]
        except KeyError as exc:
            raise ValueError(f"token is not in vocabulary: {token!r}") from exc

    def to_dict(self) -> dict:
        return {"schema_version": self.version, "tokens": list(self.tokens)}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")) + "\n"

    @classmethod
    def from_dict(cls, value: dict) -> "MathVocabulary":
        if not isinstance(value, dict) or set(value) != {"schema_version", "tokens"}:
            raise ValueError("vocabulary document must contain schema_version and tokens only")
        if not isinstance(value["tokens"], list):
            raise TypeError("vocabulary tokens must be a list")
        return cls(value["tokens"], value["schema_version"])

    @classmethod
    def from_json(cls, value: str) -> "MathVocabulary":
        try:
            parsed = json.loads(value, object_pairs_hook=_reject_duplicate_json_keys)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid vocabulary JSON") from exc
        return cls.from_dict(parsed)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "MathVocabulary":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


class MathTokenizer:
    """Longest-match lexer; whitespace and source spelling are preserved."""

    def __init__(self, vocabulary: MathVocabulary | None = None):
        self.vocabulary = vocabulary or MathVocabulary.default()
        self._tokens = self.vocabulary._lexer_tokens

    @staticmethod
    def _kind(value: str) -> str:
        if value in (" ", "\t", "\n", "\r"):
            return "whitespace"
        if value.isdigit():
            return "digit"
        if value in ("(", ")", "[", "]", "{", "}", ",", ";"):
            return "delimiter"
        if value.startswith("\\") or value in "+-*/=<>!^_|&%":
            return "operator"
        if value.isalpha():
            return "identifier"
        return "symbol"

    def assert_compatible_config(self, config) -> None:
        """Fail closed when a model/checkpoint config uses another tokenizer asset."""
        if getattr(config, "tokenizer_version", None) != self.vocabulary.version:
            raise ValueError("model config tokenizer version does not match vocabulary")
        if getattr(config, "vocab_size", None) != len(self.vocabulary):
            raise ValueError("model config vocabulary size does not match vocabulary")
        if getattr(config, "pad_token_id", None) != self.vocabulary.token_id("<PAD>"):
            raise ValueError("model config padding token ID does not match vocabulary")

    def tokenize(self, text: str) -> tuple[MathToken, ...]:
        if not isinstance(text, str):
            raise TypeError("mathematical input must be a string")
        result: list[MathToken] = []
        offset = 0
        while offset < len(text):
            match = next((token for token in self._tokens if text.startswith(token, offset)), None)
            if match is None:
                raise ValueError(f"unsupported mathematical character {text[offset]!r} at offset {offset}")
            result.append(MathToken(self.vocabulary.token_id(match),
                                    self._kind(match), match, offset))
            offset += len(match)
        return tuple(result)

    def encode(self, text: str, *, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        ids = [token.token_id for token in self.tokenize(text)]
        if add_bos:
            ids.insert(0, self.vocabulary.token_id("<BOS>"))
        if add_eos:
            ids.append(self.vocabulary.token_id("<EOS>"))
        return ids

    def decode(self, token_ids: Iterable[int], *, skip_special_tokens: bool = True) -> str:
        pieces = []
        for token_id in token_ids:
            if isinstance(token_id, bool) or not isinstance(token_id, int):
                raise TypeError("token IDs must be integers")
            if token_id < 0 or token_id >= len(self.vocabulary):
                raise ValueError(f"token ID outside vocabulary: {token_id}")
            token = self.vocabulary.tokens[token_id]
            if skip_special_tokens and token in SPECIAL_TOKENS:
                continue
            pieces.append(token)
        return "".join(pieces)
