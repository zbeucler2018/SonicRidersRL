# SonicRidersRL

Research and engineering project for building a superhuman reinforcement-learning agent for **Sonic Riders (GameCube, NTSC-U)**.

The project is infrastructure-first: before serious RL training, the goal is to build a deterministic, observable, reproducible and parallelizable Sonic Riders simulator around the Dolphin libretro core.

## Current architecture

```text
Dolphin-libretro worker process
      ↓
raw memory / controller input / frames
      ↓
semantic telemetry
      ↓
observations + events + rewards
      ↓
Gymnasium / PettingZoo
      ↓
training + self-play league
```

The Milestone 1 backend is a small custom libretro host that loads
`dolphin_libretro.so` directly on the Linux host. It creates a hidden
surfaceless OpenGL context, runs exactly the requested number of `retro_run()`
calls, and is wrapped by a deliberately small Python API. Standalone Dolphin
remains useful for reverse engineering and visual debugging. Stable-Retro is
intentionally not on the critical path.

## Current status

The project is in the emulator/telemetry infrastructure phase. Milestone 1
proves that we can:

1. build and load current Dolphin-libretro on Ubuntu;
2. boot the exact Sonic Riders NTSC-U image;
3. call `retro_run()` under frontend control;
4. inject GameCube controller state;
5. access MEM1 directly;
6. serialize/unserialize deterministic menu states.

Milestone 2 adds a read-only, versioned telemetry reconnaissance layer. It
resolves the relocatable vanilla `players[]` array from code at runtime, decodes
the documented big-endian player structure, validates the fresh-menu eight-slot
stride invariant, and independently accounts for all four controller ports.
Gameplay fields remain explicitly unvalidated until they are tested in a real
race.

Only after the telemetry/determinism gates pass do we move on to
Gymnasium/PettingZoo and serious RL training.

## Milestone 1 quick start

All downloaded core files, Dolphin system assets, run data, and reports are
kept in the repository's ignored `.local/` directory.

```bash
scripts/bootstrap_dolphin_core.sh
scripts/build_runner.sh
python3 -m sonic_riders_rl.probe
```

The probe expects the authorized ROM at
`~/Games/GameCube/SonicRiders/sonic_riders_usa.rvz`. It boots the disc,
requires Dolphin to identify it as `GXEE8P`, tests P1 input, MEM1, an
in-memory savestate restore, and a 10,000-frame synchronous stepping loop.

## Milestone 2 quick start

```bash
scripts/build_runner.sh
python3 -m unittest discover -s tests -v
python3 -m sonic_riders_rl.milestone2_probe
```

This read-only telemetry probe resolves the live `players[]` allocation from a
vanilla `_Main.rel` instruction signature. It also checks a savestate-protected
MEM1 write/restore and four distinct controller ports. The report is stored at
`.local/reports/milestone2.json`.

## Milestone 3 quick start

```bash
scripts/build_runner.sh
python3 -m sonic_riders_rl.determinism_probe
```

This probe restores a single controlled snapshot and replays the same
four-controller trace twice. It requires matching full-MEM1 and `players[]`
checksums, then records the result in `.local/reports/milestone3.json`.

## Milestone 4 quick start

```bash
scripts/build_runner.sh
python3 -m sonic_riders_rl.reset_stress_probe
```

This runs 10,000 snapshot/reset one-frame rollouts in one worker, periodically
checks its health, and confirms the final restore exactly reproduces the
baseline MEM1 checksum. Its report is `.local/reports/milestone4.json`.

## Milestone 5 quick start

```bash
scripts/build_runner.sh
python3 -m unittest discover -s tests -v
python3 -m sonic_riders_rl.race_probe
```

This reaches Sonic Riders' unmodified attract-mode race with explicit frame
stepping, validates eight moving racer records with their `ai_control` flags
set, and proves a race snapshot
replays exactly. It writes a diagnostic 640x528 PPM frame and its report below
the repository's ignored `.local/` directory. It is not yet a human-controlled
P1 race fixture.

## Milestone 6 quick start

```bash
scripts/build_runner.sh
python3 -m sonic_riders_rl.game_input_probe
```

This uses one live-race snapshot to show a one-frame native P1 Start input
takes a different, captured game branch than a neutral trace, while replaying
exactly from the same state. The attract-mode `ai_control` flags remain set;
direct P1 steering is not claimed.

## Milestone 7 quick start

```bash
scripts/build_runner.sh
python3 -m unittest discover -s tests -v
python3 -m sonic_riders_rl.control_telemetry_probe
```

This validates that P1 Start and stick input are present in Player 0's bounded,
in-MEM1 controller record. It keeps the two raw ownership-related bytes,
`ai_control` and `player_type`, distinct rather than prematurely assigning
human/CPU semantics.

## Milestone 8 quick start

```bash
scripts/build_runner.sh
python3 -m sonic_riders_rl.frame_semantics_probe
```

This empirically defines one active-race backend frame as one caller-issued
`retro_run()`: runner, video, and game-side controller clocks all advance by
the requested amount in the stock race fixture.

## Milestone 9 result

The current release Dolphin-libretro core crashes before startup when asked to
use its Null renderer. Hardware remains the only exposed and validated renderer
for this host/core; see the recorded [compatibility result](docs/milestone-9.md).

## Milestone 10 result

The stock attract transition validates controller-to-player pointer mapping,
but not direct steering: Player 0/1 can retain `player_type=0` while
`ai_control=1`. The next prerequisite is a normal menu-driven race setup, not
an RL environment.

## Milestone 11 quick start

```bash
scripts/build_runner.sh
python3 -m unittest discover -s tests -v
python3 -m sonic_riders_rl.game_mode_probe
```

This resolves the dynamically loaded retail game-mode and mode-detail words
from a paired `_Main.rel` instruction signature, then records raw state-machine
values at boot-flow and stock-attract checkpoints. It remains telemetry only.

## Documentation

- [Product Requirements Document](docs/PRD.md)
- [Architecture](docs/architecture.md)
- [Dolphin-libretro backend research](docs/dolphin-libretro.md)
- [Reverse-engineering notes](docs/reverse-engineering.md)
- [Player structure research](docs/research/player-structure.md)
- [Emulator control options](docs/research/emulator-control-options.md)
- [Milestone 1 architecture decision](docs/milestone-1-architecture.md)
- [Milestone 1 operation and validation](docs/milestone-1.md)
- [Milestone 2 architecture decision](docs/milestone-2-architecture.md)
- [Milestone 2 operation and validation](docs/milestone-2.md)
- [Milestone 3 architecture decision](docs/milestone-3-architecture.md)
- [Milestone 3 operation and validation](docs/milestone-3.md)
- [Milestone 4 operation and validation](docs/milestone-4.md)
- [Milestone 5 architecture decision](docs/milestone-5-architecture.md)
- [Milestone 5 operation and validation](docs/milestone-5.md)
- [Milestone 6 architecture decision](docs/milestone-6-architecture.md)
- [Milestone 6 operation and validation](docs/milestone-6.md)
- [Milestone 7 architecture decision](docs/milestone-7-architecture.md)
- [Milestone 7 operation and validation](docs/milestone-7.md)
- [Milestone 8 architecture decision](docs/milestone-8-architecture.md)
- [Milestone 8 operation and validation](docs/milestone-8.md)
- [Milestone 9 architecture decision](docs/milestone-9-architecture.md)
- [Milestone 9 compatibility result](docs/milestone-9.md)
- [Milestone 10 architecture decision](docs/milestone-10-architecture.md)
- [Milestone 10 investigation result](docs/milestone-10.md)
- [Milestone 11 architecture decision](docs/milestone-11-architecture.md)
- [Milestone 11 operation and validation](docs/milestone-11.md)

## External references

- Dolphin: https://github.com/dolphin-emu/dolphin
- Dolphin libretro core: https://github.com/libretro/dolphin
- Sonic Riders decompilation: https://github.com/doldecomp/sonicriders
- Sonic Riders Tournament Edition: https://github.com/RidersBoulevard/sonicriderste
- True Colors / SRTE-derived reverse engineering: https://github.com/babylon-workshop/sonicriderstruecolors

Game assets are not included in this repository.
