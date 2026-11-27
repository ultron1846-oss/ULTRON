import copy
import math
import random
import statistics
import re
import time
from dataclasses import dataclass

from .config import MIN_FOUNDATION_TRAINABLE_PARAMETERS, NeuroSparseConfig, count_parameters
from .resumable_sampler import ResumableRandomSampler
import torch
from torch.nn import functional as F

from .precision import training_autocast, validate_training_precision
from .resource_monitor import RuntimeMemoryMonitor


def causal_language_model_loss(logits: torch.Tensor, input_ids: torch.Tensor,
        load_balance: torch.Tensor | None = None, prediction_error: torch.Tensor | None = None,
        balance_weight: float = 0.01, prediction_weight: float = 0.01,
        ignore_index: int | None = 0, loss_chunk_size: int = 1024) -> torch.Tensor:
    """Causal next-token loss with chunked FP32 CE to bound temporary memory.

    Logits are processed per batch row and token chunk. This avoids creating a
    full flattened FP32 copy of [B,T,V] when logits were produced in BF16/FP16.
    Chunked reductions preserve the global token mean, including padding masks.
    """
    if logits.ndim != 3 or input_ids.ndim != 2:
        raise ValueError('expected logits [B,T,V] and input_ids [B,T]')
    if logits.shape[:2] != input_ids.shape:
        raise ValueError('logits/input_ids sequence dimensions must match')
    if input_ids.shape[0] == 0 or input_ids.shape[1] < 2:
        raise ValueError('batch must be non-empty and sequence length must be at least 2')
    if isinstance(loss_chunk_size, bool) or not isinstance(loss_chunk_size, int) or loss_chunk_size < 1:
        raise ValueError('loss_chunk_size must be a positive integer')
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

    targets = input_ids[:, 1:].long()
    if ignore_index is None:
        valid_count = targets.numel()
    else:
        valid_targets = targets.ne(ignore_index)
        if not bool(valid_targets.any()):
            raise ValueError('all next-token targets are padding; loss is undefined')
        valid_count = valid_targets.sum().clamp_min(1)

    loss_sum = None
    time_steps = targets.shape[1]
    for batch_index in range(input_ids.shape[0]):
        for start in range(0, time_steps, loss_chunk_size):
            end = min(start + loss_chunk_size, time_steps)
            chunk_logits = logits[batch_index, start:end, :].float()
            chunk_targets = targets[batch_index, start:end]
            if ignore_index is None:
                chunk_sum = F.cross_entropy(chunk_logits, chunk_targets, reduction='sum')
            else:
                chunk_sum = F.cross_entropy(
                    chunk_logits, chunk_targets, ignore_index=ignore_index, reduction='sum'
                )
            loss_sum = chunk_sum if loss_sum is None else loss_sum + chunk_sum
    loss = loss_sum / valid_count
    if load_balance is not None:
        loss = loss + balance_weight * load_balance
    if prediction_error is not None:
        loss = loss + prediction_weight * prediction_error
    return loss


def make_optimizer(model: torch.nn.Module, learning_rate: float = 3e-4,
                   weight_decay: float = 0.01, fused: bool | None = None):
    """Create AdamW; automatically use its fused CUDA implementation when safe.

    Set fused=False for a portable reference optimizer. fused=True requires all
    trainable parameters on one CUDA device. Automatic mode falls back to the
    standard implementation if the installed PyTorch build rejects fused mode.
    """
    if (isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float))
            or not math.isfinite(learning_rate) or learning_rate <= 0):
        raise ValueError('learning_rate must be a finite positive number')
    if (isinstance(weight_decay, bool) or not isinstance(weight_decay, (int, float))
            or not math.isfinite(weight_decay) or weight_decay < 0):
        raise ValueError('weight_decay must be a finite non-negative number')
    if fused is not None and not isinstance(fused, bool):
        raise TypeError('fused must be boolean or None')
    trainable_parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    if not trainable_parameters:
        raise ValueError("model has no trainable parameters")
    devices = {parameter.device for parameter in trainable_parameters}
    one_cuda_device = len(devices) == 1 and next(iter(devices)).type == 'cuda'
    use_fused = one_cuda_device if fused is None else fused
    if use_fused and not one_cuda_device:
        raise ValueError('fused AdamW requires trainable parameters on one CUDA device')
    if use_fused:
        try:
            return torch.optim.AdamW(
                trainable_parameters, lr=learning_rate, weight_decay=weight_decay, fused=True
            )
        except (TypeError, RuntimeError, ValueError):
            if fused is True:
                raise
            # Keep automatic mode portable across older/custom PyTorch builds.
    return torch.optim.AdamW(trainable_parameters, lr=learning_rate, weight_decay=weight_decay)


def _validate_optimizer_parameter_coverage(model_parameters, optimizer) -> None:
    """Require optimizer groups to contain every trainable model parameter once.

    A preflight report and matching model are not sufficient if the supplied
    optimizer silently omits trainable parameters or updates unrelated tensors.
    """
    parameter_groups = getattr(optimizer, "param_groups", None)
    if not isinstance(parameter_groups, list) or not parameter_groups:
        raise TypeError("optimizer must expose non-empty param_groups")

    expected = {
        id(parameter)
        for parameter in model_parameters
        if parameter.requires_grad
    }
    selected = {}
    for group_index, group in enumerate(parameter_groups):
        if not isinstance(group, dict):
            raise TypeError(f"optimizer param_groups[{group_index}] must be a dictionary")
        parameters = group.get("params")
        if not isinstance(parameters, (list, tuple)):
            raise TypeError(
                f"optimizer param_groups[{group_index}].params must be a list or tuple"
            )
        for parameter in parameters:
            if not isinstance(parameter, torch.Tensor):
                raise TypeError("optimizer parameter groups may contain only tensors")
            identity = id(parameter)
            if identity in selected:
                raise ValueError("optimizer contains a duplicate model parameter")
            selected[identity] = parameter

    missing = expected.difference(selected)
    unexpected = set(selected).difference(expected)
    if missing or unexpected:
        raise ValueError(
            "optimizer parameters must match the model's trainable parameter set "
            f"(missing={len(missing)}, unexpected={len(unexpected)})"
        )



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
    precision: str = "fp32"
    profile_performance: bool = False
    activation_checkpointing: bool = False

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
        validate_training_precision(self.precision)
        if not isinstance(self.profile_performance, bool):
            raise TypeError("profile_performance must be boolean")
        if not isinstance(self.activation_checkpointing, bool):
            raise TypeError("activation_checkpointing must be boolean")


def run_training_steps(model, batches, optimizer, preflight_report, *, settings,
                       training_authorized=False, scheduler=None,
                       checkpoint_callback=None, cancellation_check=None,
                       resume_metadata=None, initial_data_state=None, sampler=None, memory_monitor=None):
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
    if (isinstance(count, bool) or not isinstance(count, int)
            or count < MIN_FOUNDATION_TRAINABLE_PARAMETERS):
        raise ValueError(
            "preflight model must meet the "
            f"{MIN_FOUNDATION_TRAINABLE_PARAMETERS:,} trainable parameter minimum"
        )
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
    split_counts = preflight_report.get("split_counts")
    if (not isinstance(split_counts, dict) or isinstance(split_counts.get("train"), bool)
            or not isinstance(split_counts.get("train"), int) or split_counts.get("train") <= 0):
        raise ValueError("preflight must include a valid training split size")
    train_size = split_counts["train"]

    if resume_metadata is not None:
        if not isinstance(resume_metadata, dict):
            raise TypeError("resume_metadata must be checkpoint load metadata")
        if ((isinstance(resume_metadata.get("format_version"), bool)
                or not isinstance(resume_metadata.get("format_version"), int)
                or resume_metadata.get("format_version") < 3)
                or resume_metadata.get("rng_restored") is not True
                or not isinstance(resume_metadata.get("data_state"), dict)):
            raise ValueError("resume checkpoint must include restored RNG and data cursor state")
        if resume_metadata.get("dataset_hash_verified") is not True:
            raise ValueError("resume checkpoint dataset manifest hash was not verified")
        saved_training_settings = resume_metadata.get("training_settings")
        if saved_training_settings is None:
            if settings.precision != "fp32":
                raise ValueError(
                    "resume checkpoint lacks precision metadata; cannot safely resume BF16"
                )
        elif (not isinstance(saved_training_settings, dict)
                or saved_training_settings.get("precision", "fp32") != settings.precision):
            raise ValueError("resume checkpoint precision does not match training settings")
        if isinstance(saved_training_settings, dict):
            if saved_training_settings.get("deterministic", settings.deterministic) != settings.deterministic:
                raise ValueError("resume checkpoint deterministic setting does not match")
        resume_cursor = resume_metadata["data_state"]
        if "epoch" not in resume_cursor or "next_batch_index" not in resume_cursor:
            raise ValueError("resume checkpoint data_state must include epoch and next_batch_index")
        if resume_metadata.get("dataset_manifest_sha256") != dataset_hash:
            raise ValueError("resume checkpoint dataset manifest does not match preflight")
        if resume_cursor.get("dataset_manifest_sha256") != dataset_hash:
            raise ValueError("resume data cursor dataset manifest does not match preflight")
        if resume_cursor.get("dataset_size") != train_size:
            raise ValueError("resume data cursor dataset size does not match preflight train split")
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
        if (resume_metadata.get("optimizer_state_present") is not True
                or resume_metadata.get("optimizer_restored") is not True):
            raise ValueError("resume checkpoint optimizer state was not restored")
        scheduler_state_present = resume_metadata.get("scheduler_state_present")
        scheduler_restored = resume_metadata.get("scheduler_restored")
        if type(scheduler_state_present) is not bool or type(scheduler_restored) is not bool:
            raise ValueError("resume checkpoint scheduler restoration metadata is malformed")
        if scheduler_state_present:
            if scheduler is None or scheduler_restored is not True:
                raise ValueError("resume checkpoint scheduler state was not restored")
        elif scheduler is not None or scheduler_restored is not False:
            raise ValueError("resume checkpoint does not contain scheduler state")
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
    if cursor.get("dataset_manifest_sha256", dataset_hash) != dataset_hash:
        raise ValueError("data cursor dataset manifest hash does not match preflight")
    if cursor.get("dataset_size", train_size) != train_size:
        raise ValueError("data cursor dataset size does not match preflight train split")
    cursor["epoch"] = epoch
    cursor["next_batch_index"] = next_batch_index
    cursor["dataset_manifest_sha256"] = dataset_hash
    cursor["dataset_size"] = train_size

    committed_sampler_state = None
    if (checkpoint_callback is not None or resume_metadata is not None) and sampler is None:
        raise ValueError("checkpointing/resume requires a ResumableRandomSampler")
    if sampler is not None:
        if not isinstance(sampler, ResumableRandomSampler):
            raise TypeError("sampler must be ResumableRandomSampler")
        if getattr(batches, "sampler", None) is not sampler:
            raise ValueError("sampler must be the DataLoader sampler used by batches")
        workers = getattr(batches, "num_workers", None)
        if isinstance(workers, bool) or not isinstance(workers, int) or workers != 0:
            raise ValueError("resumable sampler requires DataLoader num_workers=0")
        loader_batch_size = getattr(batches, "batch_size", None)
        if (isinstance(loader_batch_size, bool) or not isinstance(loader_batch_size, int)
                or loader_batch_size != planned_batch):
            raise ValueError("DataLoader batch_size must match the preflight batch size")
        if getattr(batches, "drop_last", False) is not False:
            raise ValueError("resumable sampler requires DataLoader drop_last=False")
        if len(sampler.data_source) != train_size:
            raise ValueError("sampler dataset size does not match preflight train split")
        loader_dataset = getattr(batches, "dataset", None)
        if loader_dataset is None or len(loader_dataset) != train_size:
            raise ValueError("DataLoader dataset size does not match preflight train split")
        sampler_state = cursor.get("sampler_state")
        if resume_metadata is not None and not isinstance(sampler_state, dict):
            raise ValueError("resume checkpoint is missing sampler_state")
        if sampler_state is None and (
                epoch != 0 or next_batch_index != 0
                or sampler.state_dict().get("next_index") != 0):
            raise ValueError("non-zero initial cursor requires sampler_state")
        if isinstance(sampler_state, dict):
            sampler.load_state_dict(sampler_state)
        live_sampler_state = sampler.state_dict()
        if (live_sampler_state.get("dataset_manifest_sha256") != dataset_hash
                or live_sampler_state.get("seed") != settings.seed
                or live_sampler_state.get("epoch") != epoch):
            raise ValueError("sampler state does not match training dataset, seed, or epoch")
        expected_sample_cursor = min(next_batch_index * planned_batch, split_counts["train"])
        if live_sampler_state.get("next_index") != expected_sample_cursor:
            raise ValueError("sampler sample cursor does not match next_batch_index and preflight batch size")
        committed_sampler_state = copy.deepcopy(live_sampler_state)

    budget = preflight_report.get("memory_budget_bytes")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        raise ValueError("training requires a positive preflight memory budget")
    if preflight_report.get("budget_covers_persistent_state") is not True:
        raise MemoryError("preflight memory budget does not cover persistent model state")
    if memory_monitor is None:
        memory_monitor = RuntimeMemoryMonitor(budget)
    elif not isinstance(memory_monitor, RuntimeMemoryMonitor):
        raise TypeError("memory_monitor must be RuntimeMemoryMonitor or None")
    elif memory_monitor.budget_bytes != budget:
        raise ValueError("runtime memory monitor budget must match preflight memory_budget_bytes")

    config = getattr(model, "config", None)
    if isinstance(config, NeuroSparseConfig):
        if count_parameters(config) != count:
            raise ValueError("preflight trainable parameter count does not match model config")
        from .config import count_total_parameters
        if count_total_parameters(config) != total_count:
            raise ValueError("preflight total parameter count does not match model config")

    parameter_iterator = getattr(model, "parameters", None)
    if not callable(parameter_iterator):
        raise TypeError("model must expose parameters() for parameter-count validation")
    model_parameters = tuple(parameter_iterator())
    if not model_parameters or any(not isinstance(parameter, torch.Tensor)
                                    for parameter in model_parameters):
        raise ValueError("model parameters are missing or malformed")
    actual_trainable_count = sum(
        parameter.numel() for parameter in model_parameters if parameter.requires_grad
    )
    actual_total_count = sum(parameter.numel() for parameter in model_parameters)
    if actual_trainable_count != count:
        raise ValueError(
            "actual model trainable parameter count does not match preflight report"
        )
    if actual_total_count != total_count:
        raise ValueError(
            "actual model total parameter count does not match preflight report"
        )
    _validate_optimizer_parameter_coverage(model_parameters, optimizer)
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
    checkpointing_setter = getattr(model, "set_activation_checkpointing", None)
    previous_activation_checkpointing = getattr(model, "activation_checkpointing", None)
    if callable(checkpointing_setter):
        checkpointing_setter(settings.activation_checkpointing)
    elif settings.activation_checkpointing:
        raise NotImplementedError("model does not support activation checkpointing")
    model.train()
    optimizer.zero_grad(set_to_none=True)
    started = time.monotonic()
    session_steps, accumulated, microbatches_seen = 0, 0, 0
    loss_sum = None
    loss_count = 0
    recent_losses = []
    stop_reason = "dataset_exhausted"
    performance_tokens = 0
    performance_elapsed = 0.0
    performance_step_seconds = []
    performance_peak_cuda_memory_bytes = None
    step_profile_started = None
    step_profile_tokens = 0
    profile_device = None

    def time_expired():
        return time.monotonic() - started >= settings.max_seconds

    try:
        memory_monitor.check("before_training")
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

            if settings.profile_performance:
                profile_device = ids.device
                if ids.device.type == "cuda":
                    torch.cuda.synchronize(ids.device)
                    if accumulated == 0:
                        torch.cuda.reset_peak_memory_stats(ids.device)
                if accumulated == 0:
                    step_profile_started = time.perf_counter()
                    step_profile_tokens = 0
                if mask is not None:
                    if not isinstance(mask, torch.Tensor) or mask.shape != ids.shape:
                        raise ValueError("attention_mask must match input_ids when profiling")
                    step_profile_tokens += int(mask[:, 1:].sum().detach().cpu())
                else:
                    step_profile_tokens += max(0, ids.numel() - ids.shape[0])
            memory_monitor.check("before_batch", device=ids.device)
            reset_memory()
            try:
                # BF16 is opt-in; loss accumulation remains FP32 for stability.
                with training_autocast(ids.device, settings.precision):
                    output = model(ids, write_memory=False, attention_mask=mask)
                    if not isinstance(output, dict) or not isinstance(output.get("logits"), torch.Tensor):
                        raise ValueError("model output must contain logits")
                    loss = causal_language_model_loss(
                        output["logits"], ids, load_balance=output.get("load_balance_loss"),
                        prediction_error=output.get("prediction_error"))
                if time_expired():
                    stop_reason = "time_limit"
                    break
                (loss / settings.gradient_accumulation_steps).backward()
                memory_monitor.check("after_backward", device=ids.device)
                if settings.profile_performance and ids.device.type == "cuda":
                    torch.cuda.synchronize(ids.device)
                accumulated += 1
                microbatches_seen += 1
                # Keep scalar metrics on-device. Copying every microbatch loss to
                # Python forces a CUDA synchronization; defer it to the optimizer
                # boundary (and final summary) instead.
                detached_loss = loss.detach()
                recent_losses.append(detached_loss)
                loss_sum = detached_loss if loss_sum is None else loss_sum + detached_loss
                loss_count += 1
            finally:
                reset_memory()

            if accumulated == settings.gradient_accumulation_steps:
                parameters = [p for p in model.parameters() if p.grad is not None]
                norm = None
                if parameters:
                    norm = torch.nn.utils.clip_grad_norm_(
                        parameters, settings.gradient_clip_norm
                    )

                # Validate losses and the global gradient norm together. A
                # single small device-to-host transfer replaces separate
                # per-loss and per-parameter synchronization points.
                loss_finite = torch.stack([
                    torch.isfinite(value) for value in recent_losses
                ]).all()
                if norm is None:
                    checks = [bool(loss_finite.detach().cpu().item())]
                    if not checks[0]:
                        raise FloatingPointError("training loss is non-finite")
                else:
                    checks = torch.stack((loss_finite, torch.isfinite(norm))).detach().cpu().tolist()
                    if not checks[0]:
                        raise FloatingPointError("training loss is non-finite")
                    if not checks[1]:
                        raise FloatingPointError("gradient norm is non-finite")
                if cancellation_check is not None and cancellation_check():
                    stop_reason = "cancelled"
                    break
                if time_expired():
                    stop_reason = "time_limit"
                    break
                memory_monitor.check("before_optimizer_step", device=profile_device or ids.device)
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()
                # AdamW may allocate moment tensors on its first step. If this
                # sample exceeds budget, finish accounting and checkpoint the
                # completed step before stopping; never lose its cursor silently.
                memory_limit_reached = False
                try:
                    memory_monitor.check("after_optimizer_step", device=profile_device or ids.device)
                except MemoryError:
                    memory_limit_reached = True
                    stop_reason = "memory_budget"
                if settings.profile_performance:
                    if profile_device.type == "cuda":
                        torch.cuda.synchronize(profile_device)
                        peak = int(torch.cuda.max_memory_allocated(profile_device))
                        performance_peak_cuda_memory_bytes = (
                            peak if performance_peak_cuda_memory_bytes is None
                            else max(performance_peak_cuda_memory_bytes, peak)
                        )
                    step_elapsed = max(0.0, time.perf_counter() - step_profile_started)
                    performance_elapsed += step_elapsed
                    performance_tokens += step_profile_tokens
                    performance_step_seconds.append(step_elapsed)
                session_steps += 1
                global_step += 1
                optimizer.zero_grad(set_to_none=True)
                accumulated = 0
                if sampler is not None:
                    committed_sampler_state = copy.deepcopy(sampler.state_dict())
                if checkpoint_callback is not None:
                    mean_loss = torch.stack(recent_losses).mean().item()
                    checkpoint_data_state = dict(cursor)
                    checkpoint_training_settings = {
                        "precision": settings.precision,
                        "seed": settings.seed,
                        "gradient_accumulation_steps": settings.gradient_accumulation_steps,
                        "deterministic": settings.deterministic,
                        "profile_performance": settings.profile_performance,
                        "activation_checkpointing": settings.activation_checkpointing,
                    }
                    checkpoint_data_state.update({
                        "epoch": epoch,
                        "next_batch_index": next_batch_index + microbatches_seen,
                        "dataset_manifest_sha256": dataset_hash,
                        "dataset_size": train_size,
                        "seed": settings.seed,
                        "gradient_accumulation_steps": settings.gradient_accumulation_steps,
                        "training_settings": checkpoint_training_settings,
                    })
                    if committed_sampler_state is not None:
                        checkpoint_data_state["next_sample_index"] = committed_sampler_state["next_index"]
                        checkpoint_data_state["sampler_state"] = copy.deepcopy(committed_sampler_state)
                    checkpoint_callback(global_step, {
                        "mean_loss": mean_loss,
                        "data_state": checkpoint_data_state,
                        "dataset_manifest_sha256": dataset_hash,
                        "training_settings": checkpoint_training_settings,
                    })
                    try:
                        memory_monitor.check("after_checkpoint", device=profile_device or ids.device)
                    except MemoryError:
                        memory_limit_reached = True
                        stop_reason = "memory_budget"
                recent_losses.clear()
                if memory_limit_reached:
                    break
                if session_steps >= settings.max_steps:
                    stop_reason = "step_limit"
                    break
    finally:
        reset_memory()
        optimizer.zero_grad(set_to_none=True)
        if callable(checkpointing_setter) and isinstance(previous_activation_checkpointing, bool):
            checkpointing_setter(previous_activation_checkpointing)
        if isinstance(previous_training_mode, bool):
            model.train(previous_training_mode)

    # Only batches included in completed optimizer steps are committed. If the
    # final accumulation group is discarded, rewind the cursor so resume replays it.
    committed_microbatches = microbatches_seen - accumulated
    if sampler is not None:
        if committed_sampler_state is not None:
            current_sampler_state = sampler.state_dict()
            if current_sampler_state.get("next_index") != committed_sampler_state.get("next_index"):
                sampler.load_state_dict(committed_sampler_state)
        final_sampler_state = copy.deepcopy(sampler.state_dict())
    else:
        final_sampler_state = None
    final_data_state = dict(cursor)
    final_data_state.update({
        "epoch": epoch,
        "next_batch_index": next_batch_index + committed_microbatches,
        "dataset_manifest_sha256": dataset_hash,
        "dataset_size": train_size,
        "seed": settings.seed,
        "gradient_accumulation_steps": settings.gradient_accumulation_steps,
    })
    if final_sampler_state is not None:
        expected_final_sample_cursor = min(
            (next_batch_index + committed_microbatches) * planned_batch, train_size
        )
        if final_sampler_state.get("next_index") != expected_final_sample_cursor:
            raise ValueError("final sampler cursor does not match committed batch cursor")
        final_data_state["next_sample_index"] = final_sampler_state["next_index"]
        final_data_state["sampler_state"] = final_sampler_state
    return {
        "steps_completed": session_steps,
        "global_step": global_step,
        "microbatches_seen": microbatches_seen,
        "discarded_microbatches": accumulated,
        "mean_loss": loss_sum.item() / loss_count if loss_count else None,
        "stop_reason": stop_reason,
        "data_state": final_data_state,
        "dataset_manifest_sha256": dataset_hash,
        "training_authorized": True,
        "remote_execution_enabled": False,
        "resource_monitoring": "process_rss_plus_cuda_reserved_at_controller_boundaries",
        "resource_memory": memory_monitor.summary(),
        "resumed_from_checkpoint": resume_metadata is not None,
        "performance": ({
            "profiled": True,
            "completed_optimizer_steps": session_steps,
            "target_tokens": performance_tokens,
            "elapsed_seconds": performance_elapsed,
            "target_tokens_per_second": (
                performance_tokens / performance_elapsed if performance_elapsed > 0 else 0.0
            ),
            "step_seconds_median": (
                statistics.median(performance_step_seconds) if performance_step_seconds else None
            ),
            "step_seconds_p95": (
                sorted(performance_step_seconds)[min(
                    len(performance_step_seconds) - 1,
                    max(0, math.ceil(0.95 * len(performance_step_seconds)) - 1)
                )] if performance_step_seconds else None
            ),
            "peak_cuda_memory_bytes": performance_peak_cuda_memory_bytes,
            "measurement_note": "Opt-in controller timing; not a quality or comparative benchmark.",
        } if settings.profile_performance else {"profiled": False}),
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
