import test from 'node:test';
import assert from 'node:assert/strict';
import { DB_NAME, DB_VERSION, STORE_NAMES, saveExperience, listExperiences, listRecords, getMemorySummary, exportMemory, importMemory, clearMemory } from '../memory-store.js';

class FakeRequest {
  result;
  error;
  onsuccess;
  onerror;
}
class FakeStore {
  constructor() { this.records = new Map(); this.failNextPut = false; }
  put(record) {
    if (this.failNextPut) { this.failNextPut = false; throw new Error('QuotaExceededError: simulated storage write failure'); }
    this.records.set(record.id, structuredClone(record));
    return this.request(record.id);
  }
  getAll() { return this.request([...this.records.values()].map(value => structuredClone(value))); }
  count() { return this.request(this.records.size); }
  clear() { this.records.clear(); return this.request(undefined); }
  request(result) {
    const req = new FakeRequest();
    const tx = this.transaction;
    tx.pending++;
    queueMicrotask(() => {
      req.result = result;
      req.onsuccess?.();
      tx.pending--;
      tx.completeWhenIdle();
    });
    return req;
  }
}
class FakeTransaction {
  constructor(db, names) {
    this.db = db; this.names = names; this.pending = 0; this.completed = false;
    this.oncomplete = null; this.onerror = null; this.onabort = null;
  }
  objectStore(name) {
    if (!this.names.includes(name)) throw new Error('NotFoundError');
    const store = this.db.stores.get(name);
    store.transaction = this;
    return store;
  }
  completeWhenIdle() {
    queueMicrotask(() => {
      if (!this.completed && this.pending === 0) {
        this.completed = true;
        this.oncomplete?.();
      }
    });
  }
}
class FakeDatabase {
  constructor() {
    this.version = 1; this.stores = new Map(); this.closed = false;
    this.objectStoreNames = { contains: name => this.stores.has(name) };
  }
  createObjectStore(name) { const store = new FakeStore(); this.stores.set(name, store); return store; }
  transaction(names) { return new FakeTransaction(this, Array.isArray(names) ? names : [names]); }
  close() { this.closed = true; }
}
class FakeIndexedDB {
  constructor() { this.databases = new Map(); }
  open(name, version) {
    const request = new FakeRequest();
    queueMicrotask(() => {
      let db = this.databases.get(name);
      if (!db) { db = new FakeDatabase(); this.databases.set(name, db); }
      request.result = db;
      if (version > db.version) {
        db.version = version;
        request.onupgradeneeded?.();
      } else if (db.stores.size === 0) {
        request.onupgradeneeded?.();
      }
      request.onsuccess?.();
    });
    return request;
  }
  store(name, storeName) { return this.databases.get(name)?.stores.get(storeName); }
}
async function withFake(run) {
  const previous = globalThis.indexedDB;
  const fake = new FakeIndexedDB();
  globalThis.indexedDB = fake;
  try { await run(fake); } finally { globalThis.indexedDB = previous; }
}

test('local memory schema preserves the planned ULTRON stores', () => {
  assert.equal(DB_NAME, 'ULTRON_MEMORY');
  assert.equal(DB_VERSION, 1);
  assert.deepEqual(STORE_NAMES, ['experiences', 'knowledge', 'mistakes', 'checkpoints']);
});

test('experience validation rejects empty or oversized prompts before touching browser storage', async () => {
  await assert.rejects(saveExperience({ prompt: '', answer: '42' }), /prompt/i);
  await assert.rejects(saveExperience({ prompt: 'x'.repeat(501), answer: '42' }), /prompt/i);
});

test('save, list and reload persist records in IndexedDB', async () => {
  await withFake(async () => {
    const saved = await saveExperience({ id: 'exp-1', prompt: '2 + 2', answer: '4', correct: true });
    assert.equal(saved.id, 'exp-1');
    assert.equal((await listExperiences(20))[0].answer, '4');
    // A new database connection (as after a reload) sees the persisted record.
    assert.equal((await listExperiences(20)).length, 1);
    assert.equal((await getMemorySummary()).experiences, 1);
  });
});

test('write failures reject and a subsequent retry can succeed', async () => {
  await withFake(async fake => {
    fake.databases.set(DB_NAME, new FakeDatabase());
    const db = fake.databases.get(DB_NAME);
    for (const name of STORE_NAMES) db.createObjectStore(name);
    fake.store(DB_NAME, 'experiences').failNextPut = true;
    await assert.rejects(saveExperience({ id: 'retry-1', prompt: '3 + 4', answer: '7' }), /simulated storage write failure/);
    assert.equal((await saveExperience({ id: 'retry-1', prompt: '3 + 4', answer: '7' })).id, 'retry-1');
  });
});

test('export and import round-trip experiences and merge records locally', async () => {
  await withFake(async () => {
    await saveExperience({ id: 'roundtrip-1', prompt: '5 × 5', answer: '25', correct: true });
    const backup = await exportMemory();
    await clearMemory();
    assert.equal((await listExperiences()).length, 0);
    const result = await importMemory(backup);
    assert.equal(result.imported, 1);
    assert.equal((await listExperiences())[0].answer, '25');
  });
});

test('duplicate IDs within a backup are deduplicated with the last entry winning', async () => {
  await withFake(async () => {
    const result = await importMemory({
      format: 'ultron-local-memory', version: 1,
      stores: { experiences: [
        { id: 'duplicate', prompt: '1 + 1', answer: '2' },
        { id: 'duplicate', prompt: '1 + 1', answer: 'two' }
      ] }
    });
    assert.equal(result.imported, 1);
    const rows = await listExperiences();
    assert.equal(rows.length, 1);
    assert.equal(rows[0].answer, 'two');
  });
});

test('import merges by id and leaves unrelated existing records intact', async () => {
  await withFake(async () => {
    await saveExperience({ id: 'keep', prompt: '6 + 1', answer: '7' });
    await saveExperience({ id: 'replace', prompt: '2 + 2', answer: '4' });
    const result = await importMemory({
      format: 'ultron-local-memory', version: 1,
      stores: { experiences: [{ id: 'replace', prompt: '2 + 2', answer: 'four' }] }
    });
    assert.equal(result.imported, 1);
    const rows = await listExperiences();
    assert.equal(rows.length, 2);
    assert.equal(rows.find(row => row.id === 'replace').answer, 'four');
    assert.equal(rows.find(row => row.id === 'keep').answer, '7');
  });
});

test('invalid, unknown-store and malformed backups are rejected before writing', async () => {
  await withFake(async () => {
    await assert.rejects(importMemory({ format: 'other', version: 1, stores: {} }), /supported ULTRON memory backup/i);
    await assert.rejects(importMemory({ format: 'ultron-local-memory', version: 1, stores: { experiences: {} } }), /must be an array/i);
    await assert.rejects(importMemory({ format: 'ultron-local-memory', version: 1, stores: { unknown: [] } }), /unknown memory store/i);
    await assert.rejects(importMemory({ format: 'ultron-local-memory', version: 1, stores: { knowledge: [{ statement: 'bad id' }] } }), /record id/i);
    assert.equal((await listExperiences()).length, 0);
  });
});

test('import rejects oversized JSON and record-count payloads safely', async () => {
  await withFake(async () => {
    await assert.rejects(importMemory({
      format: 'ultron-local-memory', version: 1,
      stores: { knowledge: [{ id: 'large', data: 'x'.repeat(20 * 1024 * 1024) }] }
    }), /20 MB safety limit/i);
    await assert.rejects(importMemory({
      format: 'ultron-local-memory', version: 1,
      stores: { knowledge: Array.from({ length: 50001 }, (_, i) => ({ id: String(i) })) }
    }), /50,000-record/i);
  });
});

test('unavailable IndexedDB fails clearly rather than claiming to save', async () => {
  const original = globalThis.indexedDB;
  try {
    globalThis.indexedDB = undefined;
    await assert.rejects(saveExperience({ prompt: '2 + 2', answer: '4' }), /IndexedDB is unavailable/i);
  } finally {
    globalThis.indexedDB = original;
  }
});
