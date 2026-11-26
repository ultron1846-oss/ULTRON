import random
from fractions import Fraction
import pytest
from sympy import sympify, solve, Symbol, Eq
from ultron_level1 import generate_problem, verify

@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_generated_problems_verify(difficulty):
    rng = random.Random(12345)
    for _ in range(500):
        p = generate_problem(rng, difficulty)
        assert verify(p, p["answer"])
        assert not verify(p, "999999999999")

def test_invalid_difficulty():
    with pytest.raises(ValueError):
        generate_problem(random.Random(0), "impossible")

def test_randomized_sympy_agreement_5000():
    rng = random.Random(20261125)
    x = Symbol("x")
    for _ in range(5000):
        p = generate_problem(rng, rng.choice(("easy", "medium", "hard")))
        if p["kind"] == "arithmetic":
            sympy_answer = Fraction(str(sympify(p["expression"], rational=True)))
        else:
            root = solve(Eq(p["a"]*x + p["b"], p["c"]), x)[0]
            sympy_answer = Fraction(int(root.p), int(root.q))
        assert sympy_answer == Fraction(p["answer"])
        assert verify(p, sympy_answer)
        assert not verify(p, sympy_answer + 1)
