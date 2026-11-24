import hashlib
import hmac
import os
import tempfile
from pathlib import Path
import torch
from .config import NeuroSparseConfig

def _digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def save_checkpoint(path, model: torch.nn.Module, config: NeuroSparseConfig, optimizer=None, step: int = 0):
    if not isinstance(config, NeuroSparseConfig):
        raise TypeError("config must be a NeuroSparseConfig")
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        raise ValueError("step must be a non-negative integer")
    model_config = getattr(model, "config", None)
    if model_config is not None and model_config.to_dict() != config.to_dict():
        raise ValueError("checkpoint config does not match model config")

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format_version": 2,
        "config": config.to_dict(),
        "model": model.state_dict(),
        "step": step,
        "optimizer": optimizer.state_dict() if optimizer is not None else None,
    }
    fd, name = tempfile.mkstemp(prefix="." + target.name + ".", suffix=".tmp", dir=target.parent)
    os.close(fd)
    tmp = Path(name)
    manifest = target.with_suffix(target.suffix + ".sha256")
    manifest_tmp = None
    try:
        torch.save(payload, tmp)
        with tmp.open("rb") as stream:
            os.fsync(stream.fileno())
        digest = _digest(tmp)
        os.replace(tmp, target)

        manifest_fd, manifest_name = tempfile.mkstemp(
            prefix="." + manifest.name + ".", suffix=".tmp", dir=target.parent
        )
        manifest_tmp = Path(manifest_name)
        with os.fdopen(manifest_fd, "w", encoding="utf-8") as stream:
            stream.write(digest + "  " + target.name + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(manifest_tmp, manifest)
        return {"path": str(target), "sha256": digest, "step": step}
    finally:
        tmp.unlink(missing_ok=True)
        if manifest_tmp is not None:
            manifest_tmp.unlink(missing_ok=True)


def load_checkpoint(path, model: torch.nn.Module, optimizer=None, map_location="cpu"):
    target = Path(path)
    manifest = target.with_suffix(target.suffix + ".sha256")
    if not target.is_file() or not manifest.is_file():
        raise FileNotFoundError("checkpoint/manifest missing")
    fields = manifest.read_text(encoding="utf-8").split()
    if not fields or len(fields[0]) != 64 or any(ch not in "0123456789abcdef" for ch in fields[0].lower()):
        raise ValueError("checkpoint integrity manifest is malformed")
    expected = fields[0]
    actual = _digest(target)
    if not hmac.compare_digest(expected, actual):
        raise ValueError("checkpoint integrity verification failed")

    payload = torch.load(target, map_location=map_location, weights_only=True)
    if not isinstance(payload, dict):
        raise ValueError("checkpoint payload must be a mapping")
    if payload.get("format_version") != 2:
        raise ValueError("unsupported checkpoint format")
    saved_config = payload.get("config")
    model_state = payload.get("model")
    step = payload.get("step")
    if not isinstance(saved_config, dict) or not isinstance(model_state, dict):
        raise ValueError("checkpoint config/model state is malformed")
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        raise ValueError("checkpoint step must be a non-negative integer")
    model_config = getattr(model, "config", None)
    if model_config is not None and model_config.to_dict() != saved_config:
        raise ValueError("checkpoint config does not match target model config")
    optimizer_state = payload.get("optimizer")
    if optimizer is not None and optimizer_state is None:
        raise ValueError("checkpoint does not contain optimizer state")
    if optimizer_state is not None and not isinstance(optimizer_state, dict):
        raise ValueError("checkpoint optimizer state is malformed")

    model.load_state_dict(model_state)
    if optimizer is not None:
        optimizer.load_state_dict(optimizer_state)
    return {"step": step, "config": saved_config, "sha256": actual}
