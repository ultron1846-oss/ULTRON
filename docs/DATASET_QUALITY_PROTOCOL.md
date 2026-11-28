# ULTRON dataset quality and split-safety protocol

**Status:** deterministic read-only audit protocol and report schema v1.  
**No production corpus is generated, downloaded, or declared ready in this phase.**

## 1. Inputs and trust boundary

The audit accepts only an existing JSONL dataset with its sidecar manifest and a dataset-bound split manifest. Both are revalidated before any quality result is produced. Run it with python -m ultron_core.dataset_quality --dataset existing.jsonl --split-manifest existing.splits.json --output quality-report.json. Byte, row, line, sidecar-manifest, split-manifest, SQLite page-cache, index and temporary-disk limits are configurable through the CLI. The quality report is metadata, not an authorization token, mathematical proof, owner acceptance, or evidence of trained-model ability.

The quality auditor's SQLite database is disposable scratch state. It disables both main and temporary-schema journaling before creating or inserting audit tables, then applies separate page-count caps to both schemas. This prevents rollback-journal files from creating an unaccounted disk peak outside `max_temporary_bytes`; on any failure the scratch database is closed and removed, while input files remain unchanged.

The report is deterministic for identical verified input bytes and uses canonical UTF-8 JSON with sorted keys and compact separators. report_sha256 is computed over the report before that field is added. The tool writes no data rows and does not mutate the inputs.

## 2. Duplicate classes

| Check | Method | Interpretation |
|---|---|---|
| Duplicate sample ID | Exact ID uniqueness enforced by semantic verifier | Hard integrity failure |
| Duplicate row index | Exact index uniqueness enforced by semantic verifier | Hard integrity failure |
| Exact/normalized prompt duplicate | Whitespace collapse + Unicode-preserving case-fold, exact hash | Counted and reported; selected prompt groups must not cross splits |
| Exact normalized answer overlap | Whitespace collapse + case-fold, exact hash by split | Diagnostic only; frequent correct answers can naturally recur |
| Generator ingredient overlap | Canonical hash of generator version, topic and generation parameters; excludes dataset seed and row index | Any cross-split overlap is a hard warning |
| Lexical template signature | Normalize prompt then replace integer/rational literals with <num> | Diagnostic only; broad templates are expected to repeat |
| Semantic near-duplicate | No validated semantic-equivalence engine exists for all mixed-topic tasks | Explicitly not_assessed; owner review required |

The template signature is deliberately lexical. It is not structural algebraic normalization, symbolic equivalence, or semantic similarity. No defensible whole-corpus structural or semantic near-duplicate method is currently implemented, so those classes are explicitly unassessed rather than approximated by the lexical signature. The audit must not label lexical collisions as semantic duplicates.

## 3. Reference-answer and solvability checks

The semantic dataset verifier checks each supported row using the exact per-topic validator and checks that target_text equals exact_answer. The quality audit reports this same-validator repeatability check separately from an independent reconstruction check. The independent check is implemented separately in ultron_core/dataset_math_validation.py; it reconstructs each supported prompt and recomputes its exact answer from generation_parameters without importing the ingestion validator. It also checks topic-specific difficulty. This is independent implementation coverage, not a formal proof-kernel result. Existing deterministic positive/negative tests exercise the eight currently supported topic grammars (arithmetic, rational arithmetic, linear equations, polynomial derivatives, polynomial definite integrals, 2x2 determinants, 2x2 inverses and 2x2 linear systems). Each newly added generator family must bring a separate seed/difficulty replay test and an independent mathematical invariant or exact reference calculation; it cannot inherit a quality claim merely by appearing in a registry.

This establishes agreement with the current validator implementation for the supported generator grammar; it does not prove the verifier code is formally sound, establish correctness for unsupported topics, or prove that a human understands every problem statement. Independent per-generator tests should separately recompute mathematical invariants from ingredients, and any generator not covered by those tests must not be described as independently validated.

A sample is not accepted merely because it has a non-empty answer. Invalid output, malformed schemas, rejected validation status, failed identity binding, or exact-answer mismatch must fail closed.

## 4. Leakage and split checks

The v1 audit reports pairwise train/validation/test overlaps for:

- normalized prompt hashes;
- normalized answer hashes;
- lexical template signatures;
- generator-ingredient hashes;


Prompt-group split separation and ingredient overlap are integrity gates. Shared answer values and broad template signatures are diagnostic findings, not automatic leakage conclusions: independent questions can share an answer or template. Dataset-seed use counts are reported per split. A single dataset-wide seed appearing in every split is expected under schema v1; it is not a sample-level leakage signal. Repeated mathematical ingredients are detected by canonical hashes that exclude dataset seed and row index.

Evaluation records remain disjoint from training records by the manifest's selected IDs and exact prompt-group assignment. This is data-split integrity only. It does not establish an unseen-concept test, owner-curated semantic separation, or freedom from all conceptual leakage. Topic/difficulty/answer-format distributions and dominant template shares are shown per split so easy-template dominance and coverage imbalance can be reviewed explicitly.

## 5. Difficulty, topic and answer-format balance

The report emits, for each split:

- selected count and audited count;
- topic counts and number of topics represented;
- difficulty counts and observed difficulty levels;
- answer-format counts (integer, rational, matrix, assignment_pair, symbolic_or_polynomial, other);
- unique dataset-seed count and per-split dataset-seed use counts (not a per-sample seed-balance metric);
- highest-frequency lexical template per topic and its share.

These are descriptive distributions. The current generator does not define a calibrated cross-topic difficulty scale. Counts must not be interpreted as equivalent difficulty across topics. No universal balance threshold is asserted; future acceptance thresholds must be topic-specific and justified by coverage goals.

## 6. Prerequisite, adversarial and boundary coverage

The current JSONL v1 row schema has no prerequisite identifiers, explicit boundary/adversarial-case annotation, or per-case validation class. Prerequisite coverage is therefore reported as `not_assessed`; topic counts are not used as a substitute for prerequisite coverage. To assess it, a future schema must bind topic IDs to the versioned curriculum prerequisite graph and report both direct-node coverage and prerequisite-closure coverage by split.

Boundary coverage is also not currently measurable. The report therefore returns not_annotated_in_schema_v1 and a count of zero rather than infer boundary coverage from extreme numeric values. A future version should record the generator family, named boundary category, parameter constraints and expected validator behavior, then independently test valid boundary and rejected out-of-domain cases.

## 7. Reproducibility evidence

A report records dataset and split SHA-256, split counts, generator versions, dataset-level seed metadata, independent parameter/answer recheck counts and a deterministic report digest. Running the audit twice against identical inputs must yield byte-equivalent JSON and the same report digest. Transferred copies must pass dataset and split verification again before audit. Reproducibility of this audit does not imply that all generators are independently mathematically validated or that the corpus is representative.

## 8. Production gate

A report may show zero invalid exact answers and zero prompt/ingredient overlap while still failing production acceptance. At minimum, production review also needs:

1. owner approval of generation scope, retention and quotas;
2. independent mathematical validation per generator family;
3. semantic near-duplicate and concept leakage review where the method is defensible;
4. topic/difficulty/answer-format acceptance thresholds;
5. explicit boundary/adversarial coverage;
6. train/validation/final-evaluation protocol approval;
7. provenance and source-commit/runtime evidence;
8. destination-copy integrity verification;
9. separate explicit authorization for any corpus-generation job.

This phase's output is a read-only audit tool and contract documentation, not a ready corpus.


## Schema-v1 interpretation correction

Schema v1 stores a single dataset-manifest seed repeated on every row. Its repetition across train/validation/test is therefore expected and is not a sample-level seed-overlap metric; the report now labels it dataset-level metadata only. The mathematical-ingredient fingerprint excludes both that dataset seed and the unique row index. It hashes generator version, topic and canonical generation parameters.

The quality report distinguishes the same-validator repeatability scan from the independent parameter-based reconstruction scan. The former confirms the ingestion validator still accepts the row; the latter independently derives the exact prompt, target answer and difficulty from the recorded ingredients.
