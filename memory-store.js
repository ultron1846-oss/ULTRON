const DB_NAME = 'ULTRON_MEMORY';
const DB_VERSION = 1;
const STORE_NAMES = ['experiences', 'knowledge', 'mistakes', 'checkpoints'];

function openDatabase() {
  if (!globalThis.indexedDB) {
    return Promise.reject(new Error('IndexedDB is unavailable in this browser context.'));
  }
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      for (const name of STORE_NAMES) {
        if (!db.objectStoreNames.contains(name)) {
          const store = db.createObjectStore(name, { keyPath: 'id' });
          if (name !== 'checkpoints') store.createIndex('createdAt', 'createdAt');
        }
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error('Could not open local memory.'));
    request.onblocked = () => reject(new Error('Another ULTRON tab is blocking the memory database upgrade.'));
  });
}

function transactionRequest(storeName, mode, action) {
  return openDatabase().then(db => new Promise((resolve, reject) => {
    let result;
    let settled = false;
    const fail = error => {
      if (settled) return;
      settled = true;
      db.close();
      reject(error instanceof Error ? error : new Error('Local memory transaction failed.'));
    };
    try {
      const tx = db.transaction(storeName, mode);
      const request = action(tx.objectStore(storeName));
      request.onsuccess = () => { result = request.result; };
      request.onerror = () => fail(request.error || new Error('Local memory request failed.'));
      tx.oncomplete = () => {
        if (settled) return;
        settled = true;
        db.close();
        resolve(result);
      };
      tx.onerror = () => fail(tx.error || new Error('Local memory transaction failed.'));
      tx.onabort = () => fail(tx.error || new Error('Local memory transaction was aborted.'));
    } catch (error) {
      fail(error);
    }
  }));
}

function makeId() {
  return globalThis.crypto?.randomUUID?.() || `ultron-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function normalizeExperience(entry) {
  if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
    throw new TypeError('An experience record must be an object.');
  }
  const prompt = String(entry.prompt ?? '').trim();
  const answer = String(entry.answer ?? '').trim();
  if (!prompt || prompt.length > 500) throw new TypeError('Experience prompt must contain 1–500 characters.');
  if (answer.length > 2000) throw new TypeError('Experience answer must be 2,000 characters or fewer.');
  return {
    id: typeof entry.id === 'string' && entry.id.length <= 120 ? entry.id : makeId(),
    prompt,
    answer,
    correct: entry.correct === true,
    topic: String(entry.topic ?? 'Uncategorized').slice(0, 80),
    explanation: String(entry.explanation ?? '').slice(0, 2000),
    createdAt: typeof entry.createdAt === 'string' ? entry.createdAt : new Date().toISOString()
  };
}

export async function saveExperience(entry) {
  const record = normalizeExperience(entry);
  await transactionRequest('experiences', 'readwrite', store => store.put(record));
  return record;
}

export async function saveMistake(entry) {
  const record = normalizeExperience(entry);
  await transactionRequest('mistakes', 'readwrite', store => store.put(record));
  return record;
}

export async function getMemorySummary() {
  const counts = await Promise.all(STORE_NAMES.map(name =>
    transactionRequest(name, 'readonly', store => store.count())
  ));
  return Object.fromEntries(STORE_NAMES.map((name, index) => [name, counts[index]]));
}

export async function listRecords(storeName, limit = 100) {
  if (!STORE_NAMES.includes(storeName)) throw new TypeError('Unknown ULTRON memory store.');
  const records = await transactionRequest(storeName, 'readonly', store => store.getAll());
  return records
    .sort((a, b) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')))
    .slice(0, Math.max(1, Math.min(500, Number(limit) || 100)));
}

export async function listExperiences(limit = 100) {
  return listRecords('experiences', limit);
}

export async function clearMemory() {
  const db = await openDatabase();
  try {
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAMES, 'readwrite');
      for (const name of STORE_NAMES) tx.objectStore(name).clear();
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error || new Error('Could not clear local memory.'));
      tx.onabort = () => reject(tx.error || new Error('Local memory clear was aborted.'));
    });
  } finally {
    db.close();
  }
}

export async function exportMemory() {
  const stores = {};
  for (const name of STORE_NAMES) {
    stores[name] = await transactionRequest(name, 'readonly', store => store.getAll());
  }
  return {
    format: 'ultron-local-memory',
    version: DB_VERSION,
    exportedAt: new Date().toISOString(),
    stores
  };
}

export async function importMemory(payload) {
  if (!payload || payload.format !== 'ultron-local-memory' || payload.version !== DB_VERSION || !payload.stores || typeof payload.stores !== 'object') {
    throw new TypeError('This is not a supported ULTRON memory backup.');
  }
  const records = {};
  let total = 0;
  for (const name of STORE_NAMES) {
    const rows = payload.stores[name] ?? [];
    if (!Array.isArray(rows)) throw new TypeError(`Backup section "${name}" must be an array.`);
    total += rows.length;
    if (total > 50000) throw new TypeError('Backup exceeds the 50,000-record import safety limit.');
    records[name] = rows.map(row => name === 'experiences' || name === 'mistakes'
      ? normalizeExperience(row)
      : normalizeStoredRecord(row));
  }
  const db = await openDatabase();
  try {
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAMES, 'readwrite');
      for (const name of STORE_NAMES) {
        const store = tx.objectStore(name);
        for (const record of records[name]) store.put(record);
      }
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error || new Error('Memory import failed.'));
      tx.onabort = () => reject(tx.error || new Error('Memory import was aborted.'));
    });
  } finally {
    db.close();
  }
  return { imported: total };
}

function normalizeStoredRecord(record) {
  if (!record || typeof record !== 'object' || Array.isArray(record)) throw new TypeError('Backup contains an invalid memory record.');
  const id = typeof record.id === 'string' && record.id.length <= 120 ? record.id : makeId();
  return { ...record, id };
}

export { DB_NAME, DB_VERSION, STORE_NAMES };
