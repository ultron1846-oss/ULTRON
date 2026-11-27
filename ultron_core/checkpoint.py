from __future__ import annotations
import copy, hashlib, hmac, os, random, shutil, tempfile
from pathlib import Path
import torch
from .config import NeuroSparseConfig

_FORMAT_VERSION = 6

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
    allowed = {"precision", "seed", "gradient_accumulation_steps", "deterministic", "profile_performance", "activation_checkpointing"}
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
    for name in ("deterministic", "profile_performance", "activation_checkpointing"):
        if name in settings and not isinstance(settings[name], bool):
            raise TypeError(f"training_settings {name} must be boolean")
    return copy.deepcopy(settings)


def _validate_data_state_hash_binding(data_state: dict | None, dataset_hash: str | None) -> None:
    """Reject cursor/sampler hashes that are not bound to the checkpoint dataset."""
    if data_state is None:
        return

    cursor_hash = data_state.get("dataset_manifest_sha256")
    if cursor_hash is not None:
        if (not isinstance(cursor_hash, str) or len(cursor_hash) != 64
                or any(char not in "0123456789abcdef" for char in cursor_hash)):
            raise ValueError("checkpoint data_state dataset manifest hash is malformed")
        if dataset_hash is None or not hmac.compare_digest(cursor_hash, dataset_hash):
            raise ValueError("checkpoint data_state dataset manifest hash does not match checkpoint")

    sampler_state = data_state.get("sampler_state")
    if sampler_state is not None:
        if not isinstance(sampler_state, dict):
            raise ValueError("checkpoint sampler state is malformed")
        sampler_hash = sampler_state.get("dataset_manifest_sha256")
        if (not isinstance(sampler_hash, str) or len(sampler_hash) != 64
                or any(char not in "0123456789abcdef" for char in sampler_hash)):
            raise ValueError("checkpoint sampler dataset manifest hash is malformed")
        if dataset_hash is None or not hmac.compare_digest(sampler_hash, dataset_hash):
            raise ValueError("checkpoint sampler dataset manifest hash does not match checkpoint")

def _validate_resumable_data_state(data_state: dict | None, dataset_hash: str | None) -> None:
    """Validate batch/sample/sampler cursor alignment for resumable checkpoints.

    Format-v6 cursors carrying sampler_state must be self-consistent before they
    are persisted or exposed to a caller. Older format-v5 cursors remain readable.
    """
    if data_state is None or "sampler_state" not in data_state:
        return

    sampler_state = data_state.get("sampler_state")
    if not isinstance(sampler_state, dict):
        raise ValueError("checkpoint sampler state is malformed")

    required = {
        "epoch", "next_batch_index", "next_sample_index", "dataset_size",
        "batch_size", "dataset_manifest_sha256", "seed",
        "gradient_accumulation_steps",
    }
    missing = sorted(required.difference(data_state))
    if missing:
        raise ValueError(
            "checkpoint resumable data_state is missing fields: " + ", ".join(missing)
        )

    def integer(name: str, minimum: int, maximum: int | None = None) -> int:
        value = data_state.get(name)
        if (isinstance(value, bool) or not isinstance(value, int)
                or value < minimum or (maximum is not None and value > maximum)):
            raise ValueError(f"checkpoint data_state {name} is invalid")
        return value

    epoch = integer("epoch", 0)
    next_batch_index = integer("next_batch_index", 0)
    next_sample_index = integer("next_sample_index", 0)
    dataset_size = integer("dataset_size", 1)
    batch_size = integer("batch_size", 1, 1024)
    seed = integer("seed", 0, 2**63 - 1)
    accumulation = integer("gradient_accumulation_steps", 1, 128)

    cursor_hash = data_state.get("dataset_manifest_sha256")
    if (not isinstance(cursor_hash, str) or len(cursor_hash) != 64
            or any(char not in "0123456789abcdef" for char in cursor_hash)
            or dataset_hash is None or cursor_hash != dataset_hash):
        raise ValueError("checkpoint resumable cursor dataset hash is inconsistent")

    max_batches = (dataset_size + batch_size - 1) // batch_size
    if next_batch_index > max_batches:
        raise ValueError("checkpoint data_state next_batch_index exceeds the epoch")
    expected_sample_index = min(next_batch_index * batch_size, dataset_size)
    if next_sample_index != expected_sample_index:
        raise ValueError(
            "checkpoint data_state next_sample_index does not match batch cursor and batch size"
        )

    sampler_version = sampler_state.get("schema_version")
    if isinstance(sampler_version, bool) or not isinstance(sampler_version, int) or sampler_version != 1:
        raise ValueError("checkpoint sampler state schema is invalid")
    sampler_size = sampler_state.get("dataset_size")
    sampler_seed = sampler_state.get("seed")
    sampler_epoch = sampler_state.get("epoch")
    sampler_index = sampler_state.get("next_index")
    if (isinstance(sampler_size, bool) or not isinstance(sampler_size, int)
            or sampler_size != dataset_size):
        raise ValueError("checkpoint sampler dataset size does not match data_state")
    if (isinstance(sampler_seed, bool) or not isinstance(sampler_seed, int)
            or sampler_seed != seed):
        raise ValueError("checkpoint sampler seed does not match data_state")
    if (isinstance(sampler_epoch, bool) or not isinstance(sampler_epoch, int)
            or sampler_epoch != epoch):
        raise ValueError("checkpoint sampler epoch does not match data_state")
    if (isinstance(sampler_index, bool) or not isinstance(sampler_index, int)
            or sampler_index != next_sample_index):
        raise ValueError("checkpoint sampler cursor does not match data_state")

    sampler_hash = sampler_state.get("dataset_manifest_sha256")
    if sampler_hash != cursor_hash:
        raise ValueError("checkpoint sampler dataset hash does not match data_state")

    settings = _validate_training_settings(data_state.get("training_settings"))
    if settings is not None:
        if settings.get("seed", seed) != seed:
            raise ValueError("checkpoint data_state training seed does not match cursor")
        if settings.get("gradient_accumulation_steps", accumulation) != accumulation:
            raise ValueError("checkpoint data_state accumulation does not match cursor")

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
    cursor_training_settings = (
        data_state.get("training_settings") if isinstance(data_state, dict) else None
    )
    if training_settings is None:
        training_settings = cursor_training_settings
    training_settings = _validate_training_settings(training_settings)
    cursor_training_settings = _validate_training_settings(cursor_training_settings)
    if (training_settings is not None and cursor_training_settings is not None
            and training_settings != cursor_training_settings):
        raise ValueError("top-level and data_state training_settings must match")
    if dataset_manifest_sha256 is not None and (
            not isinstance(dataset_manifest_sha256, str) or len(dataset_manifest_sha256) != 64
            or any(char not in "0123456789abcdef" for char in dataset_manifest_sha256)):
        raise ValueError("dataset_manifest_sha256 must be a lowercase SHA-256 hex digest")
    _validate_data_state_hash_binding(data_state, dataset_manifest_sha256)
    _validate_resumable_data_state(data_state, dataset_manifest_sha256)
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
        "training_settings": training_settings,
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
    if version not in (2, 3, 4, 5, _FORMAT_VERSION):
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
    training_settings = _validate_training_settings(payload.get("training_settings"))
    cursor_training_settings = (
        data_state.get("training_settings") if isinstance(data_state, dict) else None
    )
    cursor_training_settings = _validate_training_settings(cursor_training_settings)
    if (training_settings is not None and cursor_training_settings is not None
            and training_settings != cursor_training_settings):
        raise ValueError("checkpoint training_settings metadata is inconsistent")
    if training_settings is None:
        training_settings = cursor_training_settings
    dataset_hash = payload.get("dataset_manifest_sha256")
    if dataset_hash is not None and (
            not isinstance(dataset_hash, str) or len(dataset_hash) != 64
            or any(char not in "0123456789abcdef" for char in dataset_hash)):
        raise ValueError("checkpoint dataset manifest hash is malformed")
    _validate_data_state_hash_binding(data_state, dataset_hash)
    if version >= 6:
        _validate_resumable_data_state(data_state, dataset_hash)
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
            "optimizer_state_present": opt_state is not None,
            "optimizer_restored": bool(optimizer is not None and opt_state is not None),
            "scheduler_state_present": sched_state is not None,
            "scheduler_restored": bool(scheduler is not None and sched_state is not None),
            "training_settings": training_settings}
