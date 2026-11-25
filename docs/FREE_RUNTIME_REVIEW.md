# Phase 9 — Free runtime and operations review

**Research snapshot:** 2026-11-25 UTC
**Budget target:** $0; no payment activation or purchased credits
**Training status:** not authorized; no provider connected and no job launched
**Owner constraints:** iPad-first; avoid phone-number verification; no Kaggle

This is a provider-terms review, not proof that an account currently has compute access. Recheck the official pages and the actual account/runtime before use.

## Google Colab — planned primary notebook, conditional on acceptance

Colab's official FAQ says free-tier usage limits, idle timeout, maximum VM lifetime, GPU type, and availability vary. It does not publish fixed free-tier usage limits. Free notebooks can run for at most 12 hours, depending on availability and usage patterns, and idle runtimes time out.

Source: [Colab FAQ — Resource Limits](https://research.google.com/colaboratory/faq.html)

**Decision:** keep Colab as the planned notebook, not a guaranteed server. At session start, inspect actual runtime type, CPU/RAM, GPU/VRAM, disk, session lifetime, and any verification/payment prompt. No job may launch from the website automatically.

## Lightning AI — excluded unless the owner changes the phone constraint

Current official pricing/support pages describe a free tier with one free active CPU Studio that restarts every four hours and promotional credits that may provide up to 80 GPU hours (credit amount and GPU-hour conversion vary). The official Studio onboarding says phone verification is required to receive the free GPU hours. Credits are promotional, may change, and are not a permanent $0 compute guarantee.

Sources:
- [Lightning AI pricing](https://lightning.ai/pricing)
- [Lightning AI free GPU hours and pricing FAQ](https://support.lightning.ai/pricing/)
- [Lightning AI Studio onboarding and phone verification](https://platform.lightning.ai/studio)

**Decision:** do not use under the current no-phone constraint. Do not add it as a usable training server unless the owner explicitly changes that constraint and confirms the account's current terms.

## Hugging Face Spaces — short auxiliary GPU checks only

Official Spaces documentation describes:
- Static Spaces as free.
- Default CPU Basic resources as 2 vCPU, 16 GB RAM, and 50 GB non-persistent disk; creating a new compute-backed Gradio/Docker Space generally requires a paid plan, with a free-account ZeroGPU exception.
- Eligible free personal accounts in good standing (verified email and account older than 30 days) may host up to two ZeroGPU Spaces.
- ZeroGPU is shared/dynamic GPU allocation, Gradio-only, with a free-account quota of approximately **5 GPU minutes per day**. Its current large/xlarge configurations advertise 48/96 GB GPU memory, but quota and queue availability are limiting factors.

Sources:
- [Spaces overview](https://huggingface.co/docs/hub/spaces-overview)
- [ZeroGPU documentation and daily quotas](https://huggingface.co/docs/hub/spaces-zerogpu)

**Decision:** ZeroGPU may be useful for a brief GPU compatibility or inference smoke test after verifying account eligibility. It is not a dependable long-running training host. Dedicated GPU Spaces are billed and must not be selected under the $0 requirement.

## Model resource feasibility

The proposed foundation configuration has **63,400,451 total parameters, of which 61,826,048 are trainable**. FP32 weights require 253,601,804 bytes (about 241.9 MiB). Gradients plus two AdamW moments for trainable parameters require 741,912,576 bytes (about 707.5 MiB); combined persistent state is about 949.4 MiB before activations, attention workspace, temporary tensors, allocator overhead, batches, and checkpoint transfer.

This is an arithmetic floor, not a benchmark or guarantee that any free runtime can train ULTRON. A single runtime must be evaluated independently. The repository does not implement distributed gradient synchronization or a multi-host trainer; multiple free accounts/runtimes cannot simply be pooled into one larger device.

## Runtime acceptance checklist — still pending

- [ ] Owner opens a clean Colab session from iPad and confirms whether access works without phone verification or payment activation.
- [ ] Record actual runtime type, CPU count, RAM, GPU/VRAM, free disk, and observed session limits.
- [ ] Confirm installation uses approved packages only; no pretrained weights or external AI APIs.
- [ ] Confirm checkpoint save, download/transfer, and restore survive runtime reset.
- [ ] Verify no charges, billing activation, or paid credits are used.
- [ ] Run environment and preflight checks only; no optimizer steps.
- [ ] Recheck provider terms at the time of use.

## Phase 9 exit status

**Research/documentation complete; operational acceptance incomplete.** No provider has been connected, no training job has been launched, and training is not approved.
