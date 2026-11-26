"""Lean checker boundary stub. No Lean process is launched by this module."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import hashlib
import re


class ProofCheckStatus(str, Enum):
    TYPECHECKED = "typechecked"
    REJECTED = "rejected"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    INVALID_INPUT = "invalid_input"


@dataclass(frozen=True)
class ProofCheckResult:
    status: ProofCheckStatus
    theorem_name: str
    source_sha256: str
    checker_version: str
    environment_sha256: str | None = None
    receipt_sha256: str | None = None
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, ProofCheckStatus):
            raise TypeError("status must be a ProofCheckStatus")
        if not isinstance(self.theorem_name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_'.]*", self.theorem_name):
            raise ValueError("theorem_name must be a Lean identifier")
        for name in ("source_sha256", "environment_sha256", "receipt_sha256"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest")
        if not isinstance(self.checker_version, str) or not self.checker_version:
            raise ValueError("checker_version must be non-empty")
        if not isinstance(self.diagnostics, tuple) or any(not isinstance(x, str) for x in self.diagnostics):
            raise TypeError("diagnostics must be a tuple of strings")


class LeanProofChecker(ABC):
    """Injectable interface; concrete local Lean execution is intentionally absent."""
    @abstractmethod
    def check(self, source: str, theorem_name: str, *, environment_sha256: str) -> ProofCheckResult:
        """Type-check source and return a bounded result; never imply trust admission."""
        raise NotImplementedError


def source_sha256(source: str) -> str:
    if not isinstance(source, str):
        raise TypeError("Lean source must be text")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()
