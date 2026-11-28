"""Versioned, integrity-checked compressed deployment artifacts."""
from __future__ import annotations

import hashlib
import hmac
import io
import math
import os
import pickle
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping

import torch
from torch import nn

_FORMAT = "ultron.compressed-model"
_FORMAT_VERSION = 1
_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")


def _json_safe(value: Any, *, field: str = "metadata") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field} contains a non-finite number")
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, field=field) for item in value]
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError(f"{field} keys must be strings")
        return {key: _json_safe(item, field=field) for key, item in value.items()}
    raise TypeError(f"{field} contains unsupported value type {type(value).__name__}")


def _state_digest(state: Mapping[str, torch.Tensor]) -> str:
    buffer = io.BytesIO()
    ordered = {}
    for name in sorted(state):
        tensor = state[name]
        if not isinstance(name, str) or not isinstance(tensor, torch.Tensor):
            raise TypeError("model_state must map string names to tensors")
        ordered[name] = tensor.detach().to(device="cpu").contiguous()
    torch.save(ordered, buffer)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def _validate_artifact_version(version: str) -> str:
    if not isinstance(version, str) or not _VERSION_PATTERN.fullmatch(version):
        raise ValueError("artifact_version must use a versioned x.y.z format")
    return version


def save_compression_artifact(
    path: str | os.PathLike,
    model: nn.Module,
    *,
    parent_checkpoint_id: str,
    artifact_version: str,
    compression_steps: list[dict],
) -> dict:
    """Write an independent, atomic compressed deployment artifact.

    This never writes to a source checkpoint unless the caller explicitly
    chooses that path. Existing artifact paths are immutable and always rejected.
    """
    if not isinstance(model, nn.Module):
        raise TypeError("model must be a torch.nn.Module")
    if not isinstance(parent_checkpoint_id, str) or not parent_checkpoint_id.strip():
        raise ValueError("parent_checkpoint_id must be a non-empty stable identifier")
    version = _validate_artifact_version(artifact_version)
    if not isinstance(compression_steps, list) or not compression_steps:
        raise ValueError("compression_steps must be a non-empty list")
    safe_steps = _json_safe(compression_steps, field="compression_steps")
    config = getattr(model, "config", None)
    config_dict = config.to_dict() if callable(getattr(config, "to_dict", None)) else None
    safe_config = _json_safe(config_dict, field="config")
    state = {
        name: tensor.detach().to(device="cpu").contiguous().clone()
        for name, tensor in model.state_dict().items()
    }
    state_sha256 = _state_digest(state)
    payload = {
        "format": _FORMAT,
        "format_version": _FORMAT_VERSION,
        "artifact_version": version,
        "parent_checkpoint_id": parent_checkpoint_id,
        "model_scope": "compressed_deployment_artifact",
        "foundation_parameter_floor_applies": False,
        "config": safe_config,
        "compression_steps": safe_steps,
        "model_state": state,
        "model_state_sha256": state_sha256,
    }

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"artifact already exists and cannot be overwritten: {target}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            torch.save(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        if target.exists():
            raise FileExistsError(f"artifact already exists and cannot be overwritten: {target}")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)

    return {
        "path": str(target),
        "format": _FORMAT,
        "format_version": _FORMAT_VERSION,
        "artifact_version": version,
        "parent_checkpoint_id": parent_checkpoint_id,
        "model_state_sha256": state_sha256,
    }


def load_compression_artifact(path: str | os.PathLike) -> dict:
    """Load and validate artifact metadata and tensor-state integrity."""
    try:
        payload = torch.load(path, map_location="cpu", weights_only=True)
    except FileNotFoundError:
        raise
    except (OSError, RuntimeError, EOFError, pickle.UnpicklingError, ValueError) as exc:
        raise ValueError("compressed artifact is unreadable or truncated") from exc
    required = {
        "format", "format_version", "artifact_version", "parent_checkpoint_id",
        "model_scope", "foundation_parameter_floor_applies", "config",
        "compression_steps", "model_state", "model_state_sha256",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("compressed artifact structure is invalid")
    if (
        payload["format"] != _FORMAT
        or isinstance(payload["format_version"], bool)
        or not isinstance(payload["format_version"], int)
        or payload["format_version"] != _FORMAT_VERSION
    ):
        raise ValueError("unsupported compressed artifact format")
    _validate_artifact_version(payload["artifact_version"])
    if not isinstance(payload["parent_checkpoint_id"], str) or not payload["parent_checkpoint_id"].strip():
        raise ValueError("compressed artifact parent checkpoint identifier is invalid")
    if payload["model_scope"] != "compressed_deployment_artifact":
        raise ValueError("artifact scope must be compressed_deployment_artifact")
    if payload["foundation_parameter_floor_applies"] is not False:
        raise ValueError("compressed artifacts must not claim the foundation parameter floor")
    if payload["config"] is not None and not isinstance(payload["config"], dict):
        raise ValueError("compressed artifact config is invalid")
    if not isinstance(payload["compression_steps"], list) or not payload["compression_steps"]:
        raise ValueError("compressed artifact steps are invalid")
    state = payload["model_state"]
    if not isinstance(state, dict) or any(
        not isinstance(name, str) or not isinstance(tensor, torch.Tensor)
        for name, tensor in state.items()
    ):
        raise ValueError("compressed artifact model state is invalid")
    expected_digest = payload["model_state_sha256"]
    if not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        raise ValueError("compressed artifact state hash is invalid")
    actual_digest = _state_digest(state)
    if not hmac.compare_digest(actual_digest, expected_digest):
        raise ValueError("compressed artifact model state hash verification failed")
    _json_safe(payload["compression_steps"], field="compression_steps")
    return payload
