# Milestone 16: human route trace capture and replay

In the viewer, press `T` to reset to the normal-race fixture and begin a trace.
Press `T` again to write it below `.local/traces/`. The right panel shows the
recording state and saved path. Replay a completed trace with:

```bash
uv run python -m sonic_riders_rl.trace_replay .local/traces/<trace>.json
```

Replay requires each recorded native P1 input frame and its raw Player 0
and race-mode telemetry to match from the same stock fixture. A saved trace is
route evidence to investigate; it does not itself validate rails, shortcuts, or
alternate routes.

## Current manual-validation status

The manual viewer trace and its replay are **skipped pending a user play
session**. No trace has been recorded as evidence, and neither rails nor
shortcuts are validated. Do not replace this with an automatically generated
trace: the purpose of this checkpoint is to preserve a human-controlled route
attempt for later investigation.
