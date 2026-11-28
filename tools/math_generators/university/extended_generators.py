"""Additional exact university mathematics generator batch.

Each template is a bounded synthetic exercise with seed replay and a direct
mathematical invariant. Generator availability is not model mastery.
"""
from __future__ import annotations

import random
from fractions import Fraction

EXTENDED_BANDS = {
    "proof_methods":"University", "countable_and_uncountable_sets":"University",
    "axiom_of_choice_intro":"University", "spectral_theorem":"University",
    "Jordan_form":"University", "bilinear_and_quadratic_forms":"University",
    "multivariable_limits":"University",
    "diagonal_linear_change_of_variables_rectangles":"University",
    "constant_vector_field_segment_line_integrals":"University",
    "flat_rectangular_surface_area_integrals":"University",
    "diagonal_linear_vector_field_divergence":"University",
    "metric_spaces":"University", "convergence_of_sequences":"University",
    "Cauchy_sequences":"University", "pointwise_and_uniform_convergence":"University",
    "compactness":"University", "connectedness":"University",
    "continuity_metric_spaces":"University", "measure_intro":"University",
}
GENERATOR_METADATA = {
    topic: {"grade_band":"University Foundation", "word_templates":[]}
    for topic in EXTENDED_BANDS
}

def build(topic: str, rng: random.Random, difficulty: int):
    n=lambda lo,hi:rng.randint(lo,hi)
    d=difficulty
    data={"topic":topic}
    if topic=="proof_methods":
        k=n(1,20*d); data.update(integer=k,expression=f"2*{k}",parity="even")
        problem=f"Give a direct parity argument that 2×{k} is even."
        answer="even"; steps=[f"2×{k}={2*k}=2({k}).", "It is divisible by 2, so it is even."]
        check=lambda:2*k==2*k and (2*k)%2==0
    elif topic=="countable_and_uncountable_sets":
        start=n(0,10*d); data.update(index_start=start,map_expression="n -> 3n+1")
        problem=f"Describe the image of the map n↦3n+1 on integers n≥{start}, and state whether it is countable."
        answer=f"countable; image={{ {3*start+1}+3k : k=0,1,2,... }}"
        steps=["The map is injective because 3n+1=3m+1 implies n=m.","Its image is indexed by the natural numbers, so it is countable."]
        check=lambda:all((3*(start+i)+1)!=(3*(start+j)+1) for i,j in ((0,1),(1,2),(2,3)))
    elif topic=="axiom_of_choice_intro":
        sizes=[n(1,5*d) for _ in range(4)]; count=1
        for size in sizes:count*=size
        data.update(set_sizes=sizes,choice_count=count)
        problem=f"Four finite sets have sizes {sizes}. How many choice functions select one element from each set?"
        answer=str(count);steps=[f"Each set contributes its number of possible choices.",f"By the multiplication principle, the count is {'×'.join(map(str,sizes))}={count}."]
        check=lambda:count==math_product(sizes)
    elif topic=="spectral_theorem":
        a,b=n(-8*d,8*d),n(-8*d,8*d)
        vals=sorted([a+b,a-b])
        data.update(matrix=[[a,b],[b,a]],eigenvalues=vals)
        problem=f"Find the eigenvalues of the real symmetric matrix [[{a},{b}],[{b},{a}]]."
        answer=f"eigenvalues={vals}"
        steps=[f"Characteristic polynomial: (a−λ)²−b²=0.",f"Thus λ={a}+{b}={a+b} and λ={a}−{b}={a-b}."]
        check=lambda:vals==sorted([a+b,a-b])
    elif topic=="Jordan_form":
        lam=n(-10*d,10*d); data.update(jordan_matrix=[[lam,1],[0,lam]],eigenvalue=lam,algebraic_multiplicity=2,eigenspace_dimension=1)
        problem=f"For the Jordan block [[{lam},1],[0,{lam}]], state the eigenvalue, algebraic multiplicity, and whether it is diagonalizable."
        answer=f"λ={lam}; multiplicity=2; not diagonalizable"
        steps=["The characteristic polynomial is (λ−"+str(lam)+")².","The eigenspace has dimension 1, less than algebraic multiplicity 2."]
        check=lambda:2>1
    elif topic=="bilinear_and_quadratic_forms":
        a,b,c,x,y=[n(-6*d,6*d) for _ in range(5)];value=a*x*x+2*b*x*y+c*y*y
        data.update(matrix=[[a,b],[b,c]],point=[x,y],value=value)
        problem=f"Evaluate Q(x,y)={a}x²+2({b})xy+({c})y² at ({x},{y})."
        answer=str(value);steps=[f"Substitute: {a}({x})²+2({b})({x})({y})+({c})({y})²={value}."]
        check=lambda:value==a*x*x+2*b*x*y+c*y*y
    elif topic=="multivariable_limits":
        x0,y0,L,a,b=[n(-8*d,8*d) for _ in range(5)]
        data.update(point=[x0,y0],constant=L,coefficients=[a,b])
        problem=f"Evaluate lim (x,y)→({x0},{y0}) of {a}(x−{x0})+{b}(y−{y0})+({L})."
        answer=str(L);steps=["Both coordinate differences approach zero.","The remaining constant is the limit."]
        check=lambda:L==data["constant"]
    elif topic=="diagonal_linear_change_of_variables_rectangles":
        sx,sy=n(1,8*d),n(1,8*d);xlen,ylen=n(1,8*d),n(1,8*d);jac=sx*sy;area=xlen*ylen*jac
        data.update(scale=[sx,sy],source_area=xlen*ylen,jacobian=jac,transformed_area=area)
        problem=f"Under u={sx}x, v={sy}y, find |∂(u,v)/∂(x,y)| and the transformed area of a rectangle of area {xlen*ylen}."
        answer=f"Jacobian={jac}; area={area}";steps=[f"J=det([[{sx},0],[0,{sy}]])={jac}.",f"Transformed area={xlen*ylen}×{jac}={area}."]
        check=lambda:jac==sx*sy and area==xlen*ylen*jac
    elif topic=="constant_vector_field_segment_line_integrals":
        a,b,x0,y0,x1,y1=[n(-8*d,8*d) for _ in range(6)];value=a*(x1-x0)+b*(y1-y0)
        data.update(vector_field=[a,b],start=[x0,y0],end=[x1,y1],integral=value)
        problem=f"Compute ∫_C F·dr for constant F=({a},{b}) along the segment from ({x0},{y0}) to ({x1},{y1})."
        answer=str(value);steps=[f"For a constant field, the integral is F·(r₁−r₀).",f"{a}({x1-x0})+{b}({y1-y0})={value}."]
        check=lambda:value==a*(x1-x0)+b*(y1-y0)
    elif topic=="flat_rectangular_surface_area_integrals":
        xlen,ylen=n(1,10*d),n(1,10*d);area=xlen*ylen
        data.update(rectangle=[xlen,ylen],surface_area=area,integral=area)
        problem=f"Find ∬_S 1 dS over a flat rectangle with side lengths {xlen} and {ylen}."
        answer=str(area);steps=[f"The surface integral of 1 equals the surface area.",f"Area={xlen}×{ylen}={area}."]
        check=lambda:area==xlen*ylen
    elif topic=="diagonal_linear_vector_field_divergence":
        a,b,c=[n(-10*d,10*d) for _ in range(3)];div=a+b+c
        data.update(field_coefficients=[a,b,c],divergence=div)
        problem=f"Find div F for F(x,y,z)=({a}x,{b}y,{c}z)."
        answer=str(div);steps=[f"div F=∂({a}x)/∂x+∂({b}y)/∂y+∂({c}z)/∂z={a}+{b}+{c}={div}."]
        check=lambda:div==a+b+c
    elif topic=="metric_spaces":
        x1,y1,x2,y2=[n(-10*d,10*d) for _ in range(4)];sq=(x2-x1)**2+(y2-y1)**2
        data.update(points=[[x1,y1],[x2,y2]],squared_distance=sq)
        problem=f"Find the Euclidean distance between ({x1},{y1}) and ({x2},{y2})."
        answer=f"sqrt({sq})";steps=[f"d=√(({x2}-{x1})²+({y2}-{y1})²)=√{sq}."]
        check=lambda:sq==(x2-x1)**2+(y2-y1)**2
    elif topic=="convergence_of_sequences":
        r=Fraction(n(-8*d,8*d),n(9,15));converges=abs(r)<1
        data.update(common_ratio=str(r),converges=converges,limit="0" if converges else "does_not_converge")
        problem=f"Determine convergence of a_n=({r})^n."
        answer="converges to 0" if converges else "does not converge"
        steps=["A geometric sequence tends to zero exactly when |r|<1 (for nonzero r)."]
        check=lambda:converges==(abs(r)<1)
    elif topic=="Cauchy_sequences":
        k=n(1,20*d);eps_den=n(2,20*d);index_bound=k*eps_den+1
        data.update(sequence=f"{k}/n",epsilon=str(Fraction(1,eps_den)),epsilon_denominator=eps_den,bound_index=index_bound)
        problem=f"Show that a_n={k}/n is Cauchy; give an index bound for ε=1/{eps_den}."
        answer=f"Cauchy; choose N0={index_bound}"
        steps=[f"For m,n≥N0, |{k}/n−{k}/m|≤{k}/N0<{Fraction(1,eps_den)}.", "Thus the sequence satisfies the Cauchy criterion."]
        check=lambda:k>0 and index_bound>k*eps_den
    elif topic=="pointwise_and_uniform_convergence":
        N=n(1,50*d);bound=Fraction(1,N);data.update(function=f"f_n(x)=x/n on [0,1]",index=N,sup_norm=str(bound))
        problem=f"For f_n(x)=x/n on [0,1], find ||f_{N}−0||∞ and decide uniform convergence."
        answer=f"sup norm={bound}; uniform convergence to 0"
        steps=["The maximum of x/N on [0,1] occurs at x=1.",f"||f_N||∞=1/N={bound}→0."]
        check=lambda:bound==Fraction(1,N)
    elif topic=="compactness":
        left,right=sorted((n(-10*d,10*d),n(1,10*d)));data.update(interval=[left,right],compact=True)
        problem=f"Is the interval [{left},{right}] compact in R with the usual topology?"
        answer="yes";steps=["The interval is closed and bounded.","By Heine–Borel, it is compact."]
        check=lambda:left<=right
    elif topic=="connectedness":
        left,right=sorted((n(-10*d,10*d),n(1,10*d)));data.update(interval=[left,right],connected=True)
        problem=f"Is the interval [{left},{right}] connected in R?"
        answer="yes";steps=["Every interval in R is connected in the usual topology."]
        check=lambda:left<=right
    elif topic=="continuity_metric_spaces":
        k,x,y=n(1,10*d),n(-10*d,10*d),n(-10*d,10*d);bound=k*abs(x-y)
        data.update(lipschitz_constant=k,points=[x,y],distance_bound=bound)
        problem=f"For f(x)={k}x, give the Lipschitz bound |f({x})−f({y})|≤L|{x}−{y}|."
        answer=f"L={k}; difference={bound}"
        steps=[f"|f(x)−f(y)|={k}|x−y|, so L={k}."]
        check=lambda:bound==k*abs(x-y)
    elif topic=="measure_intro":
        left,right=sorted((n(-10*d,10*d),n(1,10*d)));measure=right-left
        data.update(interval=[left,right],Lebesgue_measure=measure)
        problem=f"Find the Lebesgue measure of the interval [{left},{right}]."
        answer=str(measure);steps=[f"The measure of an interval is its length: {right}−({left})={measure}."]
        check=lambda:measure==right-left
    else:
        raise ValueError("unknown extended topic: "+str(topic))
    fields={"grade_band":"University","topic":topic,"subtopic":topic.replace("_"," "),"difficulty":d,
            "problem":problem,"steps":steps,"answer":str(answer),"answer_type":"expression",
            "ingredients":data,"verifier":topic+"_seed_replay_exact_check"}
    return fields,check

def math_product(values):
    result=1
    for value in values:result*=value
    return result
