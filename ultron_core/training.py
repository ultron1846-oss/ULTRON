import copy
import math
import random
import re
import time
from dataclasses import dataclass

from .config import NeuroSparseConfig, count_parameters
import torch
from torch.nn import functional as F


def causal_language_model_loss(logits: torch.Tensor, input_ids: torch.Tensor,
        load_balance: torch.Tensor | None = None, prediction_error: torch.Tensor | None = None,
        balance_weight: float = 0.01, prediction_weight: float = 0.01,
        ignore_index: int | None = 0) -> torch.Tensor:
    if logits.ndim != 3 or input_ids.ndim != 2:
        raise ValueError('expected logits [B,T,V] and input_ids [B,T]')
    if logits.shape[:2] != input_ids.shape:
        raise ValueError('logits/input_ids sequence dimensions must match')
    if input_ids.shape[0] == 0 or input_ids.shape[1] < 2:
        raise ValueError('batch must be non-empty and sequence length must be at least 2')
    for name, weight in (("balance_weight", balance_weight), ("prediction_weight", prediction_weight)):
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or weight < 0:
            raise ValueError(f"{name} must be a finite non-negative number")
    if not logits.is_floating_point():
        raise TypeError("logits must use a floating-point dtype")
    if logits.shape[-1] <= 0:
        raise ValueError("logits vocabulary dimension must be non-empty")
    if input_ids.dtype not in (torch.int32, torch.int64):
        raise TypeError("input_ids must use int32 or int64 token IDs")
    if input_ids.device != logits.device:
        raise ValueError("logits and input_ids must be on the same device")
    if ignore_index is not None and (isinstance(ignore_index, bool) or not isinstance(ignore_index, int)):
        raise TypeError("ignore_index must be an integer or None")
    for name, auxiliary in (("load_balance", load_balance), ("prediction_error", prediction_error)):
        if auxiliary is not None:
            if not isinstance(auxiliary, torch.Tensor) or auxiliary.numel() != 1:
                raise ValueError(f"{name} must be a scalar tensor")
            if not auxiliary.is_floating_point() or auxiliary.device != logits.device:
                raise ValueError(f"{name} must be a floating-point scalar on the logits device")
    targets = input_ids[:, 1:].reshape(-1).long()
    flat_logits = logits[:, :-1].reshape(-1, logits.shape[-1])
    if ignore_index is not None:
        if not bool((targets != ignore_index).any()):
            raise ValueError('all next-token targets are padding; loss is undefined')
        loss = F.cross_entropy(flat_logits, targets, ignore_index=ignore_index)
    else:
        loss = F.cross_entropy(flat_logits, targets)
    if load_balance is not None:
        loss = loss + balance_weight * load_balance
    if prediction_error is not None:
        loss = loss + prediction_weight * prediction_error
    return loss


def make_optimizer(model: torch.nn.Module, learning_rate: float = 3e-4,
                   weight_decay: float = 0.01):
    if (isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float))
            or not math.isfinite(learning_rate) or learning_rate <= 0):
        raise ValueError('learning_rate must be a finite positive number')
    if (isinstance(weight_decay, bool) or not isinstance(weight_decay, (int, float))
            or not math.isfinite(weight_decay) or weight_decay < 0):
        raise ValueError('weight_decay must be a finite non-negative number')
    trainable_parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not trainable_parameters:
        raise ValueError("model has no trainable parameters")
    return torch.optim.AdamW(trainable_parameters, lr=learning_rate, weight_decay=weight_decay)



@dataclass(frozen=True)
class TrainingSettings:
    """Bounded per-session settings; these do not authorize training.

    The wall-time cap is best-effort: it is checked between batches and before
    optimizer steps, and cannot interrupt an individual PyTorch operation.
    """
    max_steps: int = 1
    gradient_accumulation_steps: int = 1
    gradient_clip_norm: float = 1.0
    max_seconds: int = 3600
    write_memory: bool = False
    seed: int = 0
    deterministic: bool = False

    def __post_init__(self):
        if isinstance(self.max_steps, bool) or not isinstance(self.max_steps, int) or not 1 <= self.max_steps <= 1000:
            raise ValueError("max_steps must be an integer in [1, 1000]")
        if (isinstance(self.gradient_accumulation_steps, bool)
                or not isinstance(self.gradient_accumulation_steps, int)
                or not 1 <= self.gradient_accumulation_steps <= 128):
            raise ValueError("gradient_accumulation_steps must be an integer in [1, 128]")
        if (isinstance(self.gradient_clip_norm, bool)
                or not isinstance(self.gradient_clip_norm, (int, float))
                or not math.isfinite(self.gradient_clip_norm) or self.gradient_clip_norm <= 0):
            raise ValueError("gradient_clip_norm must be finite and positive")
        if isinstance(self.max_seconds, bool) or not isinstance(self.max_seconds, int) or not 1 <= self.max_seconds <= 3600:
            raise ValueError("max_seconds must be an integer in [1, 3600]")
        if not isinstance(self.write_memory, bool):
            raise TypeError("write_memory must be boolean")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or not 0 <= self.seed < 2**63:
            raise ValueError("seed must be an integer in [0, 2**63)")
        if not isinstance(self.deterministic, bool):
            raise TypeError("deterministic must be boolean")


def run_training_steps(model, batches, optimizer, preflight_report, *, settings,
                       training_authorized=False, scheduler=None,
                       checkpoint_callback=None, cancellation_check=None,
                       resume_metadata=None, initial_data_state=None, sampler=None):
    """Run bounded local training after explicit authorization.

    If a resumable sampler is supplied, it must be attached to a DataLoader
    with num_workers=0. The controller restores sampler state before creating
    the DataLoader iterator and saves sampler state with checkpoint metadata.
    """
    if training_authorized is not True:
        raise PermissionError("explicit training authorization is required")
    if not isinstance(settings, TrainingSettings):
        raise TypeError("settings must be TrainingSettings")
    if settings.write_memory:
        raise NotImplementedError(
            "memory-writing training requires sequential chunk semantics; "
            "the current controller treats each batch as independent and resets memory"
        )
    if not isinstance(preflight_report, dict) or preflight_report.get("validated") is not True:
        raise ValueError("a successful preflight report is required")
    if preflight_report.get("status") != "PREFLIGHT_ONLY":
        raise ValueError("preflight report status must be PREFLIGHT_ONLY")
    if (preflight_report.get("training_authorized") is not False
            or preflight_report.get("optimizer_steps") != 0
            or preflight_report.get("remote_execution_enabled") is not False):
        raise ValueError("preflight report must be non-authorizing and local-only")

    count = preflight_report.get("trainable_parameter_count", preflight_report.get("parameter_count"))
    if isinstance(count, bool) or not isinstance(count, int) or count < 40_000_000:
        raise ValueError("preflight model must meet the 40M trainable parameter minimum")
    if preflight_report.get("parameter_count") != count:
        raise ValueError("preflight parameter_count must equal trainable_parameter_count")
    total_count = preflight_report.get("total_parameter_count")
    if isinstance(total_count, bool) or not isinstance(total_count, int) or total_count < count:
        raise ValueError("preflight total_parameter_count is invalid")

    planned_batch = preflight_report.get("batch_size")
    planned_sequence = preflight_report.get("sequence_length")
    planned_accumulation = preflight_report.get("gradient_accumulation_steps")
    for name, value in (("batch_size", planned_batch), ("sequence_length", planned_sequence),
                         ("gradient_accumulation_steps", planned_accumulation)):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"preflight {name} is invalid")
    if planned_sequence < 2 or settings.gradient_accumulation_steps != planned_accumulation:
        raise ValueError("training accumulation/sequence plan does not match preflight")

    dataset_hash = preflight_report.get("dataset_manifest_sha256")
    if not isinstance(dataset_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", dataset_hash):
        raise ValueError("training requires a verified dataset manifest SHA-256 in preflight")

    if resume_metadata is not None:
        if not isinstance(resume_metadata, dict):
            raise TypeError("resume_metadata must be checkpoint load metadata")
        if ((isinstance(resume_metadata.get("format_version"), bool)
                or not isinstance(resume_metadata.get("format_version"), int)
                or resume_metadata.get("format_version") < 3)
                or resume_metadata.get("rng_restored") is not True
                or not isinstance(resume_metadata.get("data_state"), dict)):
            raise ValueError("resume checkpoint must include restored RNG and data cursor state")
        resume_cursor = resume_metadata["data_state"]
        if "epoch" not in resume_cursor or "next_batch_index" not in resume_cursor:
            raise ValueError("resume checkpoint data_state must include epoch and next_batch_index")
        if resume_metadata.get("dataset_manifest_sha256") != dataset_hash:
            raise ValueError("resume checkpoint dataset manifest does not match preflight")
        saved_seed = resume_cursor.get("seed")
        if (isinstance(saved_seed, bool) or not isinstance(saved_seed, int)
                or saved_seed != settings.seed):
            raise ValueError("resume checkpoint seed does not match training settings")
        saved_accumulation = resume_cursor.get("gradient_accumulation_steps")
        if (isinstance(saved_accumulation, bool) or not isinstance(saved_accumulation, int)
                or saved_accumulation != settings.gradient_accumulation_steps):
            raise ValueError("resume checkpoint accumulation does not match training settings")
        resume_step = resume_metadata.get("step")
        if isinstance(resume_step, bool) or not isinstance(resume_step, int) or resume_step < 0:
            raise ValueError("resume checkpoint global step is invalid")
        if initial_data_state is not None and initial_data_state != resume_metadata["data_state"]:
            raise ValueError("initial_data_state must match checkpoint resume cursor")
        cursor = dict(resume_cursor)
        global_step = resume_step
    else:
        if initial_data_state is not None and not isinstance(initial_data_state, dict):
            raise TypeError("initial_data_state must be a dictionary or None")
        cursor = dict(initial_data_state or {})
        global_step = 0

    epoch = cursor.get("epoch", 0)
    next_batch_index = cursor.get("next_batch_index", 0)
    if (isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0
            or isinstance(next_batch_index, bool) or not isinstance(next_batch_index, int)
            or next_batch_index < 0):
        raise ValueError("data cursor epoch/next_batch_index must be non-negative integers")
    cursor["epoch"] = epoch
    cursor["next_batch_index"] = next_batch_index

    committed_sampler_state = None
    if sampler is not None:
        if not callable(getattr(sampler, "state_dict", None)) or not callable(getattr(sampler, "load_state_dict", None)):
            raise TypeError("sampler must provide state_dict() and load_state_dict()")
        if getattr(batches, "sampler", None) is not sampler:
            raise ValueError("sampler must be the DataLoader sampler used by batches")
        workers = getattr(batches, "num_workers", None)
        if isinstance(workers, bool) or not isinstance(workers, int) or workers != 0:
            raise ValueError("resumable sampler requires DataLoader num_workers=0")
        sampler_state = cursor.get("sampler_state")
        if resume_metadata is not None and not isinstance(sampler_state, dict):
            raise ValueError("resume checkpoint is missing sampler_state")
        if isinstance(sampler_state, dict):
            sampler.load_state_dict(sampler_state)
        live_sampler_state = sampler.state_dict()
        if (live_sampler_state.get("dataset_manifest_sha256") != dataset_hash
                or live_sampler_state.get("seed") != settings.seed
                or live_sampler_state.get("epoch") != epoch):
            raise ValueError("sampler state does not match training dataset, seed, or epoch")
        committed_sampler_state = copy.deepcopy(live_sampler_state)

    budget = preflight_report.get("memory_budget_bytes")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        raise ValueError("training requires a positive preflight memory budget")
    if preflight_report.get("budget_covers_persistent_state") is not True:
        raise MemoryError("preflight memory budget does not cover persistent model state")

    config = getattr(model, "config", None)
    if isinstance(config, NeuroSparseConfig):
        if count_parameters(config) != count:
            raise ValueError("preflight trainable parameter count does not match model config")
        from .config import count_total_parameters
        if count_total_parameters(config) != total_count:
            raise ValueError("preflight total parameter count does not match model config")
    reset_memory = getattr(model, "reset_memory", None)
    if not callable(reset_memory):
        raise ValueError("model must implement reset_memory() for example isolation")
    if not callable(getattr(model, "train", None)):
        raise TypeError("model must provide train()")
    if not callable(getattr(optimizer, "step", None)) or not callable(getattr(optimizer, "zero_grad", None)):
        raise TypeError("optimizer must provide step() and zero_grad()")
    if scheduler is not None and not callable(getattr(scheduler, "step", None)):
        raise TypeError("scheduler must provide step()")
    if checkpoint_callback is not None and not callable(checkpoint_callback):
        raise TypeError("checkpoint_callback must be callable")
    if cancellation_check is not None and not callable(cancellation_check):
        raise TypeError("cancellation_check must be callable")

    if resume_metadata is None:
        seed_training_rng(settings.seed, deterministic=settings.deterministic)
    previous_training_mode = getattr(model, "training", None)
    model.train()
    optimizer.zero_grad(set_to_none=True)
    started = time.monotonic()
    session_steps, accumulated, microbatches_seen = 0, 0, 0
    losses = []
    stop_reason = "dataset_exhausted"

    def time_expired():
        return time.monotonic() - started >= settings.max_seconds

    try:
        for batch in batches:
            if cancellation_check is not None and cancellation_check():
                stop_reason = "cancelled"
                break
            if time_expired():
                stop_reason = "time_limit"
                break
            if not isinstance(batch, dict) or not isinstance(batch.get("input_ids"), torch.Tensor):
                raise TypeError("batch must contain tensor input_ids")
            ids, mask = batch["input_ids"], batch.get("attention_mask")
            if ids.ndim != 2 or ids.shape[0] == 0 or ids.shape[1] < 2:
                raise ValueError("input_ids must be a non-empty [batch, sequence] tensor with sequence >= 2")
            if ids.shape[0] > planned_batch or ids.shape[1] > planned_sequence:
                raise ValueError("batch exceeds the preflight batch/sequence resource plan")

            reset_memory()
            try:
                output = model(ids, write_memory=False, attention_mask=mask)
                if not isinstance(output, dict) or not isinstance(output.get("logits"), torch.Tensor):
                    raise ValueError("model output must contain logits")
                loss = causal_language_model_loss(
                    output["logits"], ids, load_balance=output.get("load_balance_loss"),
                    prediction_error=output.get("prediction_error"))
                if not bool(torch.isfinite(loss)):
                    raise FloatingPointError("training loss is non-finite")
                if time_expired():
                    stop_reason = "time_limit"
                    break
                (loss / settings.gradient_accumulation_steps).backward()
                accumulated += 1
                microbatches_seen += 1
                losses.append(float(loss.detach().cpu()))
            finally:
                reset_memory()

            if accumulated == settings.gradient_accumulation_steps:
                parameters = [p for p in model.parameters() if p.grad is not None]
                if parameters:
                    norm = torch.nn.utils.clip_grad_norm_(parameters, settings.gradient_clip_norm)
                    if not bool(torch.isfinite(norm)):
                        raise FloatingPointError("gradient norm is non-finite")
                    if any(not bool(torch.isfinite(p.grad).all()) for p in parameters):
                        raise FloatingPointError("gradient contains non-finite values")
                if cancellation_check is not None and cancellation_check():
                    stop_reason = "cancelled"
                    break
                if time_expired():
                    stop_reason = "time_limit"
                    break
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()
                session_steps += 1
                global_step += 1
                optimizer.zero_grad(set_to_none=True)
                accumulated = 0
                if sampler is not None:
                    committed_sampler_state = copy.deepcopy(sampler.state_dict())
                if checkpoint_callback is not None:
                    mean_loss = sum(losses[-settings.gradient_accumulation_steps:]) / settings.gradient_accumulation_steps
                    checkpoint_data_state = dict(cursor)
                    checkpoint_data_state.update({
                        "epoch": epoch,
                        "next_batch_index": next_batch_index + microbatches_seen,
                        "seed": settings.seed,
                        "gradient_accumulation_steps": settings.gradient_accumulation_steps,
                    })
                    if committed_sampler_state is not None:
                        checkpoint_data_state["sampler_state"] = copy.deepcopy(committed_sampler_state)
                    checkpoint_callback(global_step, {
                        "mean_loss": mean_loss,
                        "data_state": checkpoint_data_state,
                        "dataset_manifest_sha256": dataset_hash,
                    })
                if session_steps >= settings.max_steps:
                    stop_reason = "step_limit"
                    break
    finally:
        reset_memory()
        optimizer.zero_grad(set_to_none=True)
        if isinstance(previous_training_mode, bool):
            model.train(previous_training_mode)

    # Only batches included in completed optimizer steps are committed. If the
    # final accumulation group is discarded, rewind the cursor so resume replays it.
    committed_microbatches = microbatches_seen - accumulated
    if sampler is not None:
        if accumulated and committed_sampler_state is not None:
            sampler.load_state_dict(committed_sampler_state)
        final_sampler_state = copy.deepcopy(sampler.state_dict())
    else:
        final_sampler_state = None
    final_data_state = dict(cursor)
    final_data_state.update({
        "epoch": epoch,
        "next_batch_index": next_batch_index + committed_microbatches,
        "seed": settings.seed,
        "gradient_accumulation_steps": settings.gradient_accumulation_steps,
    })
    if final_sampler_state is not None:
        final_data_state["sampler_state"] = final_sampler_state
    return {
        "steps_completed": session_steps,
        "global_step": global_step,
        "microbatches_seen": microbatches_seen,
        "discarded_microbatches": accumulated,
        "mean_loss": sum(losses) / len(losses) if losses else None,
        "stop_reason": stop_reason,
        "data_state": final_data_state,
        "dataset_manifest_sha256": dataset_hash,
        "training_authorized": True,
        "remote_execution_enabled": False,
        "resource_monitoring": "preflight_budget_only",
        "resumed_from_checkpoint": resume_metadata is not None,
    }

def seed_training_rng(seed: int, *, deterministic: bool = False) -> dict:
    """Seed Python, Torch CPU/CUDA and deterministic backend settings."""
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
        raise ValueError("seed must be an integer in [0, 2**63)")
    if not isinstance(deterministic, bool):
        raise TypeError("deterministic must be boolean")
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(deterministic)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.deterministic = deterministic
        torch.backends.cudnn.benchmark = not deterministic
    return {"seed": seed, "deterministic_algorithms": deterministic}


def make_seeded_generator(seed: int) -> torch.Generator:
    """Return a dedicated CPU generator for deterministic DataLoader shuffling."""
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
        raise ValueError("seed must be an integer in [0, 2**63)")
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    return generator
