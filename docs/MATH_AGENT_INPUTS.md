# Math Agent input contract

This document describes the **current deterministic browser engine**, not trained neural-model capability.

## Supported arithmetic expression format

- Decimal and scientific-notation numbers: `12`, `0.25`, `.5`, `2.`, `1e-3`.
- Parentheses: `(2 + 3) * 4`.
- Unary signs: `-5 + +2`.
- Operators: `+`, `-`, `*`, `/`, `×`, `÷`, and `^`.
- Fractions are expressed as division, for example `(1/3) + (1/6)`; results use JavaScript floating-point numbers, not exact rational arithmetic.
- Numeric roots can be expressed as fractional powers for supported real values, for example `9^(1/2)` and `27^(1/3)`.
- Maximum source length: 240 characters. Maximum token count: 120.

## Supported equation format

The linear-equation solver accepts one equation with exactly one equals sign and variable `x` (uppercase `X` is normalized).

- Linear sums and differences: `2x + 3 = 11`.
- Decimal or fractional coefficients: `0.5x = 2`, `x/2 = 3`.
- Parenthesized linear expressions and multiplication/division by constants: `2(x + 1) = 10`, `(x + 1)/2 = 3`.
- It classifies unique solutions, identities (`all-real`) and contradictions (`none`).

## Unsupported by the basic expression/equation parser

- Function calls or named functions such as `sqrt(x)`, `sin(x)`, `log(x)`; use a specifically registered Math Agent tool where available.
- Symbolic variables in an arithmetic expression.
- Variables other than `x`, systems with multiple unknowns, and nonlinear equations such as `x^2 = 4` or `x*x = 4`.
- Exact symbolic radicals, complex-number results, implicit multiplication of two numeric literals, and general polynomial expansion/factorization.
- Proofs, calculus, general symbolic algebra, natural-language equations outside the bounded word-problem grammar, and unsupported notation such as `√` or `**`.

## Error and abstention behavior

Empty input, invalid characters, malformed parentheses/equations, division by zero, excessive length/token count, nonlinear equations, and non-finite results raise a descriptive error. The Math Agent must not present a guessed result for unsupported requests. In conversational mode it may offer a general next-step hint; an explicit equation that fails the linear parser is identified as unsupported and its solution is withheld.

The conversational Math Agent is tutor-first and does not reveal a final answer for ordinary input. Explicit slash commands are opt-in deterministic tools. Tool output and generated examples are not evidence of neural-model learning.
