import random
from fractions import Fraction

BANDS={"decimal_operations":"G5-6","fraction_operations":"G5-6","ratios":"G5-6","percentages":"G5-6","integers":"G5-6","exponents":"G5-6","order_of_operations":"G5-6","linear_equations":"G7-8","inequalities":"G7-8","basic_geometry":"G5-8","angles":"G5-8","statistics_basics":"G5-8","simple_probability":"G5-8"}
TOPICS=tuple(BANDS)

# Generator declarations are the source of truth for contextual coverage.
# Each entry lists the contextual templates actually used by that topic.
GENERATOR_METADATA={
 "decimal_operations":{"grade_band":"G5-6","word_templates":[]},
 "fraction_operations":{"grade_band":"G5-6","word_templates":[]},
 "ratios":{"grade_band":"G5-6","word_templates":["bead_ratio","recipe_scale"]},
 "percentages":{"grade_band":"G5-6","word_templates":["discount_amount","percentage_of","percentage_count"]},
 "integers":{"grade_band":"G5-6","word_templates":["temperature_change"]},
 "exponents":{"grade_band":"G5-6","word_templates":[]},
 "order_of_operations":{"grade_band":"G5-6","word_templates":["packs_and_items"]},
 "linear_equations":{"grade_band":"G7-8","word_templates":["ticket_bundles"]},
 "inequalities":{"grade_band":"G7-8","word_templates":["plan_cost"]},
 "basic_geometry":{"grade_band":"G5-8","word_templates":["rectangular_garden"]},
 "angles":{"grade_band":"G5-8","word_templates":["straight_line_angles"]},
 "statistics_basics":{"grade_band":"G5-8","word_templates":["quiz_scores","measurements"]},
 "simple_probability":{"grade_band":"G5-8","word_templates":["bag_counters","equally_likely_tokens"]},
}
WORD_TOPICS={topic for topic,spec in GENERATOR_METADATA.items() if spec["word_templates"]}

def semantic_check(ingredients,answer):
 """Optional semantic validator run after exact arithmetic verification."""
 try:
  topic=ingredients["topic"]
  if topic=="percentages":
   value=Fraction(str(answer))
   pct=int(ingredients["percent"]); amount=int(ingredients["amount"])
   quantity_type=ingredients["quantity_type"]
   if not 0<=pct<=100 or amount<=0:return False
   exact=Fraction(pct*amount,100)
   if value!=exact or exact<0:return False
   if quantity_type=="count":
    divisor=100//__import__("math").gcd(pct,100)
    return amount%divisor==0 and exact.denominator==1 and value.denominator==1
   if quantity_type=="continuous":
    return exact.denominator in (1,2,4,5,10,20,25,50,100)
   return False
  if topic=="ratios":
   x,y,scale=map(int,ingredients["values"])
   return x>0 and y>0 and scale>0 and x*scale>=0 and y*scale>=0
  if topic=="integers":
   value=Fraction(str(answer))
   return value.denominator==1
  if topic=="order_of_operations":
   value=Fraction(str(answer))
   a,b,c=map(int,ingredients["values"])
   return a>0 and b>0 and c>0 and value.denominator==1 and value>=0
  if topic=="linear_equations":
   value=Fraction(str(answer))
   a,x,b,c=map(int,ingredients["values"])
   contextual=bool(ingredients.get("contextual",False))
   return a>0 and a*x+b==c and value==x and (not contextual or (x>=0 and b>=0 and c>=0))
  if topic=="inequalities":
   a,bound,b,c=map(int,ingredients["values"])
   contextual=bool(ingredients.get("contextual",False))
   return a>0 and a*bound+b==c and (not contextual or (bound>=0 and b>=0 and c>=0))
  if topic=="basic_geometry":
   w,h=map(int,ingredients["values"])
   return w>0 and h>0 and w*h>0 and 2*(w+h)>0
  if topic=="angles":
   value=Fraction(str(answer))
   angle=int(ingredients["angle"])
   return value==180-angle and 0<angle<180 and 0<180-angle<180
  if topic=="statistics_basics":
   values=list(map(int,ingredients["values"]))
   context=ingredients.get("context_type","measurement")
   return bool(values) and all(v>=0 for v in values) and (context!="quiz_scores" or all(v<=100 for v in values))
  if topic=="simple_probability":
   value=Fraction(str(answer))
   red,blue,green=map(int,ingredients["values"])
   total=red+blue+green
   return red>=0 and blue>=0 and green>=0 and total>0 and value==Fraction(red,total) and 0<=value<=1
  return True
 except (KeyError,TypeError,ValueError,ZeroDivisionError):
  return False

def _make(topic,r,d):
 n=lambda lo,hi:r.randint(lo,hi)
 if topic=="decimal_operations":
  a,b=n(10,200*d),n(1,99*d); op=r.choice(["+","-","×"])
  if op=="-" and b>a:a,b=b,a
  val=Fraction(a+b,100) if op=="+" else Fraction(a-b,100) if op=="-" else Fraction(a*b,10000)
  ans=format(float(val),".4f").rstrip("0").rstrip("."); q=f"Calculate {a/100:.2f} {op} {b/100:.2f}."
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
  ingredients={"topic":topic,"values":[x,y,scale],"quantity_type":"count"}
  ans=f"red={red}; blue={blue}"
  q=r.choice([f"Red and blue beads are in ratio {x}:{y}. There are {total} beads. How many of each?",f"A recipe uses ingredients in ratio {x}:{y}. Scale both amounts by {scale}."])
  steps=[f"Scale factor is {scale}.",f"Red={x}×{scale}={red}; blue={y}×{scale}={blue}.",f"Check: {red}+{blue}={total}."]
  check=lambda:red+blue==total and red*y==blue*x
 elif topic=="percentages":
  pct=n(5,min(25*d,100))
  quantity_type=r.choice(["count","continuous"])
  if quantity_type=="count":
   unit=100//__import__("math").gcd(pct,100)
   amount=unit*n(1,max(1,(100*d)//unit))
   val=Fraction(pct*amount,100)
   ans=str(val.numerator)
   q=f"A group has {amount} students. {pct}% of them walk to school. How many students is that?"
  else:
   amount=n(20,100*d)
   val=Fraction(pct*amount,100)
   ans=f"{float(val):.2f}"
   q=r.choice([
    f"A {amount}-dollar item is discounted by {pct}%. How much money is saved? Round to the nearest cent.",
    f"Find {pct}% of {amount}.",
    f"A {amount}-kilometer route is shortened by {pct}%. How many kilometers are removed? Round to the nearest hundredth."
   ])
  ingredients={"topic":topic,"percent":pct,"amount":amount,"quantity_type":quantity_type}
  steps=[f"Convert {pct}% to {pct}/100.",f"{pct}/100 × {amount} = {ans}."]
  check=lambda:Fraction(ans)==val and Fraction(pct,100)*amount==val
 elif topic=="integers":
  a,b=n(-30*d,30*d),n(-30*d,30*d); val=a+b; ans=str(val)
  ingredients={"topic":topic,"values":[a,b],"quantity_type":"signed_integer"}
  q=r.choice([f"The temperature is {a} degrees and changes by {b} degrees. Find the new temperature.",f"Calculate {a}+({b})."])
  steps=[f"Add signed integers: {a}+({b})={val}.",f"Check: {val}-({b})={a}."]
  check=lambda:int(ans)-b==a
 elif topic=="exponents":
  base,power=n(2,5),n(2,min(5,d+1)); val=base**power; ans=str(val); q=f"Evaluate {base}^{power}."
  steps=[f"Multiply {base} by itself {power} times.",f"Result: {ans}."]
  check=lambda:base**power==int(ans)
 elif topic=="order_of_operations":
  a,b,c=n(2,10*d),n(2,10*d),n(2,10*d); val=a+b*c; ans=str(val)
  ingredients={"topic":topic,"values":[a,b,c],"quantity_type":"count"}
  q=r.choice([f"Evaluate {a}+{b}×{c}.",f"A purchase has {b} packs with {c} items each, plus {a} extra items. How many items?"])
  steps=[f"Multiply first: {b}×{c}={b*c}.",f"Then add: {a}+{b*c}={val}."]
  check=lambda:int(ans)==a+b*c
 elif topic=="linear_equations":
  a,x,b=n(2,5*d),n(-10*d,10*d),n(-20*d,20*d); c=a*x+b; ans=str(x)
  contextual=x>=0 and b>=0 and c>=0 and r.choice([True,False])
  ingredients={"topic":topic,"values":[a,x,b,c],"contextual":contextual,"quantity_type":"count" if contextual else "signed_integer"}
  q=(f"A club sells {a} tickets per bundle and has a balance adjustment of {b}. The final total is {c}. Solve {a}x+({b})={c}." if contextual else f"Solve {a}x+({b})={c}.")
  steps=[f"Subtract {b}: {a}x={c-b}.",f"Divide by {a}: x={x}.",f"Check: {a}×{x}+({b})={c}."]
  check=lambda:a*int(ans)+b==c
 elif topic=="inequalities":
  a,bound,b=n(2,5*d),n(-10*d,10*d),n(-20*d,20*d); c=a*bound+b; sign=r.choice(["<",">"]); ans=f"x {sign} {bound}"
  contextual=bound>=0 and b>=0 and c>=0 and r.choice([True,False])
  ingredients={"topic":topic,"values":[a,bound,b,c],"contextual":contextual,"quantity_type":"cost" if contextual else "signed_integer"}
  q=(f"A plan costs {a} per unit plus adjustment {b}; its total must be {sign} {c}. State the condition on x." if contextual else f"Solve {a}x+({b}) {sign} {c}.")
  steps=[f"Subtract {b}: {a}x {sign} {c-b}.",f"Divide by positive {a}; sign stays the same: {ans}."]
  check=lambda:a*bound+b==c and (a*(bound-1)+b<c if sign=="<" else a*(bound+1)+b>c)
 elif topic=="basic_geometry":
  w,h=n(2,12*d),n(2,12*d); area=w*h; peri=2*(w+h); ans=f"area={area}; perimeter={peri}"
  ingredients={"topic":topic,"values":[w,h],"quantity_type":"length"}
  q=r.choice([f"A rectangular garden is {w} m by {h} m. Find its area and perimeter.",f"Find the area and perimeter of a {w} by {h} rectangle."])
  steps=[f"Area={w}×{h}={area} square units.",f"Perimeter=2({w}+{h})={peri} units."]
  check=lambda:w*h==area and 2*(w+h)==peri
 elif topic=="angles":
  a=n(15,165); val=180-a; ans=str(val); ingredients={"topic":topic,"angle":a,"quantity_type":"angle"}; q=r.choice([f"Two angles form a straight line. One is {a}°. Find the other.",f"Find the supplementary angle to {a}°."])
  steps=[f"Supplementary angles total 180°.",f"180°−{a}°={val}°."]
  check=lambda:int(ans)+a==180 and 0<int(ans)<180
 elif topic=="statistics_basics":
  vals=[n(1,20*d) for _ in range(5)]; ordered=sorted(vals); mean=Fraction(sum(vals),5); med=ordered[2]; ran=ordered[-1]-ordered[0]
  ingredients={"topic":topic,"values":vals,"quantity_type":"score"}
  ans=f"mean={mean}; median={med}; range={ran}"
  q=r.choice([f"Five quiz scores are {', '.join(map(str,vals))}. Find mean, median, and range.",f"Measurements are {', '.join(map(str,vals))}. Calculate mean, median, and range."])
  steps=[f"Mean={sum(vals)}÷5={mean}.",f"Sorted data={ordered}; median={med}.",f"Range={ordered[-1]}−{ordered[0]}={ran}."]
  check=lambda:sum(vals)==mean*5 and ordered[2]==med and ordered[-1]-ordered[0]==ran
 elif topic=="simple_probability":
  red,blue,green=n(1,8*d),n(1,8*d),n(1,8*d); total=red+blue+green; val=Fraction(red,total); ans=f"{val.numerator}/{val.denominator}"
  ingredients={"topic":topic,"values":[red,blue,green],"quantity_type":"count"}
  q=r.choice([f"A bag has {red} red, {blue} blue, and {green} green counters. Find P(red).",f"There are {total} equally likely tokens, {red} are red. Find the probability of red."])
  steps=[f"Total outcomes={red}+{blue}+{green}={total}.",f"P(red)={red}/{total}={ans}."]
  check=lambda:Fraction(ans)==val and val*total==red
 else:raise ValueError("unknown topic: "+str(topic))
 ingredients=locals().get("ingredients",{"topic":topic})
 return {"grade_band":BANDS[topic],"topic":topic,"subtopic":topic.replace("_"," "),"difficulty":d,"problem":q,"steps":steps,"answer":str(ans),"answer_type":"fraction" if "/" in str(ans) else "expression" if "=" in str(ans) else "integer","ingredients":ingredients,"verifier":topic+"_replay_and_exact_check"},check

def generate(seed:int,difficulty:int=1,topic:str="ratios")->dict:
 if not isinstance(seed,int):raise TypeError("seed must be int")
 if difficulty not in (1,2,3,4,5):raise ValueError("difficulty must be 1..5")
 if topic not in BANDS:raise ValueError("unknown topic: "+str(topic))
 fields,check=_make(topic,random.Random(seed),difficulty); fields.update(id=f"g5-8-{topic}-{seed}-{difficulty}",seed=seed)
 if not check():raise ArithmeticError("answer verification failed")
 if not semantic_check(fields.get("ingredients",{"topic":topic}),fields["answer"]):
  raise ArithmeticError("semantic verification failed")
 replay,_=_make(topic,random.Random(seed),difficulty)
 if replay!={k:v for k,v in fields.items() if k not in ("id","seed")}:raise ArithmeticError("replay failed")
 return fields
GENERATORS={t:(lambda seed,difficulty=1,topic=t:generate(seed,difficulty,topic)) for t in TOPICS}
def verify(problem:dict)->bool:
 try:
  expected=generate(problem["seed"],problem["difficulty"],problem["topic"])
  if expected!=problem:return False
  _,check=_make(problem["topic"],random.Random(problem["seed"]),problem["difficulty"])
  return bool(check()) and semantic_check(expected.get("ingredients",{"topic":problem["topic"]}),expected["answer"])
 except (KeyError,TypeError,ValueError,ArithmeticError,ZeroDivisionError):return False
