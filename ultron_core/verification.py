from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from .math_ir import Expr,ExprKind,FormulaCandidate,VerificationStatus

@dataclass(frozen=True)
class ProbeResult:
    status:VerificationStatus
    samples_checked:int
    counterexample:dict[str,Fraction]|None
    note:str

def evaluate(expr:Expr,env:dict[str,Fraction])->Fraction:
    if expr.kind==ExprKind.INTEGER: return Fraction(int(expr.value))
    if expr.kind==ExprKind.RATIONAL: return Fraction(str(expr.value))
    if expr.kind==ExprKind.SYMBOL:
        if str(expr.value) not in env: raise ValueError(f"missing {expr.value}")
        return env[str(expr.value)]
    vals=[evaluate(a,env) for a in expr.args]
    if expr.kind==ExprKind.ADD: return sum(vals,Fraction(0))
    if expr.kind==ExprKind.MUL:
        out=Fraction(1)
        for value in vals: out*=value
        return out
    if expr.kind==ExprKind.NEG: return -vals[0]
    if expr.kind==ExprKind.POW:
        if vals[1].denominator!=1: raise ValueError("integer exponents only")
        return vals[0]**int(vals[1])
    raise ValueError(f"unsupported expression {expr.kind.value}")

def probe_candidate(candidate:FormulaCandidate,variable_names=("x","y"),sample_values=(-3,-2,-1,0,1,2,3))->ProbeResult:
    eq=candidate.expression
    if eq.kind!=ExprKind.EQUAL: raise ValueError("candidate must be equality")
    checked=0
    for values in product(sample_values,repeat=len(variable_names)):
        env={name:Fraction(v) for name,v in zip(variable_names,values)}
        try: lhs,rhs=(evaluate(a,env) for a in eq.args)
        except (ZeroDivisionError,ValueError): continue
        checked+=1
        if lhs!=rhs:
            return ProbeResult(VerificationStatus.REJECTED,checked,env,"Finite-domain counterexample found.")
    return ProbeResult(VerificationStatus.EXPERIMENTALLY_SUPPORTED,checked,None,
                       "No counterexample in tested finite domain; this is not a proof.")
