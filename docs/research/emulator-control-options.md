# Emulator Control Options

## Evaluated approaches

### Standalone Dolphin + external control

Possible through memory tools, controller injection, debugger APIs, or a custom IPC layer.

Pros:
- mature UI and debugging;
- easiest manual inspection.

Cons:
- synchronization problem between external process and continuously running emulator;
- more IPC and pause/frame-step coordination;
- more moving parts for high-rate RL.

Status: retain for debugging, not preferred training runtime.

### Felk Dolphin scripting fork

Felk exposes controller overrides, memory access, savestates, pause/resume, frame callbacks and framebuffer callbacks.

It is a valuable reference implementation and scripting/debugging tool. The main RL concern is that a frame event is not inherently the same as a synchronous atomic `step(N)` command while the emulator is paused.

Status: useful reference/fallback, not preferred production hot path.

### Stable-Retro

Stable-Retro is familiar from the zbeucler2018/HotWheelsGym project and now has improving support for hardware-rendered libretro cores. However, using it for Sonic would introduce another abstraction layer between Dolphin-libretro and the Sonic-specific telemetry/multi-agent system.

The project already requires custom four-controller, eight-racer, PettingZoo, semantic-event and self-play functionality, so integrating Dolphin into Stable-Retro would not eliminate enough custom work to justify making it a dependency.

Status: optional future upstream/community contribution, not initial runtime.

### Direct Dolphin-libretro

Preferred approach.

Pros:
- `retro_run()` naturally matches environment stepping;
- direct MEM1 access;
- native libretro controller callbacks;
- in-memory serialization;
- process-level worker isolation;
- minimal runtime surface;
- no IPC needed in the hot path.

Cons:
- must implement a small libretro frontend;
- exact frame semantics and reset determinism must be validated;
- hardware/Null rendering behavior must be benchmarked.

Status: primary backend for the first engineering spike.
