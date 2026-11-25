-- ULTRON security safeguard: RLS does not restrict TRUNCATE.
-- Safe to re-run. This only removes a table privilege; it does not delete data.
REVOKE TRUNCATE ON TABLE
  public.experiences,
  public.knowledge,
  public.mistakes,
  public.checkpoints,
  public.backups,
  public.memory_imports
FROM authenticated;

-- Verification (expect false for every row):
SELECT c.relname AS table_name,
       has_table_privilege('authenticated', c.oid, 'TRUNCATE') AS authenticated_can_truncate,
       has_table_privilege('anon', c.oid, 'TRUNCATE') AS anon_can_truncate
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname IN (
    'experiences', 'knowledge', 'mistakes',
    'checkpoints', 'backups', 'memory_imports'
  )
  AND c.relkind = 'r'
ORDER BY c.relname;
