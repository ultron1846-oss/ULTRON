import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('control-room shell exposes its five primary destinations', async () => {
  const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');
  for (const page of ['overview','learning','agent','servers','settings']) assert.match(html, new RegExp(`data-page="${page}"`));
  assert.match(html, /viewport-fit=cover/);
  assert.match(html, /mobile-menu/);
});

test('frontend clearly represents training as disabled and does not implement training execution', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  assert.match(app, /TRAINING DISABLED/);
  assert.match(app, /REMOTE EXECUTION DISABLED/);
  assert.doesNotMatch(app, /\b(?:optimizer\.step|backward\s*\(|trainModel\s*\(|startTraining\s*\()/);
  assert.doesNotMatch(app, /\beval\s*\(|new Function/);
});

test('provider directory handles a missing server file without inventing availability', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  assert.match(app, /fetch\('\.\/servers\.json'/);
  assert.match(app, /Provider directory unavailable/);
  assert.match(app, /No provider is assumed available/);
});

test('math agent uses the existing deterministic math engine', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  assert.match(app, /evaluateExpression/);
  assert.match(app, /solveLinearEquation/);
  assert.match(app, /Unsupported requests are not guessed/);
});
