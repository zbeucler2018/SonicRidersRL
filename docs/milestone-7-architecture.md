# Milestone 7 architecture decision: raw player-control telemetry

## Decision

Extend the version-scoped player decoder with three documented raw fields:

- `input_address` at player offset `0x000`;
- `ai_control` at `0x0BC` (already decoded); and
- `player_type` at `0x0BD`.

Follow each non-null in-MEM1 input pointer through a bounded 0x30-byte
controller decoder. Expose raw controller port, held/edge buttons, sticks, and
connection fields. The decoder does not infer a human/CPU label beyond the
two raw flags.

## Evidence motivating the split

In the retail attract-mode race, live slot 0 had `ai_control=1` and
`player_type=0`, while slots 1–7 had both bytes set. After the Start-driven
presentation transition, slots 0 and 1 had `player_type=0` but still had
`ai_control=1`. Treating `ai_control` as a complete ownership label would
therefore be wrong.

The live input pointers were non-null, MEM1-resident, and 0x30 bytes apart:
`0x801af9f0`, `0x801afa20`, … . Those facts are enough to add a guarded raw
decoder and test P1 input propagation without a fixed global address.

## Alternatives rejected

- **Infer “human controlled” solely from `ai_control`:** contradicted by the
  retail live state above.
- **Hard-code the controller array base:** the player-owned pointer provides a
  safer relocation-tolerant boundary.
- **Write the flags to force control:** would mask their semantics and bypass
  the game's normal state machine.
- **Promote these bytes to policy semantics now:** their behavior remains
  community-derived until a normal-flow controllable race validates it.
