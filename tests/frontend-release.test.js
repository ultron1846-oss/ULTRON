import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
const read = path => readFile(new URL('../' + path, import.meta.url), 'utf8');

test('GitHub Pages stages required runtime modules and excludes account authentication', async () => {
  const [workflow, app, html] = await Promise.all([read('.github/workflows/pages.yml'), read('app.js'), read('index.html')]);
  for (const module of ['math-engine.js', 'supabase-integration.js', 'memory-store.js']) {
    assert.ok(app.includes(module), `app entry must import ${module}`);
    assert.ok(workflow.includes(module), `Pages artifact must stage ${module}`);
  }
  assert.doesNotMatch(app, /owner-auth|signInOwner|verifyOwner|signOutOwner|renderOwner|bindOwner/);
  assert.doesNotMatch(html, /data-page="owner"|Owner sign in|owner-password|owner-email/);
  assert.doesNotMatch(workflow, /owner-auth\.js/);
});
test('mobile navigation has accessible controls and closes on Escape/outside interaction', async () => {
  const [html, app] = await Promise.all([read('index.html'), read('app.js')]);
  assert.match(html, /aria-controls="sidebar"/);
  assert.match(html, /aria-expanded="false"/);
  assert.match(app, /event\.key==='Escape'/);
  assert.match(app, /document\.addEventListener\('pointerdown'/);
  assert.match(app, /aria-current/);
});
test('contrast preference persists locally and is exposed as a pressed state', async () => {
  const [html, app] = await Promise.all([read('index.html'), read('app.js')]);
  assert.match(html, /id="theme-toggle"[^>]*aria-pressed="false"/);
  assert.match(app, /ultron-soft-contrast/);
  assert.match(app, /applyContrastPreference/);
});
test('Memory Vault supports mistake review, safe clear-all and committed transactions', async () => {
  const [app, memory] = await Promise.all([read('app.js'), read('memory-store.js')]);
  assert.match(app, /memory-mistake-history/);
  assert.match(app, /memory-clear/);
  assert.match(app, /window\.confirm\(/);
  assert.match(app, /await clearMemory\(\);navigate\('memory'\)/);
  assert.match(memory, /export async function listRecords/);
  assert.match(memory, /export async function clearMemory/);
  assert.match(memory, /tx\.oncomplete/);
  assert.match(app, /setTimeout\(\(\)=>URL\.revokeObjectURL\(url\),1000\)/);
});
test('all browser modules pass syntax validation', async () => {
  for (const path of ['app.js', 'math-engine.js', 'supabase-integration.js', 'memory-store.js']) {
    execFileSync(process.execPath, ['--check', new URL('../' + path, import.meta.url).pathname]);
  }
});
test('frontend release keeps remote execution and model training disabled', async () => {
  const [app, servers] = await Promise.all([read('app.js'), read('servers.json')]);
  assert.match(app, /REMOTE EXECUTION DISABLED/);
  assert.match(app, /MODEL TRAINING DISABLED/);
  const directory = JSON.parse(servers);
  assert.ok(directory.providers.every(provider => provider.execution_enabled === false));
  assert.doesNotMatch(app, /colab\.googleapis\.com|googleapis\.com\/compute/);
});

test('Learn & practice page contains the topic roadmap but no fixed exercise interface', async () => {
  const app = await read('app.js');
  const start = app.indexOf('function renderLearning(){');
  const end = app.indexOf('function renderAgent(){', start);
  assert.ok(start >= 0 && end > start, 'learning renderer exists');
  const learning = app.slice(start, end);
  for (const removed of ['Practice an exercise', 'EXERCISE 2 OF 4', 'practice-question', 'practice-answer', 'practice-check', 'practice-hint', 'practice-next', 'Check answer', 'Show hint', 'Next exercise']) {
    assert.ok(!learning.includes(removed), `removed practice UI text/control: ${removed}`);
  }
  assert.match(learning, /Mathematics roadmap/);
  assert.match(learning, /data-topic-index/);
});
test('practice exercise handlers and fixtures are removed without deleting existing memory records', async () => {
  const app = await read('app.js');
  assert.doesNotMatch(app, /const exercises = \[/);
  assert.doesNotMatch(app, /document\.querySelector\('#practice-(?:check|hint|next)'\)/);
  assert.match(app, /listExperiences\(50\)/);
  assert.match(app, /listRecords\('mistakes',30\)/);
});

test('Pages deployment validates all required assets and rejects retired auth artifacts', async () => {
  const workflow = await read('.github/workflows/pages.yml');
  assert.match(workflow, /Validate static site inputs/);
  assert.match(workflow, /set -eu/);
  assert.match(workflow, /test -s/);
  assert.match(workflow, /if \[ -e owner-auth\.js \]/);
  assert.match(workflow, /mkdir -p _site/);
});
test('static shell does not present a public access mode', async () => {
  const html = await read('index.html');
  assert.doesNotMatch(html, /public-pill|PUBLIC BROWSER ACCESS|PUBLIC MATHEMATICS WORKSPACE|PUBLIC DASHBOARD/i);
  assert.match(html, /No account required/);
});
test('all required Pages runtime assets exist and are non-empty', async () => {
  for (const path of ['index.html', 'styles.css', 'app.js', 'math-engine.js', 'supabase-integration.js', 'memory-store.js', 'servers.json', 'command-center.html']) {
    const content = await read(path);
    assert.ok(content.trim().length > 0, `required static asset is empty: ${path}`);
  }
});

test('retired browser auth module and its dedicated tests are absent', async () => {
  await assert.rejects(read('owner-auth.js'), { code: 'ENOENT' });
  await assert.rejects(read('tests/owner-auth.test.js'), { code: 'ENOENT' });
});
