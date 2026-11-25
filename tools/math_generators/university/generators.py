"""Deterministic university-foundation math practice generators.

These are exact synthetic exercise templates, not a trained model or broad
university-level solver. Each item is independently recomputable from its seed.
"""
from __future__ import annotations

import math
import random
from fractions import Fraction

BANDS = {
    "linear_algebra": "University",
    "multivariable_calculus": "University",
    "differential_equations": "University",
    "discrete_mathematics": "University",
    "real_analysis": "University",
    "abstract_algebra": "University",
    "optimization": "University",
    "numerical_methods": "University",
    "probability_theory": "University",
}
TOPICS = tuple(BANDS)
GENERATOR_METADATA = {
    topic: {"grade_band": "University Foundation", "word_templates": []}
    for topic in TOPICS
}


def _build(topic: str, rng: random.Random, difficulty: int):
    n = lambda lo, hi: rng.randint(lo, hi)
    d = difficulty
    data = {"topic": topic}
    if topic == "linear_algebra":
        a,b,c,e=[n(-8*d,8*d) for _ in range(4)]
        det=a*e-b*c
        u,v=n(-5*d,5*d),n(-5*d,5*d)
        out=(a*u+b*v,c*u+e*v)
        data.update(matrix=[a,b,c,e],determinant=det,vector=[u,v],product=list(out))
        problem=f"For A=[[{a},{b}],[{c},{e}]] and v=({u},{v}), find det(A) and Av."
        answer=f"det={det}; Av=({out[0]},{out[1]})"
        steps=[f"det(A)={a}×{e}−{b}×{c}={det}.",f"Av=({a}×{u}+{b}×{v},{c}×{u}+{e}×{v})=({out[0]},{out[1]})."]
        exact=lambda:det==a*e-b*c and out==(a*u+b*v,c*u+e*v)
    elif topic == "multivariable_calculus":
        a,b,c,x,y=[n(-5*d,5*d) for _ in range(6)]
        dx=2*a*x+b*y; dy=b*x+2*c*y
        data.update(coefficients=[a,b,c],point=[x,y],partial_x=dx,partial_y=dy)
        problem=f"For f(x,y)={a}x²+({b})xy+({c})y², compute both partial derivatives at ({x},{y})."
        answer=f"df/dx={dx}; df/dy={dy}"
        steps=[f"∂f/∂x=2({a})x+({b})y; at point: {dx}.",f"∂f/∂y=({b})x+2({c})y; at point: {dy}."]
        exact=lambda:dx==2*a*x+b*y and dy==b*x+2*c*y
    elif topic == "differential_equations":
        k,y0=n(-4*d,4*d),n(1,8*d)
        data.update(rate=k,initial_value=y0,solution=f"{y0}*exp({k}t)")
        problem=f"Solve y'=({k})y with initial condition y(0)={y0}."
        answer=f"y(t)={y0}e^({k}t)"
        steps=["Separate variables: dy/y=k dt.",f"Integrate: ln|y|=kt+C.",f"Apply y(0)={y0}: y(t)={y0}e^({k}t)."]
        exact=lambda:y0>0 and data["solution"]==f"{y0}*exp({k}t)"
    elif topic == "discrete_mathematics":
        a,b,m=n(2,20*d),n(1,12*d),n(2,30*d)
        value=pow(a,b,m)
        data.update(base=a,exponent=b,modulus=m,result=value)
        problem=f"Compute {a}^{b} modulo {m}."
        answer=str(value)
        steps=[f"Evaluate the integer power {a}^{b}.",f"Take the remainder modulo {m}: {value}."]
        exact=lambda:0<=value<m and value==pow(a,b,m)
    elif topic == "real_analysis":
        c,n0=n(1,30*d),n(1,20*d)
        data.update(numerator=c,sequence=f"{c}/n",limit="0",sample_index=n0,sample_value=str(Fraction(c,n0)))
        problem=f"Find the limit as n→∞ of the sequence a_n={c}/n."
        answer="0"
        steps=[f"For every ε>0, choose N>{c}/ε.",f"Then n≥N implies |{c}/n−0|<{c}/N<ε.", "Therefore the sequence converges to 0."]
        exact=lambda:c>0 and data["limit"]=="0"
    elif topic == "abstract_algebra":
        order,k=n(2,30*d),n(0,30*d)
        element=k%order
        element_order=order//math.gcd(order,element)
        data.update(group=f"Z/{order}Z",modulus=order,element=element,element_order=element_order)
        problem=f"In the additive cyclic group Z/{order}Z, find the order of element [{element}]."
        answer=str(element_order)
        steps=[f"The order is the least positive r with r×{element}≡0 (mod {order}).",f"ord([{element}])={order}/gcd({order},{element})={element_order}."]
        exact=lambda:element_order==order//math.gcd(order,element) and (element*element_order)%order==0
    elif topic == "optimization":
        a=n(1,5*d); b,c=n(-10*d,10*d),n(-10*d,10*d)
        xv=Fraction(-b,2*a); yv=Fraction(4*a*c-b*b,4*a)
        data.update(a=a,b=b,c=c,vertex_x=str(xv),minimum=str(yv))
        problem=f"Find the minimum and minimizer of f(x)={a}x²+({b})x+({c})."
        answer=f"x={xv}; minimum={yv}"
        steps=[f"Since a={a}>0, the parabola opens upward.",f"Vertex x=−b/(2a)={xv}.",f"Substitution gives f(x)={yv}."]
        exact=lambda:a>0 and xv==Fraction(-b,2*a) and yv==a*xv*xv+b*xv+c
    elif topic == "numerical_methods":
        target=n(2,30*d); x0=Fraction(n(target+1,4*target+10),1)
        x1=(x0+Fraction(target,x0))/2
        data.update(target=target,initial=str(x0),newton_step=str(x1),equation=f"x^2-{target}=0")
        problem=f"Perform one Newton iteration for x²−{target}=0 starting at x₀={x0}."
        answer=str(x1)
        steps=[f"f(x)=x²−{target}, f'(x)=2x.",f"x₁=x₀−f(x₀)/f'(x₀)=(x₀+{target}/x₀)/2={x1}."]
        exact=lambda:x0>0 and x1==(x0+Fraction(target,x0))/2
    elif topic == "probability_theory":
        disease,nondisease,positive_disease,positive_nondisease=[n(1,20*d) for _ in range(4)]
        numerator=disease*positive_disease
        denominator=numerator+nondisease*positive_nondisease
        posterior=Fraction(numerator,denominator)
        data.update(prior_cases=disease,prior_non_cases=nondisease,positive_given_case=positive_disease,positive_given_noncase=positive_nondisease,posterior=str(posterior))
        problem=f"Bayes count model: {disease} cases with positive rate {positive_disease}/{disease} and {nondisease} non-cases with positive rate {positive_nondisease}/{nondisease}. Find P(case|positive)."
        answer=f"{posterior.numerator}/{posterior.denominator}"
        steps=[f"Positive cases={disease}×{positive_disease}={numerator}.",f"All positives={numerator}+{nondisease}×{positive_nondisease}={denominator}.",f"Posterior={numerator}/{denominator}={answer}."]
        exact=lambda:denominator>0 and posterior==Fraction(numerator,denominator) and 0<=posterior<=1
    else:
        raise ValueError("unknown topic: "+str(topic))
    fields={"grade_band":BANDS[topic],"topic":topic,"subtopic":topic.replace("_"," "),"difficulty":d,
            "problem":problem,"steps":steps,"answer":str(answer),"answer_type":"expression",
            "ingredients":data,"verifier":topic+"_seed_replay_exact_check"}
    return fields, exact


def generate(seed: int, difficulty: int=1, topic: str="linear_algebra") -> dict:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise TypeError("seed must be int")
    if difficulty not in (1,2,3,4,5):
        raise ValueError("difficulty must be 1..5")
    if topic not in BANDS:
        raise ValueError("unknown topic: "+str(topic))
    fields,check=_build(topic,random.Random(seed),difficulty)
    fields.update(id=f"university-{topic}-{seed}-{difficulty}",seed=seed)
    if not check():
        raise ArithmeticError("exact answer verification failed")
    replay,_=_build(topic,random.Random(seed),difficulty)
    if replay!={k:v for k,v in fields.items() if k not in ("id","seed")}:
        raise ArithmeticError("deterministic replay failed")
    return fields


def verify(problem: dict) -> bool:
    try:
        return generate(problem["seed"],problem["difficulty"],problem["topic"])==problem
    except (KeyError,TypeError,ValueError,ArithmeticError,ZeroDivisionError):
        return False


GENERATORS={t:(lambda seed,difficulty=1,topic=t:generate(seed,difficulty,topic)) for t in TOPICS}
