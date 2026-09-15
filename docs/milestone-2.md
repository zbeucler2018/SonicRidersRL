# Milestone 2: telemetry reconnaissance and four-port validation

## Scope

Milestone 2 extends the emulator substrate with:

- independent accounting for all four GameCube controller ports;
- analog L/R trigger injection through libretro's analog-button channel;
- a snapshot-protected bounded MEM1 write/restore check;
- dynamic resolution of vanilla `players[]` from `_Main.rel` code;
- typed big-endian decoding of the eight `0x1080`-byte player slots; and
- a versioned schema with validation status on every field.

It does **not** implement an environment, observations, rewards, semantic
events, scripted gameplay, a real-race reset snapshot, or any RL library.

## Why `players[]` is resolved at runtime

The vanilla executable loads `_Main.rel` dynamically. The static structure
layout in community source has a symbolic `players[]` base, but no fixed MEM1
address should be assumed. `resolve_players_array()` instead recognizes the
specific code pattern that performs `players[index]` using a `0x1080` stride.
The resolver fails closed if the expected `GXEE8P` signature is absent or
ambiguous.

At a fresh menu boot, the probe validates that the eight stride-separated
`character` bytes are `[0, 1, 2, 3, 4, 5, 6, 7]`. This proves the runtime
array/base/stride combination for this controlled state. Position, speed, Air,
Rings, lap, placement, state, and `stageProgress` are intentionally decoded
but remain unvalidated during a race.

## Run the validation

```bash
scripts/build_runner.sh
python3 -m unittest discover -s tests -v
python3 -m sonic_riders_rl.milestone2_probe
```

The probe writes its machine-readable report to
`.local/reports/milestone2.json`. It asserts:

- the game identifies as `GXEE8P`;
- a single, bounds-valid `players[]` reference is found in MEM1;
- the fresh-menu eight-slot character invariant matches the documented stride;
- a one-byte write is observable and exactly undone by savestate restore; and
- all four ports produce non-neutral input callback values, including L and R
  analog trigger-only states on ports 2 and 3.

All emulator outputs and downloaded upstream source checkouts remain under the
repository's ignored `.local/` directory.
