// Pure normalization for the browser-local future workload preference.
// This value is a preference only; it does not allocate or measure memory.
export function normalizeMemoryPreference(raw, fallback = 6) {
  const parsed = raw === null || raw === undefined || raw === '' ? Number.NaN : Number(raw);
  const safeFallback = Number.isFinite(Number(fallback))
    ? Math.min(10, Math.max(2, Math.round(Number(fallback))))
    : 6;
  if (!Number.isFinite(parsed)) return safeFallback;
  return Math.min(10, Math.max(2, Math.round(parsed)));
}
