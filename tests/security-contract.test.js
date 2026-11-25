import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const read = path => readFile(new URL('../' + path, import.meta.url), 'utf8');

test('public frontend security contract stays fail-closed', async () => {
  const [html, app, integration, auth, servers] = await Promise.all([
    read('index.html'), read('app.js'), read('supabase-integration.js'),
    read('owner-auth.js'), read('servers.json')
  ]);
  assert.ok(html.includes('data-page="owner"'));
  assert.ok(!html.includes('data-page="signup"'));
  assert.ok(!app.includes('functions.invoke'));
  assert.ok(!app.includes('fetch(' + "'training-control'"));
  assert.ok(!app.includes('fetch(' + "'device-control'"));
  assert.ok(!integration.includes('service_role') && !integration.includes('sb_secret_'));
  assert.ok(!auth.includes('service_role') && !auth.includes('sb_secret_'));
  assert.ok(auth.includes('/functions/v1/training-control'));
  assert.ok(auth.includes('verifyOwner'));
  assert.ok(app.includes('MODEL TRAINING DISABLED'));
  assert.ok(app.includes('REMOTE EXECUTION DISABLED'));
  assert.ok(JSON.parse(servers).providers.every(provider => provider.execution_enabled === false));
});

test('repeatable SQL safeguard revokes, never grants, TRUNCATE for user-data tables', async () => {
  const sql = await read('docs/security/revoke_authenticated_truncate.sql');
  assert.ok(sql.includes('REVOKE TRUNCATE'));
  assert.ok(sql.includes('FROM authenticated'));
  for (const table of ['experiences','knowledge','mistakes','checkpoints','backups','memory_imports']) {
    assert.ok(sql.includes('public.' + table));
  }
  assert.ok(sql.includes('has_table_privilege'));
  assert.ok(!sql.includes('GRANT TRUNCATE'));
});
