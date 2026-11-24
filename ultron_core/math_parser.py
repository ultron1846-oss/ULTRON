"""Recursive-descent parser for ULTRON's explicitly supported scalar-math grammar.

The parser converts lexer output into the existing typed Expr IR. It does not
use eval/exec, infer mathematical domains, or claim support for full LaTeX.
"""
from __future__ import annotations

from fractions import Fraction
import re

from .math_ir import Expr, ExprKind
from .math_tokenizer import MathToken, MathTokenizer


class MathParseError(ValueError):
    """A syntax error with a source-character offset."""

    def __init__(self, message: str, offset: int):
        self.offset = offset
        super().__init__(f"{message} at offset {offset}")


_LATEX_SYMBOLS = {
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ",
    r"\delta": "δ", r"\theta": "θ", r"\lambda": "λ",
    r"\mu": "μ", r"\pi": "π", r"\sigma": "σ",
    r"\phi": "φ", r"\omega": "ω",
}

_SUPERSCRIPT_DIGITS = dict(zip("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789"))
_SUPERSCRIPT_SIGNS = {"⁺": "+", "⁻": "-"}


class _RecursiveParser:
    def __init__(self, tokens: tuple[MathToken, ...], max_nesting: int):
        self.tokens = tuple(token for token in tokens if token.kind != "whitespace")
        self.position = 0
        self.max_nesting = max_nesting
        self.nesting = 0
        self.end_offset = tokens[-1].offset + len(tokens[-1].value) if tokens else 0

    def _enter(self, offset: int) -> None:
        self.nesting += 1
        if self.nesting > self.max_nesting:
            self.nesting -= 1
            raise MathParseError("maximum parser nesting exceeded", offset)

    def _leave(self) -> None:
        self.nesting -= 1

    def _peek(self) -> MathToken | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def _take(self) -> MathToken:
        token = self._peek()
        if token is None:
            raise MathParseError("unexpected end of input", self.end_offset)
        self.position += 1
        return token

    def _accept(self, *values: str) -> MathToken | None:
        token = self._peek()
        if token is not None and token.value in values:
            self.position += 1
            return token
        return None

    def _expect(self, value: str) -> MathToken:
        token = self._accept(value)
        if token is None:
            current = self._peek()
            offset = current.offset if current is not None else self.end_offset
            raise MathParseError(f"expected {value!r}", offset)
        return token

    @staticmethod
    def _is_digit(token: MathToken | None) -> bool:
        return token is not None and token.kind == "digit"

    @staticmethod
    def _is_identifier(token: MathToken | None) -> bool:
        return token is not None and token.kind == "identifier"

    def parse(self) -> Expr:
        if not self.tokens:
            raise MathParseError("expression is empty", 0)
        expression = self._parse_equality()
        remaining = self._peek()
        if remaining is not None:
            raise MathParseError(
                f"unexpected token {remaining.value!r}", remaining.offset
            )
        return expression

    def _parse_equality(self) -> Expr:
        left = self._parse_sum()
        operator = self._accept("=")
        if operator is None:
            return left
        right = self._parse_sum()
        if self._peek() is not None and self._peek().value == "=":
            raise MathParseError("chained equality is not supported", self._peek().offset)
        return Expr(ExprKind.EQUAL, args=(left, right))

    def _parse_sum(self) -> Expr:
        result = self._parse_product()
        while True:
            operator = self._accept("+", "-")
            if operator is None:
                return result
            right = self._parse_product()
            kind = ExprKind.ADD if operator.value == "+" else ExprKind.SUB
            result = Expr(kind, args=(result, right))

    def _starts_primary(self, token: MathToken | None) -> bool:
        if token is None:
            return False
        return (
            self._is_digit(token)
            or self._is_identifier(token)
            or token.value in ("(", ".")
            or token.value in _LATEX_SYMBOLS
        )

    def _parse_product(self) -> Expr:
        result = self._parse_unary()
        while True:
            operator = self._accept("*", "×", "·", "/", "÷")
            if operator is not None:
                right = self._parse_unary()
                kind = ExprKind.MUL if operator.value in ("*", "×", "·") else ExprKind.DIV
                result = Expr(kind, args=(result, right))
                continue

            following = self._peek()
            if not self._starts_primary(following):
                return result

            # f(x) is deliberately not interpreted as f multiplied by x:
            # function-call semantics do not yet exist in the current IR.
            if result.kind == ExprKind.SYMBOL and following.value == "(":
                raise MathParseError(
                    "function-call syntax is not supported; function IR is not implemented",
                    following.offset,
                )
            right = self._parse_unary()
            result = Expr(ExprKind.MUL, args=(result, right))

    def _parse_unary(self) -> Expr:
        operator = self._accept("+", "-")
        if operator is None:
            return self._parse_power()
        self._enter(operator.offset)
        try:
            operand = self._parse_unary()
        finally:
            self._leave()
        if operator.value == "+":
            return operand
        return Expr(ExprKind.NEG, args=(operand,))

    def _parse_power(self) -> Expr:
        base = self._parse_primary()
        token = self._peek()
        if token is not None and (
            token.value in _SUPERSCRIPT_DIGITS or token.value in _SUPERSCRIPT_SIGNS
        ):
            start = token.offset
            previous_end = start
            sign = 1
            if token.value in _SUPERSCRIPT_SIGNS:
                sign = -1 if token.value == "⁻" else 1
                self.position += 1
                previous_end += len(token.value)
            digits = []
            while self._peek() is not None and self._peek().value in _SUPERSCRIPT_DIGITS:
                current = self._peek()
                if current.offset != previous_end:
                    break
                self.position += 1
                digits.append(_SUPERSCRIPT_DIGITS[current.value])
                previous_end = current.offset + len(current.value)
            if not digits:
                raise MathParseError("superscript sign must be followed by digits", start)
            exponent = Expr(ExprKind.INTEGER, value=sign * int("".join(digits)))
            base = Expr(ExprKind.POW, args=(base, exponent))

        operator = self._accept("^")
        if operator is not None:
            self._enter(operator.offset)
            try:
                exponent = self._parse_unary()
            finally:
                self._leave()
            return Expr(ExprKind.POW, args=(base, exponent))
        return base

    def _parse_number(self) -> Expr:
        first = self._peek()
        assert first is not None
        pieces = []
        previous_end = first.offset

        if first.value == ".":
            pieces.append(".")
            self.position += 1
            next_token = self._peek()
            if not self._is_digit(next_token) or next_token.offset != previous_end + 1:
                raise MathParseError("decimal point must be followed by digits", first.offset)
            previous_end += 1
        while self._is_digit(self._peek()) and self._peek().offset == previous_end:
            token = self._take()
            pieces.append(token.value)
            previous_end = token.offset + len(token.value)

        if self._peek() is not None and self._peek().value == ".":
            dot = self._peek()
            if dot.offset == previous_end:
                self.position += 1
                pieces.append(".")
                previous_end += 1
                if not self._is_digit(self._peek()) or self._peek().offset != previous_end:
                    raise MathParseError("decimal point must be followed by digits", dot.offset)
                while self._is_digit(self._peek()) and self._peek().offset == previous_end:
                    token = self._take()
                    pieces.append(token.value)
                    previous_end = token.offset + len(token.value)

        raw = "".join(pieces)
        try:
            if "." in raw:
                exact = Fraction(raw)
                return Expr(ExprKind.RATIONAL, value=f"{exact.numerator}/{exact.denominator}")
            return Expr(ExprKind.INTEGER, value=int(raw))
        except (ValueError, ZeroDivisionError) as exc:
            raise MathParseError("invalid exact numeric literal", first.offset) from exc

    def _parse_identifier(self) -> Expr:
        first = self._take()
        pieces = [_LATEX_SYMBOLS.get(first.value, first.value)]
        previous_end = first.offset + len(first.value)

        # A contiguous alphanumeric name is one symbol (for example velocity2).
        if first.value not in _LATEX_SYMBOLS:
            while (
                (self._is_identifier(self._peek()) or self._is_digit(self._peek()))
                and self._peek().offset == previous_end
            ):
                token = self._take()
                pieces.append(token.value)
                previous_end = token.offset + len(token.value)

        # Support one simple subscript: x_1, x_i and x_{12}.
        underscore = self._peek()
        if underscore is not None and underscore.value == "_" and underscore.offset == previous_end:
            self.position += 1
            pieces.append("_")
            previous_end = underscore.offset + 1
            braced = self._peek()
            if braced is not None and braced.value == "{" and braced.offset == previous_end:
                self.position += 1
                previous_end += 1
                subscript = []
                while self._peek() is not None and self._peek().value != "}":
                    token = self._peek()
                    if token.offset != previous_end or not (
                        self._is_identifier(token) or self._is_digit(token)
                    ):
                        raise MathParseError("subscript must contain contiguous letters or digits", token.offset)
                    token = self._take()
                    subscript.append(token.value)
                    previous_end = token.offset + len(token.value)
                closing = self._peek()
                if closing is None or closing.value != "}" or closing.offset != previous_end or not subscript:
                    offset = closing.offset if closing is not None else self.end_offset
                    raise MathParseError("invalid braced subscript", offset)
                self.position += 1
                pieces.extend(subscript)
            else:
                subscript = []
                while self._peek() is not None and self._peek().offset == previous_end and (
                    self._is_identifier(self._peek()) or self._is_digit(self._peek())
                ):
                    token = self._take()
                    subscript.append(token.value)
                    previous_end = token.offset + len(token.value)
                if not subscript:
                    raise MathParseError("subscript marker must be followed by letters or digits", underscore.offset)
                pieces.extend(subscript)

        name = "".join(pieces)
        if not name.isidentifier():
            raise MathParseError("invalid identifier", first.offset)
        return Expr(ExprKind.SYMBOL, value=name)

    def _parse_primary(self) -> Expr:
        token = self._peek()
        if token is None:
            raise MathParseError("expected a number, symbol or parenthesized expression", self.end_offset)
        if self._is_digit(token) or token.value == ".":
            return self._parse_number()
        if self._is_identifier(token) or token.value in _LATEX_SYMBOLS:
            return self._parse_identifier()
        opening = self._accept("(")
        if opening is not None:
            self._enter(opening.offset)
            try:
                expression = self._parse_sum()
                self._expect(")")
                return expression
            finally:
                self._leave()
        raise MathParseError(
            f"unsupported token {token.value!r}; this grammar accepts scalar arithmetic and equality",
            token.offset,
        )


class MathParser:
    """Parse supported mathematical text into ULTRON's existing Expr IR.

    Grammar: exact decimal/integer literals, identifiers, parentheses, unary
    signs, +, -, *, /, ×, ·, ÷, right-associative integer/general powers, and
    one top-level equality. Adjacent factors imply multiplication (2x, 2(x+1)).
    Contiguous letters form one identifier (velocity), never an implicit product.
    """

    def __init__(
        self,
        tokenizer: MathTokenizer | None = None,
        *,
        max_source_chars: int = 100_000,
        max_tokens: int = 1_024,
        max_nesting: int = 128,
    ):
        for name, value in (
            ("max_source_chars", max_source_chars),
            ("max_tokens", max_tokens),
            ("max_nesting", max_nesting),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        self.tokenizer = tokenizer or MathTokenizer()
        self.max_source_chars = max_source_chars
        self.max_tokens = max_tokens
        self.max_nesting = max_nesting

    def parse(self, source: str) -> Expr:
        if not isinstance(source, str):
            raise TypeError("mathematical input must be a string")
        if len(source) > self.max_source_chars:
            raise MathParseError("maximum source length exceeded", self.max_source_chars)
        try:
            tokens = self.tokenizer.tokenize(source)
        except ValueError as exc:
            match = re.search(r"at offset (\d+)$", str(exc))
            if match is None:
                raise
            message = str(exc).rsplit(" at offset ", 1)[0]
            raise MathParseError(message, int(match.group(1))) from exc
        if len(tokens) > self.max_tokens:
            raise MathParseError("maximum token count exceeded", tokens[self.max_tokens].offset)
        return _RecursiveParser(tokens, self.max_nesting).parse()


def parse_math(source: str, tokenizer: MathTokenizer | None = None) -> Expr:
    """Convenience function for parsing source text into an Expr."""
    return MathParser(tokenizer).parse(source)
