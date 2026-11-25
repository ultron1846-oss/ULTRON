from __future__ import annotations
import copy, hashlib, hmac, os, random, shutil, tempfile
from pathlib import Path
import torch
from .config import NeuroSparseConfig

_FORMAT_VERSION = 5

def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _manifest(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".sha256")

def _backup(path: Path) -> Path:
    return Path(str(path) + ".bak")

def _valid_pair(path: Path, manifest: Path) -> bool:
    try:
        fields = manifest.read_text(encoding="utf-8").split()
        return bool(fields and len(fields[0]) == 64
                    and all(ch in "0123456789abcdef" for ch in fields[0])
                    and hmac.compare_digest(fields[0], _digest(path)))
    except OSError:
        return False

def _atomic_copy(source: Path, destination: Path) -> None:
    fd, name = tempfile.mkstemp(prefix="." + destination.name + ".", suffix=".tmp", dir=destination.parent)
    temporary = Path(name)
    try:
        with source.open("rb") as src, os.fdopen(fd, "wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

def _capture_rng() -> dict:
    return {"python": random.getstate(), "torch_cpu": torch.random.get_rng_state(),
            "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []}

def _restore_rng(state: dict) -> None:
    if not isinstance(state, dict) or not {"python", "torch_cpu", "torch_cuda"} <= set(state):
        raise ValueError("checkpoint RNG state is malformed")
    random.setstate(state["python"])
    cpu = state["torch_cpu"]
    if not isinstance(cpu, torch.Tensor) or cpu.dtype != torch.uint8:
        raise ValueError("checkpoint CPU RNG state is malformed")
    torch.random.set_rng_state(cpu.cpu())
    cuda = state["torch_cuda"]
    if not isinstance(cuda, list) or any(not isinstance(x, torch.Tensor) for x in cuda):
        raise ValueError("checkpoint CUDA RNG state is malformed")
    if cuda:
        if not torch.cuda.is_available() or len(cuda) != torch.cuda.device_count():
            raise ValueError("checkpoint CUDA RNG state does not match available devices")
        torch.cuda.set_rng_state_all(cuda)

def _validate_model_state(model: torch.nn.Module, model_state: dict) -> None:
    expected = model.state_dict()
    if model_state.keys() != expected.keys():
        missing = sorted(map(str, set(expected) - set(model_state)))
        unexpected = sorted(map(str, set(model_state) - set(expected)))
        raise ValueError(f"checkpoint model state keys do not match (missing={missing}, unexpected={unexpected})")
    for name, target in expected.items():
        actual = model_state[name]
        if not isinstance(target, torch.Tensor) or not isinstance(actual, torch.Tensor):
            raise ValueError(f"checkpoint model state entry {name!r} must be a tensor")
        if actual.shape != target.shape:
            raise ValueError(f"checkpoint model state tensor {name!r} has shape {tuple(actual.shape)}; expected {tuple(target.shape)}")
        if actual.layout != target.layout:
            raise ValueError(f"checkpoint model state tensor {name!r} has layout {actual.layout}; expected {target.layout}")
        if actual.dtype != target.dtype:
            raise ValueError(f"checkpoint model state tensor {name!r} has dtype {actual.dtype}; expected {target.dtype}")

def _validate_training_settings(settings: dict | None) -> dict | None:
    if settings is None:
        return None
    if not isinstance(settings, dict):
        raise TypeError("training_settings must be a dictionary or None")
    allowed = {"precision", "seed", "gradient_accumulation_steps", "deterministic", "profile_performance"}
    if set(settings) - allowed:
        raise ValueError("training_settings contains unsupported fields")
    precision = settings.get("precision", "fp32")
    if precision not in ("fp32", "bf16"):
        raise ValueError("training_settings precision must be fp32 or bf16")
    seed = settings.get("seed")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63):
        raise ValueError("training_settings seed is invalid")
    accumulation = settings.get("gradient_accumulation_steps")
    if accumulation is not None and (isinstance(accumulation, bool) or not isinstance(accumulation, int) or not 1 <= accumulation <= 128):
        raise ValueError("training_settings gradient_accumulation_steps is invalid")
    for name in ("deterministic", "profile_performance"):
        if name in settings and not isinstance(settings[name], bool):
            raise TypeError(f"training_settings {name} must be boolean")
    return copy.deepcopy(settings)


def save_checkpoint(path, model: torch.nn.Module, config: NeuroSparseConfig,
                   optimizer=None, step: int = 0, scheduler=None, data_state=None, dataset_manifest_sha256=None, training_settings=None):
    if not isinstance(config, NeuroSparseConfig):
        raise TypeError("config must be a NeuroSparseConfig")
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        raise ValueError("step must be a non-negative integer")
    model_config = getattr(model, "config", None)
    if model_config is not None and model_config.to_dict() != config.to_dict():
        raise ValueError("checkpoint config does not match model config")
    if data_state is not None and not isinstance(data_state, dict):
        raise TypeError("data_state must be a dictionary or None")
    if data_state is not None and dataset_manifest_sha256 is None:
        raise ValueError("data_state requires a dataset manifest SHA-256")
    if training_settings is None and isinstance(data_state, dict):
        training_settings = data_state.get("training_settings")
    training_settings = _validate_training_settings(training_settings)
    if dataset_manifest_sha256 is not None and (
            not isinstance(dataset_manifest_sha256, str) or len(dataset_manifest_sha256) != 64
            or any(char not in "0123456789abcdef" for char in dataset_manifest_sha256)):
        raise ValueError("dataset_manifest_sha256 must be a lowercase SHA-256 hex digest")
    if scheduler is not None and not hasattr(scheduler, "state_dict"):
        raise TypeError("scheduler must provide state_dict")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = _manifest(target)
    backup_path, backup_manifest = _backup(target), _backup(manifest)
    if _valid_pair(target, manifest):
        _atomic_copy(target, backup_path)
        _atomic_copy(manifest, backup_manifest)
    payload = {
        "format_version": _FORMAT_VERSION, "config": config.to_dict(),
        "model": model.state_dict(), "step": step,
        "optimizer": optimizer.state_dict() if optimizer is not None else None,
        "scheduler": scheduler.state_dict() if scheduler is not None else None,
        "rng": _capture_rng(), "data_state": data_state,
        "dataset_manifest_sha256": dataset_manifest_sha256,
    }
    fd, name = tempfile.mkstemp(prefix="." + target.name + ".", suffix=".tmp", dir=target.parent)
    temporary = Path(name)
    manifest_temporary = None
    try:
        with os.fdopen(fd, "wb") as stream:
            torch.save(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        digest = _digest(temporary)
        os.replace(temporary, target)
        manifest_fd, manifest_name = tempfile.mkstemp(prefix="." + manifest.name + ".", suffix=".tmp", dir=target.parent)
        manifest_temporary = Path(manifest_name)
        with os.fdopen(manifest_fd, "w", encoding="utf-8") as stream:
            stream.write(digest + "  " + target.name + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(manifest_temporary, manifest)
        return {"path": str(target), "sha256": digest, "step": step}
    finally:
        temporary.unlink(missing_ok=True)
        if manifest_temporary is not None:
            manifest_temporary.unlink(missing_ok=True)

def load_checkpoint(path, model: torch.nn.Module, optimizer=None, map_location="cpu",
                   scheduler=None, restore_rng: bool = True, expected_dataset_manifest_sha256=None):
    target = Path(path)
    manifest = _manifest(target)
    backup_path, backup_manifest = _backup(target), _backup(_manifest(target))
    if _valid_pair(target, manifest):
        source = target
    elif _valid_pair(backup_path, backup_manifest):
        source = backup_path
    else:
        if not target.is_file() and not backup_path.is_file():
            raise FileNotFoundError("checkpoint/manifest missing")
        raise ValueError("checkpoint and backup integrity verification failed")
    payload = torch.load(source, map_location=map_location, weights_only=True)
    if not isinstance(payload, dict):
        raise ValueError("checkpoint payload must be a mapping")
    version = payload.get("format_version")
    if version not in (2, 3, 4, _FORMAT_VERSION):
        raise ValueError("unsupported checkpoint format")
    saved_config, model_state, step = payload.get("config"), payload.get("model"), payload.get("step")
    if not isinstance(saved_config, dict) or not isinstance(model_state, dict):
        raise ValueError("checkpoint config/model state is malformed")
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        raise ValueError("checkpoint step must be a non-negative integer")
    model_config = getattr(model, "config", None)
    if model_config is not None and model_config.to_dict() != saved_config:
        raise ValueError("checkpoint config does not match target model config")
    _validate_model_state(model, model_state)
    opt_state = payload.get("optimizer")
    if optimizer is not None and opt_state is None:
        raise ValueError("checkpoint does not contain optimizer state")
    if opt_state is not None and not isinstance(opt_state, dict):
        raise ValueError("checkpoint optimizer state is malformed")
    sched_state = payload.get("scheduler")
    if scheduler is not None and not isinstance(sched_state, dict):
        raise ValueError("checkpoint does not contain scheduler state")
    if sched_state is not None and not isinstance(sched_state, dict):
        raise ValueError("checkpoint scheduler state is malformed")
    data_state = payload.get("data_state")
    if data_state is not None and not isinstance(data_state, dict):
        raise ValueError("checkpoint data state is malformed")
    training_settings = payload.get("training_settings")
    if training_settings is None and isinstance(data_state, dict):
        training_settings = data_state.get("training_settings")
    training_settings = _validate_training_settings(training_settings)
    dataset_hash = payload.get("dataset_manifest_sha256")
    if dataset_hash is not None and (
            not isinstance(dataset_hash, str) or len(dataset_hash) != 64
            or any(char not in "0123456789abcdef" for char in dataset_hash)):
        raise ValueError("checkpoint dataset manifest hash is malformed")
    if expected_dataset_manifest_sha256 is not None and (
            not isinstance(expected_dataset_manifest_sha256, str)
            or len(expected_dataset_manifest_sha256) != 64
            or any(char not in "0123456789abcdef" for char in expected_dataset_manifest_sha256)):
        raise ValueError("expected_dataset_manifest_sha256 must be a lowercase SHA-256 hex digest")
    if data_state is not None and expected_dataset_manifest_sha256 is None:
        raise ValueError("expected dataset manifest hash is required to restore a data cursor")
    dataset_hash_verified = False
    if expected_dataset_manifest_sha256 is not None:
        if dataset_hash is None:
            raise ValueError("checkpoint has no dataset manifest hash for expected dataset")
        if not hmac.compare_digest(dataset_hash, expected_dataset_manifest_sha256):
            raise ValueError("checkpoint dataset manifest hash does not match expected dataset")
        dataset_hash_verified = True
    rng_state = payload.get("rng")
    if restore_rng and version >= 3 and not isinstance(rng_state, dict):
        raise ValueError("checkpoint RNG state is missing")
    model_before = {k: v.detach().clone() for k, v in model.state_dict().items()}
    opt_before = copy.deepcopy(optimizer.state_dict()) if optimizer is not None else None
    sched_before = copy.deepcopy(scheduler.state_dict()) if scheduler is not None else None
    rng_before = _capture_rng() if restore_rng else None
    try:
        if optimizer is not None:
            optimizer.load_state_dict(opt_state)
        if scheduler is not None:
            scheduler.load_state_dict(sched_state)
        model.load_state_dict(model_state)
        if restore_rng and version >= 3:
            _restore_rng(rng_state)
    except Exception:
        model.load_state_dict(model_before)
        if optimizer is not None:
            optimizer.load_state_dict(opt_before)
        if scheduler is not None:
            scheduler.load_state_dict(sched_before)
        if restore_rng and rng_before is not None:
            _restore_rng(rng_before)
        raise
    return {"step": step, "config": saved_config, "sha256": _digest(source),
            "source_path": str(source), "data_state": data_state,
            "dataset_manifest_sha256": dataset_hash, "format_version": version,
            "rng_restored": bool(restore_rng and version >= 3),
            "dataset_hash_verified": dataset_hash_verified,
            "training_settings": training_settings}
