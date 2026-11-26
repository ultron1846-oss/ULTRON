import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('redundant custom Pages deployment workflow is removed and root assets remain', async () => {
  await assert.rejects(readFile(new URL('../.github/workflows/pages.yml', import.meta.url), 'utf8'), { code: 'ENOENT' });
  for (const path of ['index.html', 'styles.css', 'app.js', 'math-engine.js', 'supabase-integration.js', 'memory-store.js', 'servers.json']) {
    const content = await readFile(new URL('../' + path, import.meta.url), 'utf8');
    assert.ok(content.trim().length > 0, `missing or empty Pages asset: ${path}`);
  }
});
test('test workflow runs the built-in suite on PRs and main pushes', async () => {
  const workflow = await readFile(new URL('../.github/workflows/test.yml', import.meta.url), 'utf8');
  assert.match(workflow, /pull_request:/);
  assert.match(workflow, /branches: \[main\]/);
  assert.match(workflow, /run: npm test/);
});
