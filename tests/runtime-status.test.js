import test from 'node:test';
import assert from 'node:assert/strict';
import {
  RuntimeStatusMonitor,
  RUNTIME_STATUS_REFRESH_MS,
  RUNTIME_STATUS_STALE_MS,
  formatStatusAge
} from '../runtime-status.js';

const payload = (checkedAt = new Date().toISOString()) => ({
  ok: true,
  control_plane: 'online',
  model_status: 'untrained',
  training_enabled: false,
  remote_execution_enabled: false,
  provider_directory: 'informational_only',
  checked_at: checkedAt
});

test('mock success produces an online fresh snapshot with generic non-authorizing flags', async () => {
  let now = Date.parse('2026-11-28T03:00:00.000Z');
  let calls = 0;
  const monitor = new RuntimeStatusMonitor({
    fetchStatus: async () => { calls += 1; return payload(new Date(now).toISOString()); },
    now: () => now
  });

  const snapshot = await monitor.refresh();
  assert.equal(calls, 1);
  assert.equal(snapshot.state, 'online');
  assert.equal(snapshot.data.model_status, 'untrained');
  assert.equal(snapshot.data.training_enabled, false);
  assert.equal(snapshot.data.remote_execution_enabled, false);
  assert.equal(snapshot.ageMs, 0);
  assert.equal(snapshot.error, null);
});

test('failed refresh preserves last successful response and marks it stale', async () => {
  let now = Date.parse('2026-11-28T03:00:00.000Z');
  let available = true;
  const monitor = new RuntimeStatusMonitor({
    fetchStatus: async () => {
      if (!available) throw new Error('HTTP 503');
      return payload(new Date(now).toISOString());
    },
    now: () => now,
    staleAfterMs: 1_000
  });

  const good = await monitor.refresh();
  assert.equal(good.state, 'online');
  available = false;
  now += 1_500;
  const stale = await monitor.refresh();
  assert.equal(stale.state, 'stale');
  assert.equal(stale.data.control_plane, 'online');
  assert.equal(stale.error, 'HTTP 503');
  assert.equal(stale.ageMs, 1_500);
});

test('offline state never calls the mocked runtime and preserves last-known state as stale', async () => {
  let calls = 0;
  const monitor = new RuntimeStatusMonitor({
    fetchStatus: async () => { calls += 1; return payload(); }
  });

  const initial = await monitor.refresh({ online: true });
  const stale = await monitor.setOnline(false);
  assert.equal(initial.state, 'online');
  assert.equal(stale.state, 'stale');
  assert.equal(stale.online, false);
  assert.match(stale.error, /offline/i);
  assert.equal(calls, 1);

  const offlineFirst = new RuntimeStatusMonitor({ fetchStatus: async () => { calls += 1; return payload(); } });
  assert.equal((await offlineFirst.refresh({ online: false })).state, 'offline');
  assert.equal(calls, 1);
});

test('invalid mock payload fails closed instead of reporting service online', async () => {
  const monitor = new RuntimeStatusMonitor({
    fetchStatus: async () => ({ ...payload(), remote_execution_enabled: true })
  });
  const snapshot = await monitor.refresh();
  assert.equal(snapshot.state, 'unavailable');
  assert.equal(snapshot.data, null);
  assert.match(snapshot.error, /read-only contract/i);
});

test('concurrent refreshes share one in-flight mocked request', async () => {
  let calls = 0;
  let resolve;
  const pending = new Promise(done => { resolve = done; });
  const monitor = new RuntimeStatusMonitor({
    fetchStatus: async () => { calls += 1; return pending; }
  });

  const first = monitor.refresh();
  const second = monitor.refresh();
  assert.equal(calls, 1);
  resolve(payload());
  const [a, b] = await Promise.all([first, second]);
  assert.equal(a.state, 'online');
  assert.equal(b.state, 'online');
});

test('periodic status refresh starts and stops cleanly with injected timer functions', async () => {
  let timerCallback;
  let timerDelay;
  let cleared = null;
  let calls = 0;
  const monitor = new RuntimeStatusMonitor({
    fetchStatus: async () => { calls += 1; return payload(); },
    setIntervalImpl: (callback, delay) => { timerCallback = callback; timerDelay = delay; return 42; },
    clearIntervalImpl: id => { cleared = id; }
  });

  await monitor.start();
  assert.equal(timerDelay, RUNTIME_STATUS_REFRESH_MS);
  timerCallback();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls, 2);
  monitor.stop();
  assert.equal(cleared, 42);
  assert.equal(monitor.interval, null);
  assert.equal(RUNTIME_STATUS_STALE_MS, 120_000);
});

test('status age formatting remains readable', () => {
  assert.equal(formatStatusAge(0), 'just now');
  assert.equal(formatStatusAge(12_000), '12s ago');
  assert.equal(formatStatusAge(120_000), '2m ago');
  assert.equal(formatStatusAge(3_900_000), '1h 5m ago');
  assert.equal(formatStatusAge(null), 'unknown age');
});
