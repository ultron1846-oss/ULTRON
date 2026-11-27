import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('control-room shell exposes all five primary destinations', async () => {
  const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');
  for (const page of ['overview', 'learning', 'agent', 'servers', 'settings']) {
    assert.ok(html.includes(`data-page="${page}"`), `missing navigation destination: ${page}`);
  }
  assert.ok(html.includes('viewport-fit=cover'));
  assert.ok(html.includes('mobile-menu'));
});

test('frontend keeps model training and remote execution disabled', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  assert.ok(app.includes('TRAINING DISABLED'));
  assert.ok(app.includes('REMOTE EXECUTION DISABLED'));
  assert.ok(!app.includes('optimizer.step('));
  assert.ok(!app.includes('startTraining('));
  assert.ok(!app.includes('new Function'));
});

test('provider directory handles missing data without inventing availability', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  assert.ok(app.includes("fetch('./servers.json'"));
  assert.ok(app.includes('Provider directory unavailable'));
  assert.ok(app.includes('No provider is assumed available'));
});

test('Math Agent uses the existing deterministic engine and rejects unsupported input', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  assert.ok(app.includes('evaluateExpression'));
  assert.ok(app.includes('solveLinearEquation'));
  assert.ok(app.includes('Unsupported requests are not guessed'));
});


test('Math Agent exposes commands for every mathematics roadmap topic', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  for (const command of [
    '/arithmetic', '/algebra', '/geometry', '/trigonometry', '/calculus',
    '/linear-algebra', '/probability', '/statistics', '/number-theory', '/logic-proofs'
  ]) assert.ok(app.includes(`command:'${command}'`), `missing topic command: ${command}`);
  assert.ok(app.includes("command==='/help'"));
  assert.ok(app.includes("command==='/topics'"));
  assert.ok(app.includes('data-topic-command'));
  assert.ok(app.includes('PLANNED · NOT SOLVER-SUPPORTED'));
});

test('settings exports a versioned runtime config without enabling execution', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  assert.ok(app.includes('export-runtime-config'));
  assert.ok(app.includes('ultron-runtime-config.json'));
  assert.ok(app.includes('schema_version:1'));
  assert.ok(app.includes('training_authorized:false'));
  assert.ok(app.includes('remote_execution_enabled:false'));
  assert.ok(app.includes('configuration only. It does not start training'));
});
