# Bounded linear constant-coefficient first-order ODE generator

**Topic ID:** linear_constant_coefficient_first_order_ODEs  
**Status:** generator available and independently validated; no trained-model benchmark or mastery claim.

## Supported family

The generator accepts exact rational coefficients in

\[
y'=a y+b,\qquad y(0)=y_0.
\]

When \(a=0\), the exact solution is \(y(t)=y_0+bt\). When \(a\ne0\), it is

\[
y(t)=\left(y_0+\frac{b}{a}\right)e^{at}-\frac{b}{a}.
\]

This is one bounded constant-coefficient linear family. It is not a general first-order ODE solver and does not support variable coefficients, separable general equations, exact differential forms, implicit families, systems, or higher-order ODEs.

## Bounds and difficulty

- Input values a, b, and y0 are rational pairs [numerator, denominator].
- Absolute input numerator is at most 10; positive denominator is at most 5.
- Difficulty d in {1,2,3,4,5} narrows absolute numerator to at most 2d and denominator to at most d.
- Seeds are integers from 0 through 2^31 - 1.
- Derived solution numerator and denominator are each capped at 1,000 before validator parsing.
- Booleans, floats, malformed pairs, non-positive denominators, unsupported keys and values outside the difficulty envelope are rejected.

Difficulty changes the rational coefficient envelope; it does not claim mastery or compare difficulty to other topic families.

## Independent verification

The validator does not regenerate the seed. It reconstructs exact rational coefficients from ingredients, then checks the symbolic ODE identity and initial condition independently:

- For a=0, with y=c0+c1t, check c0=y0 and c1=b=ac0+b.
- For a!=0, with y=c1e^(at)+c0, check the exponent rate is a, ac0+b=0, and c1+c0=y0.

It then reconstructs the canonical prompt, derivation steps and answer to reject tampering. Tests independently recompute these identities for 500 fixed seeds, exercise both solution branches and homogeneous/inhomogeneous cases, and cover input, seed, difficulty and derived-value boundaries.

## Curriculum status

The old broad first_order_ODEs item remains catalogued but unavailable. This narrow subfamily is the only first-order ODE family claimed as implemented. Second-order equations, systems of ODEs, PDEs, separable variable-coefficient equations and exact equations remain incomplete.
