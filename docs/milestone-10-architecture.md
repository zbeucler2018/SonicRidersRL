# Milestone 10 architecture decision: reject the attract transition as a P1 fixture

## Decision

Do not treat Sonic Riders' post-attract transition as a controllable-race
fixture. Retain it only as a repeatable telemetry/reset state.

The experiment used one serialized transition state and compared neutral,
P0 Start/A/B, and P1 Start traces. It decoded both raw control flags and the
player-owned controller pointers before and after the transition.

## Evidence

At the transition boundary:

- Players 0 and 1 had `ai_control=0`, `player_type=0`.
- They mapped to controller ports 0 and 1, respectively.
- Players 2 and 3 mapped to ports 2 and 3; the remaining AI slots referenced
  port 0 in this state.

After 1,200 caller-driven frames, Players 0 and 1 retained `player_type=0`
but had `ai_control=1`, as did the remaining players. Neutral and stick traces
then produced identical decoded player trajectories from the same snapshot.

This distinguishes controller plumbing (working) from racer ownership (still
AI-driven). It also confirms neither raw flag alone is a complete ownership
classification.

## Consequence

The next controllable-race task must enter a normal game mode through its
ordinary menu/state machine, then prove that a port-specific trace changes the
corresponding player trajectory from a shared snapshot. Do not force this by
writing control flags or selecting a mode through raw memory.
