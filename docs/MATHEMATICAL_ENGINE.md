# Mathematical Engine Status

## Implemented on the open foundation branch

`math-engine.js` exports `tokenize`, `evaluateExpression`, and `solveLinearEquation`. The expression parser accepts decimal numbers, parentheses, unary signs, `+`, `-`, `*`, `/`, and `^`. It rejects unrecognized characters, malformed expressions, division by zero, oversized input, and non-finite results. It does not execute JavaScript and does not use `eval()` or `new Function()`.

The equation solver handles a narrow one-variable linear format with numeric coefficients, for example `2x + 3 = 11`. This is not symbolic algebra. The grammar, floating-point tolerance policy, exponent domain behavior, and broader malformed-input cases still need specification.

## Next engineering work

Before adding mathematical domains, document the grammar and expected errors, add reference examples and regression tests, and independently check equation solutions by substitution. Keep numerical operations separate from symbolic transformations. Do not label unsupported functionality as available.
