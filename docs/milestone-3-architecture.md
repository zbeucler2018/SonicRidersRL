# Milestone 3 architecture decision: exact snapshot replay

## Goal

Prove the emulator boundary can restore a known state and replay an identical
controller trace without diverging. This is a substrate determinism check, not
yet a claim about race-level determinism.

## Decision

Compare both the whole MEM1 mapping and the resolved eight-player allocation
after replaying a non-neutral four-port trace twice from the same in-memory
savestate. The runner calculates an FNV-1a 64-bit checksum locally, avoiding a
large MEM1 transfer over the Python protocol. The probe separately compares the
typed player records to make an accidental checksum collision implausible for
the telemetry it exposes.

The test is bound to one core process, ROM, core revision, snapshot, and
configuration. It is intentionally not a cross-host, cross-revision, or
real-race reproducibility assertion.

## Rejected alternatives

- Comparing savestate byte streams: the current public snapshot is an
  owner-process token, not an exported portable blob.
- Comparing only a 64 KiB memory sample: a local full-MEM1 checksum costs
  little and has a materially stronger failure signal.
- Defining success from menu fields alone: menu player records are also
  compared, but the full mapping detects divergence outside their static data.
- Calling this game-level race determinism: race telemetry must first be
  validated in a reproducible race-entry fixture.
