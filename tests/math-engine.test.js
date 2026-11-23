import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateExpression, solveLinearEquation, tokenize } from '../math-engine.js';

test('parses standard arithmetic and precedence', () => {
  assert.equal(evaluateExpression('(12 + 8) / 4 ^ 2'), 1.25);
  assert.equal(evaluateExpression('-2^2'), -4);
  assert.equal(evaluateExpression('2 * (3 + 4)'), 14);
});
test('rejects unsafe, malformed and invalid expressions', () => {
  for (const value of ['', '1 / 0', '2 + process.exit()', '2 $ 3', '(4 + 1', '1e999']) assert.throws(() => evaluateExpression(value));
  assert.throws(() => tokenize('1'.repeat(241)), /too long/);
});
test('solves single-variable linear equations', () => {
  assert.deepEqual(solveLinearEquation('2x + 3 = 11'), { kind: 'unique', value: 4 });
  assert.deepEqual(solveLinearEquation('x + 2 = x + 2'), { kind: 'all-real' });
  assert.deepEqual(solveLinearEquation('x + 2 = x + 3'), { kind: 'none' });
  assert.throws(() => solveLinearEquation('x^2 = 4'));
});
