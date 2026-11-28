import test from 'node:test';
import assert from 'node:assert/strict';
import { DB_NAME, DB_VERSION, STORE_NAMES, saveExperience, importMemory } from '../memory-store.js';

test('local memory schema preserves the planned ULTRON stores', () => {
  assert.equal(DB_NAME, 'ULTRON_MEMORY');
  assert.equal(DB_VERSION, 2);
  assert.deepEqual(STORE_NAMES, ['experiences', 'knowledge', 'mistakes', 'checkpoints']);
});

test('experience validation rejects empty or oversized prompts before touching browser storage', async () => {
  await assert.rejects(saveExperience({ prompt: '', answer: '42' }), /prompt/i);
  await assert.rejects(saveExperience({ prompt: 'x'.repeat(501), answer: '42' }), /prompt/i);
});

test('memory import rejects an unknown or malformed backup format', async () => {
  await assert.rejects(importMemory({ format: 'other', version: 1, stores: {} }), /supported ULTRON memory backup/i);
  await assert.rejects(importMemory({ format: 'ultron-local-memory', version: 1, stores: { experiences: {} } }), /must be an array/i);
});

test('experience write reports unavailable IndexedDB instead of pretending to save', async () => {
  const original = globalThis.indexedDB;
  try {
    globalThis.indexedDB = undefined;
    await assert.rejects(saveExperience({ prompt: '2 + 2', answer: '4', correct: true }), /IndexedDB is unavailable/i);
  } finally {
    globalThis.indexedDB = original;
  }
});
