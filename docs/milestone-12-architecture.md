# Milestone 12 architecture decision: normal-flow P1 fixture

## Decision

Keep the existing stock Dolphin-libretro subprocess backend and add a narrow,
menu-driven validation fixture. The fixture drives the fresh USA retail menu
with port-0 GameCube input only, takes a savestate once a normal Free Race is
active, and compares neutral movement with a forward-stick trace.

## Why

The backend was already able to boot GXEE8P, step caller-driven frames, inject
all controller ports, expose MEM1, and restore snapshots. The missing evidence
was game ownership: the stock attract race has `ai_control=1` for every racer.
The normal path provides the smallest stock fixture where Player 0 is
human-owned and references connected port 0.

The tested retail sequence is deliberately concrete: Start enters the title
flow; eleven A confirmations reach character/gear selection; Start commits the
selection; A confirms the default course. The active checkpoint is retail
Free Race (`CurrentGameMode=700`, mode-detail delta `3`). At that checkpoint,
negative left-stick Y moves Player 0; face buttons and triggers do not move a
start-line racer by themselves.

## Rejected alternatives

- Writing game memory to force a roster, race state, or player position would
  hide the exact stock control behavior this milestone needs to establish.
- Reusing the attract race would keep the known all-AI ownership ambiguity.
- A Gym or multi-agent wrapper would add policy-facing abstractions before the
  controllable stock fixture is proven.
