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
  const pathsStart = audit.indexOf('const paths = [');
  const pathsEnd = audit.indexOf('];', pathsStart);
  assert.notEqual(pathsStart, -1, 'security audit must declare its source path list');
  assert.notEqual(pathsEnd, -1, 'security audit path list must be closed');
  const pathsBlock = audit.slice(pathsStart, pathsEnd);
  const scanned = new Set(
    pathsBlock.split('\\n')
      .map(line => line.trim())
      .filter(line => line.startsWith("'"))
      .map(line => line.slice(1, line.indexOf("'", 1)))
  );
  const imported = app.split('\\n').flatMap(line => {
    const marker = "from './";
    const index = line.indexOf(marker);
    if (index < 0) return [];
    return [line.slice(index + marker.length).split('?')[0].split("'")[0].split('"')[0]];
  });
  assert.ok(imported.length > 0, 'browser app must declare local module imports');
  for (const modulePath of imported) {
    assert.ok(scanned.has(modulePath), `browser module ${modulePath} is missing from the static security audit`);
  }
});
