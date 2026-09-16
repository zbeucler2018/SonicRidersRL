# Milestone 16: human route trace contract

`T` starts recording by first restoring the normal-race fixture; `T` again
ends the recording and writes an ignored, versioned JSON trace under
`.local/traces/`. Each four-frame step records native P1 controller state and
raw Player 0/race-mode telemetry. `trace_replay` reboots the same fixture and
requires every recorded step to match exactly. These traces are preparation for
route probes, not evidence that rails, shortcuts, or alternate routes are
validated.
