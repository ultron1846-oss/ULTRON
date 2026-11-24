from dataclasses import replace
from .math_ir import Expr,ExprKind,FormulaCandidate,VerificationStatus

def symbol(name:str)->Expr:
    if not name.isidentifier(): raise ValueError("invalid symbol")
    return Expr(ExprKind.SYMBOL,value=name)

def integer(value:int)->Expr: return Expr(ExprKind.INTEGER,value=value)

def equality(lhs:Expr,rhs:Expr,assumptions=())->FormulaCandidate:
    return FormulaCandidate(Expr(ExprKind.EQUAL,args=(lhs,rhs),assumptions=tuple(assumptions)),assumptions=tuple(assumptions))

def polynomial_identity_candidates()->list[FormulaCandidate]:
    """Hand-authored seed templates; this is not autonomous discovery."""
    x,y=symbol("x"),symbol("y")
    return [
        equality(Expr(ExprKind.ADD,args=(x,y)),Expr(ExprKind.ADD,args=(y,x))),
        equality(Expr(ExprKind.MUL,args=(x,y)),Expr(ExprKind.MUL,args=(y,x))),
        equality(Expr(ExprKind.MUL,args=(x,Expr(ExprKind.ADD,args=(y,integer(1))))),
                 Expr(ExprKind.ADD,args=(Expr(ExprKind.MUL,args=(x,y)),x)))
    ]

def mark_experimental(candidate:FormulaCandidate,evidence:tuple[str,...])->FormulaCandidate:
    if not evidence: raise ValueError("evidence is required")
    return replace(candidate,status=VerificationStatus.EXPERIMENTALLY_SUPPORTED,evidence=evidence)
