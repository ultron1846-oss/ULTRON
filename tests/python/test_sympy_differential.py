"""Fixed-seed SymPy differential tests: 1,000 cases in each engine area."""
import random, unittest
from fractions import Fraction
import sympy as sp
from ultron_core.algebraic import RealAlgebraicNumber
from ultron_core.algebraic_arithmetic import add as aa, subtract as asub, multiply as amul, divide as adiv
from ultron_core.math_ir import Expr, ExprKind
from ultron_core.math_parser import parse_math
from ultron_core.polynomial import Polynomial
from ultron_core.polynomial_verifier import verify_polynomial_identity
from ultron_core.rational import RationalFunction
from ultron_core.rational_verifier import verify_rational_identity
from ultron_core.verification import evaluate
X=sp.Symbol("x"); N=1000

def sym(expr):
 k=expr.kind
 if k==ExprKind.INTEGER:return sp.Integer(expr.value)
 if k==ExprKind.RATIONAL:return sp.Rational(str(expr.value))
 if k==ExprKind.SYMBOL:return sp.Symbol(str(expr.value))
 a=[sym(v) for v in expr.args]
 if k==ExprKind.ADD:return sum(a)
 if k==ExprKind.SUB:return a[0]-a[1]
 if k==ExprKind.MUL:return sp.prod(a)
 if k==ExprKind.DIV:return a[0]/a[1]
 if k==ExprKind.POW:return a[0]**a[1]
 if k==ExprKind.NEG:return -a[0]
 if k==ExprKind.EQUAL:return sp.Eq(a[0],a[1])
 raise AssertionError(k)

def rp(rng,degree=4):
 cs=[rng.randint(-6,6) for _ in range(degree+1)]
 if cs[-1]==0:cs[-1]=rng.choice((-3,-2,-1,1,2,3))
 terms=[(() if i==0 else (("x",i),),Fraction(c)) for i,c in enumerate(cs) if c]
 return Polynomial(tuple(sorted(terms))),sp.Poly(sum(c*X**i for i,c in enumerate(cs)),X)
def spoly(p):return sp.Poly(sym(p.to_expr()),X)

class SympyDifferential(unittest.TestCase):
 def test_parser_evaluator_1000(self):
  r=random.Random(0xA11CE)
  for i in range(N):
   a,b,c,d=r.randint(-30,30),r.randint(-30,30),r.randint(-15,15),r.randint(1,20)
   text=f"(({a})+({b}))*({c})/({d})"; got=evaluate(parse_math(text),{}); want=sp.sympify(text,rational=True)
   self.assertEqual(got,Fraction(int(want.p),int(want.q)),msg=f"seed=A11CE case={i} input={text}")
 def test_polynomial_ops_1000(self):
  r=random.Random(0xB01A)
  for i in range(N):
   p,ps=rp(r,r.randint(1,4));q,qs=rp(r,r.randint(1,4))
   self.assertEqual(spoly(p.add(q)),sp.Poly(ps.as_expr()+qs.as_expr(),X),msg=f"seed=B01A case={i} p={ps} q={qs}")
   self.assertEqual(spoly(p.multiply(q)),sp.Poly(ps.as_expr()*qs.as_expr(),X),msg=f"seed=B01A case={i} p={ps} q={qs}")
 def test_rational_functions_1000(self):
  r=random.Random(0xA4710);checked=0
  while checked<N:
   p,ps=rp(r,3);q,qs=rp(r,3);u,us=rp(r,2);v,vs=rp(r,2);x=r.randint(-8,8)
   if qs.eval(x)==0 or vs.eval(x)==0:continue
   f,g=RationalFunction(p,q),RationalFunction(u,v);env={"x":Fraction(x)}
   pairs=[("f",f.evaluate(env),sp.cancel(ps.as_expr()/qs.as_expr()).subs(X,x)),
          ("g",g.evaluate(env),sp.cancel(us.as_expr()/vs.as_expr()).subs(X,x)),
          ("sum",f.add(g).evaluate(env),sp.cancel(ps.as_expr()/qs.as_expr()+us.as_expr()/vs.as_expr()).subs(X,x)),
          ("product",f.multiply(g).evaluate(env),sp.cancel(ps.as_expr()*us.as_expr()/(qs.as_expr()*vs.as_expr())).subs(X,x))]
   for name,got,want in pairs:self.assertEqual(got,Fraction(int(want.p),int(want.q)),msg=f"seed=A4710 case={checked} op={name} f={ps}/{qs} g={us}/{vs} x={x}")
   checked+=1
 def test_univariate_division_gcd_1000(self):
  r=random.Random(0xD1A1DE)
  for i in range(N):
   p,ps=rp(r,r.randint(2,5));q,qs=rp(r,r.randint(1,3));quo,rem=p.divide_univariate(q,variable="x");sq,sr=sp.div(ps,qs)
   self.assertEqual(spoly(quo),sq,msg=f"seed=D1A1DE case={i} dividend={ps} divisor={qs}")
   self.assertEqual(spoly(rem),sr,msg=f"seed=D1A1DE case={i} dividend={ps} divisor={qs}")
   self.assertEqual(spoly(p.gcd_univariate(q,variable="x")),sp.gcd(ps,qs).monic(),msg=f"seed=D1A1DE case={i} p={ps} q={qs}")
 def test_sturm_root_count_1000(self):
  r=random.Random(0x570A);i=0
  while i<N:
   p,ps=rp(r,r.randint(1,5));lo,hi=sorted((r.randint(-8,0),r.randint(1,8)))
   if ps.eval(lo)==0 or ps.eval(hi)==0:continue
   got=p.real_root_count_univariate(lo,hi,variable="x");want=int(ps.count_roots(lo,hi))
   self.assertEqual(got,want,msg=f"seed=570A case={i} polynomial={ps} interval=({lo},{hi})");i+=1
 def test_algebraic_arithmetic_1000(self):
  r=random.Random(0xA16EB);ns=[n for n in range(2,40) if int(n**0.5)**2!=n];x2=Polynomial.variable("x").power(2)
  for i in range(N):
   m,n=r.choice(ns),r.choice(ns)
   a=RealAlgebraicNumber.from_isolating_interval(x2.add(Polynomial.constant(-m)),int(m**0.5),int(m**0.5)+1,variable="x")
   b=RealAlgebraicNumber.from_isolating_interval(x2.add(Polynomial.constant(-n)),int(n**0.5),int(n**0.5)+1,variable="x")
   op=r.choice(("add","sub","mul","div"))
   if op=="add":z,w=aa(a,b),sp.sqrt(m)+sp.sqrt(n)
   elif op=="sub":z,w=asub(a,b),sp.sqrt(m)-sp.sqrt(n)
   elif op=="mul":z,w=amul(a,b),sp.sqrt(m)*sp.sqrt(n)
   else:z,w=adiv(a,b),sp.sqrt(m)/sp.sqrt(n)
   self.assertEqual(sp.simplify(spoly(z.polynomial).as_expr().subs(X,w)),0,msg=f"seed=A16EB case={i} sqrt({m}) {op} sqrt({n})")
   if z.is_rational:
    self.assertEqual(sp.simplify(w-sp.Rational(z.rational_value)),0,msg=f"seed=A16EB case={i} rational result={z.rational_value}")
   else:
    self.assertTrue(sp.Gt(w,sp.Rational(z.lower)) and sp.Lt(w,sp.Rational(z.upper)),msg=f"seed=A16EB case={i} interval={z.lower},{z.upper}")
 def test_polynomial_identity_1000(self):
  r=random.Random(0x9011)
  for i in range(N):
   p,ps=rp(r,r.randint(1,3));q,qs=rp(r,r.randint(1,3))
   if i%2:lhs,rhs=p.multiply(q).to_expr(),q.multiply(p).to_expr()
   else:lhs,rhs=p.add(q).to_expr(),p.add(q.scale(-1)).to_expr()
   result=verify_polynomial_identity(Expr(ExprKind.EQUAL,args=(lhs,rhs)));want=sp.expand(sym(lhs)-sym(rhs))==0
   self.assertEqual(result.status.value=="formally_verified",bool(want),msg=f"seed=9011 case={i} lhs={sym(lhs)} rhs={sym(rhs)}")
 def test_rational_identity_1000(self):
  r=random.Random(0xA471F)
  for i in range(N):
   p,ps=rp(r,r.randint(1,3));q,qs=rp(r,r.randint(1,3));u,us=rp(r,r.randint(1,2));v,vs=rp(r,r.randint(1,2))
   lhs=Expr(ExprKind.DIV,args=(p.to_expr(),q.to_expr()))
   rhs=Expr(ExprKind.DIV,args=(p.multiply(u).to_expr(),q.multiply(u).to_expr())) if i%2 else Expr(ExprKind.DIV,args=(u.to_expr(),v.to_expr()))
   result=verify_rational_identity(Expr(ExprKind.EQUAL,args=(lhs,rhs)));want=sp.cancel(sym(lhs)-sym(rhs))==0
   self.assertEqual(result.status.value=="formally_verified",bool(want),msg=f"seed=A471F case={i} lhs={sym(lhs)} rhs={sym(rhs)}")

if __name__=="__main__":unittest.main()
