import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
const read = path => readFile(new URL('../' + path, import.meta.url), 'utf8');

test('GitHub Pages stages every runtime module, including owner authentication', async () => {
  const [workflow, app] = await Promise.all([read('.github/workflows/pages.yml'), read('app.js')]);
  assert.match(workflow, /cp owner-auth\.js _site\//);
  for (const module of ['math-engine.js', 'supabase-integration.js', 'owner-auth.js', 'memory-store.js']) {
    assert.ok(app.includes(module), `app entry must import ${module}`);
    assert.ok(workflow.includes(module), `Pages artifact must stage ${module}`);
  }
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
  assert.match(memory, /export async function listRecords/);
  assert.match(memory, /export async function clearMemory/);
  assert.match(memory, /tx\.oncomplete/);
  assert.match(app, /setTimeout\(\(\)=>URL\.revokeObjectURL\(url\),1000\)/);
});
test('all browser modules pass syntax validation', async () => {
  for (const path of ['app.js', 'math-engine.js', 'supabase-integration.js', 'memory-store.js', 'owner-auth.js']) {
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
