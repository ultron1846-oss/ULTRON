"""Recursive-descent parser for ULTRON's explicitly supported scalar-math grammar.

The parser converts lexer output into the existing typed Expr IR. It does not
use eval/exec, infer mathematical domains, or claim support for full LaTeX.
"""
from __future__ import annotations

from fractions import Fraction

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


class _RecursiveParser:
    def __init__(self, tokens: tuple[MathToken, ...]):
        self.tokens = tuple(token for token in tokens if token.kind != "whitespace")
        self.position = 0
        self.end_offset = (
            tokens[-1].offset + len(tokens[-1].value) if tokens else 0
        )

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
        operand = self._parse_unary()
        if operator.value == "+":
            return operand
        return Expr(ExprKind.NEG, args=(operand,))

    def _parse_power(self) -> Expr:
        base = self._parse_primary()
        if self._accept("^") is not None:
            exponent = self._parse_unary()
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
        if first.value in _LATEX_SYMBOLS:
            return Expr(ExprKind.SYMBOL, value=_LATEX_SYMBOLS[first.value])
        pieces = [first.value]
        previous_end = first.offset + len(first.value)
        while self._is_identifier(self._peek()) and self._peek().offset == previous_end:
            token = self._take()
            pieces.append(token.value)
            previous_end = token.offset + len(token.value)
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
        if self._accept("(") is not None:
            expression = self._parse_sum()
            self._expect(")")
            return expression
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

    def __init__(self, tokenizer: MathTokenizer | None = None):
        self.tokenizer = tokenizer or MathTokenizer()

    def parse(self, source: str) -> Expr:
        tokens = self.tokenizer.tokenize(source)
        return _RecursiveParser(tokens).parse()


def parse_math(source: str, tokenizer: MathTokenizer | None = None) -> Expr:
    """Convenience function for parsing source text into an Expr."""
    return MathParser(tokenizer).parse()
