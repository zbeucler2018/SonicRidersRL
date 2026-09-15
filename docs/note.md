## Implementation note

Treat the architecture and behavioral requirements in this PRD as authoritative, but **do not treat the current Docker, Dolphin-libretro, or Null-renderer implementation as a required design**.

Previous work attempted a custom Dolphin-libretro frontend running inside Docker with the Null renderer. That path exposed several emulator/runtime issues and should be considered an abandoned prototype unless investigation shows it is clearly the best option.

Prioritize the simplest robust implementation that satisfies the actual requirements:

* programmatic Sonic Riders boot
* deterministic/exact frame advancement
* GameCube controller input injection
* direct emulated RAM access
* savestate/reset support
* no real-time 60 Hz pacing requirement
* ability to run many independent emulator workers later
* clean Python-facing backend API

It is acceptable to use standalone Dolphin, modify Dolphin directly, use another Dolphin embedding approach, run outside Docker, use a normal graphics backend, or otherwise change the implementation substantially.

Do not optimize for headless rendering until the core control loop, memory access, inputs, and savestates are working reliably.

Existing experimental Dolphin patches and frontend code may be inspected for useful findings, but should not be assumed correct or preserved.
