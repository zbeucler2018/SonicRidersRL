# Milestone 5 architecture decision: stock attract-mode race fixture

## Decision

Use Sonic Riders' unmodified attract-mode race as the first repeatably
reachable in-race fixture. The runner also gains a deliberately diagnostic-only PPM
frame capture command, backed by the already-required hardware-rendered EGL
pbuffer.

The fixture is reached by 9,000 frontend-controlled `retro_run()` calls from a
fresh GXEE8P boot. It has all eight racers active and all `ai_control` bytes
set. It is therefore suitable for validating the live player array, race-state
snapshots, and replay at the game level. It is not described as a substitute
for a human-controlled race setup.

## Why this fixture

- It exercises the exact retail image and normal game flow; no RAM patch,
  hacked save, custom ISO, or Tournament Edition behavior is required.
- It reaches a real moving race consistently while retaining caller-paced
  emulation. The 9,000-frame count is a simulation count, not a wall-clock
  delay.
- The eight slots expose independent indices, placements, positions, and
  movement, so it is a materially stronger telemetry target than a static menu.
- An in-memory snapshot taken there can prove that the existing reset and
  replay primitives continue to work after live race data has been loaded.

Independent fresh boots can reach valid demo races at different pre-snapshot
positions. Consequently this milestone does **not** call fresh boot bitwise
deterministic. The canonical reset baseline is the in-process snapshot taken
after entry; exact replay is tested from that baseline, which is the PRD's
serialized-state determinism contract.

## Debug capture boundary

`CAPTURE name.ppm` is constrained to a simple filename below a worker's own
save directory. The Python API applies the same validation. It reads the
current EGL pbuffer through `glReadPixels` and writes a binary PPM image.

This is intentionally a visual debugging instrument, not a rendered
observation API, image preprocessor, human UI, or a rendering-mode claim. It
does not put pixels into the transition API or introduce a training dependency.

## Alternatives deferred

- **RAM writes to force a stage/menu state:** would bypass the ordinary retail
  state machine and make reset/determinism results harder to trust.
- **A guessed menu-navigation script:** navigation has not yet been validated
  across loading transitions. Guessing it would create a brittle fixture.
- **A modified ISO/save file:** changes the behavioral target away from the
  required vanilla GXEE8P build.
- **Calling the attract demo a controlled P1 race:** its eight slots report
  `ai_control=true`; controller callback consumption is proven, but an
  in-race P1-response assertion remains future work. `player_type` must also
  be inspected before assigning ownership semantics.
