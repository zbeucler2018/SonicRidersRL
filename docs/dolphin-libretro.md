# Dolphin-libretro Backend Research

## Decision

Dolphin-libretro is the preferred training backend.

The current core already supplies nearly all primitives required by an RL environment:

- frontend-controlled `retro_run()` execution;
- GameCube controller callbacks;
- direct GameCube MEM1 exposure;
- memory-map registration beginning at guest address `0x80000000`;
- `retro_serialize_size()` / `retro_serialize()` / `retro_unserialize()`;
- rendered and Null graphics paths.

This removes the need for an IPC protocol around a continuously running standalone Dolphin process.

## Why direct libretro instead of RetroArch

RetroArch is a general frontend. Training only needs a small subset of the ABI:

```text
retro_set_environment
retro_set_input_poll
retro_set_input_state
retro_set_video_refresh
retro_set_audio_sample_batch
retro_init
retro_load_game
retro_run
retro_get_memory_data
retro_serialize
retro_unserialize
```

A purpose-built frontend can discard or minimize video/audio during state-only training.

## Memory

The GameCube address space uses big-endian values. MEM1 begins at guest address `0x80000000`.

The frontend should expose typed reads/writes and bulk ranges. Sonic-specific interpretation belongs in the telemetry layer, not in Dolphin.

## Frame semantics

The first major validation task is to establish exactly what one call to `retro_run()` advances for Sonic Riders under the selected Dolphin configuration.

Acceptance criteria:

```text
snapshot S
+ action A
+ one retro_run()
→ exactly one documented simulation step
```

If video frames and game-simulation frames differ, the project must define a canonical simulation step and document the mapping.

## Serialization

Serialization is the preferred reset mechanism. Required test:

```text
snapshot S
+ action trace A
→ trajectory T1

restore S
+ same A
→ trajectory T2

T1 ≈ T2
```

Compare position, speed, Air, Rings, lap, placement, stage progress, player state, and race state.

## Rendering modes

Target modes:

- `STATE_ONLY`: maximum throughput; prefer Null rendering if compatible.
- `PIXEL_TRAINING`: capture frames for visual policies.
- `HUMAN_RENDER`: normal rendering for debugging/evaluation.

## Initial benchmark matrix

Benchmark:

```text
rendered + audio
rendered + muted/discarded audio
Null rendering
Null rendering + minimal callbacks
```

Measure per-worker FPS, aggregate FPS, environment steps/sec, CPU, RAM, GPU, reset latency, and failure rate.

## Fork policy

Do not create a private Dolphin fork unless required. Generic fixes should be proposed to `libretro/dolphin` where practical. Sonic-specific telemetry/reward logic remains entirely outside the emulator.
