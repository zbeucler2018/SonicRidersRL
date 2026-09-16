# Milestone 14: normal-route stage-progress validation

Run the validation after the standard setup:

```bash
scripts/build_runner.sh
uv run python -m sonic_riders_rl.stage_progress_probe
```

The probe starts from the process-local normal-race fixture. It compares 120
neutral P1 frames with 120 frames of forward-stick input, then restores and
replays the forward trace. It requires Player 0's position, speed, and
`stage_progress` to show normal-route movement, while the neutral Player 0
trace remains at the start line.

CPU racers are allowed to progress during neutral frames, so neutral validation
is correctly scoped to Player 0 and the race mode. Exact whole-state equality
is reserved for the repeated forward trace after reset.

## Validated result

On the same GXEE8P/core fixture as Milestone 13, neutral Player 0 position and
stage progress changed by exactly zero. The 120-frame forward trace moved
Player 0 by `30.742255301614108` world units, produced speed
`0.4167484939098358`, and advanced `stage_progress` from `79000.4296875` to
`79000.828125` (delta `0.3984375`). Replaying the trace from the fixture
matched the full race state and full-MEM1 checksum `0x3fd5bb190ee620dc`.

The schema now marks position and speed as validated in a normal P1 race, and
marks stage progress as validated only for this short normal-route start. It
does **not** yet validate reverse movement, rails, alternate routes, shortcuts,
turbulence, falls/respawns, lap transitions, or other tracks.
