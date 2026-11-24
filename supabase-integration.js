// Audited Supabase contract for the public ULTRON Pages frontend.
// This is a documentation snapshot, not a live health check. Never put server secrets here.
export const supabaseBackendAudit = Object.freeze({
  projectRef: 'euhmejpaswmdpsutbtse',
  projectStatusAtInspection: 'ACTIVE_HEALTHY',
  inspectedOn: '2026-11-24',
  services: [
    {
      name: 'device-control',
      state: 'retired',
      label: 'RETIRED · HTTP 410',
      detail: 'The deployed function explicitly retires device pairing and rejects old clients.'
    },
    {
      name: 'training-control',
      state: 'owner-gated',
      label: 'OWNER SESSION REQUIRED',
      detail: 'Requires a valid authenticated owner JWT. The public website has no login and must not call this function.'
    }
  ],
  blockers: [
    'The training-control function currently allows the previous GitHub Pages origin, not the current ULTRON Pages origin.',
    'The training-control function currently targets shayaanfarsheed-cmd/ULTRONAI instead of ultron1846-oss/ULTRON.',
    'The memory and training tables are owner-linked and protected by row-level security; public anonymous reads are not appropriate.',
    'No public, read-only health endpoint currently exists for this website.'
  ]
});
