from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

class ExprKind(str, Enum):
    INTEGER="integer"; RATIONAL="rational"; SYMBOL="symbol"; ADD="add"; MUL="mul"; POW="pow"; NEG="neg"; EQUAL="equal"

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
            ExprKind.ADD: None, ExprKind.MUL: None, ExprKind.POW: 2,
            ExprKind.NEG: 1, ExprKind.EQUAL: 2,
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

    def can_enter_trusted_knowledge(self) -> bool:
        """Fail closed until a real proof-kernel receipt can be validated.

        The status enum is ordinary candidate metadata and can be constructed
        by callers; it is not evidence that a theorem was formally checked.
        """
        return False
