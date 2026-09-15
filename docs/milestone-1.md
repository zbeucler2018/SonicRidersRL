# Milestone 1: emulator-control substrate

## Scope

This is deliberately the emulator boundary, not an RL environment. It has no
Sonic telemetry schema, observations, rewards, Gymnasium/PettingZoo adapter,
policy, trainer, self-play logic, or reverse-engineering-dependent game state.

## Components

- `runner/sonic_libretro_runner.cpp` dynamically loads one Dolphin libretro
  core in one worker process. It provides a surfaceless EGL/OpenGL context,
  libretro callbacks, four controller slots, MEM1 access, and in-memory
  savestate retention.
- `sonic_riders_rl.backend.LibretroDolphinBackend` is the small Python-facing
  API. It owns one runner subprocess and exposes `launch`, `step`,
  `read_memory`, `write_memory`, `snapshot`, `restore`, `health`, and `close`.
- `sonic_riders_rl.probe` performs the live end-to-end validation.

The runner uses a normal upstream hardware renderer through a hidden,
surfaceless OpenGL context. Video and audio output are discarded; it does not
use Docker or depend on Dolphin's Null renderer.

## Frame and input semantics

`step(controllers, frames=N)` atomically replaces the current state for ports
0–3, then makes `N` synchronous `retro_run()` calls. The current upstream core
uses `RunSingleFrame()` in this runner's single-core configuration. The host
does not register a libretro frame-time callback or sleep between calls, and
the core option `dolphin_emulation_speed=0.0` selects unlimited speed.

Each `ControllerState` preserves libretro's GameCube-compatible button bitmask
and signed 16-bit main stick, C-stick, and trigger axes. The probe uses a
non-neutral P1 state (A, Z, main stick, C-stick, and trigger) and verifies
that Dolphin queried nonzero P1 input while emulating.

## Memory and reset contract

The runner accepts the core's `RETRO_ENVIRONMENT_SET_MEMORY_MAPS` descriptor
and exposes MEM1 at guest base `0x80000000`. GameCube MEM1 is expected to be
`0x01800000` bytes and big-endian. Memory access is bounds-checked against that
descriptor; callers use guest addresses, never host pointers.

`snapshot()` returns an owner-process token for state retained in the runner's
memory. `restore(token)` calls `retro_unserialize()` synchronously and then
reacquires the MEM1 pointer. Tokens are intentionally not portable across core
processes or core builds. That is the appropriate fast-reset primitive for a
future worker; persistent snapshots need explicit version metadata before they
are introduced.

## Running validation

```bash
scripts/bootstrap_dolphin_core.sh
scripts/build_runner.sh
python3 -m unittest discover -s tests -v
python3 -m sonic_riders_rl.probe
```

The final command stores the machine-readable result in
`.local/reports/milestone1.json`. It asserts all of the following:

- Dolphin identifies the loaded disc as `GXEE8P`.
- MEM1 has the expected base, 24 MiB size, and big-endian mapping.
- P1's injected non-neutral controller values are read by the emulator.
- A 64 KiB MEM1 sample exactly matches after a save/restore round trip.
- Ten caller-driven 1,000-frame control commands (10,000 frames total) complete
  in the same healthy worker.

The report also records the core library revision, the downloaded core's
SHA-256, savestate size/reset latency, and stepping throughput. All runtime
artifacts remain under `.local/`.

## Deliberate reliability choices

The worker turns off Dolphin fastmem and fastmem arena because direct host page
protection is not required for this substrate and can be unavailable in
sandboxed worker environments. It also uses Dolphin single-core mode for this
first exact stepping proof. These are reliability settings, not a throughput
claim; future benchmark work can revisit them without changing the Python API.
