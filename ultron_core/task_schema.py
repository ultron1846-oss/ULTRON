"""Canonical, verifier-bound math task records and leakage-safe target export.

The verification receipt is integrity-bound metadata, not a digital signature or
formal proof. Training targets are built from an explicit allowlist and never
contain verifier receipts or problem metadata.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from .problem import Problem, ProblemVerifier

TASK_SCHEMA_VERSION = 1
VERIFICATION_RECEIPT_SCHEMA_VERSION = 1
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _problem_subject_sha256(problem: Problem) -> str:
    """Bind a verifier result to the complete serialized problem record."""
    validated = Problem.from_dict(problem.to_dict())
    return _sha256_json(validated.to_dict())


def _reject_duplicate_object_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


@dataclass(frozen=True)
class VerificationReceipt:
    """Versioned record of one verifier's boolean result for one problem."""

    schema_version: int
    verifier_id: str
    verifier_version: str
    outcome: str
    subject_sha256: str

    def __post_init__(self) -> None:
        if (isinstance(self.schema_version, bool)
                or not isinstance(self.schema_version, int)
                or self.schema_version != VERIFICATION_RECEIPT_SCHEMA_VERSION):
            raise ValueError("unsupported verification receipt schema version")
        for name, value in (("verifier_id", self.verifier_id),
                            ("verifier_version", self.verifier_version)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
        if self.outcome not in ("verified", "rejected"):
            raise ValueError("verification outcome must be verified or rejected")
        if not isinstance(self.subject_sha256, str) or not _SHA256_RE.fullmatch(self.subject_sha256):
            raise ValueError("subject_sha256 must be a lowercase SHA-256 digest")

    @classmethod
    def from_verifier(
        cls,
        problem: Problem,
        verifier: ProblemVerifier,
        *,
        verifier_id: str,
        verifier_version: str,
    ) -> "VerificationReceipt":
        if not isinstance(problem, Problem):
            raise TypeError("problem must be a Problem")
        if not callable(getattr(verifier, "verify", None)):
            raise TypeError("verifier must provide verify(problem)")
        # Re-validate even directly constructed Problem objects before a receipt
        # is bound to them.
        validated_problem = Problem.from_dict(problem.to_dict())
        result = verifier.verify(validated_problem)
        if type(result) is not bool:
            raise TypeError("problem verifier must return a boolean")
        return cls(
            VERIFICATION_RECEIPT_SCHEMA_VERSION,
            verifier_id,
            verifier_version,
            "verified" if result else "rejected",
            _problem_subject_sha256(validated_problem),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VerificationReceipt":
        required = {
            "schema_version", "verifier_id", "verifier_version",
            "outcome", "subject_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != required:
            raise ValueError("verification receipt fields do not match schema version 1")
        return cls(
            value["schema_version"], value["verifier_id"], value["verifier_version"],
            value["outcome"], value["subject_sha256"],
        )


@dataclass(frozen=True)
class MathTaskRecord:
    """Canonical full task record: problem + derivation/answer + verifier receipt.

    The problem's `steps` field is the derivation and its `answer` field is the
    answer. `to_training_target_dict` exports only prompt, derivation and answer.
    """

    schema_version: int
    problem: Problem
    verification: VerificationReceipt

    def __post_init__(self) -> None:
        if (isinstance(self.schema_version, bool)
                or not isinstance(self.schema_version, int)
                or self.schema_version != TASK_SCHEMA_VERSION):
            raise ValueError("unsupported math task schema version")
        if not isinstance(self.problem, Problem):
            raise TypeError("problem must be a Problem")
        if not isinstance(self.verification, VerificationReceipt):
            raise TypeError("verification must be a VerificationReceipt")
        subject = _problem_subject_sha256(self.problem)
        if self.verification.subject_sha256 != subject:
            raise ValueError("verification receipt does not match serialized problem contents")

    @classmethod
    def from_verifier(
        cls,
        problem: Problem,
        verifier: ProblemVerifier,
        *,
        verifier_id: str,
        verifier_version: str,
    ) -> "MathTaskRecord":
        receipt = VerificationReceipt.from_verifier(
            problem, verifier, verifier_id=verifier_id,
            verifier_version=verifier_version,
        )
        return cls(TASK_SCHEMA_VERSION, Problem.from_dict(problem.to_dict()), receipt)

    @property
    def task_id(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "problem": self.problem.to_dict(),
            "verification": self.verification.to_dict(),
        }
        return _sha256_json(payload)

    @property
    def training_eligible(self) -> bool:
        return self.verification.outcome == "verified"

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "problem": self.problem.to_dict(),
            "verification": self.verification.to_dict(),
        }
        return {"task_id": _sha256_json(payload), **payload}

    def to_json(self) -> str:
        """Return deterministic compact UTF-8 JSON for storage/manifests."""
        return _canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MathTaskRecord":
        required = {"task_id", "schema_version", "problem", "verification"}
        if not isinstance(value, Mapping) or set(value) != required:
            raise ValueError("math task fields do not match schema version 1")
        problem = Problem.from_dict(value["problem"])
        verification = VerificationReceipt.from_dict(value["verification"])
        task = cls(value["schema_version"], problem, verification)
        task_id = value["task_id"]
        if not isinstance(task_id, str) or not _SHA256_RE.fullmatch(task_id):
            raise ValueError("task_id must be a lowercase SHA-256 digest")
        if task_id != task.task_id:
            raise ValueError("task_id does not match serialized task contents")
        return task

    @classmethod
    def from_json(cls, value: str) -> "MathTaskRecord":
        if not isinstance(value, str):
            raise TypeError("math task JSON must be text")
        try:
            parsed = json.loads(value, object_pairs_hook=_reject_duplicate_object_keys)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("invalid or ambiguous math task JSON") from exc
        return cls.from_dict(parsed)

    def to_training_target_dict(self) -> dict[str, Any]:
        """Export only allowlisted supervised fields; verifier metadata is excluded."""
        if not self.training_eligible:
            raise ValueError("rejected tasks cannot be exported as training targets")
        return {
            "problem": self.problem.prompt,
            "derivation": list(self.problem.steps),
            "answer": self.problem.answer,
        }

    def to_training_target_json(self) -> str:
        return _canonical_json(self.to_training_target_dict())
