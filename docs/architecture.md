# Architecture

## Goal

Create a deterministic Sonic Riders simulator suitable for single-agent RL, four-player self-play, privileged-state research, and eventual pixel-based human-comparable evaluation.

## Layering

```text
Dolphin-libretro
    ↓
LibretroDolphinBackend
    ↓
Raw Game Memory
    ↓
MemorySchema / Semantic Telemetry
    ↓
RiderState / RaceState / EventDetector
    ↓
Observation Builder + Reward Model
    ↓
Gymnasium / PettingZoo Parallel
    ↓
SB3 / Sample Factory / TorchRL / League
```

Strict separation is intentional:

- Dolphin does not contain Sonic-specific reward logic.
- Telemetry does not depend on a trainer.
- Rewards do not contain raw GameCube addresses.
- Trainers do not know how controller callbacks are implemented.

## Preferred runtime

The production training path is a minimal frontend loading `dolphin_libretro.so` directly.

```text
Trainer
  ↓
SonicRidersEnv
  ↓
LibretroDolphinBackend
  ↓
Minimal libretro frontend
  ↓
dolphin_libretro.so
```

Standalone Dolphin is retained for reverse engineering and manual debugging. Felk is a useful reference/debugging tool. Stable-Retro is not part of the initial runtime.

## Core step

The target environment transition is:

```python
result = backend.step(
    controllers={0: a0, 1: a1, 2: a2, 3: a3},
    frames=4,
)
```

Semantics:

```text
set four controller states
→ retro_run() × N
→ read MEM1
→ decode telemetry
→ derive events
→ compute reward
→ return observation
```

No wall-clock sleeps should be required.

## Reset

Use in-memory libretro serialization:

```text
known race state
→ retro_serialize()
→ snapshot bytes

training reset
→ retro_unserialize(snapshot)
```

Snapshots are version-bound to the game hash and Dolphin-libretro revision unless proven otherwise.

## Parallelism

Initially use one Dolphin-libretro instance per process. This gives clean process isolation and makes worker restart straightforward.

Remote rollout nodes should host complete actor loops locally and exchange trajectory batches / policy weights, not individual frame actions.
