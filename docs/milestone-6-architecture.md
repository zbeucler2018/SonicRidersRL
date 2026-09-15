# Milestone 6 architecture decision: snapshot-differential P1 validation

## Decision

Validate the end-to-end P1 input path by comparing two traces from the exact
same serialized, stock attract-mode race state:

```text
snapshot
├── 600 neutral frames
└── one P1 Start frame + 599 neutral frames
```

The probe requires the Start trace to be exactly replayable and to differ from
neutral in both full MEM1 and a captured hardware-rendered PPM frame.

## Why this is the correct boundary now

The runner's per-port callback counters already prove that Dolphin asks for
P1 input. This additional comparison proves a GameCube Start transition
changes the retail game's visible state and MEM1 from the same initial state.
It is therefore evidence of game-level control propagation rather than just
frontend bookkeeping.

The fixture is deliberately the unmodified attract demo, not a RAM-forced
race. Its `ai_control` flags are set, so a stick trace has no player-position
effect there. The milestone does not claim human-racer steering; it makes that
remaining limitation explicit.

## Alternatives rejected

- **Callback counts only:** useful plumbing evidence, but cannot establish a
  game-visible effect.
- **Directly changing control flags or spawning a race through MEM1 writes:**
  would invalidate the normal-game-flow premise and make later reset results
  less trustworthy.
- **A manual visual assertion:** cannot be reproduced in CI or from a saved
  state. The PPM digest makes the visual branch testable without adding a
  pixel-observation interface.
