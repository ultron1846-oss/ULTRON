import test from 'node:test';
import assert from 'node:assert/strict';
import { fetchSupabasePublicStatus } from '../supabase-integration.js';

test('public status client calls only the read-only action with a publishable key', async () => {
  const originalFetch = globalThis.fetch;
  let captured;
  globalThis.fetch = async (url, options) => {
    captured = { url, options };
    return new Response(JSON.stringify({
      ok: true,
      control_plane: 'online',
      model_status: 'untrained',
      training_enabled: false,
      remote_execution_enabled: false
    }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  };

  try {
    const result = await fetchSupabasePublicStatus();
    assert.equal(result.control_plane, 'online');
    assert.equal(captured.url, 'https://euhmejpaswmdpsutbtse.supabase.co/functions/v1/training-control');
    assert.equal(captured.options.method, 'POST');
    assert.deepEqual(JSON.parse(captured.options.body), { action: 'public_status' });
    assert.match(captured.options.headers.apikey, /^sb_publishable_/);
    assert.equal('Authorization' in captured.options.headers, false);
    assert.equal(captured.options.cache, 'no-store');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('public status client rejects non-success responses', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({
    ok: false,
    error: 'Unavailable'
  }), { status: 503, headers: { 'Content-Type': 'application/json' } });

  try {
    await assert.rejects(fetchSupabasePublicStatus(), /Unavailable/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
