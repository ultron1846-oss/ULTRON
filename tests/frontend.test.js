import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('control-room shell exposes its seven primary destinations', async () => {
  const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');
  for (const page of ['overview','learning','agent','memory','servers','backend','settings']) assert.match(html, new RegExp(`data-page="${page}"`));
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
  assert.match(backend, /owner-session gated/);
  assert.match(backend, /public_status/);
  assert.match(backend, /ultron1846-oss\/ULTRON/);
  assert.doesNotMatch(backend, /service_role|sb_secret_|ULTRON_GITHUB_TOKEN/);
  assert.doesNotMatch(app, /functions\.invoke|fetch\([^)]*training-control|fetch\([^)]*device-control/);
});


test('Pages deployment stages every runtime module and data file', async () => {
  const workflow = await readFile(new URL('../.github/workflows/pages.yml', import.meta.url), 'utf8');
  assert.match(workflow, /cp index\.html styles\.css app\.js math-engine\.js supabase-integration\.js memory-store\.js servers\.json command-center\.html _site\//);
});


test('learning page exposes topic exploration and real local practice interactions', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  assert.match(app, /function renderLearning/);
  assert.match(app, /data-topic-index/);
  assert.match(app, /practice-check/);
  assert.match(app, /saveExperience/);
  assert.match(app, /ultron-practice-count/);
  assert.match(app, /MODEL TRAINING DISABLED/);
});

test('Colab directory is informational and remote execution stays disabled', async () => {
  const directory = JSON.parse(await readFile(new URL('../servers.json', import.meta.url), 'utf8'));
  assert.equal(directory.providers[0].id, 'google-colab');
  assert.equal(directory.providers[0].execution_enabled, false);
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  assert.match(app, /REMOTE EXECUTION DISABLED/);
  assert.match(app, /Official provider site/);
  assert.doesNotMatch(app, /colab\.googleapis\.com|googleapis\.com\/compute/);
});

test('memory page provides local backup and restore without public Supabase table access', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  const memory = await readFile(new URL('../memory-store.js', import.meta.url), 'utf8');
  assert.match(app, /renderMemory/);
  assert.match(app, /memory-export/);
  assert.match(app, /memory-import-file/);
  assert.match(memory, /ULTRON_MEMORY/);
  assert.match(memory, /experiences.*knowledge.*mistakes.*checkpoints/);
  assert.match(memory, /ultron-local-memory/);
  assert.doesNotMatch(app, /from ['"]@supabase|\.from\(['"]experiences/);
});
