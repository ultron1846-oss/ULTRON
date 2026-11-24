from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class ExprKind(str, Enum):
    INTEGER="integer"; RATIONAL="rational"; SYMBOL="symbol"; ADD="add"; MUL="mul"; POW="pow"; NEG="neg"; EQUAL="equal"

@dataclass(frozen=True)
class Expr:
    kind: ExprKind
    value: str | int | None = None
    args: tuple["Expr", ...] = ()
    assumptions: tuple[str, ...] = ()

    def __post_init__(self):
        arity={ExprKind.INTEGER:0,ExprKind.RATIONAL:0,ExprKind.SYMBOL:0,ExprKind.ADD:None,ExprKind.MUL:None,ExprKind.POW:2,ExprKind.NEG:1,ExprKind.EQUAL:2}[self.kind]
        if arity is not None and len(self.args)!=arity: raise ValueError(f"{self.kind.value} requires {arity} args")
        if self.kind in (ExprKind.INTEGER,ExprKind.RATIONAL,ExprKind.SYMBOL) and self.value is None: raise ValueError("atomic expression requires value")
        if self.kind not in (ExprKind.INTEGER,ExprKind.RATIONAL,ExprKind.SYMBOL) and self.value is not None: raise ValueError("operator expression cannot have value")

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

    def can_enter_trusted_knowledge(self)->bool:
        return self.status == VerificationStatus.FORMALLY_VERIFIED
