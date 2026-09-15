# Milestone 1 architecture decision

## Decision

Milestone 1 uses the current upstream `libretro/dolphin` core directly on the
Linux host. A small native runner owns the libretro ABI and a surfaceless
EGL/OpenGL context; a minimal Python package invokes that runner and provides the future
backend-facing API.

The runner drives `retro_run()` synchronously, supplies GameCube controller
callbacks, obtains MEM1 through the core's registered memory map, and uses the
core's serialize/unserialize API.  It creates a normal hidden OpenGL context.
There is no Docker layer and no Null-renderer dependency.

## Why this is the smallest robust route

The upstream libretro API directly provides each Milestone 1 primitive behind
one in-process control boundary: game loading, caller-paced frame execution,
controller state callbacks, memory maps, and savestates.  The native runner
avoids asking Python to own an OpenGL context or cross an IPC boundary for every
emulated frame.  A process remains the unit of isolation, which is appropriate
for later emulator workers.

## Alternatives rejected for this milestone

- **Standalone Dolphin plus external control:** stock standalone Dolphin is
  excellent for manual debugging, but does not expose a small synchronous RPC
  API that atomically sets inputs, advances an exact frame count, and returns
  memory.  Adding one would require maintaining a Dolphin patch and its own
  control protocol.
- **Docker:** it adds graphics and device-runtime variability without providing
  a Milestone 1 control primitive.
- **Null renderer:** it is a later performance experiment.  A normal hidden
  OpenGL context is the compatibility-first baseline.

## Pinned upstream input

The validation report records the core's embedded library version/revision and
the SHA-256 of the downloaded core binary. The core source is a local, ignored
checkout under `.local/` so all task artifacts stay inside this repository.
