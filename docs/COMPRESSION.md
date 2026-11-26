# Compression policy

## Foundation checkpoint parameter floor

The requirement of **at least 60,000,000 trainable parameters** applies only to the
ULTRON **foundation training checkpoint**. The current foundation configuration
accounts for 63,400,451 total parameters and 61,826,048 trainable parameters.

A compressed model is a separate, versioned **deployment artifact**. Every
compressed artifact must record its parent foundation checkpoint (including a
stable checkpoint identifier or version) and the ordered compression steps
applied to produce it. The artifact should also record the compression
configuration and resulting artifact version so that it can be traced and
reproduced.

A compressed deployment artifact never replaces, overwrites, or becomes the
foundation training checkpoint. The 60M trainable-parameter floor is not a
requirement for compressed deployment artifacts, and compressed artifacts
must never be described as meeting that foundation floor. The floor remains
attached to the uncompressed foundation training checkpoint only.

## Compression quality and calibration

Compression quality can only be judged on a **trained model** using a
**verified benchmark** with a documented baseline and evaluation procedure.
Parameter counts, successful code tests, synthetic smoke checks, or results
from an untrained model are not evidence of compression quality or retained
mathematical capability.

**No calibration corpus has been generated.** No calibration quality,
calibration coverage, or calibrated compression result may be claimed until a
calibration corpus has been deliberately prepared and its provenance and
validation have been reviewed.

Until a trained checkpoint and verified benchmark are available, compression
quality remains unmeasured. This report tooling accounts for parameters only;
it does not apply compression transformations or establish quality.

## Scope and safety boundary

The parameter-reporting utility may construct the model on the PyTorch
meta-device to inspect the real module structure without allocating foundation
weights. If meta-device construction is unavailable, it falls back to the
existing analytical configuration counters and explicitly reports that the
category/module breakdown is unavailable.

This documentation and report implementation do not authorize model training,
optimizer steps, corpus generation, calibration-corpus generation, cloud
execution, or remote execution. Those activities require separate
authorization.
