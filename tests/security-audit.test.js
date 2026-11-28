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

test('static security audit covers every local module imported by the browser app', async () => {
  const [audit, app] = await Promise.all([
    readFile(new URL('../security-audit.mjs', import.meta.url), 'utf8'),
    readFile(new URL('../app.js', import.meta.url), 'utf8')
  ]);
  const pathsBlock = audit.match(/const paths = \\[([\\s\\S]*?)\\];/)?.[1];
  assert.ok(pathsBlock, 'security audit must declare its source path list');
  const scanned = new Set([...pathsBlock.matchAll(/'([^']+)'/g)].map(match => match[1]));
  const imported = [...app.matchAll(/from\\s+['"]\\.\\/([^?'"]+)/g)].map(match => match[1]);
  assert.ok(imported.length > 0, 'browser app must declare local module imports');
  for (const path of imported) {
    assert.ok(scanned.has(path), `browser module ${path} is missing from the static security audit`);
  }
});
