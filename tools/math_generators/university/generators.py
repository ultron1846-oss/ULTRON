"""Deterministic university-foundation math practice generators.

These are exact synthetic exercise templates, not a trained model or broad
university-level solver. Each item is independently recomputable from its seed.
"""
from __future__ import annotations

import math
import random
from fractions import Fraction

from .extended_generators import EXTENDED_BANDS, build as build_extended

BANDS = {
    "linear_algebra": "University",
    "multivariable_calculus": "University",
    "differential_equations": "University",
    "discrete_mathematics": "University",
    "abstract_algebra": "University",
    "optimization": "University",
    "numerical_methods": "University",
    "probability_theory": "University",
    "sets_and_functions": "University",
    "propositional_logic": "University",
    "mathematical_induction": "University",
    "vectors_and_vector_spaces": "University",
    "systems_linear_equations": "University",
    "eigenvalues_and_eigenvectors": "University",
    "Taylor_series": "University",
    "conditional_probability": "University",
    "counting_principles": "University",
    "predicate_logic": "University",
    "relations_and_equivalence": "University",
    "subspaces_and_span": "University",
    "linear_independence": "University",
    "basis_and_dimension": "University",
    "matrix_rank": "University",
    "limits_and_continuity": "University",
    "derivative_theory": "University",
    "quantifiers": "University",
    "cardinality": "University",
    "linear_transformations": "University",
    "diagonalization": "University",
    "inner_product_spaces": "University",
    "orthogonality_and_projection": "University",
    "least_squares": "University",
    "mean_value_theorems": "University",
    "Riemann_integral": "University",
    "improper_integrals": "University",
    "sequences_and_series": "University",
    "power_series": "University",
    "gradient_and_directional_derivatives": "University",
    "chain_rule_multivariable": "University",
}
BANDS.update(EXTENDED_BANDS)
TOPICS = tuple(BANDS)
WORD_TOPICS = {"conditional_probability", "counting_principles"}
GENERATOR_METADATA = {
    topic: {
        "grade_band": "University Foundation",
        "word_templates": (
            ["population-count conditional probability scenario"]
            if topic == "conditional_probability"
            else ["wardrobe-combination counting scenario"]
            if topic == "counting_principles"
            else []
        ),
    }
    for topic in TOPICS
}


def _build(topic: str, rng: random.Random, difficulty: int):
    if topic in EXTENDED_BANDS:
        return build_extended(topic, rng, difficulty)
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
        a,b,c,x,y=[n(-5*d,5*d) for _ in range(5)]
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
        disease,nondisease=n(1,20*d),n(1,20*d)
        positive_disease,positive_nondisease=n(0,disease),n(0,nondisease)
        if positive_disease+positive_nondisease==0:
            positive_disease=1
        numerator=positive_disease
        denominator=positive_disease+positive_nondisease
        posterior=Fraction(numerator,denominator)
        data.update(prior_cases=disease,prior_non_cases=nondisease,positive_given_case=positive_disease,positive_given_noncase=positive_nondisease,posterior=str(posterior))
        problem=f"Bayes count model: {disease} cases with positive rate {positive_disease}/{disease} and {nondisease} non-cases with positive rate {positive_nondisease}/{nondisease}. Find P(case|positive)."
        answer=f"{posterior.numerator}/{posterior.denominator}"
        steps=[f"Positive cases={positive_disease} (the generated count among cases).",f"All positives={positive_disease}+{positive_nondisease}={denominator}.",f"Posterior={numerator}/{denominator}={answer}."]
        exact=lambda:denominator>0 and posterior==Fraction(numerator,denominator) and 0<=posterior<=1
    elif topic == "sets_and_functions":
        size_a,size_b=n(5,40*d),n(5,40*d)
        intersection=n(0,min(size_a,size_b))
        union=size_a+size_b-intersection
        data.update(size_a=size_a,size_b=size_b,intersection=intersection,union=union)
        problem=f"Two finite sets have |A|={size_a}, |B|={size_b}, and |A∩B|={intersection}. Find |A∪B|."
        answer=str(union)
        steps=[f"Use inclusion-exclusion: |A∪B|=|A|+|B|−|A∩B|.",f"{size_a}+{size_b}−{intersection}={union}."]
        exact=lambda:union==size_a+size_b-intersection and max(size_a,size_b)<=union<=size_a+size_b
    elif topic == "propositional_logic":
        p,q=bool(n(0,1)),bool(n(0,1))
        operator=rng.choice(("AND","OR","XOR","IMPLIES"))
        if operator=="AND":
            value=p and q
        elif operator=="OR":
            value=p or q
        elif operator=="XOR":
            value=p != q
        else:
            value=(not p) or q
        expected={"AND":p and q,"OR":p or q,"XOR":p != q,"IMPLIES":(not p) or q}[operator]
        data.update(p=p,q=q,operator=operator,value=value)
        problem=f"Evaluate p {operator} q when p={str(p).lower()} and q={str(q).lower()}."
        answer=str(value).lower()
        steps=[f"Apply the truth rule for {operator}.",f"The result is {str(value).lower()}."]
        exact=lambda:value==expected
    elif topic == "mathematical_induction":
        k=n(1,25*d)
        base_sum=1
        formula=Fraction(k*(k+1),2)
        lhs=Fraction(k*(k+1),2)+(k+1)
        rhs=Fraction((k+1)*(k+2),2)
        data.update(sample_n=k,formula="sum(1..n)=n(n+1)/2",base_case_sum=base_sum,induction_lhs=str(lhs),induction_rhs=str(rhs))
        problem=f"Prove by induction that 1+2+...+n=n(n+1)/2 for every n≥1; show the induction step at n={k}."
        answer="Base case: true. Induction step: n(n+1)/2+(n+1)=(n+1)(n+2)/2."
        steps=["Base n=1: 1=1(1+1)/2.",f"Assume the formula at n={k}.",f"Add n+1: n(n+1)/2+(n+1)=(n+1)(n+2)/2.", "Therefore the statement holds for all n≥1 by induction."]
        exact=lambda:base_sum==1 and formula==Fraction(k*(k+1),2) and lhs==rhs and lhs==Fraction((k+1)*(k+2),2)
    elif topic == "vectors_and_vector_spaces":
        u1,u2,v1,v2=n(-8*d,8*d),n(-8*d,8*d),n(-8*d,8*d),n(-8*d,8*d)
        alpha,beta=n(-5*d,5*d),n(-5*d,5*d)
        result=(alpha*u1+beta*v1,alpha*u2+beta*v2)
        data.update(u=[u1,u2],v=[v1,v2],alpha=alpha,beta=beta,linear_combination=list(result))
        problem=f"For u=({u1},{u2}), v=({v1},{v2}), compute {alpha}u+({beta})v."
        answer=f"({result[0]},{result[1]})"
        steps=[f"First component: {alpha}×{u1}+({beta})×{v1}={result[0]}.",f"Second component: {alpha}×{u2}+({beta})×{v2}={result[1]}."]
        exact=lambda:result==(alpha*u1+beta*v1,alpha*u2+beta*v2)
    elif topic == "systems_linear_equations":
        while True:
            a,b,c,e=[n(-8*d,8*d) for _ in range(4)]
            determinant=a*e-b*c
            if determinant:
                break
        x,y=n(-6*d,6*d),n(-6*d,6*d)
        r1,r2=a*x+b*y,c*x+e*y
        data.update(coefficients=[a,b,c,e],constants=[r1,r2],determinant=determinant,solution=[x,y])
        problem=f"Solve {a}x+({b})y={r1}; {c}x+({e})y={r2}."
        answer=f"x={x}; y={y}"
        steps=[f"Determinant Δ={a}×{e}−{b}×{c}={determinant}≠0, so the solution is unique.",f"Substitution confirms x={x}, y={y}."]
        exact=lambda:determinant==a*e-b*c and determinant!=0 and (a*x+b*y,c*x+e*y)==(r1,r2)
    elif topic == "eigenvalues_and_eigenvectors":
        a,b=n(-12*d,12*d),n(-12*d,12*d)
        data.update(matrix=[[a,0],[0,b]],eigenvalues=[a,b],eigenvectors=[[1,0],[0,1]])
        problem=f"Find the eigenvalues of the diagonal matrix A=[[{a},0],[0,{b}]]."
        answer=f"λ1={a}; λ2={b}"
        steps=[f"det(A−λI)=({a}−λ)({b}−λ).",f"The characteristic roots are λ={a} and λ={b}."]
        exact=lambda:data["matrix"]==[[a,0],[0,b]] and (a,b)==tuple(data["eigenvalues"]) and (a-a)*(a-b)==0 and (b-a)*(b-b)==0
    elif topic == "Taylor_series":
        a,b,c,h=n(-8*d,8*d),n(-8*d,8*d),n(-8*d,8*d),n(-5*d,5*d)
        fh=a*h*h+b*h+c
        derivative=2*a*h+b
        data.update(coefficients=[a,b,c],center=h,value_at_center=fh,derivative_at_center=derivative,taylor_quadratic=a)
        problem=f"Find the degree-2 Taylor polynomial of f(x)={a}x²+({b})x+({c}) centered at x={h}."
        answer=f"P2(x)={fh}+({derivative})(x−{h})+({a})(x−{h})²"
        steps=[f"f({h})={fh}.",f"f'({h})={derivative}.",f"f''/2={a}.", "Use P₂(x)=f(h)+f'(h)(x−h)+f''(h)(x−h)²/2."]
        exact=lambda:fh==a*h*h+b*h+c and derivative==2*a*h+b and all(fh+derivative*(x-h)+a*(x-h)**2==a*x*x+b*x+c for x in (h-1,h,h+1))
    elif topic == "conditional_probability":
        b_total=n(1,40*d)
        intersection=n(0,b_total)
        probability=Fraction(intersection,b_total)
        data.update(condition_count=b_total,event_and_condition_count=intersection,conditional_probability=str(probability))
        problem=f"Among {b_total} outcomes satisfying condition B, {intersection} also satisfy event A. Find P(A|B)."
        answer=f"{probability.numerator}/{probability.denominator}"
        steps=[f"P(A|B)=count(A∩B)/count(B).",f"{intersection}/{b_total}={answer}."]
        exact=lambda:b_total>0 and probability==Fraction(intersection,b_total) and 0<=probability<=1
    elif topic == "counting_principles":
        shirts,pants,shoes=n(2,12*d),n(2,10*d),n(2,8*d)
        total=shirts*pants*shoes
        data.update(shirt_choices=shirts,pants_choices=pants,shoe_choices=shoes,combinations=total)
        problem=f"A wardrobe has {shirts} shirts, {pants} pants, and {shoes} pairs of shoes. How many outfits choose one of each?"
        answer=str(total)
        steps=["Use the multiplication principle for independent choices.",f"{shirts}×{pants}×{shoes}={total} outfits."]
        exact=lambda:total==shirts*pants*shoes and total>0

    elif topic == "predicate_logic":
        size=n(2,8*d)
        threshold=n(0,size)
        quantifier=rng.choice(("forall","exists"))
        satisfying=[x for x in range(1,size+1) if x<=threshold]
        value=(len(satisfying)==size) if quantifier=="forall" else bool(satisfying)
        data.update(domain=list(range(1,size+1)),threshold=threshold,quantifier=quantifier,satisfying=satisfying,value=value)
        symbol="∀" if quantifier=="forall" else "∃"
        problem=f"Over the domain {{1,...,{size}}}, evaluate {symbol}x: x≤{threshold}."
        answer=str(value).lower()
        steps=[f"The values satisfying x≤{threshold} are {satisfying}.",f"The {quantifier} statement is {str(value).lower()}."]
        exact=lambda:value==((threshold==size) if quantifier=="forall" else threshold>=1)
    elif topic == "relations_and_equivalence":
        size=n(4,20*d)
        modulus=n(2,min(8,size))
        element=n(0,size-1)
        cls=[x for x in range(size) if x%modulus==element%modulus]
        data.update(domain=list(range(size)),modulus=modulus,element=element,equivalence_class=cls)
        problem=f"On {{0,...,{size-1}}}, define a~b iff a≡b (mod {modulus}). Find the equivalence class of {element}."
        answer=str(cls)
        steps=[f"Members of the class have remainder {element%modulus} modulo {modulus}.",f"The class is {cls}."]
        exact=lambda:cls==[x for x in range(size) if x%modulus==element%modulus]
    elif topic == "subspaces_and_span":
        x,y=n(-20*d,20*d),n(-20*d,20*d)
        data.update(vectors=[[1,0],[0,1]],target=[x,y],coefficients=[x,y])
        problem=f"Express ({x},{y}) as a linear combination of e1=(1,0) and e2=(0,1)."
        answer=f"{x}e1+({y})e2"
        steps=[f"Use the standard basis: ({x},{y})={x}(1,0)+({y})(0,1)."]
        exact=lambda:[x,y]==data["target"] and [x,y]==data["coefficients"]
    elif topic == "linear_independence":
        a,b,c,e=[n(-8*d,8*d) for _ in range(4)]
        determinant=a*e-b*c
        independent=determinant!=0
        data.update(vectors=[[a,b],[c,e]],determinant=determinant,independent=independent)
        problem=f"Determine whether vectors ({a},{b}) and ({c},{e}) in R² are linearly independent."
        answer="independent" if independent else "dependent"
        steps=[f"Form the determinant {a}×{e}−{b}×{c}={determinant}.",f"Nonzero determinant means {answer}."]
        exact=lambda:independent==(determinant!=0) and determinant==a*e-b*c
    elif topic == "basis_and_dimension":
        while True:
            a,b,c,e=[n(-8*d,8*d) for _ in range(4)]
            determinant=a*e-b*c
            if determinant!=0:
                break
        data.update(vectors=[[a,b],[c,e]],determinant=determinant,is_basis=True,dimension=2)
        problem=f"Do vectors ({a},{b}) and ({c},{e}) form a basis of R²? State the dimension."
        answer="yes; dimension=2"
        steps=[f"The determinant is {determinant}≠0, so the vectors are independent.", "Two independent vectors in R² form a basis; dim(R²)=2."]
        exact=lambda:determinant==a*e-b*c and determinant!=0 and data["dimension"]==2
    elif topic == "matrix_rank":
        a,b,c,e=[n(-6*d,6*d) for _ in range(4)]
        determinant=a*e-b*c
        rank=2 if determinant else (1 if any((a,b,c,e)) else 0)
        data.update(matrix=[[a,b],[c,e]],determinant=determinant,rank=rank)
        problem=f"Find the rank of matrix [[{a},{b}],[{c},{e}]]."
        answer=str(rank)
        steps=[f"The determinant is {determinant}.",f"Rank is {rank} by the 2×2 rank criterion."]
        exact=lambda:rank==(2 if determinant else (1 if any((a,b,c,e)) else 0))
    elif topic == "limits_and_continuity":
        center=n(-10*d,10*d)
        slope=n(-8*d,8*d)
        limit_value=n(-20*d,20*d)
        data.update(center=center,slope=slope,constant=limit_value,limit=limit_value)
        problem=f"Evaluate lim(x→{center}) [{slope}(x−{center})+({limit_value})]."
        answer=str(limit_value)
        steps=[f"As x approaches {center}, the term {slope}(x−{center}) approaches 0.",f"The limit is {limit_value}."]
        exact=lambda:limit_value==data["constant"]
    elif topic == "derivative_theory":
        a,b,c,x=n(-8*d,8*d),n(-8*d,8*d),n(-8*d,8*d),n(-10*d,10*d)
        derivative=2*a*x+b
        data.update(coefficients=[a,b,c],point=x,derivative_at_point=derivative)
        problem=f"For f(x)={a}x²+({b})x+({c}), find f'({x})."
        answer=str(derivative)
        steps=[f"Differentiate: f'(x)=2({a})x+({b}).",f"Substitute x={x}: f'({x})={derivative}."]
        exact=lambda:derivative==2*a*x+b


    elif topic == "quantifiers":
        size=n(2,10*d); threshold=n(0,size); quantifier=rng.choice(("forall","exists"))
        value=(threshold==size) if quantifier=="forall" else threshold>0
        data.update(domain=list(range(1,size+1)),threshold=threshold,quantifier=quantifier,value=value)
        problem=f"On the domain {{1,...,{size}}}, evaluate {('∀' if quantifier=='forall' else '∃')}x: x≤{threshold}."
        answer=str(value).lower()
        steps=[f"Exactly {threshold} domain values satisfy x≤{threshold}.",f"The quantified statement is {answer}."]
        exact=lambda:value==((threshold==size) if quantifier=="forall" else threshold>0)
    elif topic == "cardinality":
        size=n(1,40*d); modulus=n(2,10*d); residues=sorted({x%modulus for x in range(size)})
        data.update(set_size=size,modulus=modulus,distinct_residues=residues,cardinality=len(residues))
        problem=f"Let S={{0,1,...,{size-1}}}. How many distinct residues modulo {modulus} occur in S?"
        answer=str(len(residues))
        steps=[f"Count distinct remainders modulo {modulus} among the {size} integers.",f"There are {len(residues)} distinct residues."]
        exact=lambda:len(residues)==min(size,modulus)
    elif topic == "linear_transformations":
        a,b,c,e=[n(-6*d,6*d) for _ in range(4)]; x,y=n(-8*d,8*d),n(-8*d,8*d)
        result=(a*x+b*y,c*x+e*y)
        data.update(matrix=[a,b,c,e],vector=[x,y],image=list(result))
        problem=f"For T(x,y)=({a}x+({b})y,({c})x+({e})y), find T({x},{y})."
        answer=f"({result[0]},{result[1]})"
        steps=[f"Multiply the matrix by the vector: ({a}×{x}+{b}×{y},{c}×{x}+{e}×{y})={result}."]
        exact=lambda:result==(a*x+b*y,c*x+e*y)
    elif topic == "diagonalization":
        a,b=n(-10*d,10*d),n(-10*d,10*d)
        data.update(matrix=[[a,0],[0,b]],diagonal_entries=[a,b],diagonalizable=True)
        problem=f"Is diagonal matrix [[{a},0],[0,{b}]] diagonalizable? Give its diagonal entries."
        answer=f"yes; D=diag({a},{b})"
        steps=["Every diagonal matrix is already diagonalized by the identity matrix.",f"The diagonal entries are {a} and {b}."]
        exact=lambda:data["diagonalizable"] and data["diagonal_entries"]==[a,b]
    elif topic == "inner_product_spaces":
        x,y,u,v=n(-10*d,10*d),n(-10*d,10*d),n(-10*d,10*d),n(-10*d,10*d)
        dot=x*u+y*v
        data.update(vector=[x,y],other=[u,v],inner_product=dot)
        problem=f"Compute the standard inner product of ({x},{y}) and ({u},{v}) in R²."
        answer=str(dot)
        steps=[f"⟨u,v⟩={x}×{u}+{y}×{v}={dot}."]
        exact=lambda:dot==x*u+y*v
    elif topic == "orthogonality_and_projection":
        x,y=n(-10*d,10*d),n(-10*d,10*d)
        dot=x*1+y*0
        data.update(vector=[x,y],onto=[1,0],dot_product=dot,projection=[x,0])
        problem=f"Project ({x},{y}) orthogonally onto the x-axis."
        answer=f"({x},0)"
        steps=["The projection onto the x-axis keeps the first coordinate and sets the second to zero.",f"Projection=({x},0)."]
        exact=lambda:data["projection"]==[x,0] and dot==x
    elif topic == "least_squares":
        a,b,c=n(-10*d,10*d),n(-10*d,10*d),n(-10*d,10*d)
        denominator=a*a+b*b
        if denominator==0: a=1; denominator=1
        scalar=Fraction(a*c,denominator)
        data.update(column=[a,b],target=[c,0],normal_equation_coefficient=str(scalar),squared_norm=denominator)
        problem=f"Find the least-squares scalar t minimizing ||t({a},{b})−({c},0)||²."
        answer=str(scalar)
        steps=[f"Minimizer t=(v·w)/(v·v)=({a}×{c})/({denominator})={scalar}."]
        exact=lambda:scalar==Fraction(a*c,a*a+b*b)
    elif topic == "mean_value_theorems":
        a,b,c=n(-8*d,8*d),n(-8*d,8*d),n(-8*d,8*d)
        left,right=sorted((n(-5*d,5*d),n(1,6*d)))
        if left==right: right+=1
        slope=Fraction(a*(right**2-left**2)+b*(right-left),right-left)
        c_value=Fraction(left+right,2)
        data.update(coefficients=[a,b,c],interval=[left,right],mean_value_point=str(c_value),secant_slope=str(slope))
        problem=f"For f(x)={a}x²+({b})x+({c}) on [{left},{right}], find a c satisfying the Mean Value Theorem."
        answer=f"c={c_value}"
        steps=[f"Secant slope is {slope}.",f"f'(x)=2({a})x+({b}); x=({left}+{right})/2={c_value} gives the secant slope."]
        exact=lambda:Fraction(2*a*c_value+b)==slope
    elif topic == "Riemann_integral":
        a,b=n(-8*d,8*d),n(-8*d,8*d); left,right=sorted((n(-5*d,5*d),n(1,8*d)))
        integral=Fraction(a*(right**2-left**2),2)+b*(right-left)
        data.update(linear_coefficients=[a,b],interval=[left,right],integral=str(integral))
        problem=f"Evaluate the definite integral ∫[{left},{right}] ({a}x+({b})) dx."
        answer=str(integral)
        steps=[f"An antiderivative is ({a}/2)x²+({b})x.",f"Evaluate at the endpoints to obtain {integral}."]
        exact=lambda:integral==Fraction(a*(right**2-left**2),2)+b*(right-left)
    elif topic == "improper_integrals":
        p=n(2,6*d); value=Fraction(1,p-1)
        data.update(power=p,integral_from_one=value,converges=True)
        problem=f"Evaluate the convergent improper integral ∫[1,∞) 1/x^{p} dx."
        answer=str(value)
        steps=[f"For p={p}>1, the integral converges.",f"∫₁∞ x^(-{p})dx=1/({p}−1)={value}."]
        exact=lambda:p>1 and value==Fraction(1,p-1)
    elif topic == "sequences_and_series":
        r=Fraction(n(-8*d,8*d),n(9,15))
        if abs(r)>=1: r=Fraction(1,3)
        first=n(-10*d,10*d); total=Fraction(first,1)/(1-r)
        data.update(first_term=first,common_ratio=str(r),sum=str(total),converges=True)
        problem=f"Find the sum of the infinite geometric series with first term {first} and ratio {r}."
        answer=str(total)
        steps=[f"|r|={abs(r)}<1, so the series converges.",f"Sum=a₁/(1−r)={first}/(1−({r}))={total}."]
        exact=lambda:abs(r)<1 and total==Fraction(first,1)/(1-r)
    elif topic == "power_series":
        center=n(-5*d,5*d); radius=n(1,8*d); x=center+n(-5,5)
        data.update(center=center,coefficient=1,radius=radius,test_point=x,converges=abs(x-center)<radius)
        problem=f"Determine whether the geometric power series Σ((x−{center})/{radius})^n converges at x={x}."
        answer="converges" if abs(x-center)<radius else "diverges"
        steps=[f"A geometric series converges exactly when |(x−{center})/{radius}|<1.",f"At x={x}, the series {answer}."]
        exact=lambda:(data["converges"]==(abs(x-center)<radius)) and (answer==("converges" if abs(x-center)<radius else "diverges"))
    elif topic == "gradient_and_directional_derivatives":
        a,b,x,y,u,v=n(-8*d,8*d),n(-8*d,8*d),n(-8*d,8*d),n(-8*d,8*d),n(-5*d,5*d),n(-5*d,5*d)
        directional=2*a*x*u+2*b*y*v
        data.update(coefficients=[a,b],point=[x,y],direction=[u,v],gradient=[2*a*x,2*b*y],directional_derivative=directional)
        problem=f"For f(x,y)={a}x²+{b}y², find the directional derivative at ({x},{y}) along vector ({u},{v}) (not normalized)."
        answer=str(directional)
        steps=[f"Gradient=(2({a})x,2({b})y).",f"Dot with direction ({u},{v}) gives {directional}."]
        exact=lambda:directional==2*a*x*u+2*b*y*v
    elif topic == "chain_rule_multivariable":
        a,b,t=n(-8*d,8*d),n(-8*d,8*d),n(-6*d,6*d)
        x=t*t; y=3*t+1; value=2*a*x*(2*t)+b*(3)
        data.update(coefficients=[a,b],parameter=t,x_value=x,y_value=y,derivative=value)
        problem=f"If f(x,y)={a}x²+{b}y, x=t² and y=3t+1, find df/dt at t={t}."
        answer=str(value)
        steps=[f"df/dt=(2({a})x)(2t)+({b})(3).",f"Substitute t={t}, x={x}: df/dt={value}."]
        exact=lambda:value==4*a*t**3+3*b

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
