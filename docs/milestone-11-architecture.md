# Milestone 11 architecture decision: resolve game mode from a paired REL reference

## Decision

Add a small read-only resolver for the two retail state-machine words
`CurrentGameMode` and `geGame_ModeDetail`. It reconstructs both addresses from
one exact, paired instruction sequence in the dynamically loaded vanilla
`_Main.rel`, then bounds-checks the targets against MEM1.

The resolver returns raw integers and their signed difference only. That
difference uses the community race-state convention only while the game is in
a race mode. It does not mutate game memory, navigate a menu, classify
controller ownership, or expose an environment abstraction.

## Why this approach

The previous player-array resolver already established that `_Main.rel` moves
at runtime, so a RAM constant would be brittle. The paired code site is
stronger than scanning for plausible values: it contains four relocation
immediates plus a fixed instruction tail, and it requires every matching site
to reconstruct the same distinct in-MEM1 address pair.

The code shape comes from the locally pinned `sonicriderste` source's vanilla
`_Main` disassembly, where it loads both words before comparing their
difference. The live probe is the required GXEE8P validation; Tournament
Edition naming remains provenance, not proof by itself.

## Alternatives rejected

- **Fixed guest addresses:** invalid for a dynamically loaded REL.
- **Broad scan for values such as 700:** values are state-dependent and not a
  stable address identity.
- **Raw mode/control writes:** would bypass the normal game state machine and
  cannot establish a realistic RL reset fixture.
- **Treating the attract race as controllable:** Milestone 10 disproved that
  inference; this resolver only helps distinguish flow states while a normal
  menu-driven fixture is established later.
