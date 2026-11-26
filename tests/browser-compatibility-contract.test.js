import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const read = path => readFile(new URL('../' + path, import.meta.url), 'utf8');

test('browser shell declares mobile viewport and keeps a visible startup fallback', async () => {
  const html = await read('index.html');
  assert.match(html, /name="viewport"[^>]*viewport-fit=cover/);
  assert.match(html, /STARTUP \/ FALLBACK VIEW/);
  assert.match(html, /window\.addEventListener\('error'/);
  assert.match(html, /window\.addEventListener\('unhandledrejection'/);
  assert.match(html, /id="page-content"[^>]*tabindex="-1"/);
});

test('responsive styles cover narrow portrait and landscape viewports', async () => {
  const css = await read('styles.css');
  assert.match(css, /@media\(max-width:760px\)/);
  assert.match(css, /@media\(max-width:760px\) and \(orientation:landscape\)/);
  assert.match(css, /min-width:0/);
  assert.match(css, /max-width:100%/);
  assert.match(css, /env\(safe-area-inset-bottom\)/);
});

test('touch controls meet the 44px minimum and keyboard focus is visible', async () => {
  const css = await read('styles.css');
  const html = await read('index.html');
  assert.match(css, /min-height:44px/);
  assert.match(css, /:focus-visible/);
  assert.match(html, /aria-controls="sidebar"/);
  assert.match(html, /aria-expanded="false"/);
});

test('navigation supports keyboard dismissal, active state and narrow-screen close', async () => {
  const app = await read('app.js');
  assert.match(app, /event\.key==='Escape'/);
  assert.match(app, /document\.addEventListener\('pointerdown'/);
  assert.match(app, /aria-current/);
  assert.match(app, /mobileMenu\.setAttribute\('aria-expanded'/);
  assert.match(app, /history\.replaceState/);
});

test('memory uses IndexedDB and has export/import recovery contracts', async () => {
  const app = await read('app.js');
  const memory = await read('memory-store.js');
  assert.match(memory, /indexedDB\.open/);
  assert.match(memory, /tx\.oncomplete/);
  assert.match(memory, /db\.onversionchange/);
  assert.match(memory, /MAX_IMPORT_BYTES/);
  assert.match(memory, /unknown memory store/);
  assert.match(app, /Retry save/);
  assert.match(app, /memory-export/);
  assert.match(app, /memory-import-file/);
  assert.match(app, /Import failed:/);
});

test('automated checks explicitly preserve manual iPad Safari acceptance as pending', async () => {
  const acceptance = await read('docs/IPAD_FRONTEND_ACCEPTANCE.md');
  assert.match(acceptance, /Manual Safari acceptance:\s*pending/i);
  assert.match(acceptance, /actual iPad/);
  assert.match(acceptance, /portrait and landscape/);
});
