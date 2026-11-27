import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createRuntimeConfig,
  serializeRuntimeConfig,
  validateRuntimeConfig
} from '../runtime-config.js';

const valid = () => createRuntimeConfig(6);

test('builder exports selected memory with conservative non-authorizing defaults', () => {
  assert.deepEqual(createRuntimeConfig(8), {
    schema_version: 1,
    memory_budget_gib: 8,
    batch_size: 1,
    sequence_length: 256,
    gradient_accumulation_steps: 1,
    training_authorized: false,
    remote_execution_enabled: false
  });
});

test('builder accepts the slider endpoints', () => {
  assert.equal(createRuntimeConfig(2).memory_budget_gib, 2);
  assert.equal(createRuntimeConfig(10).memory_budget_gib, 10);
});

test('builder rejects invalid memory preference values', () => {
  for (const value of [true, false, 1, 11, 0, -1, 6.5, '6', NaN, Infinity]) {
    assert.throws(() => createRuntimeConfig(value));
  }
});

test('validator returns a canonical schema object', () => {
  const config = valid();
  assert.deepEqual(validateRuntimeConfig(config), config);
});

test('validator rejects null, arrays, and primitive roots', () => {
  for (const value of [null, [], 6, 'config']) {
    assert.throws(() => validateRuntimeConfig(value), /object/);
  }
});

test('validator rejects missing and additional keys', () => {
  const missing = valid();
  delete missing.batch_size;
  assert.throws(() => validateRuntimeConfig(missing), /keys do not match/);
  assert.throws(() => validateRuntimeConfig({...valid(), extra: 1}), /keys do not match/);
});

test('validator rejects unsupported schema version', () => {
  assert.throws(() => validateRuntimeConfig({...valid(), schema_version: 2}), /schema_version/);
});

test('validator rejects non-integer and out-of-range workload fields', () => {
  const cases = [
    ['batch_size', true], ['batch_size', 0], ['batch_size', 17],
    ['sequence_length', 1], ['sequence_length', 2049],
    ['gradient_accumulation_steps', 0], ['gradient_accumulation_steps', 129]
  ];
  for (const [field, value] of cases) {
    assert.throws(() => validateRuntimeConfig({...valid(), [field]: value}));
  }
});

test('validator refuses authorization or remote execution flags', () => {
  assert.throws(() => validateRuntimeConfig({...valid(), training_authorized: true}), /cannot authorize/);
  assert.throws(() => validateRuntimeConfig({...valid(), remote_execution_enabled: true}), /cannot enable/);
});

test('serialization is parseable and retains non-authorizing fields', () => {
  const source = serializeRuntimeConfig(createRuntimeConfig(9));
  assert.equal(source.endsWith('\n'), true);
  assert.deepEqual(JSON.parse(source), createRuntimeConfig(9));
});
