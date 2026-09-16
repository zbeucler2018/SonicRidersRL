# Milestone 14 architecture decision: normal-route stage-progress gate

## Decision

Add a narrow integration probe that starts from the validated process-local
normal-race fixture, compares a neutral trace with a P1 forward trace, and
requires `Player + 0xBC4` (`stage_progress`) to advance alongside actual world
movement and speed. The same forward trace must replay exactly from the
fixture, including full MEM1.

## Why

The PRD identifies stage progress as the leading dense reward candidate, but
the current schema correctly labels it unvalidated. The earliest honest gate
is a human-controlled normal-route start, not an inference from an attract
race or a community offset alone.

## Scope boundary

This validates only a short default-route start segment. Reverse travel, rails,
Flight/Power routes, shortcuts, turbulence, falls/respawns, lap transitions,
and every track remain unvalidated and are explicitly deferred to route
coverage work. No reward, observation, Gymnasium, or semantic-event code is
introduced here.
