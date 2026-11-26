import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateExpression, solveLinearEquation, tokenize } from '../math-engine.js';

test('supports arithmetic precedence, grouping and operator aliases', () => {
  assert.equal(evaluateExpression('(12 + 8) / 4 ^ 2'), 1.25);
  assert.equal(evaluateExpression('-2^2'), -4);
  assert.equal(evaluateExpression('2 * (3 + 4)'), 14);
  assert.equal(evaluateExpression('18 × 7 ÷ 3'), 42);
  assert.equal(evaluateExpression('2^3^2'), 512);
});

test('supports fractions as division, decimals, scientific notation and negative values', () => {
  assert.equal(evaluateExpression('(1/3) + (1/6)'), 0.5);
  assert.equal(evaluateExpression('.5 + 1.25'), 1.75);
  assert.equal(evaluateExpression('2.'), 2);
  assert.equal(evaluateExpression('1e-3 * 1000'), 1);
  assert.equal(evaluateExpression('-3.5 + 2'), -1.5);
});

test('supports powers and numeric roots expressed as fractional powers', () => {
  assert.equal(evaluateExpression('9^(1/2)'), 3);
  assert.equal(evaluateExpression('27^(1/3)'), 3);
  assert.equal(evaluateExpression('2^-3'), 0.125);
  assert.throws(() => evaluateExpression('(-8)^(1/3)'), /numeric range/);
});

test('rejects empty, malformed, unsafe, unsupported and overlong expressions with clear errors', () => {
  assert.throws(() => evaluateExpression(''), /Enter a mathematical expression/);
  assert.throws(() => evaluateExpression('   '), /Enter a mathematical expression/);
  assert.throws(() => evaluateExpression('1 / 0'), /Division by zero/);
  assert.throws(() => evaluateExpression('18 ÷ 0'), /Division by zero/);
  assert.throws(() => evaluateExpression('2 + process.exit()'), /Unsupported character or format/);
  assert.throws(() => evaluateExpression('2 $ 3'), /Unsupported character or format/);
  assert.throws(() => evaluateExpression('(4 + 1'), /Missing closing parenthesis/);
  assert.throws(() => evaluateExpression('1e999'), /numeric range/);
  assert.throws(() => evaluateExpression('2 + 3 xyz'), /Unsupported character or format/);
  assert.throws(() => tokenize('1'.repeat(241)), /too long/);
  assert.throws(() => evaluateExpression('1+'.repeat(61)+'1'), /too many parts/);
});

test('solves linear equations with integer, decimal, fractional and negative coefficients', () => {
  assert.deepEqual(solveLinearEquation('2x + 3 = 11'), { kind: 'unique', value: 4 });
  assert.deepEqual(solveLinearEquation('0.5x = 2'), { kind: 'unique', value: 4 });
  assert.deepEqual(solveLinearEquation('x/2 = 3'), { kind: 'unique', value: 6 });
  assert.deepEqual(solveLinearEquation('-3x + 6 = 0'), { kind: 'unique', value: 2 });
  assert.deepEqual(solveLinearEquation('2(x + 1) = 10'), { kind: 'unique', value: 4 });
  assert.deepEqual(solveLinearEquation('(x + 1)/2 = 3'), { kind: 'unique', value: 5 });
  assert.deepEqual(solveLinearEquation('X + 2 = 5'), { kind: 'unique', value: 3 });
});

test('classifies identities and contradictions', () => {
  assert.deepEqual(solveLinearEquation('x + 2 = x + 2'), { kind: 'all-real' });
  assert.deepEqual(solveLinearEquation('x + 2 = x + 3'), { kind: 'none' });
});

test('rejects nonlinear, multi-variable, malformed and unsafe equations', () => {
  for (const value of [
    'x^2 = 4',
    'x*x = 4',
    '(x + 1)(x - 1) = 0',
    'x + y = 3',
    'x =',
    '= 3',
    'x == 2',
    'x = 2 = 3',
    'x = 1/0',
    'x = process.exit()',
    ''
  ]) assert.throws(() => solveLinearEquation(value), undefined, value);
  assert.throws(() => solveLinearEquation('x'.repeat(241)), /too long/);
});

test('returns only finite equation solutions', () => {
  assert.throws(() => solveLinearEquation('1e-308x = 1e308'), /numeric range/);
});
