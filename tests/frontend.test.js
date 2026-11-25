import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';

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


test('Pages uses the built-in deployment and root runtime assets', async () => {
  await assert.rejects(readFile(new URL('../.github/workflows/pages.yml', import.meta.url), 'utf8'), { code: 'ENOENT' });
  for (const path of ['index.html', 'styles.css', 'app.js', 'math-engine.js', 'supabase-integration.js', 'memory-store.js', 'servers.json']) {
    const content = await readFile(new URL('../' + path, import.meta.url), 'utf8');
    assert.ok(content.trim().length > 0, `missing or empty Pages runtime asset: ${path}`);
  }
});
test('learning page exposes the mathematics roadmap without the removed fixed exercise UI', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  const start = app.indexOf('function renderLearning(){');
  const end = app.indexOf('function renderAgent(){', start);
  assert.ok(start >= 0 && end > start);
  const learning = app.slice(start, end);
  assert.match(learning, /data-topic-index/);
  assert.match(learning, /Mathematics roadmap/);
  assert.doesNotMatch(learning, /Practice an exercise|practice-check|practice-answer|practice-hint|practice-next/);
  assert.match(app, /MODEL TRAINING DISABLED/);
  assert.match(app, /listExperiences\(50\)/);
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


test('frontend entry point keeps a useful overview visible before modules load', async () => {
  const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');
  assert.match(html, /STARTUP \/ FALLBACK VIEW/);
  assert.match(html, /NEURAL MODEL/);
  assert.match(html, /TRAINING DISABLED/);
  assert.match(html, /window\.addEventListener\('error'/);
  assert.match(html, /window\.addEventListener\('unhandledrejection'/);
  assert.match(html, /app\.js\?v=/);
});

test('overview contains real project status and actionable navigation instead of empty chart placeholders', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  const overview = app.slice(app.indexOf('function renderOverview'), app.indexOf('function renderLearning'));
  assert.match(overview, /Foundation workspace online/);
  assert.match(overview, /Math Agent/);
  assert.match(overview, /Google Colab/);
  assert.match(overview, /What is being built/);
  assert.doesNotMatch(overview, /No telemetry|Learning curve|Neural model evaluation/);
  assert.match(app, /nav\.addEventListener\('click'/);
  assert.match(app, /function navigate\(page\)/);
  assert.match(app, /Could not open/);
});

test('browser entry and imported modules pass JavaScript syntax checks', async () => {
  for (const path of ['app.js', 'math-engine.js', 'supabase-integration.js', 'memory-store.js']) {
    execFileSync(process.execPath, ['--check', new URL('../' + path, import.meta.url).pathname]);
  }
});


test('Supabase public status client sends only the publishable key and read-only action', async () => {
  const { fetchSupabasePublicStatus } = await import('../supabase-integration.js');
  let request;
  const payload = {
    ok: true,
    control_plane: 'online',
    model_status: 'untrained',
    training_enabled: false,
    remote_execution_enabled: false,
    provider_directory: 'informational_only',
    checked_at: '2026-11-24T04:00:00.000Z'
  };
  const result = await fetchSupabasePublicStatus({
    fetchImpl: async (url, options) => {
      request = { url, options };
      return new Response(JSON.stringify(payload), { status: 200 });
    }
  });
  assert.equal(result.control_plane, 'online');
  assert.match(request.url, /\/functions\/v1\/training-control$/);
  assert.equal(request.options.method, 'POST');
  assert.deepEqual(JSON.parse(request.options.body), { action: 'public_status' });
  assert.match(request.options.headers.apikey, /^sb_publishable_/);
  assert.equal(request.options.headers.Authorization, undefined);
  assert.equal(request.options.cache, 'no-store');
  assert.ok(request.options.signal instanceof AbortSignal);
});

test('Supabase public status client rejects unsafe or incomplete status payloads', async () => {
  const { fetchSupabasePublicStatus } = await import('../supabase-integration.js');
  await assert.rejects(
    fetchSupabasePublicStatus({
      fetchImpl: async () => new Response(JSON.stringify({
        ok: true,
        control_plane: 'online',
        training_enabled: true,
        remote_execution_enabled: false,
        provider_directory: 'informational_only'
      }), { status: 200 })
    }),
    /safe read-only contract/
  );
});

test('Supabase public status client reports HTTP and malformed JSON errors', async () => {
  const { fetchSupabasePublicStatus } = await import('../supabase-integration.js');
  await assert.rejects(
    fetchSupabasePublicStatus({ fetchImpl: async () => new Response('unavailable', { status: 503 }) }),
    /HTTP 503/
  );
  await assert.rejects(
    fetchSupabasePublicStatus({ fetchImpl: async () => new Response('not-json', { status: 200 }) }),
    /invalid JSON/
  );
});

test('Supabase public status client bounds requests and reports timeouts clearly', async () => {
  const { fetchSupabasePublicStatus } = await import('../supabase-integration.js');
  await assert.rejects(
    fetchSupabasePublicStatus({
      timeoutMs: 1,
      fetchImpl: async (_url, options) => {
        await new Promise((resolve, reject) => {
          options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
        });
      }
    }),
    /timed out/
  );
});

test('Supabase backend page exposes generic status and retains owner sign-in', async () => {
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  assert.match(app, /id="supabase-refresh"/);
  assert.match(app, /id="supabase-status-checked"/);
  assert.match(app, /OWNER-GATED/);
  assert.match(app, /renderOwner/);
  assert.match(app, /owner sign in/i);
  assert.match(app, /training-control public_status action/);
  assert.match(app, /protected health action/);
  // Request timeout behavior is asserted in the Supabase client test above.
});
