# Canonical math task serialization — schema v1

**Status:** implemented in the canonical task API; CI validation and merge are pending.  
**Scope:** task/problem serialization and target projection only. This document does not authorize dataset generation or model training.

## Design

A task is stored as three distinct layers:

1. **Problem:** source, topic, prompt, worked steps, final answer, seed/difficulty, normalized prompt identity, generation-ingredients digest, and source metadata.
2. **Verification receipt:** verifier ID/version, outcome, declared verification scope, and a digest of the complete serialized problem.
3. **Task envelope:** schema version plus a content-derived task ID that covers both the complete problem and receipt.

This prevents the answer, derivation, and verifier outcome from being conflated into one text string. The verifier receipt is metadata; it is never part of the supervised target.

## Schema v1

The canonical envelope has these fields:

```json
{
  "task_id": "<sha256 of the canonical envelope payload>",
  "schema_version": 1,
  "problem": {
    "schema_version": 1,
    "problem_id": "<sha256 of the normalized problem identity>",
    "source": "generator.identifier",
    "topic": "topic.identifier",
    "prompt": "Problem statement",
    "answer": "Final answer",
    "seed": 1846,
    "difficulty": 1,
    "normalized_text": "normalized problem statement",
    "ingredients_sha256": "<sha256 of generator ingredients>",
    "steps": ["Worked step one", "Worked step two"],
    "metadata": [["field", "value"]]
  },
  "verification": {
    "schema_version": 1,
    "verifier_id": "verifier.identifier",
    "verifier_version": "1",
    "outcome": "verified",
    "verified_fields": ["problem", "derivation", "answer"],
    "subject_sha256": "<sha256 of the complete problem document>"
  }
}
```

The example is illustrative. Hash strings shown as placeholders are not valid serialized values.

### Canonical encoding and validation

- JSON keys are sorted, UTF-8 is preserved, separators are compact, and non-finite JSON numbers are rejected.
- Duplicate JSON object keys are rejected while parsing.
- Task, problem, and receipt documents reject unknown/missing fields and unsupported schema versions.
- `Problem.from_dict` verifies the normalized prompt, field types, metadata shape/order, and content-derived problem identity.
- The receipt subject digest covers the entire serialized `Problem`, including exact prompt text, steps, answer, and metadata.
- `task_id` covers the task schema version, complete problem document, and complete verification receipt.
- Verifier callbacks must return the actual boolean `True` or `False`; strings, integers, and other truthy/falsy values are not accepted as results.

The problem identity deliberately normalizes prompt whitespace/case and includes source, topic, seed, difficulty, and ingredients digest. The receipt subject digest then binds the exact, unnormalized record content, so a change to steps or answer invalidates the receipt.

## Verification scope

`ProblemVerifier.verify(problem)` returns a boolean. A separate `verified_fields(problem)` declaration records which parts the verifier actually checks:

- `problem`: source/problem identity and prompt are checked.
- `answer`: final answer correctness is checked.
- `derivation`: the worked steps are checked.

The conservative base default is `("problem", "answer")`. `CoreExactVerifier` uses this default because it validates the supported prompt/answer relation but does not independently validate every worked step. `ReplayGeneratorVerifier` also defaults to problem+answer only. A caller must explicitly configure derivation coverage, and its verifier callback must actually validate every claimed step; the schema records that declaration but cannot prove the verifier implementation is sound.

A verifier that only checks the final answer must not claim derivation coverage merely because a step list is present. The current built-in core verifier therefore does not make such tasks exportable as worked-solution targets.

## Supervised target projection

`MathTaskRecord.to_training_target_dict()` exports only this allowlisted object:

```json
{
  "problem": "Problem statement",
  "derivation": ["Worked step one", "Worked step two"],
  "answer": "Final answer"
}
```

Export is refused unless:
- the verifier outcome is `verified`;
- the declared verified fields are exactly `problem`, `derivation`, and `answer`, in that order; and
- the problem contains non-empty worked steps.

The target projection excludes task IDs, problem IDs, source metadata, generation parameters, verifier IDs/versions, receipt digests, and verifier outcomes. This is a deliberate leakage boundary: validation metadata must not become a shortcut or target token sequence. Rejected or answer-only-verified tasks may still be stored as task records, but cannot be exported as worked-solution targets.

This API defines the canonical serialization and export contract. It does not itself create a corpus, populate a training dataset, authorize training, or run an optimizer.

## Trust boundary and limitations

SHA-256 fields detect accidental changes and bind a receipt to the serialized contents. They are **not signatures** and do not authenticate who produced the receipt. A party able to rewrite a record can recompute its hashes. Trust still depends on the verifier implementation, its version, an audited verifier allowlist, and the provenance of the record. A receipt is not a formal proof or proof-kernel acceptance. The explicit `verified_fields` list is a verifier-supplied scope declaration; the schema cannot independently establish that the verifier checked those fields correctly.

Schema changes require a new schema version and explicit migration. Do not silently reinterpret version-1 task or receipt documents.
