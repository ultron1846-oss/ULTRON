"""Deterministic, verified original-template Grade 1-4 math generators."""
from __future__ import annotations
import random
import re
from fractions import Fraction

BANDS = {
    "counting":"G1-2", "addition":"G1-2", "subtraction":"G1-2", "place_value":"G1-2",
    "multiplication":"G3-4", "division":"G3-4", "fractions_basics":"G3-4",
    "simple_word_problems":"G3-4", "time_and_money":"G3-4", "perimeter_and_area":"G3-4",
}
TOPICS = tuple(BANDS)

# Contextual template declarations drive the generated coverage registry.
GENERATOR_METADATA = {
    "counting": {"grade_band": "G1-2", "word_templates": []},
    "addition": {"grade_band": "G1-2", "word_templates": []},
    "subtraction": {"grade_band": "G1-2", "word_templates": []},
    "place_value": {"grade_band": "G1-2", "word_templates": []},
    "multiplication": {"grade_band": "G3-4", "word_templates": ["equal_groups"]},
    "division": {"grade_band": "G3-4", "word_templates": ["sharing_items"]},
    "fractions_basics": {"grade_band": "G3-4", "word_templates": ["fraction_story"]},
    "simple_word_problems": {"grade_band": "G3-4", "word_templates": ["cards", "fruit", "bags", "tables"]},
    "time_and_money": {"grade_band": "G3-4", "word_templates": ["journey_time", "pencil_price"]},
    "perimeter_and_area": {"grade_band": "G3-4", "word_templates": ["rectangle_context"]},
}
WORD_TOPICS = {topic for topic, spec in GENERATOR_METADATA.items() if spec["word_templates"]}
PHRASES = {
    "counting":["Count by {s}: {a}, {b}, ... What is term {k}?","Start at {a}; count forward by {s}. What is term {k}?"],
    "addition":["Calculate {expr}.","Find the total: {expr}."],
    "subtraction":["Calculate {a} − {b}.","What is {a} minus {b}?"],
    "place_value":["In {n}, what is the value of the digit in the {place} place?","What is the {place}-place value of {digit} in {n}?"],
    "multiplication":["Calculate {a} × {b}.","There are {a} groups of {b}. How many altogether?"],
    "division":["Calculate {a} ÷ {b}.","Share {a} items equally among {b} groups. How many per group?"],
    "fractions_basics":["Add and simplify: {a}/{d} + {b}/{d}.","You have {a}/{d} and receive {b}/{d} more. What fraction is that?"],
}
PLACES = ["ones","tens","hundreds","thousands","ten-thousands","hundred-thousands","millions"]

def semantic_check(topic: str, answer: str, problem: str) -> bool:
    """Check elementary quantity domains after the exact topic verifier."""
    try:
        if topic in {"counting", "addition", "subtraction", "place_value",
                     "multiplication", "division", "simple_word_problems"}:
            return int(answer) >= 0
        if topic == "fractions_basics":
            return Fraction(answer) >= 0
        if topic == "time_and_money":
            if answer.startswith("$"):
                return bool(re.fullmatch(r"\$\d+\.\d{2}", answer))
            match = re.fullmatch(r"(\d+) hours? (\d+) minutes?", answer)
            return bool(match and int(match.group(2)) < 60 and int(match.group(1)) >= 0)
        if topic == "perimeter_and_area":
            match = re.fullmatch(r"perimeter=(\d+); area=(\d+)", answer)
            return bool(match and int(match.group(1)) > 0 and int(match.group(2)) > 0)
        return False
    except (ValueError, ZeroDivisionError):
        return False


def _build(topic, rng, d):
    n=lambda lo,hi:rng.randint(lo,hi)
    phrase=lambda t,**kw:rng.choice(PHRASES[t]).format(**kw)
    if topic=="counting":
        a=n(0,25*d); s=n(1,d+2); k=n(3,4+d); ans=a+s*(k-1)
        q=phrase(topic,a=a,b=a+s,s=s,k=k)
        steps=[f"There are {k-1} steps after the first term.",f"{a}+{s}×{k-1}={ans}."]
        check=lambda x: x==str(ans) and ans-s*(k-1)==a
        typ="integer"
    elif topic=="addition":
        vals=[n(0,20*d),n(0,20*d)]+([n(0,10*d)] if d>=3 else [])+([n(0,10*d)] if d>=5 else [])
        ans=sum(vals); expr=" + ".join(map(str,vals)); q=phrase(topic,expr=expr)
        steps=[f"Add the numbers: {expr}={ans}."]
        check=lambda x: x==str(ans) and sum(vals)==ans
        typ="integer"
    elif topic=="subtraction":
        a,b=sorted([n(0,30*d),n(0,30*d)],reverse=True); ans=a-b
        q=phrase(topic,a=a,b=b); steps=[f"Subtract: {a}−{b}={ans}."]
        check=lambda x: x==str(ans) and ans+b==a
        typ="integer"
    elif topic=="place_value":
        digits=[n(1,9)]+[n(0,9) for _ in range(d+1)]; num=int("".join(map(str,digits)))
        pos=n(0,len(digits)-1); place=10**pos; digit=(num//place)%10; ans=digit*place
        q=phrase(topic,n=num,place=PLACES[pos],digit=digit)
        steps=[f"The digit is {digit}; its place is {place}.",f"{digit}×{place}={ans}."]
        check=lambda x: x==str(ans) and (num//place)%10==digit
        typ="integer"
    elif topic=="multiplication":
        a,b=n(1,12*d),n(1,12); ans=a*b; q=phrase(topic,a=a,b=b)
        steps=[f"{a}×{b}={ans}."]
        if d>=3: steps.append(f"Check: {ans}÷{b}={a}.")
        check=lambda x: x==str(ans) and ans//b==a and ans%b==0
        typ="integer"
    elif topic=="division":
        b=n(1,12); quotient=n(1,12*d); a=b*quotient; ans=quotient; q=phrase(topic,a=a,b=b)
        steps=[f"Find the number that times {b} gives {a}.",f"{a}÷{b}={ans}."]
        check=lambda x: x==str(ans) and ans*b==a and a%b==0
        typ="integer"
    elif topic=="fractions_basics":
        den=n(2,12); a=n(1,den-1); b=n(1,den-1); total=Fraction(a+b,den)
        ans=str(total.numerator) if total.denominator==1 else f"{total.numerator}/{total.denominator}"
        q=phrase(topic,a=a,b=b,d=den)
        steps=[f"Same denominator: ({a}+{b})/{den}={a+b}/{den}.",f"Simplify to {ans}."]
        check=lambda x: x==ans and Fraction(a,den)+Fraction(b,den)==total and total==Fraction(a+b,den)
        typ="fraction"
    elif topic=="simple_word_problems":
        a,b=n(2,20*d),n(2,20*d); op=rng.choice(["add","multiply"] if d>=3 else ["add"])
        if op=="add":
            ans=a+b; q=rng.choice([f"Sam has {a} cards and gets {b} more. How many now?",f"A basket has {a} pears and {b} apples. How many fruits altogether?"])
            steps=[f"Combine: {a}+{b}={ans}."]; check=lambda x:x==str(ans) and ans-a==b
        else:
            ans=a*b; q=rng.choice([f"There are {a} bags with {b} marbles each. How many marbles?",f"Each of {a} tables has {b} chairs. How many chairs?"])
            steps=[f"Equal groups: {a}×{b}={ans}.",f"Check: {ans}÷{a}={b}."]; check=lambda x:x==str(ans) and ans//a==b and ans%a==0
        typ="integer"
    elif topic=="time_and_money":
        if rng.choice([True,False]):
            mins=n(1,180*d); h,m=divmod(mins,60); ans=f"{h} hour{'s' if h!=1 else ''} {m} minute{'s' if m!=1 else ''}"
            q=rng.choice([f"A journey takes {mins} minutes. Write it as hours and minutes.",f"Convert {mins} minutes into hours and leftover minutes."])
            steps=[f"{mins}÷60={h} hours with {m} minutes left."]
            check=lambda x:x==ans and h*60+m==mins and 0<=m<60
        else:
            cents=n(20,500*d); dollars,rem=divmod(cents,100); ans=f"${dollars}.{rem:02d}"
            q=rng.choice([f"A pencil costs {cents} cents. Write the price in dollars.",f"Convert {cents} cents into dollars and cents."])
            steps=[f"100 cents = $1, so {cents} cents = {ans}."]
            check=lambda x:x==ans and dollars*100+rem==cents and 0<=rem<100
        typ="expression"
    elif topic=="perimeter_and_area":
        w,h=n(1,8*d),n(1,8*d); p=2*(w+h); area=w*h; ans=f"perimeter={p}; area={area}"
        q=rng.choice([f"A rectangle is {w} units wide and {h} units long. Find perimeter and area.",f"Find the perimeter and area of a {w} by {h} rectangle."])
        steps=[f"Perimeter: 2×({w}+{h})={p} units.",f"Area: {w}×{h}={area} square units."]
        check=lambda x:x==ans and p==2*(w+h) and area==w*h
        typ="expression"
    else: raise ValueError("unknown topic: "+str(topic))
    return {"grade_band":BANDS[topic],"topic":topic,"subtopic":topic.replace("_"," "),
            "difficulty":d,"problem":q,"steps":steps,"answer":str(ans),"answer_type":typ,
            "verifier":topic+"_replay_and_inverse_check"},check

def generate(seed:int,difficulty:int=1,topic:str="addition")->dict:
    if not isinstance(seed,int): raise TypeError("seed must be int")
    if difficulty not in (1,2,3,4,5): raise ValueError("difficulty must be 1..5")
    if topic not in BANDS: raise ValueError("unknown topic: "+str(topic))
    fields,check=_build(topic,random.Random(seed),difficulty)
    fields.update(id=f"g1-4-{topic}-{seed}-{difficulty}",seed=seed)
    if not check(fields["answer"]): raise ArithmeticError("answer verification failed")
    if not semantic_check(topic, fields["answer"], fields["problem"]):
        raise ArithmeticError("semantic verification failed")
    replay,_=_build(topic,random.Random(seed),difficulty)
    if replay!= {k:v for k,v in fields.items() if k not in ("id","seed")}:
        raise ArithmeticError("deterministic replay failed")
    return fields

GENERATORS={t:(lambda seed,difficulty=1,topic=t:generate(seed,difficulty,topic)) for t in TOPICS}

def verify(problem:dict)->bool:
    try:
        t=problem["topic"]; seed=problem["seed"]; d=problem["difficulty"]
        expected=generate(seed,d,t)
        if expected!=problem: return False
        _,check=_build(t,random.Random(seed),d)
        return bool(check(problem["answer"]))
    except (KeyError,TypeError,ValueError,ArithmeticError):
        return False
