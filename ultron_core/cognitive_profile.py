"""Validated, model-agnostic cognitive behavior profile for ULTRON.

This module defines runtime policy only. It does not claim that the untrained
language model already has these capabilities, nor does it perform inference.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from enum import Enum


class CognitiveMode(str, Enum):
    """Selectable inference policies."""

    BALANCED = "balanced"
    QUICK = "quick"
    DEEP_REASONING = "deep_reasoning"
    MATHEMATICAL = "mathematical"
    CREATIVE = "creative"
    REFLECTIVE = "reflective"


@dataclass(frozen=True)
class CognitiveBehaviorProfile:
    """Target behavior blending rigorous reasoning and natural conversation."""

    name: str = "ULTRON Cognitive Profile"
    version: int = 1
    factuality_priority: float = 1.0
    reasoning_effort: float = 0.85
    conversational_naturalness: float = 0.80
    creative_flexibility: float = 0.70
    self_check_strength: float = 0.90
    uncertainty_calibration: float = 1.0
    empathy_and_context: float = 0.75
    working_memory_items: int = 7
    planning_steps: int = 8
    critique_passes: int = 1
    require_evidence_for_claims: bool = True
    preserve_user_goal: bool = True
    avoid_fake_introspection: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be a positive integer")
        for field in (
            "factuality_priority",
            "reasoning_effort",
            "conversational_naturalness",
            "creative_flexibility",
            "self_check_strength",
            "uncertainty_calibration",
            "empathy_and_context",
        ):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{field} must be numeric")
            if not math.isfinite(value):
                raise ValueError(f"{field} must be finite")
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field} must be in [0, 1]")
        for field in ("working_memory_items", "planning_steps", "critique_passes"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")
        if self.working_memory_items < 1 or self.planning_steps < 1:
            raise ValueError("working memory and planning steps must be positive")
        for field in (
            "require_evidence_for_claims",
            "preserve_user_goal",
            "avoid_fake_introspection",
        ):
            if not isinstance(getattr(self, field), bool):
                raise TypeError(f"{field} must be bool")

    @classmethod
    def default(cls) -> "CognitiveBehaviorProfile":
        """Return ULTRON's target behavior; values are policy weights, not scores."""
        return cls()

    def policy_for(self, mode: CognitiveMode = CognitiveMode.BALANCED) -> dict[str, object]:
        """Return deterministic policy settings for a selected inference mode."""
        if not isinstance(mode, CognitiveMode):
            raise TypeError("mode must be CognitiveMode")
        policy: dict[str, object] = {
            "mode": mode.value,
            "factuality_priority": self.factuality_priority,
            "reasoning_effort": self.reasoning_effort,
            "conversational_naturalness": self.conversational_naturalness,
            "creative_flexibility": self.creative_flexibility,
            "empathy_and_context": self.empathy_and_context,
            "self_check_strength": self.self_check_strength,
            "uncertainty_calibration": self.uncertainty_calibration,
            "max_planning_steps": self.planning_steps,
            "critique_passes": self.critique_passes,
            "working_memory_items": self.working_memory_items,
            "require_evidence_for_claims": self.require_evidence_for_claims,
            "preserve_user_goal": self.preserve_user_goal,
            "avoid_fake_introspection": self.avoid_fake_introspection,
        }
        if mode == CognitiveMode.QUICK:
            policy.update(reasoning_effort=0.25, max_planning_steps=2, critique_passes=0)
        elif mode == CognitiveMode.DEEP_REASONING:
            policy.update(reasoning_effort=1.0, max_planning_steps=self.planning_steps, critique_passes=max(2, self.critique_passes))
        elif mode == CognitiveMode.MATHEMATICAL:
            policy.update(reasoning_effort=1.0, max_planning_steps=self.planning_steps, critique_passes=max(2, self.critique_passes), require_formal_verification=True)
        elif mode == CognitiveMode.CREATIVE:
            policy.update(creative_flexibility=self.creative_flexibility, critique_passes=0)
        elif mode == CognitiveMode.REFLECTIVE:
            policy.update(reasoning_effort=0.9, critique_passes=max(1, self.critique_passes), review_goal_alignment=True)
        return policy


DEFAULT_COGNITIVE_PROFILE = CognitiveBehaviorProfile.default()
