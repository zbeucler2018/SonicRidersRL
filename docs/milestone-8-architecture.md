# Milestone 8 architecture decision: steady-state frame semantics

## Decision

Define one canonical low-level environment frame as one requested
`retro_run()` call after the game is in an active race state. Validate that
definition with three independent steady-state counters:

1. runner `total_frames`;
2. core video callbacks; and
3. Player 0's game-side `time_since_last_input` counter.

The probe also requires nonzero movement and stage-progress deltas to show
that those caller-driven frames advance live game simulation.

## Evidence

From the stock attract-mode fixture, requests of 1, 60, and 300 frames each
produced equal deltas in all three counters. The game-side controller clock
advanced by exactly 1, 60, and 300 respectively, while Player 0's position and
`stage_progress` changed.

The startup path is intentionally not part of this equality: the first two
frontend calls can initialize the core without a video callback. That is a
boot/render initialization detail, not a reason to redefine a simulation
step. Once the active state is reached, video and simulation are one-to-one on
this pinned core/build.

## Alternatives rejected

- **Wall-clock 60 Hz pacing:** violates the PRD and cannot establish an exact
  transition boundary.
- **Treating a video callback as the canonical step:** fails during core
  startup, while `retro_run()` remains the API the frontend controls.
- **Inferring frames from player position alone:** route geometry and
  start-line state make it insufficient without direct counters.
