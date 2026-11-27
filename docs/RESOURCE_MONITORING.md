# Runtime memory-budget monitoring

The bounded training controller samples memory usage against the byte budget in the successful preflight report. This guard does not authorize training; the controller still requires explicit authorization and local-only preflight state.

## Measurement

At controller boundaries, the monitor combines:

- Current process resident-set size (RSS), using psutil when available, /proc/self/statm on Linux, or the native Windows working-set API.
- CUDA allocator-reserved bytes for the active CUDA device. Before the first batch, reservations on visible CUDA devices are summed.

On platforms without a current-RSS source, the Unix resource.getrusage fallback reports the process lifetime peak RSS. The result includes a limitation note; it must not be described as current RSS on those platforms.

The budget is a process-level sampled limit, not a guarantee that the whole machine or GPU has that much free memory. It does not include memory held by other processes. CUDA reserved memory is included because allocator reservations occupy device memory even when not all reserved bytes are currently allocated to tensors.

## Check points

The controller checks before entering training, at each batch boundary, after backward, before and after optimizer steps, and after checkpoint callbacks. A sample above the budget raises MemoryError and stops the controller from proceeding to another safe boundary.

The monitor cannot interrupt a single PyTorch operation, CUDA kernel, batch transfer, or allocator call. A sudden allocation may therefore exceed the budget or trigger an operating-system/CUDA out-of-memory failure before the next sample. In particular, AdamW may allocate moment tensors during its first optimizer step; the controller samples immediately afterward and stops if the budget is exceeded, but that first step cannot be rolled back by the monitor.

## Interpretation

- The monitor's peak is the maximum of its discrete samples, not a hardware profiler's continuous peak.
- The preflight persistent-state estimate remains necessary but is not sufficient for a workload to fit.
- The website's RAM preference is a UI preference and does not allocate physical RAM or connect to a runtime.
- No training run or real foundation-model optimizer step is implied by these tests.
