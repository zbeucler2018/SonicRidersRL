# SonicRidersRL

Research and engineering project for building a superhuman reinforcement-learning agent for **Sonic Riders (GameCube, NTSC-U)**.

The project is infrastructure-first: before serious RL training, the goal is to build a deterministic, observable, reproducible and parallelizable Sonic Riders simulator around the Dolphin libretro core.

## Current architecture

```text
Dolphin-libretro
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

The preferred training backend is a minimal custom libretro frontend that loads `dolphin_libretro.so` directly. Standalone Dolphin remains useful for reverse engineering and visual debugging. Stable-Retro is intentionally not on the critical path.

## Current status

The project is in the emulator/telemetry infrastructure phase. The next engineering spike is to prove that we can:

1. build and load current Dolphin-libretro on Ubuntu;
2. boot the exact Sonic Riders NTSC-U image;
3. call `retro_run()` under frontend control;
4. inject GameCube controller state;
5. access MEM1 directly;
6. serialize/unserialize deterministic race states.

Only after those gates pass do we move on to Gymnasium/PettingZoo and serious RL training.

## Documentation

- [Product Requirements Document](docs/PRD.md)
- [Architecture](docs/architecture.md)
- [Dolphin-libretro backend research](docs/dolphin-libretro.md)
- [Reverse-engineering notes](docs/reverse-engineering.md)
- [Player structure research](docs/research/player-structure.md)
- [Emulator control options](docs/research/emulator-control-options.md)

## External references

- Dolphin: https://github.com/dolphin-emu/dolphin
- Dolphin libretro core: https://github.com/libretro/dolphin
- Sonic Riders decompilation: https://github.com/doldecomp/sonicriders
- Sonic Riders Tournament Edition: https://github.com/RidersBoulevard/sonicriderste
- True Colors / SRTE-derived reverse engineering: https://github.com/babylon-workshop/sonicriderstruecolors

Game assets are not included in this repository.
