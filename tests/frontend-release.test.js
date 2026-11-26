import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
const read = path => readFile(new URL('../' + path, import.meta.url), 'utf8');

test('static frontend requires no login or sign-up and has no owner authentication route', async () => {
  const [app, html] = await Promise.all([read('app.js'), read('index.html')]);
  assert.doesNotMatch(html, /data-page="owner"|Owner sign in|owner-signin-form|data-page="signup"|Sign up/i);
  assert.doesNotMatch(app, /owner-auth\.js|renderOwner|bindOwner|signInOwner|verifyOwner|signOutOwner|owner-signin|owner-password/);
  assert.match(html, /No login or sign-up required/);
  assert.match(app, /Account-free public website/);
});
test('account-free frontend exposes no job, checkpoint mutation or pairing controls', async () => {
  const app = await read('app.js');
  const html = await read('index.html');
  assert.doesNotMatch(app, /id="training-(?:start|pause|stop|resume|save)"/);
  assert.doesNotMatch(app, /data-page="owner"|data-page="pairing"|id="pairing/);
  assert.doesNotMatch(html, /data-page="owner"|data-page="pairing"|Owner sign in/i);
  assert.match(app, /READ-ONLY CONTROL PLANE/);
  assert.match(app, /No job controls/);
});
test('iPad responsive contract includes viewport, safe areas, touch targets and local RAM preference', async () => {
  const [html, css, app] = await Promise.all([read('index.html'), read('styles.css'), read('app.js')]);
  assert.match(html, /name="viewport"/);
  assert.match(css, /@media\(max-width:760px\)/);
  assert.match(css, /env\(safe-area-inset-bottom\)/);
  assert.match(css, /min-height:44px/);
  assert.match(app, /id="memory-slider" type="range" min="2" max="10" step="1"/);
  assert.match(app, /safeSet\('ultron-memory-level',slider.value\)/);
  assert.match(app, /does not allocate device RAM/);
  assert.match(app, /Saved in this browser only/);
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

test('no duplicate custom Pages artifact deployment workflow remains', async () => {
  await assert.rejects(read('.github/workflows/pages.yml'), { code: 'ENOENT' });
  const workflow = await read('.github/workflows/test.yml');
  assert.match(workflow, /pull_request/);
  assert.match(workflow, /run: npm test/);
});
test('static shell has no access-mode toggle, login, sign-up or owner route', async () => {
  const html = await read('index.html');
  const app = await read('app.js');
  assert.doesNotMatch(html, /public-pill|PUBLIC BROWSER ACCESS|PUBLIC MATHEMATICS WORKSPACE|PUBLIC DASHBOARD/i);
  assert.doesNotMatch(html, /data-page="owner"|data-page="signup"|Owner sign in|Sign up/i);
  assert.doesNotMatch(app, /owner-auth\.js|renderOwner|bindOwner|signInOwner|verifyOwner|signOutOwner/);
});
test('all required Pages runtime assets exist and are non-empty', async () => {
  for (const path of ['index.html', 'styles.css', 'app.js', 'math-engine.js', 'supabase-integration.js', 'memory-store.js', 'servers.json', 'command-center.html']) {
    const content = await read(path);
    assert.ok(content.trim().length > 0, `required static asset is empty: ${path}`);
  }
});

