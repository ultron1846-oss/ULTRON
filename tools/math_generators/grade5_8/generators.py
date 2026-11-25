import random
from fractions import Fraction

BANDS={"decimal_operations":"G5-6","fraction_operations":"G5-6","ratios":"G5-6","percentages":"G5-6","integers":"G5-6","exponents":"G5-6","order_of_operations":"G5-6","linear_equations":"G7-8","inequalities":"G7-8","basic_geometry":"G5-8","angles":"G5-8","statistics_basics":"G5-8","simple_probability":"G5-8"}
TOPICS=tuple(BANDS)
WORD_TOPICS={"ratios","percentages","linear_equations","inequalities","basic_geometry","angles","statistics_basics","simple_probability"}

def _make(topic,r,d):
 n=lambda lo,hi:r.randint(lo,hi)
 if topic=="decimal_operations":
  a,b=n(10,200*d),n(1,99*d); op=r.choice(["+","-","×"])
  if op=="-" and b>a:a,b=b,a
  val=Fraction(a+b,100) if op=="+" else Fraction(a-b,100) if op=="-" else Fraction(a*b,10000)
  ans=f"{float(val):.2f}"; q=f"Calculate {a/100:.2f} {op} {b/100:.2f}."
  steps=[f"Work in hundredths: {a} {op} {b}.",f"Result: {ans}."]
  check=lambda:Fraction(ans)==val
 elif topic=="fraction_operations":
  a,b,c,e=n(1,5*d),n(2,9),n(1,5*d),n(2,9); x,y=Fraction(a,b),Fraction(c,e); op=r.choice(["+","-"]); val=x+y if op=="+" else x-y
  ans=str(val.numerator) if val.denominator==1 else f"{val.numerator}/{val.denominator}"
  q=f"Calculate {a}/{b} {op} {c}/{e} and simplify."
  steps=[f"Use common denominator {b*e}: {a*e}/{b*e} {op} {c*b}/{b*e}.",f"Simplify to {ans}."]
  check=lambda:Fraction(ans)==val
 elif topic=="ratios":
  x,y,scale=n(1,6*d),n(1,6*d),n(2,5*d); red,blue=x*scale,y*scale; total=red+blue
  ans=f"red={red}; blue={blue}"
  q=r.choice([f"Red and blue beads are in ratio {x}:{y}. There are {total} beads. How many of each?",f"A recipe uses ingredients in ratio {x}:{y}. Scale both amounts by {scale}."])
  steps=[f"Scale factor is {scale}.",f"Red={x}×{scale}={red}; blue={y}×{scale}={blue}.",f"Check: {red}+{blue}={total}."]
  check=lambda:red+blue==total and red*y==blue*x
 elif topic=="percentages":
  pct,amount=n(5,25*d),n(20,100*d); val=Fraction(pct*amount,100); ans=str(val.numerator) if val.denominator==1 else f"{val.numerator}/{val.denominator}"
  q=r.choice([f"A {amount}-dollar item is discounted by {pct}%. How many dollars are saved?",f"Find {pct}% of {amount}.",f"{pct}% of {amount} students walk to school. How many is that?"])
  steps=[f"Convert {pct}% to {pct}/100.",f"{pct}/100 × {amount} = {ans}."]
  check=lambda:Fraction(ans)==val and Fraction(pct,100)*amount==val
 elif topic=="integers":
  a,b=n(-30*d,30*d),n(-30*d,30*d); val=a+b; ans=str(val)
  q=r.choice([f"The temperature is {a} degrees and changes by {b} degrees. Find the new temperature.",f"Calculate {a}+({b})."])
  steps=[f"Add signed integers: {a}+({b})={val}.",f"Check: {val}-({b})={a}."]
  check=lambda:int(ans)-b==a
 elif topic=="exponents":
  base,power=n(2,5),n(2,min(5,d+1)); val=base**power; ans=str(val); q=f"Evaluate {base}^{power}."
  steps=[f"Multiply {base} by itself {power} times.",f"Result: {ans}."]
  check=lambda:base**power==int(ans)
 elif topic=="order_of_operations":
  a,b,c=n(2,10*d),n(2,10*d),n(2,10*d); val=a+b*c; ans=str(val)
  q=r.choice([f"Evaluate {a}+{b}×{c}.",f"A purchase has {b} packs with {c} items each, plus {a} extra items. How many items?"])
  steps=[f"Multiply first: {b}×{c}={b*c}.",f"Then add: {a}+{b*c}={val}."]
  check=lambda:int(ans)==a+b*c
 elif topic=="linear_equations":
  a,x,b=n(2,5*d),n(-10*d,10*d),n(-20*d,20*d); c=a*x+b; ans=str(x)
  q=r.choice([f"Solve {a}x+({b})={c}.",f"A club sells {a} tickets per bundle and has a balance adjustment of {b}. The final total is {c}. Solve {a}x+({b})={c}."])
  steps=[f"Subtract {b}: {a}x={c-b}.",f"Divide by {a}: x={x}.",f"Check: {a}×{x}+({b})={c}."]
  check=lambda:a*int(ans)+b==c
 elif topic=="inequalities":
  a,bound,b=n(2,5*d),n(-10*d,10*d),n(-20*d,20*d); c=a*bound+b; sign=r.choice(["<",">"]); ans=f"x {sign} {bound}"
  q=r.choice([f"Solve {a}x+({b}) {sign} {c}.",f"A plan costs {a} per unit plus adjustment {b}; its total must be {sign} {c}. State the condition on x."])
  steps=[f"Subtract {b}: {a}x {sign} {c-b}.",f"Divide by positive {a}; sign stays the same: {ans}."]
  check=lambda:a*bound+b==c and (a*(bound-1)+b<c if sign=="<" else a*(bound+1)+b>c)
 elif topic=="basic_geometry":
  w,h=n(2,12*d),n(2,12*d); area=w*h; peri=2*(w+h); ans=f"area={area}; perimeter={peri}"
  q=r.choice([f"A rectangular garden is {w} m by {h} m. Find its area and perimeter.",f"Find the area and perimeter of a {w} by {h} rectangle."])
  steps=[f"Area={w}×{h}={area} square units.",f"Perimeter=2({w}+{h})={peri} units."]
  check=lambda:w*h==area and 2*(w+h)==peri
 elif topic=="angles":
  a=n(15,165); val=180-a; ans=str(val); q=r.choice([f"Two angles form a straight line. One is {a}°. Find the other.",f"Find the supplementary angle to {a}°."])
  steps=[f"Supplementary angles total 180°.",f"180°−{a}°={val}°."]
  check=lambda:int(ans)+a==180 and 0<int(ans)<180
 elif topic=="statistics_basics":
  vals=[n(1,20*d) for _ in range(5)]; ordered=sorted(vals); mean=Fraction(sum(vals),5); med=ordered[2]; ran=ordered[-1]-ordered[0]
  ans=f"mean={mean}; median={med}; range={ran}"
  q=r.choice([f"Five quiz scores are {', '.join(map(str,vals))}. Find mean, median, and range.",f"Measurements are {', '.join(map(str,vals))}. Calculate mean, median, and range."])
  steps=[f"Mean={sum(vals)}÷5={mean}.",f"Sorted data={ordered}; median={med}.",f"Range={ordered[-1]}−{ordered[0]}={ran}."]
  check=lambda:sum(vals)==mean*5 and ordered[2]==med and ordered[-1]-ordered[0]==ran
 elif topic=="simple_probability":
  red,blue,green=n(1,8*d),n(1,8*d),n(1,8*d); total=red+blue+green; val=Fraction(red,total); ans=f"{val.numerator}/{val.denominator}"
  q=r.choice([f"A bag has {red} red, {blue} blue, and {green} green counters. Find P(red).",f"There are {total} equally likely tokens, {red} are red. Find the probability of red."])
  steps=[f"Total outcomes={red}+{blue}+{green}={total}.",f"P(red)={red}/{total}={ans}."]
  check=lambda:Fraction(ans)==val and val*total==red
 else:raise ValueError("unknown topic: "+str(topic))
 return {"grade_band":BANDS[topic],"topic":topic,"subtopic":topic.replace("_"," "),"difficulty":d,"problem":q,"steps":steps,"answer":str(ans),"answer_type":"fraction" if "/" in str(ans) else "expression" if "=" in str(ans) else "integer","verifier":topic+"_replay_and_exact_check"},check

def generate(seed:int,difficulty:int=1,topic:str="ratios")->dict:
 if not isinstance(seed,int):raise TypeError("seed must be int")
 if difficulty not in (1,2,3,4,5):raise ValueError("difficulty must be 1..5")
 if topic not in BANDS:raise ValueError("unknown topic: "+str(topic))
 fields,check=_make(topic,random.Random(seed),difficulty); fields.update(id=f"g5-8-{topic}-{seed}-{difficulty}",seed=seed)
 if not check():raise ArithmeticError("answer verification failed")
 replay,_=_make(topic,random.Random(seed),difficulty)
 if replay!={k:v for k,v in fields.items() if k not in ("id","seed")}:raise ArithmeticError("replay failed")
 return fields
GENERATORS={t:(lambda seed,difficulty=1,topic=t:generate(seed,difficulty,topic)) for t in TOPICS}
def verify(problem:dict)->bool:
 try:
  expected=generate(problem["seed"],problem["difficulty"],problem["topic"])
  if expected!=problem:return False
  _,check=_make(problem["topic"],random.Random(problem["seed"]),problem["difficulty"])
  return bool(check())
 except (KeyError,TypeError,ValueError,ArithmeticError,ZeroDivisionError):return False
