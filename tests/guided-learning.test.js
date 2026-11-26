import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../app.js', import.meta.url), 'utf8');
const start = source.indexOf('function answerAgent(){');
const end = source.indexOf('async function loadTrainingStatus()', start);
assert.notEqual(start, -1, 'answerAgent exists');
assert.notEqual(end, -1, 'answerAgent has a stable boundary');
const answerAgent = source.slice(start, end);

test('ordinary learner input is routed through hints rather than final answers', () => {
  assert.match(answerAgent, /if\(runAgentCommand\(raw\)\)return;/);
  assert.equal(answerAgent.includes(String.fromCharCode(92, 92, 115)), false, 'regex whitespace escapes must not be doubled');
  assert.equal(answerAgent.includes(String.fromCharCode(92, 92, 110)), false, 'hint newline escapes must not be doubled');
  assert.match(answerAgent, /GUIDED LEARNING · ANSWER WITHHELD/);
  assert.match(answerAgent, /GUIDED EQUATION MODE · FINAL VALUE WITHHELD/);
  assert.match(answerAgent, /GUIDED CALCULATION · FINAL RESULT WITHHELD/);
  assert.doesNotMatch(answerAgent, /wordProblem\.result/);
  assert.match(answerAgent, /solveLinearEquation\(equation\[1\]\)/, 'equation parser is used only to validate support before a hint');
  assert.doesNotMatch(answerAgent, /evaluateExpression\(/);
  assert.match(answerAgent, /I will not guess a solution/);
  assert.doesNotMatch(answerAgent, /Answer:\s*\$\{/);
});

test('the learner must explicitly invoke a slash tool', () => {
  assert.match(answerAgent, /runAgentCommand\(raw\)/);
  assert.match(source, /Calculator, graph and numerical commands run only when explicitly typed/);
});
