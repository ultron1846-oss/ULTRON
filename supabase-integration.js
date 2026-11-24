// Public browser integration for ULTRON's narrowly scoped Supabase status endpoint.
// The publishable key is designed for browser use. Never add service-role or secret keys here.
const PROJECT_URL = 'https://euhmejpaswmdpsutbtse.supabase.co';
const PUBLISHABLE_KEY = 'sb_publishable_5QK9sdn3C4EIeB0Jy_8TDQ_UKAaZ-9l';
const REQUEST_TIMEOUT_MS = 10000;

export const supabaseBackendAudit = Object.freeze({
  projectRef: 'euhmejpaswmdpsutbtse',
  projectName: 'ultron-memory',
  region: 'ap-south-1',
  currentWebsiteRepository: 'ultron1846-oss/ULTRON',
  projectStatusAtInspection: 'ACTIVE_HEALTHY',
  inspectedOn: '2026-11-24',
  services: [
    {
      name: 'device-control',
      state: 'retired',
      label: 'RETIRED · HTTP 410',
      detail: 'The function remains deployed but its current handler rejects every request with HTTP 410. It cannot pair devices, issue credentials or accept heartbeats.'
    },
    {
      name: 'training-control',
      state: 'protected',
      label: 'PUBLIC STATUS · OWNER ACTIONS',
      detail: 'The public_status action returns generic service-state flags only. Health, status, start and stop actions require a verified owner session inside the function.'
    }
  ],
  blockers: [
    'The public website has no login and therefore cannot access owner-linked memory, checkpoint or training records. Those tables remain protected by row-level security.',
    'The public status endpoint is read-only. It does not return owner IDs, records, run metadata, provider credentials or secrets.',
    'Provider discovery is informational only. The website does not submit provider jobs or launch remote workloads; actual model training remains disabled.',
    'The Supabase security advisor reports three retired device/pairing tables with RLS enabled but no policies, plus disabled leaked-password protection. These are separate backend-hardening items and were not changed by this frontend integration.'
  ]
});

export async function fetchSupabasePublicStatus({
  fetchImpl = fetch,
  timeoutMs = REQUEST_TIMEOUT_MS
} = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetchImpl(`${PROJECT_URL}/functions/v1/training-control`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        apikey: PUBLISHABLE_KEY
      },
      body: JSON.stringify({ action: 'public_status' }),
      cache: 'no-store',
      signal: controller.signal
    });

    if (!response.ok) {
      throw new Error(`Supabase status request failed (HTTP ${response.status}).`);
    }

    let payload;
    try {
      payload = await response.json();
    } catch {
      throw new Error('Supabase returned an invalid JSON status response.');
    }

    if (
      payload?.ok !== true ||
      payload?.control_plane !== 'online' ||
      payload?.training_enabled !== false ||
      payload?.remote_execution_enabled !== false ||
      payload?.provider_directory !== 'informational_only'
    ) {
      throw new Error('Supabase returned a status payload that does not match ULTRON’s safe read-only contract.');
    }

    return payload;
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error('Supabase status request timed out. The website did not access private backend data.');
    }
    throw error instanceof Error ? error : new Error('Supabase status request failed.');
  } finally {
    clearTimeout(timeout);
  }
}
