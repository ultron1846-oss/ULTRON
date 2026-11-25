# Phase 9 — Free runtime and operations review

**Review date:** 2026-11-25
**Budget target:** $0
**Training status:** not authorized; no provider connected and no job launched.
**Owner constraints:** iPad-first workflow; avoid providers requiring phone-number verification; no Kaggle.

## Provider findings

### Google Colab — planned primary, availability not guaranteed

Official Colab FAQ states that free-tier compute limits and hardware availability are dynamic and not guaranteed. It does not publish fixed GPU/VM lifetime limits; the FAQ says free notebooks may run for at most 12 hours depending on availability and usage, and idle timeouts apply. GPU type and access can change between sessions.

Source: [Colab FAQ — Resource Limits](https://research.google.com/colaboratory/faq.html)

Operational decision: keep Colab as the selected notebook option, but treat GPU availability, memory, and runtime lifetime as values to inspect at session start. The ULTRON website must not display a GPU as available until a live, user-authorized runtime check reports it.

### Lightning AI — excluded under current no-phone constraint

Lightning AI currently advertises up to 80 free GPU hours / up to 30 promotional credits, with one free CPU Studio that restarts every four hours. Its official pricing/support page also states that phone number verification is required to prevent abuse.

Sources:
- [Lightning AI pricing](https://lightning.ai/pricing)
- [Lightning AI pricing/support FAQ](https://support.lightning.ai/pricing/)

Operational decision: do not use unless the owner explicitly changes the no-phone constraint and confirms the current free-credit terms. Promotional credits are not a permanent $0 training guarantee.

### Hugging Face Spaces — auxiliary only

Official Spaces documentation lists a default CPU Basic environment with 2 vCPU, 16 GB RAM, and 50 GB non-persistent disk; free GPU availability is not a guaranteed default. The documentation also notes that compute-backed Gradio/Docker Spaces may require a paid plan.

Source: [Hugging Face Spaces overview](https://huggingface.co/docs/hub/spaces-overview)

Operational decision: not a dependable persistent training host. Could be considered for static demos or auxiliary CPU checks only after verifying current account and storage terms.

## Feasibility assessment

The current foundation configuration has 63,400,451 trainable parameters. The theoretical FP32 weights + gradients + two AdamW moment tensors require about 967.4 MiB before activations, attention workspace, temporary tensors, allocator overhead, input data, and checkpoint transfer. This does not prove that a free GPU/CPU session can train it.

The current project has no distributed trainer, multi-host gradient synchronization, or runtime scheduler. Several free accounts/runtimes cannot simply be combined into one larger training device. The near-term design is **single-runtime, checkpoint-resumable work**, not multi-server distributed training.

## Runtime acceptance checklist

- [ ] Start a clean Colab session from iPad browser and verify no phone-number step is required for the user's account.
- [ ] Record actual runtime type, CPU count, RAM, GPU name/VRAM, free disk, and current session limits.
- [ ] Confirm all required packages install from approved sources and no pretrained weights/API are downloaded.
- [ ] Confirm the checkpoint save/restore path survives runtime reset and file transfer.
- [ ] Run only environment/preflight checks until separate training authorization.
- [ ] Verify zero charges and no billing/credit-card activation.
- [ ] Recheck provider terms and limits at time of use; this review is a dated snapshot.

## Phase 9 exit status

Provider constraints have been researched and the operating strategy documented. Phase 9 remains **incomplete** until a clean, owner-authorized runtime acceptance test confirms actual free resources, no phone verification, zero cost, and checkpoint transfer. No training is approved.
