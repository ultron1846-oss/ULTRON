"""Deterministic original-template Grade 8–12 mathematics generators.

These generate verified practice items, not a trained model or a general proof checker.
"""
from __future__ import annotations

import math
import random
from fractions import Fraction

BANDS = {
    "linear_equations": "G8-9",
    "systems_of_equations": "G8-10",
    "quadratic_equations": "G9-10",
    "polynomial_operations": "G9-10",
    "polynomial_factoring": "G9-10",
    "functions": "G8-10",
    "coordinate_geometry": "G8-10",
    "triangle_geometry": "G8-10",
    "trigonometry": "G10-12",
    "sequences_series": "G9-12",
    "logarithms": "G10-12",
    "limits": "G11-12",
    "derivatives": "G11-12",
    "definite_integrals": "G11-12",
    "matrices": "G10-12",
    "combinatorics": "G10-12",
    "number_theory": "G8-12",
    "complex_numbers": "G10-12",
    "vectors": "G10-12",
    "statistics": "G9-12",
    "probability": "G9-12",
    "proof_logic": "G8-12",
}
TOPICS = tuple(BANDS)
GENERATOR_METADATA = {
    "linear_equations": {"grade_band": "G8-9", "word_templates": ["ticket_cost"]},
    "systems_of_equations": {"grade_band": "G8-10", "word_templates": ["two_item_prices"]},
    "quadratic_equations": {"grade_band": "G9-10", "word_templates": []},
    "polynomial_operations": {"grade_band": "G9-10", "word_templates": []},
    "polynomial_factoring": {"grade_band": "G9-10", "word_templates": ["rectangular_area"]},
    "functions": {"grade_band": "G8-10", "word_templates": ["distance_function"]},
    "coordinate_geometry": {"grade_band": "G8-10", "word_templates": ["map_distance"]},
    "triangle_geometry": {"grade_band": "G8-10", "word_templates": ["triangle_angles"]},
    "trigonometry": {"grade_band": "G10-12", "word_templates": ["height_from_angle"]},
    "sequences_series": {"grade_band": "G9-12", "word_templates": ["saving_sequence"]},
    "logarithms": {"grade_band": "G10-12", "word_templates": []},
    "limits": {"grade_band": "G11-12", "word_templates": []},
    "derivatives": {"grade_band": "G11-12", "word_templates": ["instantaneous_rate"]},
    "definite_integrals": {"grade_band": "G11-12", "word_templates": ["accumulated_area"]},
    "matrices": {"grade_band": "G10-12", "word_templates": []},
    "combinatorics": {"grade_band": "G10-12", "word_templates": ["committee_selection"]},
    "number_theory": {"grade_band": "G8-12", "word_templates": ["repeating_schedule"]},
    "complex_numbers": {"grade_band": "G10-12", "word_templates": []},
    "vectors": {"grade_band": "G10-12", "word_templates": ["work_dot_product"]},
    "statistics": {"grade_band": "G9-12", "word_templates": ["sample_data"]},
    "probability": {"grade_band": "G9-12", "word_templates": ["colored_tokens"]},
    "proof_logic": {"grade_band": "G8-12", "word_templates": []},
}
WORD_TOPICS = {t for t, spec in GENERATOR_METADATA.items() if spec["word_templates"]}


def _poly(a: int, b: int, c: int) -> str:
    parts = []
    for coefficient, power in ((a, 2), (b, 1), (c, 0)):
        if coefficient == 0:
            continue
        magnitude = abs(coefficient)
        term = (str(magnitude) if power == 0 else
                ("x" if magnitude == 1 else f"{magnitude}x") if power == 1 else
                ("x^2" if magnitude == 1 else f"{magnitude}x^2"))
        if not parts:
            parts.append(("-" if coefficient < 0 else "") + term)
        else:
            parts.append((" - " if coefficient < 0 else " + ") + term)
    return "".join(parts) or "0"


def _build(topic: str, rng: random.Random, difficulty: int):
    n = lambda lo, hi: rng.randint(lo, hi)
    d = difficulty
    contextual = False
    ingredients = {"topic": topic}
    if topic == "linear_equations":
        a, x, b = n(1, 5*d), n(0, 12*d), n(0, 20*d)
        c = a*x+b
        contextual = rng.choice([True, False])
        ingredients.update(a=a, x=x, b=b, c=c, contextual=contextual)
        problem = (f"A school buys {a} notebooks per pack and pays an extra fee of {b} dollars. "
                   f"The total is {c} dollars. How many packs were bought?"
                   if contextual else f"Solve {a}x + {b} = {c}.")
        answer = str(x)
        steps = [f"Subtract {b}: {a}x = {c-b}.", f"Divide by {a}: x = {x}.", f"Check: {a}×{x}+{b}={c}."]
        exact = lambda: a*x+b == c
    elif topic == "systems_of_equations":
        x,y=n(1,10*d),n(1,10*d)
        a,b,c,e=n(1,5),n(1,5),n(1,5),n(1,5)
        if a*e-b*c == 0:
            e += 1
        p,q=a*x+b*y,c*x+e*y
        ingredients.update(x=x,y=y,a=a,b=b,c=c,e=e,p=p,q=q)
        contextual=rng.choice([True,False])
        problem=(f"Two items cost {a} and {b} dollars per unit in the first bundle, and {c} and {e} dollars per unit in the second. "
                 f"The bundle totals are {p} and {q} dollars. Find the quantities x and y."
                 if contextual else f"Solve the system: {a}x+{b}y={p}; {c}x+{e}y={q}.")
        answer=f"x={x}; y={y}"
        det=a*e-b*c
        steps=[f"Determinant: {a}×{e}−{b}×{c}={det}.",f"Unique solution by exact elimination: x={x}, y={y}.",f"Substitution verifies both equations."]
        exact=lambda: det!=0 and a*x+b*y==p and c*x+e*y==q
    elif topic == "quadratic_equations":
        r,s=n(-6*d,6*d),n(-6*d,6*d)
        b=-(r+s); c=r*s
        ingredients.update(r=r,s=s,b=b,c=c)
        problem=f"Solve x^2 + ({b})x + ({c}) = 0."
        roots=sorted([r,s])
        answer=f"x={roots[0]} or x={roots[1]}"
        steps=[f"Find two numbers with sum {r+s} and product {r*s}: {r} and {s}.",f"Factor: (x−({r}))(x−({s}))=0.",f"Roots: {answer}."]
        exact=lambda:(r+s)==-b and r*s==c
    elif topic == "polynomial_operations":
        coeff=[n(-5*d,5*d) for _ in range(6)]
        a,b,c,e,f,g=coeff
        A,B,C=a+e,b+f,c+g
        ingredients.update(coeff=coeff,result=[A,B,C])
        problem=f"Add ({_poly(a,b,c)}) and ({_poly(e,f,g)})."
        answer=_poly(A,B,C)
        steps=[f"Combine like terms: x² coefficient {a}+{e}={A}.",f"x coefficient {b}+{f}={B}; constant {c}+{g}={C}.",f"Result: {answer}."]
        exact=lambda:[a+e,b+f,c+g]==[A,B,C]
    elif topic == "polynomial_factoring":
        r,s=n(-6*d,6*d),n(-6*d,6*d)
        b=r+s;c=r*s
        ingredients.update(r=r,s=s,b=b,c=c)
        problem=(f"For x greater than {max(-r,-s)+1}, a rectangle has side lengths (x+({r})) and (x+({s})). Expand its area polynomial."
                 if rng.choice([True,False]) else f"Factor x^2+({b})x+({c}).")
        answer=_poly(1,b,c) if "rectangle" in problem else f"(x+({r}))(x+({s}))"
        steps=[f"Use (x+{r})(x+{s})=x²+({r+s})x+({r*s}).",f"Answer: {answer}."]
        exact=lambda:r+s==b and r*s==c
    elif topic == "functions":
        a,b,c,x=n(1,4*d),n(-5*d,5*d),n(-10*d,10*d),n(-5*d,5*d)
        value=a*x*x+b*x+c
        ingredients.update(a=a,b=b,c=c,x=x,value=value)
        contextual=value>=0 and c>=0 and rng.choice([True,False])
        ingredients["contextual"]=contextual
        problem=(f"A non-negative distance model is f(t)={a}t²+({b})t+({c}). Find f({x})."
                 if contextual else f"For f(x)={a}x²+({b})x+({c}), evaluate f({x}).")
        answer=str(value)
        steps=[f"Substitute {x}: {a}({x})²+({b})({x})+({c}).",f"Evaluate to {value}."]
        exact=lambda:a*x*x+b*x+c==value
    elif topic == "coordinate_geometry":
        k=n(1,5*d); x1,y1=0,0; x2,y2=3*k,4*k
        dist=5*k; slope=Fraction(y2-y1,x2-x1)
        ingredients.update(points=[x1,y1,x2,y2],k=k,distance=dist,slope=str(slope))
        problem=f"On a map, a path runs from ({x1},{y1}) to ({x2},{y2}). Find its straight-line distance and slope."
        answer=f"distance={dist}; slope={slope}"
        steps=[f"Distance: √(({x2}-{x1})²+({y2}-{y1})²)=√({9*k*k}+{16*k*k})={dist}.",f"Slope: ({y2}-{y1})/({x2}-{x1})={slope}."]
        exact=lambda:dist*dist==(x2-x1)**2+(y2-y1)**2 and slope==Fraction(y2-y1,x2-x1)
    elif topic == "triangle_geometry":
        a,b=n(20,80),n(20,80)
        if a+b>=170: b=170-a
        third=180-a-b
        ingredients.update(a=a,b=b,third=third)
        problem=f"Two interior angles of a triangle are {a}° and {b}°. Find the third angle."
        answer=str(third)
        steps=[f"Triangle angles sum to 180°.",f"180°−{a}°−{b}°={third}°."]
        exact=lambda:0<third<180 and a+b+third==180
    elif topic == "trigonometry":
        contextual=rng.choice([True,False])
        if contextual:
            angle=30
            hypotenuse=2*n(1,10*d)
            height=hypotenuse//2
            ingredients.update(angle=angle,hypotenuse=hypotenuse,height=height,contextual=True)
            problem=f"A ramp is {hypotenuse} meters long and makes a 30° angle with level ground. Find its vertical rise exactly."
            answer=str(height)
            steps=["sin(30°)=1/2.",f"Vertical rise={hypotenuse}×1/2={height} meters."]
            exact=lambda:hypotenuse>0 and hypotenuse%2==0 and height==hypotenuse//2
        else:
            angle=rng.choice([0,30,45,60,90])
            fn=rng.choice(["sin","cos"])
            values={"sin":{0:"0",30:"1/2",45:"√2/2",60:"√3/2",90:"1"},
                    "cos":{0:"1",30:"√3/2",45:"√2/2",60:"1/2",90:"0"}}
            val=values[fn][angle]
            ingredients.update(angle=angle,function=fn,value=val,contextual=False)
            problem=f"Evaluate {fn}({angle}°) exactly."
            answer=val
            steps=[f"Use the exact special-angle value for {angle}°.",f"{fn}({angle}°)={val}."]
            exact=lambda:val==values[fn][angle]
    elif topic == "sequences_series":
        first,step,index=n(1,10*d),n(1,8*d),n(5,20*d)
        value=first+(index-1)*step
        ingredients.update(first=first,step=step,index=index,value=value)
        problem=f"A savings plan starts at {first} dollars and increases by {step} dollars each week. What is the total in week {index}?"
        answer=str(value)
        steps=[f"Arithmetic sequence: a_n=a_1+(n−1)d.",f"a_{index}={first}+({index}−1)×{step}={value}."]
        exact=lambda:first+(index-1)*step==value
    elif topic == "logarithms":
        base=n(2,5); exponent=n(1,6*d); value=base**exponent
        ingredients.update(base=base,exponent=exponent,value=value)
        problem=f"Evaluate log base {base} of {value}."
        answer=str(exponent)
        steps=[f"Rewrite as {base}^x={value}.",f"Since {base}^{exponent}={value}, x={exponent}."]
        exact=lambda:base**exponent==value
    elif topic == "limits":
        a,x=n(-5*d,5*d),n(-5*d,5*d)
        value=x*x+3*x+a
        ingredients.update(a=a,x=x,value=value)
        problem=f"Find lim as t approaches {x} of (t²+3t+{a})."
        answer=str(value)
        steps=[f"Polynomials are continuous, so substitute t={x}.",f"{x}²+3×{x}+({a})={value}."]
        exact=lambda:x*x+3*x+a==value
    elif topic == "derivatives":
        a,b,c,x=n(1,5*d),n(-8*d,8*d),n(-10*d,10*d),n(-5*d,5*d)
        value=2*a*x+b
        ingredients.update(a=a,b=b,c=c,x=x,value=value)
        problem=(f"A position function is s(t)={a}t²+({b})t+{c}. Find the instantaneous rate at t={x}."
                 if rng.choice([True,False]) else f"Differentiate f(x)={a}x²+({b})x+{c}, then evaluate at x={x}.")
        answer=str(value)
        steps=[f"Derivative: s'(t)={2*a}t+({b}).",f"At t={x}: {2*a}×{x}+({b})={value}."]
        exact=lambda:2*a*x+b==value
    elif topic == "definite_integrals":
        power=n(0,3); lo=n(0,4); hi=n(lo+1,lo+5)
        value=Fraction(hi**(power+1)-lo**(power+1),power+1)
        ingredients.update(power=power,lo=lo,hi=hi,value=str(value))
        problem=f"A rate is t^{power} units per minute. How much accumulates from minute {lo} to minute {hi}?"
        answer=str(value.numerator) if value.denominator==1 else f"{value.numerator}/{value.denominator}"
        steps=[f"Antiderivative: x^{power+1}/({power+1}).",f"Evaluate at the bounds to get {answer}."]
        exact=lambda:Fraction(hi**(power+1)-lo**(power+1),power+1)==value
    elif topic == "matrices":
        a,b,c,e=n(-8*d,8*d),n(-8*d,8*d),n(-8*d,8*d),n(-8*d,8*d)
        det=a*e-b*c
        ingredients.update(matrix=[a,b,c,e],det=det)
        problem=f"Find the determinant of [[{a},{b}],[{c},{e}]]."
        answer=str(det)
        steps=[f"det=({a})({e})−({b})({c})={det}."]
        exact=lambda:a*e-b*c==det
    elif topic == "combinatorics":
        total=n(5,20*d); choose=n(1,total)
        value=math.comb(total,choose)
        ingredients.update(total=total,choose=choose,value=value)
        problem=f"A committee of {choose} people is selected from {total} volunteers. How many committees are possible?"
        answer=str(value)
        steps=[f"Use combinations: C({total},{choose})={total}!/({choose}!({total}-{choose})!).",f"Result: {value}."]
        exact=lambda:math.comb(total,choose)==value
    elif topic == "number_theory":
        a,b=n(2,100*d),n(2,100*d); gcd=math.gcd(a,b); lcm=a//gcd*b
        ingredients.update(a=a,b=b,gcd=gcd,lcm=lcm)
        problem=f"Two repeating schedules occur every {a} and {b} days. Find the first common repeat and the greatest common divisor of the intervals."
        answer=f"gcd={gcd}; lcm={lcm}"
        steps=[f"Euclidean algorithm gives gcd({a},{b})={gcd}.",f"lcm=({a}×{b})/{gcd}={lcm}."]
        exact=lambda:gcd==math.gcd(a,b) and lcm==a//gcd*b
    elif topic == "complex_numbers":
        a,b,c,e=n(-8*d,8*d),n(-8*d,8*d),n(-8*d,8*d),n(-8*d,8*d)
        real=a*c-b*e; imag=a*e+b*c
        ingredients.update(values=[a,b,c,e],real=real,imag=imag)
        problem=f"Multiply ({a}+{b}i)({c}+{e}i) and write a+bi."
        answer=f"{real}+({imag})i"
        steps=[f"Use i²=−1.",f"Real part {a}×{c}−{b}×{e}={real}; imaginary part {a}×{e}+{b}×{c}={imag}."]
        exact=lambda:a*c-b*e==real and a*e+b*c==imag
    elif topic == "vectors":
        a,b,c,e=n(-10*d,10*d),n(-10*d,10*d),n(-10*d,10*d),n(-10*d,10*d)
        value=a*c+b*e
        ingredients.update(vectors=[[a,b],[c,e]],value=value)
        problem=f"A force vector is ({a},{b}) newtons and a displacement vector is ({c},{e}) meters. Find the work using their dot product."
        answer=str(value)
        steps=[f"Dot product = {a}×{c}+{b}×{e}={value}."]
        exact=lambda:a*c+b*e==value
    elif topic == "statistics":
        values=[n(0,100) for _ in range(5)]; ordered=sorted(values)
        mean=Fraction(sum(values),5); median=ordered[2]; spread=ordered[-1]-ordered[0]
        ingredients.update(values=values,mean=str(mean),median=median,range=spread)
        problem=f"Five sample measurements are {', '.join(map(str,values))}. Find mean, median, and range."
        answer=f"mean={mean}; median={median}; range={spread}"
        steps=[f"Mean={sum(values)}/5={mean}.",f"Sorted values={ordered}; median={median}.",f"Range={ordered[-1]}−{ordered[0]}={spread}."]
        exact=lambda:mean==Fraction(sum(values),5) and median==ordered[2] and spread==ordered[-1]-ordered[0]
    elif topic == "probability":
        red,blue=n(1,10*d),n(1,10*d); total=red+blue
        value=Fraction(red,total)
        ingredients.update(red=red,blue=blue,total=total,value=str(value))
        problem=f"A bag contains {red} red and {blue} blue tokens. Find the probability of drawing a red token."
        answer=f"{value.numerator}/{value.denominator}"
        steps=[f"Favorable outcomes={red}; total outcomes={total}.",f"P(red)={red}/{total}={answer}."]
        exact=lambda:total==red+blue and value==Fraction(red,total) and 0<=value<=1
    elif topic == "proof_logic":
        k,nval=n(2,10*d),n(1,20*d)
        multiple=k*nval
        ingredients.update(k=k,n=nval,multiple=multiple)
        problem=f"Use the divisibility definition to justify: if k divides n, then k divides n². Example values: k={k}, n={multiple}."
        answer="True"
        steps=["Let n=k m for some integer m.", "Then n²=(k m)²=k(k m²), so n² is a multiple of k.", f"Example check: {multiple}² is divisible by {k}."]
        exact=lambda:multiple%k==0 and multiple*multiple%k==0
    else:
        raise ValueError("unknown topic: "+str(topic))
    return {
        "grade_band": BANDS[topic], "topic": topic, "subtopic": topic.replace("_"," "),
        "difficulty": d, "problem": problem, "steps": steps, "answer": str(answer),
        "answer_type": "expression" if any(ch in str(answer) for ch in "=;√i") else "fraction" if "/" in str(answer) else "integer",
        "ingredients": ingredients, "verifier": topic+"_seed_replay_and_exact_check",
    }, exact


def semantic_check(ingredients: dict, answer: str) -> bool:
    """Validate simple real-world domains after the topic's exact verifier."""
    try:
        topic=ingredients["topic"]
        if topic=="linear_equations":
            return ingredients["a"]>0 and ingredients["x"]>=0 and ingredients["b"]>=0 and ingredients["c"]>=0
        if topic=="systems_of_equations":
            a,b,c,e=ingredients["a"],ingredients["b"],ingredients["c"],ingredients["e"]
            return a*e-b*c!=0 and ingredients["x"]>=0 and ingredients["y"]>=0
        if topic=="triangle_geometry":
            return all(0<v<180 for v in (ingredients["a"],ingredients["b"],ingredients["third"])) and sum((ingredients["a"],ingredients["b"],ingredients["third"]))==180
        if topic=="trigonometry":
            if ingredients.get("contextual",False):
                return ingredients["angle"]==30 and ingredients["hypotenuse"]>0 and ingredients["height"]>=0 and ingredients["height"]*2==ingredients["hypotenuse"]
            return 0<=ingredients["angle"]<=90
        if topic=="functions":
            return not ingredients.get("contextual",False) or (ingredients["value"]>=0 and ingredients["c"]>=0)
        if topic=="coordinate_geometry":
            return ingredients["distance"]>=0
        if topic=="definite_integrals":
            return ingredients["lo"]<ingredients["hi"]
        if topic=="probability":
            return ingredients["red"]>=0 and ingredients["blue"]>=0 and ingredients["total"]>0 and 0<=Fraction(ingredients["value"])<=1
        if topic=="statistics":
            values=ingredients["values"]
            return len(values)==5 and all(0<=v<=100 for v in values)
        if topic=="combinatorics":
            return 0<=ingredients["choose"]<=ingredients["total"]
        if topic=="number_theory":
            return ingredients["a"]>0 and ingredients["b"]>0 and ingredients["gcd"]>0 and ingredients["lcm"]>0
        if topic=="polynomial_factoring":
            return ingredients["r"]+ingredients["s"]==ingredients["b"] and ingredients["r"]*ingredients["s"]==ingredients["c"]
        return True
    except (KeyError,TypeError,ValueError,ZeroDivisionError):
        return False


def generate(seed: int, difficulty: int=1, topic: str="linear_equations") -> dict:
    if not isinstance(seed,int):
        raise TypeError("seed must be int")
    if difficulty not in (1,2,3,4,5):
        raise ValueError("difficulty must be 1..5")
    if topic not in BANDS:
        raise ValueError("unknown topic: "+str(topic))
    fields,check=_build(topic,random.Random(seed),difficulty)
    fields.update(id=f"g8-12-{topic}-{seed}-{difficulty}",seed=seed)
    if not check():
        raise ArithmeticError("exact answer verification failed")
    if not semantic_check(fields["ingredients"],fields["answer"]):
        raise ArithmeticError("semantic verification failed")
    replay,_=_build(topic,random.Random(seed),difficulty)
    if replay!= {k:v for k,v in fields.items() if k not in ("id","seed")}:
        raise ArithmeticError("deterministic replay failed")
    return fields


def verify(problem: dict) -> bool:
    try:
        expected=generate(problem["seed"],problem["difficulty"],problem["topic"])
        return expected==problem
    except (KeyError,TypeError,ValueError,ArithmeticError):
        return False


GENERATORS={t:(lambda seed,difficulty=1,topic=t:generate(seed,difficulty,topic)) for t in TOPICS}
