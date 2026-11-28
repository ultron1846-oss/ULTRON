export const RUNTIME_STATUS_REFRESH_MS = 60_000;
export const RUNTIME_STATUS_STALE_MS = 120_000;

function validTimestamp(value) {
  if (typeof value !== 'string' || !value) return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export class RuntimeStatusMonitor {
  constructor({
    fetchStatus,
    now = Date.now,
    refreshIntervalMs = RUNTIME_STATUS_REFRESH_MS,
    staleAfterMs = RUNTIME_STATUS_STALE_MS,
    onChange = () => {},
    setIntervalImpl = globalThis.setInterval,
    clearIntervalImpl = globalThis.clearInterval
  } = {}) {
    if (typeof fetchStatus !== 'function') throw new TypeError('fetchStatus must be a function');
    if (typeof now !== 'function' || typeof onChange !== 'function') throw new TypeError('now and onChange must be functions');
    if (!Number.isInteger(refreshIntervalMs) || refreshIntervalMs < 1) throw new RangeError('refreshIntervalMs must be a positive integer');
    if (!Number.isInteger(staleAfterMs) || staleAfterMs < 1) throw new RangeError('staleAfterMs must be a positive integer');

    this.fetchStatus = fetchStatus;
    this.now = now;
    this.refreshIntervalMs = refreshIntervalMs;
    this.staleAfterMs = staleAfterMs;
    this.onChange = onChange;
    this.setIntervalImpl = setIntervalImpl;
    this.clearIntervalImpl = clearIntervalImpl;
    this.interval = null;
    this.inFlight = null;
    this.online = true;
    this.state = 'idle';
    this.data = null;
    this.lastSuccessAt = null;
    this.statusTimestamp = null;
    this.error = null;
  }

  getSnapshot() {
    const now = this.now();
    const ageMs = this.lastSuccessAt === null ? null : Math.max(0, now - this.statusTimestamp);
    let state = this.state;
    if (this.data && this.online && state === 'online' && ageMs !== null && ageMs > this.staleAfterMs) {
      state = 'stale';
    }
    return {
      state,
      data: this.data,
      lastSuccessAt: this.lastSuccessAt,
      statusTimestamp: this.statusTimestamp,
      ageMs,
      staleAfterMs: this.staleAfterMs,
      online: this.online,
      error: this.error
    };
  }

  publish() {
    const snapshot = this.getSnapshot();
    this.onChange(snapshot);
    return snapshot;
  }

  async refresh({ online = this.online } = {}) {
    this.online = online !== false;
    if (!this.online) {
      this.state = this.data ? 'stale' : 'offline';
      this.error = 'This device is offline. No status request was sent.';
      return this.publish();
    }
    if (this.inFlight) return this.inFlight;

    this.state = this.data ? 'refreshing' : 'checking';
    this.error = null;
    this.publish();

    this.inFlight = (async () => {
      try {
        const payload = await this.fetchStatus();
        if (!payload || payload.ok !== true || payload.control_plane !== 'online' ||
            payload.training_enabled !== false || payload.remote_execution_enabled !== false ||
            payload.provider_directory !== 'informational_only') {
          throw new Error('Runtime returned a status payload outside the read-only contract.');
        }
        const receivedAt = this.now();
        const serverTimestamp = validTimestamp(payload.checked_at);
        this.data = payload;
        this.lastSuccessAt = receivedAt;
        this.statusTimestamp = serverTimestamp !== null && serverTimestamp <= receivedAt + 30_000
          ? serverTimestamp
          : receivedAt;
        this.error = null;
        this.state = 'online';
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Runtime status request failed.';
        this.state = this.data ? 'stale' : 'unavailable';
      } finally {
        this.inFlight = null;
      }
      return this.publish();
    })();
    return this.inFlight;
  }

  setOnline(online) {
    this.online = online !== false;
    if (!this.online) {
      this.state = this.data ? 'stale' : 'offline';
      this.error = 'This device is offline. The last successful status, if any, is shown as stale.';
      return this.publish();
    }
    this.error = null;
    return this.refresh({ online: true });
  }

  start() {
    if (this.interval === null && typeof this.setIntervalImpl === 'function') {
      this.interval = this.setIntervalImpl(() => {
        if (this.online) void this.refresh();
      }, this.refreshIntervalMs);
    }
    return this.refresh({ online: this.online });
  }

  stop() {
    if (this.interval !== null && typeof this.clearIntervalImpl === 'function') {
      this.clearIntervalImpl(this.interval);
      this.interval = null;
    }
  }
}

export function formatStatusAge(ageMs) {
  if (!Number.isFinite(ageMs) || ageMs < 0) return 'unknown age';
  if (ageMs < 1_000) return 'just now';
  if (ageMs < 60_000) return Math.floor(ageMs / 1_000) + 's ago';
  const minutes = Math.floor(ageMs / 60_000);
  if (minutes < 60) return minutes + 'm ago';
  return Math.floor(minutes / 60) + 'h ' + (minutes % 60) + 'm ago';
}
