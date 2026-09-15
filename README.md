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
6. serialize/unserialize deterministic race states.

Only after these gates pass do we move on to Gymnasium/PettingZoo and serious RL training.

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

## Documentation

- [Product Requirements Document](docs/PRD.md)
- [Architecture](docs/architecture.md)
- [Dolphin-libretro backend research](docs/dolphin-libretro.md)
- [Reverse-engineering notes](docs/reverse-engineering.md)
- [Player structure research](docs/research/player-structure.md)
- [Emulator control options](docs/research/emulator-control-options.md)
- [Milestone 1 architecture decision](docs/milestone-1-architecture.md)
- [Milestone 1 operation and validation](docs/milestone-1.md)

## External references

- Dolphin: https://github.com/dolphin-emu/dolphin
- Dolphin libretro core: https://github.com/libretro/dolphin
- Sonic Riders decompilation: https://github.com/doldecomp/sonicriders
- Sonic Riders Tournament Edition: https://github.com/RidersBoulevard/sonicriderste
- True Colors / SRTE-derived reverse engineering: https://github.com/babylon-workshop/sonicriderstruecolors

Game assets are not included in this repository.
