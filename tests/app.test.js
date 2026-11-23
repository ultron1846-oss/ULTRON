import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('static shell exposes every requested primary section and entry points', async () => {
  const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');
  const app = await readFile(new URL('../app.js', import.meta.url), 'utf8');
  for (const page of ['dashboard','mathematics','learning','engine','knowledge','training']) assert.match(html, new RegExp(`data-page="${page}"`));
  for (const page of ['settings','system']) assert.match(app, new RegExp(`${page}:`));
  assert.match(html, /viewport/);
  assert.match(app, /localStorage/);
  assert.doesNotMatch(app, /\beval\s*\(|new Function/);
});
