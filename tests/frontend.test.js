import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('control-room shell exposes its six primary destinations', async () => {
  const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');
  for (const page of ['overview','learning','agent','servers','backend','settings']) assert.match(html, new RegExp(`data-page="${page}"`));
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


test('Supabase backend page documents the audited contract without exposing owner-only controls', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');
  const backend = await readFile(new URL('../supabase-integration.js', import.meta.url), 'utf8');
  assert.match(html, /data-page="backend"/);
  assert.match(app, /renderBackend/);
  assert.match(backend, /device-control/);
  assert.match(backend, /training-control/);
  assert.match(backend, /owner JWT/);
  assert.match(backend, /ultron1846-oss\/ULTRON/);
  assert.doesNotMatch(backend, /service_role|sb_secret_|ULTRON_GITHUB_TOKEN/);
  assert.doesNotMatch(app, /functions\.invoke|fetch\([^)]*training-control|fetch\([^)]*device-control/);
});


test('Pages deployment stages the Supabase integration module required by app.js', async () => {
  const workflow = await readFile(new URL('../.github/workflows/pages.yml', import.meta.url), 'utf8');
  assert.match(workflow, /supabase-integration\.js _site\//);
});
