import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { evaluateExpression, solveLinearEquation } from '../math-engine.js';
const read = path => readFile(new URL('../' + path, import.meta.url), 'utf8');

test('documented arithmetic and linear-equation formats are executable', () => {
  assert.equal(evaluateExpression('(1/3) + (1/6)'), 0.5);
  assert.equal(evaluateExpression('9^(1/2)'), 3);
  assert.deepEqual(solveLinearEquation('2(x + 1) = 10'), { kind: 'unique', value: 4 });
  assert.deepEqual(solveLinearEquation('x/2 = 3'), { kind: 'unique', value: 6 });
});

test('unsupported equations fail closed rather than yielding a guessed answer', () => {
  for (const input of ['x^2 = 4', 'x*x = 4', 'x + y = 3', 'x == 2', 'x = process.exit()']) {
    assert.throws(() => solveLinearEquation(input), undefined, input);
  }
});

test('Math Agent validates equation grammar but keeps final solutions withheld', async () => {
  const app = await read('app.js');
  const agent = app.slice(app.indexOf('function answerAgent(){'), app.indexOf('async function loadTrainingStatus(){'));
  assert.match(agent, /solveLinearEquation\(equation\[1\]\)/);
  assert.match(agent, /UNSUPPORTED EQUATION · NO ANSWER FABRICATED/);
  assert.match(agent, /I will not guess a solution/);
  assert.match(agent, /I will not invent a result/);
  assert.match(agent, /GUIDED EQUATION MODE · FINAL VALUE WITHHELD/);
  assert.doesNotMatch(agent, /addChat\('assistant',[^\n]*\.value/);
});

test('the published contract states scope, limits, errors and unsupported notation', async () => {
  const doc = await read('docs/MATH_AGENT_INPUTS.md');
  const app = await read('app.js');
  assert.match(doc, /Supported arithmetic expression format/);
  assert.match(doc, /Unsupported by the basic expression\/equation parser/);
  assert.match(doc, /240 characters/);
  assert.match(doc, /does not present a guessed result|must not present a guessed result/);
  assert.match(app, /Full Math Agent input specification/);
});
