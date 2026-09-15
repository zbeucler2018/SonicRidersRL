# Sonic Riders Superhuman Agent
## Product Requirements Document — v0.5
### Deterministic Libretro Simulation, Game Telemetry, Self-Play, and Superhuman Racing

## 0. Executive Summary

Build a reinforcement-learning system capable of producing a **superhuman Sonic Riders agent**, ultimately able to defeat skilled human players under a controlled competitive ruleset.

Initial target:

- **Game:** Sonic Riders
- **Platform:** Nintendo GameCube
- **Build:** vanilla NTSC-U
- **Training emulator:** Dolphin-libretro
- **Debugging emulator:** standalone Dolphin

The project is explicitly **infrastructure-first**. Before serious RL training, build a deterministic, observable, reproducible and parallelizable simulator supporting exact frame stepping, four GameCube controller ports, direct MEM1 access, in-memory reset, semantic telemetry for up to eight racers, state-only/rendered modes, Gymnasium/PettingZoo APIs, and multi-process workers.

The preferred production training architecture is a **minimal purpose-built libretro frontend loading `dolphin_libretro.so` directly**. Standalone Dolphin remains useful for reverse engineering and debugging. Stable-Retro is intentionally not on the initial critical path. A private Dolphin fork is a contingency only.

## 1. Product Goal

The final agent should master both mechanics and racing strategy.

Mechanical scope includes steering, jumps, tricks, Air management, boosting, drifting/drift dashes, shortcuts, Speed rails, Flight/Power routes, turbulence, items, obstacle avoidance and recovery.

Competitive scope includes overtaking, defending, attacking, tornado placement, resource management, opponent-aware routing, positional strategy and self-play adaptation.

The long-term benchmark is skilled human competition, not merely stock CPU performance.

## 2. Initial Non-Goals

The first environment does not require pixel-only observations, all tracks, all characters/gears, Tournament Edition, eight learning-controlled racers, a final league, a final reward, a final RL algorithm or a custom Dolphin fork.

## 3. Architectural Principle

```text
Dolphin-libretro
      ↓
raw memory / input / frames
      ↓
semantic telemetry
      ↓
observations / events / rewards
      ↓
Gymnasium / PettingZoo
      ↓
trainer / league
```

Dolphin must not know Sonic reward semantics. Telemetry must not depend on a trainer. Rewards must not contain raw addresses. Trainers must not know controller plumbing.

## 4. Preferred Emulator Architecture

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

RetroArch itself is not required for training.

## 5. Backend Interface

Conceptually:

```python
class SonicRidersBackend:
    def launch(self, config): ...
    def reset(self, snapshot): ...
    def step(self, controllers, frames=1, capture_frame=False): ...
    def read_memory(self, requests): ...
    def write_memory(self, writes): ...
    def capture_frame(self): ...
    def health(self): ...
    def close(self): ...
```

Initial implementations:

```text
LibretroDolphinBackend      preferred
StandaloneDolphinBackend    debugging/fallback
```

## 6. Atomic Environment Step

Target operation:

```python
result = backend.step(
    controllers={0: action0, 1: action1, 2: action2, 3: action3},
    frames=4,
)
```

Semantics:

```text
set controller states
→ retro_run() × N
→ read resulting MEM1
→ return StepResult
```

The same action remains held throughout the frame interval. No wall-clock sleeps are used.

## 7. Minimal Libretro Frontend

Responsibilities:

- load core and game;
- configure environment callbacks;
- provide four controller states;
- handle/discard video and audio callbacks;
- expose memory maps;
- serialize/unserialize states;
- run frames;
- cleanly shut down.

Menus, shaders, achievements, playlists and other general frontend features are out of scope.

## 8. Direct GameCube RAM

GameCube MEM1 begins at guest address `0x80000000` and uses big-endian values. The backend should expose typed reads/writes plus bulk ranges. Sonic-specific interpretation belongs in versioned schemas.

## 9. Serialized Reset

Preferred reset model:

```text
known race state
→ retro_serialize()
→ snapshot bytes

training reset
→ retro_unserialize(snapshot)
```

Each snapshot records game hash, core Git SHA, track, mode, character, gear, player count, checksum and memory-schema version.

## 10. Determinism

Required property:

> Given the same serialized state and identical controller trace, the resulting game-level trajectory is equivalent within defined tolerance.

Validate at minimum position, speed, Air, Rings, lap, placement, stage progress, player state and race state.

## 11. Frame Semantics

Empirically prove what one `retro_run()` means for Sonic Riders. If video-frame and simulation-frame semantics differ, define and document the canonical environment step.

## 12. Frontend Pacing

Training must run as fast as emulation permits. Audio/video callbacks must not force wall-clock pacing.

## 13. Rendering Modes

Support:

```text
STATE_ONLY
PIXEL_TRAINING
HUMAN_RENDER
```

Benchmark Dolphin's Null renderer rather than assuming it is faster or always compatible.

## 14. Input

Preserve native GameCube controller capability including analog stick/triggers and buttons. Initial multiplayer target is all four controller ports in one emulator instance.

## 15. Player Architecture

Current community reverse engineering indicates:

```text
MaxPlayerCount = 8
MaxControllerCount = 4
Player stride = 0x1080
```

All eight racers should be observable; the first four are immediately controller-capable.

## 16. Versioned Memory Schema

Use explicit schemas such as:

```text
schemas/GXEE8P/vanilla_ntscu_v1.yaml
```

Each field records type, offset, provenance and validation status.

## 17. Core Telemetry

Initial telemetry should cover:

- position / orientation / forward vector;
- speed / vertical speed / stage progress;
- Air / gain / loss;
- Rings / level;
- lap / placement;
- character / gear;
- current/previous player state;
- boost / drift / brake / jump charge;
- rail state and rail ID;
- turbulence;
- trick state/rank/failure;
- wall bonk / Air Pit / status effects;
- combat relationships.

## 18. Semantic Events

Derive semantic events primarily from consecutive telemetry snapshots:

```text
BoostStarted
RingCollected
LevelChanged
TrickLanded
GrindStarted / GrindEnded
TurbulenceEntered / Exited
AttackHit
LapCompleted
WallBonk
```

## 19. Stage Progress

Validate `Player + 0xBC4` (`stageProgress`) across normal route, reverse movement, rails, Flight/Power routes, shortcuts, alternate paths, turbulence, falls/respawns and lap transitions.

If robust, it is the leading dense progress-reward candidate.

## 20. Observation Tiers

- Tier A: privileged structured state.
- Tier B: human-accessible structured state.
- Tier C: pixels.

Support asymmetric actor-critic training with a restricted actor and privileged critic.

## 21. Gymnasium / PettingZoo

Use Gymnasium for Time Attack, debugging and early PPO baselines. Use PettingZoo Parallel for simultaneous four-player self-play.

## 22. Initial Reward

Start deliberately narrow:

```text
+ forward progress
+ lap completion
+ race completion
- fall/death
- prolonged lack of progress
```

Do not initially reward Rings, Air, tricks, rails, boosting, attacks, items or turbulence directly.

## 23. Trainers

- Stable-Baselines3: baseline/smoke testing.
- Sample Factory: leading high-throughput/self-play candidate.
- TorchRL: MAPPO/IPPO/custom MARL research.

Environment remains framework-independent.

## 24. Actor/Learner Architecture

Prefer CPU emulator workers and a GPU learner / batched inference layer. Remote actor nodes should run full local environment loops and send trajectories, not frame-by-frame network RPCs.

## 25. Self-Play Progression

```text
Time Attack
→ stock CPU
→ 1v1 policy races
→ historical opponents
→ 4-player self-play
→ league training
→ human competition
```

Maintain current, recent, historical and exploiter policies rather than only latest-vs-latest.

## 26. Eight-Racer Long-Term Goal

Observe all eight racers immediately. Controlling CPU slots 4–7 by intercepting/replacing CPU decisions is an experimental later milestone.

## 27. Multi-Worker Scaling

Benchmark worker counts empirically (1, 2, 4, 8, 12, 16, then expand if useful). Measure per-worker and aggregate emulation FPS, env steps/sec, CPU/RAM/GPU, frame latency, reset latency, inference latency and failures.

## 28. Standalone Dolphin / Felk / Stable-Retro

Standalone Dolphin: manual gameplay, memory inspection, reverse engineering and visual debugging.

Felk: reference implementation and scripting/debugging tool.

Stable-Retro: not part of the initial Sonic runtime. Consider later as an optional upstream/community contribution after the direct Dolphin-libretro backend is proven.

## 29. Custom Dolphin Fork Policy

A private Dolphin fork is justified only if required functionality cannot reasonably be implemented in libretro or upstreamed generically.

## 30. Fault Tolerance

Every worker needs heartbeat, timeout, graceful shutdown, forced-kill fallback, restart, state reload and trajectory invalidation.

## 31. Reproducibility

Every run records project SHA, Dolphin-libretro SHA, frontend SHA, game hash, snapshot checksum, track/mode/character/gear/player count, seed, schema versions, frame skip, render mode, trainer/version/architecture and hyperparameters.

## 32. Experiment Tracking

Default: Weights & Biases.

Log infrastructure metrics separately from gameplay telemetry and training return.

## 33. Repository Structure

```text
sonic-riders-rl/
├── sonic_env/
├── telemetry/
├── backends/
├── libretro_runner/
├── reverse_engineering/
├── league/
├── trainers/
├── evaluation/
├── configs/
├── tests/
├── scripts/
└── docs/
```

## 34. Infrastructure Gates

A. Build current Dolphin-libretro on Ubuntu.

B. Load `dolphin_libretro.so` without RetroArch.

C. Boot exact Sonic Riders NTSC-U.

D. Validate `retro_run()` frame semantics.

E. Control Player 1 programmatically.

F. Independently control all four GC ports.

G. Read known Sonic state from MEM1.

H. Safely write a known memory value.

I. Resolve vanilla `players[]` and validate `0x1080` stride.

J. Validate P1 telemetry.

K. Validate all active racers.

L. Serialize and restore a race state in memory.

M. Prove deterministic replay.

N. Run at least 10,000 reset/short-rollout cycles.

O. Confirm unthrottled execution.

P. Validate state-only/Null mode.

Q. Validate stage progress.

R. Complete a Gymnasium race episode.

S. Run a four-agent PettingZoo race.

T. Benchmark multi-worker scaling.

Serious RL begins only after these gates.

## 35. First Emulator Deliverable

Build `sonic-libretro-runner` capable of:

```text
load dolphin_libretro.so
load Sonic Riders
set controller input
run frame
read MEM1
serialize
unserialize
shutdown
```

No RL library is involved in this milestone.

## 36. First Telemetry Deliverable

`python -m sonic_env.telemetry.watch` should show live race state and P1 telemetry, then all eight racers.

## 37. Immediate Engineering Sequence

```text
1. Pin exact Sonic Riders NTSC-U hash.
2. Pin current dolphin-libretro revision.
3. Build dolphin-libretro on Ubuntu.
4. Write minimal standalone libretro frontend.
5. Boot Sonic Riders.
6. Run frames without RetroArch.
7. Confirm unthrottled execution.
8. Inject P1 input.
9. Inject all four controllers.
10. Obtain MEM1 pointer.
11. Read/write known RAM.
12. Resolve players[].
13. Validate P1 telemetry.
14. Validate all eight racers.
15. Implement typed MemorySchema.
16. Test serialize/unserialize.
17. Validate deterministic replay.
18. Run 10k reset stress test.
19. Test Null renderer.
20. Benchmark rendered vs Null throughput.
21. Validate stageProgress.
22. Build semantic events.
23. Build Gymnasium env.
24. Build PettingZoo Parallel env.
25. Benchmark multi-process scaling.
26. Integrate W&B.
27. Run scripted/random baseline.
28. Train first Metal City agent.
```

## 38. ML Milestones

M1 finish Metal City.

M2 beat stock CPU.

M3 mechanical mastery.

M4 strong Time Attack.

M5 multi-track agent.

M6 four-player self-play.

M7 league training.

M8 character/Gear generalization.

M9 vision policy.

M10 Tournament Edition.

M11 human challenge.

M12 experimental eight-racer control.

## 39. Definition of Superhuman

A superhuman claim requires a predefined evaluation protocol: same game build, equivalent logical controller capability, no hidden privileged RAM for the official actor, fixed conditions, qualified opponents, enough repeated races for statistical confidence, and separate Time Attack vs multiplayer evaluation.

## 40. Architecture Decision — v0.5

```text
GAME
    Sonic Riders, GameCube NTSC-U vanilla

TRAINING EMULATOR
    Dolphin-libretro

TRAINING FRONTEND
    custom minimal libretro runner

STANDALONE DOLPHIN
    reverse engineering / debugging / fallback

FELK
    reference/debugging tool

STABLE-RETRO
    not on initial critical path

CUSTOM DOLPHIN FORK
    contingency only

FRAME EXECUTION
    frontend-controlled retro_run()

INPUT
    four GameCube ports via libretro callbacks

MEMORY
    direct MEM1, big endian, guest base 0x80000000

RESET
    retro_serialize / retro_unserialize

SINGLE AGENT
    Gymnasium

MULTI AGENT
    PettingZoo Parallel

BASELINE RL
    Stable-Baselines3

HIGH-THROUGHPUT RL
    Sample Factory candidate

MARL RESEARCH
    TorchRL candidate

TRACKING
    Weights & Biases
```

## 41. Final Requirement

The primary engineering product is:

> A deterministic, directly controlled Dolphin-libretro Sonic Riders simulator exposing native inputs, direct game memory, fast serialized resets, semantic telemetry and scalable process-level parallelism.

If this simulation boundary is correct and fast, the downstream ML stack remains replaceable.
