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

## Setup and validation

The checked-in Dolphin-libretro source is a pinned Git submodule. Downloaded
core binaries, Dolphin system assets, build products, run data, and reports
remain in ignored repository-local directories.

```bash
git submodule update --init --recursive
uv sync --dev
scripts/setup_dolphin_core.sh
scripts/build_runner.sh
uv run python -m unittest discover -s tests -v
uv run python -m sonic_riders_rl.normal_race_probe
```

The normal-race probe expects the authorized ROM at
`~/Games/GameCube/SonicRiders/sonic_riders_usa.rvz`. It verifies the latest
end-to-end fixture: booting `GXEE8P`, controlled frame stepping, P1 movement in
a normal race, direct MEM1 access, snapshot replay, and the earlier 10,000-step
stability gate. The formal normal-race reset fixture additionally verifies 32
exact in-memory restores. See [development setup](docs/development.md) for
details and the individual milestone records for their exact historical
commands/results.

## Documentation

- [Product Requirements Document](docs/PRD.md)
- [Development setup](docs/development.md)
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
- [Milestone 12 architecture decision](docs/milestone-12-architecture.md)
- [Milestone 12 operation and validation](docs/milestone-12.md)
- [Milestone 13 architecture decision](docs/milestone-13-architecture.md)
- [Milestone 13 operation and validation](docs/milestone-13.md)
- [Milestone 14 architecture decision](docs/milestone-14-architecture.md)
- [Milestone 14 operation and validation](docs/milestone-14.md)

## External references

- Dolphin: https://github.com/dolphin-emu/dolphin
- Dolphin libretro core: https://github.com/libretro/dolphin
- Sonic Riders decompilation: https://github.com/doldecomp/sonicriders
- Sonic Riders Tournament Edition: https://github.com/RidersBoulevard/sonicriderste
- True Colors / SRTE-derived reverse engineering: https://github.com/babylon-workshop/sonicriderstruecolors

Game assets are not included in this repository.
