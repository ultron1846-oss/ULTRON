from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import json

SUPPORTED_FUNCTIONS = frozenset({"sin", "cos", "tan", "asin", "acos", "atan", "exp", "ln", "log", "sqrt", "abs"})\n\n\nclass ExprKind(str, Enum):
    INTEGER="integer"; RATIONAL="rational"; SYMBOL="symbol"; ADD="add"; SUB="sub"; MUL="mul"; DIV="div"; POW="pow"; NEG="neg"; CALL="call"; EQUAL="equal"; NOT_EQUAL="not_equal"; LESS_THAN="less_than"; LESS_EQUAL="less_equal"; GREATER_THAN="greater_than"; GREATER_EQUAL="greater_equal"

@dataclass(frozen=True)
class Expr:
    kind: ExprKind
    value: str | int | None = None
    args: tuple["Expr", ...] = ()
    assumptions: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.kind, ExprKind):
            raise TypeError("kind must be an ExprKind")
        if not isinstance(self.args, tuple) or any(not isinstance(arg, Expr) for arg in self.args):
            raise TypeError("args must be a tuple of Expr nodes")
        if not isinstance(self.assumptions, tuple) or any(not isinstance(item, str) for item in self.assumptions):
            raise TypeError("assumptions must be a tuple of strings")
        arity = {
            ExprKind.INTEGER: 0, ExprKind.RATIONAL: 0, ExprKind.SYMBOL: 0,
            ExprKind.ADD: None, ExprKind.SUB: 2, ExprKind.MUL: None, ExprKind.DIV: 2, ExprKind.POW: 2,
            ExprKind.NEG: 1, ExprKind.CALL: 1, ExprKind.EQUAL: 2, ExprKind.NOT_EQUAL: 2,
            ExprKind.LESS_THAN: 2, ExprKind.LESS_EQUAL: 2, ExprKind.GREATER_THAN: 2, ExprKind.GREATER_EQUAL: 2,
        }[self.kind]
        if arity is not None and len(self.args) != arity:
            raise ValueError(f"{self.kind.value} requires {arity} args")
        if self.kind in (ExprKind.ADD, ExprKind.MUL) and len(self.args) < 2:
            raise ValueError(f"{self.kind.value} requires at least two args")
        if self.kind == ExprKind.INTEGER:
            if isinstance(self.value, bool) or not isinstance(self.value, int):
                raise TypeError("integer expression value must be an int")
        elif self.kind == ExprKind.RATIONAL:
            if isinstance(self.value, bool) or not isinstance(self.value, (str, int)):
                raise TypeError("rational expression value must be a string or int")
            try:
                Fraction(str(self.value))
            except (ValueError, ZeroDivisionError) as exc:
                raise ValueError("rational expression value must be a valid non-zero-denominator rational") from exc
        elif self.kind == ExprKind.SYMBOL:
            if not isinstance(self.value, str) or not self.value.isidentifier():
                raise ValueError("symbol expression value must be a valid identifier")
        elif self.value is not None:
            raise ValueError("operator expression cannot have value")

    def to_dict(self) -> dict:
        """Return a lossless, version-independent structural representation."""
        return {
            "kind": self.kind.value,
            "value": self.value,
            "args": [argument.to_dict() for argument in self.args],
            "assumptions": list(self.assumptions),
        }

    @classmethod
    def from_dict(cls, value: dict) -> "Expr":
        if not isinstance(value, dict) or set(value) != {"kind", "value", "args", "assumptions"}:
            raise ValueError("expression document must contain kind, value, args and assumptions only")
        if not isinstance(value["kind"], str):
            raise TypeError("expression kind must be a string")
        if not isinstance(value["args"], list) or not isinstance(value["assumptions"], list):
            raise TypeError("expression args and assumptions must be lists")
        try:
            kind = ExprKind(value["kind"])
        except ValueError as exc:
            raise ValueError(f"unsupported expression kind: {value['kind']}") from exc
        args = tuple(cls.from_dict(argument) for argument in value["args"])
        assumptions = tuple(value["assumptions"])
        return cls(kind=kind, value=value["value"], args=args, assumptions=assumptions)

    def canonical_json(self) -> str:
        """Canonical structural JSON; this does not perform algebraic simplification."""
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"))

    def structural_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class VerificationStatus(str, Enum):
    CANDIDATE="candidate"; EXPERIMENTALLY_SUPPORTED="experimentally_supported"; DERIVED="derived"; FORMALLY_VERIFIED="formally_verified"; REJECTED="rejected"; UNRESOLVED="unresolved"

@dataclass(frozen=True)
class FormulaCandidate:
    expression: Expr
    domain: tuple[str,...]=()
    assumptions: tuple[str,...]=()
    provenance: tuple[str,...]=()
    status: VerificationStatus=VerificationStatus.CANDIDATE
    evidence: tuple[str,...]=()
    candidate_id: str=""

    def __post_init__(self) -> None:
        if not isinstance(self.expression, Expr):
            raise TypeError("expression must be an Expr")
        for name in ("domain", "assumptions", "provenance", "evidence"):
            value = getattr(self, name)
            if not isinstance(value, tuple) or any(not isinstance(item, str) for item in value):
                raise TypeError(f"{name} must be a tuple of strings")
        if not isinstance(self.status, VerificationStatus):
            raise TypeError("status must be a VerificationStatus")
        if not isinstance(self.candidate_id, str):
            raise TypeError("candidate_id must be a string")

    def can_enter_trusted_knowledge(self) -> bool:
        """Fail closed until a real proof-kernel receipt can be validated.

        The status enum is ordinary candidate metadata and can be constructed
        by callers; it is not evidence that a theorem was formally checked.
        """
        return False
