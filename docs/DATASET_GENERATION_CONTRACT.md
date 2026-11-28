# ULTRON dataset generation contract

**Status:** contract for the existing bounded generator and verification path.  
**No corpus is created by this document or this phase.**

## 1. Data products and versions

The current pipeline has three different versioned records. They must not be conflated.

| Data product | Current version | Purpose |
|---|---:|---|
| JSONL MathExample sample | v1 (defined by exact required-field set) | Generator-compatible row used by the current semantic dataset verifier |
| Dataset sidecar manifest | schema v1 | Binds the JSONL bytes, generator version, seed, topic sequence, row count and topic counts |
| Canonical MathTaskRecord envelope | schema v1 | Separates problem, verification receipt and approved target projection |

The JSONL sample currently has no individual schema_version field. Its version is inherited from the dataset manifest and fixed row schema below. Do not add, remove, or reinterpret row fields without defining a new row schema and an explicit verifier migration. The canonical task envelope is a separate, richer contract; it is not currently the JSONL row format.

## 2. JSONL sample schema v1

Each record has exactly these fields:

| Field | Type | Contract |
|---|---|---|
| example_id | lowercase SHA-256 hex string | Hash of canonical generation identity |
| generator_version | string | Must equal the verifier's supported generator release |
| topic | string | Must be in the manifest's declared supported-topic sequence |
| difficulty | positive integer | bool is not an integer for this schema |
| input_text | UTF-8 string | Problem statement |
| target_text | UTF-8 string | Supervised answer text |
| exact_answer | UTF-8 string | Must equal target_text and pass the topic-specific exact validator |
| seed | integer | Must equal the dataset manifest seed |
| index | non-negative integer | Unique within the dataset |
| generation_parameters | object of string keys and integer/string values | Reconstructs the generated ingredients |
| validation_status | literal string | Accepted rows must be semantically_checked |
| provenance | string | Generator/validator provenance description |

JSON object parsing rejects duplicate keys and non-standard constants. Unknown and missing row fields are rejected. Rows must be newline-terminated UTF-8 JSON.

## 3. Canonical serialization and identity

The current writer accepts an iterable and serializes one row at a time as UTF-8 JSON with sorted keys, compact separators, and ensure_ascii=false, followed by exactly one newline byte. It does not retain a full encoded dataset string. The dataset SHA-256 covers the complete concatenated JSONL byte stream, including those newline bytes. Duplicate IDs and row indices are rejected while streaming.

The row identity digest covers this canonical payload:

generator_version, seed, index, topic, input_text, target_text, and generation_parameters.

It is encoded as sorted-key, compact UTF-8 JSON with ensure_ascii=false, then SHA-256 hashed. The verifier independently reconstructs this payload and compares the digest. difficulty, validation_status, and provenance are schema-checked but are not currently part of the row identity digest. The enclosing dataset digest still covers every serialized row field.

The dataset sidecar manifest is schema v1 and contains exactly:

- schema_version
- generator_version
- seed
- topics (ordered list supplied to generation)
- example_count
- topic_counts
- sha256 (complete JSONL digest)

The sidecar itself is canonical sorted-key compact UTF-8 JSON followed by a newline. Dataset content and sidecar are written using separate temporary files, fsync, and os.replace. They are **not a single atomic two-file transaction**: interruption between replacements can leave a mismatched pair, which must fail closed during verification. Never treat the pair as valid unless the verifier accepts both.

## 4. Deterministic seed and provenance rules

generate_examples(seed, count, topics) uses a private random.Random(seed) instance. It selects topics in the exact order supplied to topics and uses that same RNG stream for topic selection and generator ingredients. Therefore output depends on all of:

- generator version and implementation;
- integer seed;
- count;
- ordered topic sequence;
- Python random-library behavior/runtime;
- exact generation-parameter and canonicalization rules.

For a reproducible replay, retain the original seed, exact ordered topic list, count, generator version, and source commit. The sidecar currently records the first four except source commit/runtime fingerprint; those missing environment fields are an explicit metadata limitation, not assumed facts. A generator algorithm or canonical identity change requires a generator-version change and new regression fixtures. Do not claim cross-Python-version byte reproducibility without an explicit compatibility test.

The provenance string is descriptive metadata, not an authenticated signature. SHA-256 detects accidental changes and binds bytes; it does not establish author identity or prove that a validator is trustworthy.

## 5. Mathematical and structural validation

write_dataset rejects empty/non-MathExample inputs, duplicate IDs, seed/topic mismatches, rejected status, and answers that fail the current exact topic validator. verify_dataset independently checks:

- strict manifest schema/version, seed, topics, count, topic counts and digest;
- byte, row and line limits before/until parsing;
- strict UTF-8/JSON, duplicate-key and non-standard-constant rejection;
- exact row field set and field types;
- unique sample IDs and unique row indices;
- row seed, generator version and topic agreement with manifest;
- target_text equals exact_answer;
- per-topic exact-answer recomputation;
- reconstructed content-derived example ID;
- final byte count, row count, file metadata stability and SHA-256.

The current exact validator covers only the topics in the SUPPORTED_TOPICS list in ultron_core/data_generation.py. Do not extrapolate its correctness to unsupported topics or broader mathematical reasoning. The separate university generator families use their own replay/independent validators and are not automatically accepted by this JSONL dataset schema.

## 6. Reproducible split manifest

Split manifest schema v1 uses prompt_group_hash_v1. It binds:

- the complete dataset SHA-256;
- signed-64-bit split seed;
- validation and test fractions;
- sorted, unique sample-ID arrays for train, validation, and test;
- a canonical SHA-256 over the unsigned manifest payload.

The splitter normalizes prompt whitespace and assigns each normalized prompt group from a SHA-256 bucket derived from split seed and prompt. It selects the lexicographically smallest example ID as the group representative. As a result, exact normalized prompt groups cannot span splits, but duplicate rows within a prompt group can be left unselected. The quality audit reports unassigned source rows and duplicate prompts; this is intentional and must not be mistaken for complete source-row utilization.

Split IDs are represented as JSON arrays today. The parser enforces a 32 MiB default ceiling and the repository preflight has a 100,000-row cap. This is bounded, but memory still grows with manifest size; this is not an O(1)-memory manifest protocol.

## 7. Retention, deletion and transfer

- Treat source JSONL and its manifest as one integrity-bound pair; retain them together.
- Treat split manifest as dependent metadata and retain it with the exact dataset digest it names.
- Temporary verified snapshots and SQLite offset indexes are ephemeral caches. They must be closed and removed on success or failure; do not publish them as authoritative data.
- Before deletion, verify that the exact source and sidecars are the intended files and that a separate verified copy exists when retention is required. This phase performs no destructive data deletion.
- After copying/transferring a dataset, sidecar and split manifest, recompute byte hashes and run semantic dataset and split verification in the destination environment before use.
- Account separately for source dataset bytes, split-manifest bytes, temporary snapshot bytes, SQLite index bytes, SQLite temporary files, and report output. Do not equate Python tracemalloc with total process or device memory.
- Failed or interrupted pair writes must be quarantined/rebuilt; never repair a digest by silently accepting unknown bytes.

## 8. Current gaps

The generator accepts the shared DatasetResourceLimits policy: row count, total JSONL bytes, row-line bytes and sidecar manifest bytes are enforced on write; the same limits can be applied during read. It still keeps bounded in-memory sets of IDs and indices (maximum 100,000 by default), so writer metadata is O(N), not constant-memory. The generator returns a tuple and is itself bounded by the configured row cap.

The current v1 sidecar does not record Python implementation/version, source commit, per-generator parameter schema versions, or a signed provenance identity. The JSONL row does not carry a standalone schema version. The manifest's ID arrays remain O(N) memory. These limitations are recorded explicitly and are not silently promoted to production-ready guarantees.

A future format should introduce explicit row schema metadata and generation-runtime fingerprints using a new manifest version, preserve read-only migration for v1, and independently verify that replays reproduce byte-identical output before changing the accepted generator version.
