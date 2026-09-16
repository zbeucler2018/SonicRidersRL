# Milestone 13 architecture decision: process-local normal-race reset fixture

## Decision

Promote the proven stock Free Race checkpoint into a small
`NormalRaceFixture` API. It holds the runner-owned in-memory snapshot token,
the resolved telemetry addresses, complete reset-critical baseline telemetry,
and version-bound metadata. `fixture.reset(backend)` restores the token then
requires the race mode, all eight decoded racer records, and the entire MEM1
checksum to match the captured baseline exactly.

The fixture remains intentionally process-local. A runner snapshot identifier
is valid only in the runner process that allocated it; a worker creates its
fixture once through the stock menu and reuses it for episode resets.

## Why

This directly implements the PRD's serialized-reset contract without adding an
environment or training abstraction. It records the game SHA-256,
Dolphin-libretro source revision and core version, frontend revision, selected
character/gear, mode, player count, snapshot checksum, full-MEM1 checksum, and
the versioned memory schema. The default-course track field is explicitly
`default-course-unresolved`: guessing a semantic track name would be worse than
recording the current telemetry limitation.

## Rejected alternatives

- **Persisting raw savestate bytes to disk:** the current native protocol
  exposes deliberately in-memory tokens only. Disk persistence adds a new
  format and compatibility surface without helping fast same-worker resets.
- **Resetting through menus every episode:** it is slower and would weaken the
  reset/determinism guarantee already available through `retro_unserialize()`.
- **Starting observations, rewards, or Gymnasium now:** those need a stable,
  metadata-bound reset boundary first.
