# Resumable random sampler

`ultron_core.resumable_sampler.ResumableRandomSampler` creates a deterministic shuffled index permutation for each epoch. Its state records dataset size, manifest SHA-256, seed, epoch, and the next sample index.

The sampler can restore the remaining tail of the same permutation exactly when the dataset manifest, dataset length, and seed match. It rejects mismatched or malformed state.

For a synchronous DataLoader, save sampler state after a completed batch and restore it before creating the next DataLoader iterator:

```python
from ultron_core.resumable_sampler import ResumableRandomSampler

sampler = ResumableRandomSampler(
    dataset,
    seed=1846,
    dataset_manifest_sha256=dataset_manifest_sha256,
)
# Use DataLoader(dataset, sampler=sampler, num_workers=0).
state = sampler.state_dict()
# Save state with the model checkpoint; on restart:
sampler.load_state_dict(state)
```

**Exact-resume constraint:** use `num_workers=0` with this sampler unless the training loop separately records the number of samples actually consumed. Worker prefetch can advance a sampler beyond the last completed training batch.

The bounded trainer can now accept this sampler through its `sampler=` argument. It restores `data_state['sampler_state']` before the DataLoader iterator is created and includes the current sampler state in checkpoint callback metadata. The notebook callback must persist the provided `data_state` with `save_checkpoint`. This is not yet clean-runtime equivalence: the owner must test checkpoint save/reload/resume using `num_workers=0` before training readiness can be approved. No model training is performed by the sampler.
