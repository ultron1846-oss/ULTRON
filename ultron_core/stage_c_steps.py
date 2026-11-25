"""Bounded exact-rational step verifier for Stage C benchmark traces.

It evaluates a small arithmetic AST, never Python code, and does not invoke a
model or generate training examples.
"""
from __future__ import annotations
import ast
import operator
import re
from fractions import Fraction
from typing import Mapping

_NAME=re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
_BINOPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}
_UNARY={ast.UAdd:operator.pos,ast.USub:operator.neg}
_MAX_EXPR_CHARS=512
_MAX_AST_NODES=128

def _fraction(value):
    if isinstance(value,bool): raise ValueError("boolean is not a rational value")
    if isinstance(value,Fraction): return value
    if isinstance(value,int): return Fraction(value)
    if isinstance(value,str):
        try: return Fraction(value.strip())
        except (ValueError,ZeroDivisionError) as exc: raise ValueError("invalid exact rational") from exc
    raise ValueError("value must be an integer or rational string")

def _evaluate(node,values):
    if isinstance(node,ast.Expression): return _evaluate(node.body,values)
    if isinstance(node,ast.Constant) and isinstance(node.value,(int,float)) and not isinstance(node.value,bool):
        return Fraction(str(node.value))
    if isinstance(node,ast.Name):
        if node.id not in values: raise ValueError(f"unknown or forward reference: {node.id}")
        return values[node.id]
    if isinstance(node,ast.BinOp) and type(node.op) in _BINOPS:
        left=_evaluate(node.left,values); right=_evaluate(node.right,values)
        if isinstance(node.op,ast.Div) and right==0: raise ValueError("division by zero")
        return _BINOPS[type(node.op)](left,right)
    if isinstance(node,ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_evaluate(node.operand,values))
    raise ValueError(f"unsupported expression syntax: {type(node).__name__}")

def verify_rational_steps(steps,final_expression,expected_answer):
    """Verify named exact-rational steps in order and the final answer.

    Each step is {'name': identifier, 'expression': arithmetic expression,
    'claimed_value': exact rational}. References may only point backward.
    """
    if not isinstance(steps,(list,tuple)): raise TypeError("steps must be a list or tuple")
    if not isinstance(final_expression,str) or not final_expression.strip(): raise ValueError("final_expression must be non-empty")
    values={}; reports=[]; issues=[]
    for index,step in enumerate(steps):
        if not isinstance(step,Mapping): raise ValueError(f"step {index} must be a mapping")
        name=step.get("name"); expression=step.get("expression"); claim=step.get("claimed_value")
        if not isinstance(name,str) or not _NAME.fullmatch(name): raise ValueError(f"step {index} has invalid name")
        if name in values: raise ValueError(f"duplicate step name: {name}")
        if not isinstance(expression,str) or not expression.strip() or len(expression)>_MAX_EXPR_CHARS:
            raise ValueError(f"step {name} expression must be 1..{_MAX_EXPR_CHARS} characters")
        try:
            tree=ast.parse(expression,mode="eval")
            if sum(1 for _ in ast.walk(tree))>_MAX_AST_NODES: raise ValueError("expression exceeds AST node limit")
            actual=_evaluate(tree,values)
            claimed=_fraction(claim)
            correct=actual==claimed
            if correct: values[name]=actual
            reports.append({"name":name,"expression":expression,"computed_value":str(actual),"claimed_value":str(claimed),"correct":correct})
            if not correct: issues.append(f"step {name} claimed value does not match its expression")
        except (SyntaxError,ValueError,ZeroDivisionError,TypeError,OverflowError) as exc:
            reports.append({"name":name,"expression":expression,"correct":False,"error":str(exc)})
            issues.append(f"step {name}: {exc}")
    final_value=None; final_correct=False
    try:
        if len(final_expression)>_MAX_EXPR_CHARS:
            raise ValueError("final expression exceeds complexity limit")
        tree=ast.parse(final_expression,mode="eval")
        if sum(1 for _ in ast.walk(tree))>_MAX_AST_NODES:
            raise ValueError("final expression exceeds complexity limit")
        final_value=_evaluate(tree,values)
        final_correct=final_value==_fraction(expected_answer)
        if not final_correct: issues.append("final expression does not match reference answer")
    except (SyntaxError,ValueError,ZeroDivisionError,TypeError,OverflowError) as exc:
        issues.append(f"final expression: {exc}")
    return {"schema_version":1,"verification_kind":"bounded_exact_rational_step_trace",
            "step_count":len(steps),"verified_steps":sum(bool(x.get("correct")) for x in reports),
            "steps":reports,"final_expression":final_expression,
            "computed_final_value":str(final_value) if final_value is not None else None,
            "final_answer_correct":final_correct,"trace_valid":not issues,
            "issues":issues,"model_invoked":False,"training_performed":False,
            "data_generated":False,"external_ai_api_used":False,
            "limitations":["Verifies only exact rational arithmetic in a restricted expression grammar.",
                           "Does not assess natural-language decomposition, theorem proofs, or general word-problem reasoning."]}
