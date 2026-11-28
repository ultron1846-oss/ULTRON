import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFile } from 'node:fs/promises';

test('focused static frontend security audit passes against selected current source', () => {
  const output = execFileSync(process.execPath, ['security-audit.mjs'], { encoding: 'utf8' });
  assert.match(output, /focused static security audit passed/i);
  assert.match(output, /not a security certification/i);
});

test('security and dependency workflow is read-only and audits declared dependency sets', async () => {
  const workflow = await readFile(new URL('../.github/workflows/security-audit.yml', import.meta.url), 'utf8');
  assert.match(workflow, /permissions:\s+contents: read/);
  assert.match(workflow, /npm audit --audit-level=high/);
  assert.match(workflow, /pip-audit -r requirements-ai\.txt/);
  assert.match(workflow, /pip-audit -r requirements-test\.txt/);
  assert.match(workflow, /pip-audit -r requirements-seed\.txt/);
});

test('static security audit includes the runtime status browser module', async () => {
  const audit = await readFile(new URL('../security-audit.mjs', import.meta.url), 'utf8');
  assert.ok(audit.includes("'runtime-status.js'"));
});
