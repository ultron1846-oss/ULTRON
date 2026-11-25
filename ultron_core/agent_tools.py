"""Small allow-listed function tool registry for ULTRON's agent runtime.

The registry is intentionally explicit: tool names map to local callables and
unknown names are rejected. No arbitrary Python, shell, network, or eval tool
is exposed.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from .math_solver_tool import run_math_solver


MATH_SOLVER_TOOL: dict[str, Any] = {
    "name": "math_solver",
    "description": (
        "Solve supported linear equations, evaluate exact scalar arithmetic, "
        "or conservatively simplify supported mathematical expressions. "
        "Use this tool for deterministic math; it does not solve nonlinear "
        "equations or unsupported function calls."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["evaluate", "simplify", "solve"],
            },
            "expression": {
                "type": "string",
                "description": "A scalar arithmetic expression or one equality.",
            },
            "variables": {
                "type": "object",
                "description": "Exact integer or rational-string bindings for evaluate.",
                "additionalProperties": {"type": ["integer", "string"]},
            },
            "variable": {
                "type": "string",
                "description": "Optional variable name for solving a linear equation.",
            },
        },
        "required": ["operation", "expression"],
        "additionalProperties": False,
    },
}

_TOOL_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "math_solver": run_math_solver,
}


def get_tool_specs() -> list[dict[str, Any]]:
    """Return tool descriptions in agent function-calling format."""
    return [deepcopy(MATH_SOLVER_TOOL)]


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a named agent tool through the local allow-list."""
    if not isinstance(name, str):
        raise TypeError("tool name must be a string")
    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        raise ValueError(f"unknown or unavailable tool: {name}")
    return handler(arguments)
