import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { validateProviderDirectory } from '../provider-directory.js';

const readDirectory = async () => JSON.parse(
  await readFile(new URL('../servers.json', import.meta.url), 'utf8')
);

test('current provider directory validates as informational and disabled', async () => {
  const validated = validateProviderDirectory(await readDirectory());
  assert.equal(validated.schema_version, 1);
  assert.equal(validated.providers.length, 1);
  assert.equal(validated.providers[0].id, 'google-colab');
  assert.equal(validated.providers[0].execution_enabled, false);
});

test('provider directory rejects execution-enabled entries', async () => {
  const source = await readDirectory();
  source.providers[0].execution_enabled = true;
  assert.throws(() => validateProviderDirectory(source), /execution must remain disabled/i);
});

test('provider directory rejects non-HTTPS links and embedded credentials', async () => {
  const source = await readDirectory();
  source.providers[0].url = 'http://example.com';
  assert.throws(() => validateProviderDirectory(source), /HTTPS/i);
  source.providers[0].url = 'https://user:password@example.com';
  assert.throws(() => validateProviderDirectory(source), /credentials/i);
});

test('provider directory rejects unknown schema, duplicate IDs and malformed fields', async () => {
  const source = await readDirectory();
  assert.throws(() => validateProviderDirectory({ ...source, schema_version: 2 }), /schema version/i);
  assert.throws(() => validateProviderDirectory({ ...source, unexpected: true }), /schema/i);
  assert.throws(() => validateProviderDirectory({
    ...source,
    providers: [source.providers[0], source.providers[0]]
  }), /duplicate provider IDs/i);
  assert.throws(() => validateProviderDirectory({
    ...source,
    providers: [{ ...source.providers[0], name: '' }]
  }), /name/i);
});
