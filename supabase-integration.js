// Public browser integration for ULTRON's narrowly scoped Supabase status endpoint.
// The publishable key is designed for browser use. Never add service-role or secret keys here.
const PROJECT_URL = 'https://euhmejpaswmdpsutbtse.supabase.co';
const PUBLISHABLE_KEY = 'sb_publishable_5QK9sdn3C4EIeB0Jy_8TDQ_UKAaZ-9l';

export const supabaseBackendAudit = Object.freeze({
  projectRef: 'euhmejpaswmdpsutbtse',
  currentWebsiteRepository: 'ultron1846-oss/ULTRON',
  projectStatusAtInspection: 'ACTIVE_HEALTHY',
  trainingControlVersion: 8,
  inspectedOn: '2026-11-24',
  services: [
    {
      name: 'device-control',
      state: 'retired',
      label: 'RETIRED · HTTP 410',
      detail: 'Device pairing is retired. The deployed function rejects stale pairing clients.'
    },
    {
      name: 'training-control',
      state: 'public-status-owner-controls',
      label: 'PUBLIC STATUS · OWNER CONTROLS',
      detail: 'The public_status action returns safe service-state flags only. health, status, start and stop remain owner-session gated.'
    }
  ],
  blockers: [
    'Memory and training records remain owner-linked and protected by row-level security; this public website cannot read them without an authenticated owner session.',
    'Provider discovery remains informational. No provider jobs, device pairing or remote training controls are exposed.',
    'Actual model training remains disabled. The public status response reports this explicitly.'
  ]
});

export async function fetchSupabasePublicStatus() {
  const response = await fetch(`${PROJECT_URL}/functions/v1/training-control`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      apikey: PUBLISHABLE_KEY
    },
    body: JSON.stringify({ action: 'public_status' }),
    cache: 'no-store'
  });

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error('Supabase returned an invalid status response.');
  }

  if (!response.ok || payload?.ok !== true) {
    throw new Error(payload?.error || `Supabase status request failed (HTTP ${response.status}).`);
  }
  return payload;
}
