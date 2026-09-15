# Milestone 4: reset-stress validation

## Scope

This milestone validates the fast reset primitive under repetition, without an
RL environment. A single worker bootstraps a controlled GXEE8P menu state,
captures one in-memory snapshot, and repeats:

```text
restore snapshot
→ apply a non-neutral P1 state
→ advance a caller-selected number of frames
→ periodic worker health check
```

After the final cycle it restores once more and requires a full-MEM1 checksum
to equal the pre-stress baseline.

## Run it

```bash
scripts/build_runner.sh
python3 -m sonic_riders_rl.reset_stress_probe
```

The default is 10,000 one-frame rollout/reset cycles, satisfying PRD
infrastructure gate N at the emulator-control level. Use `--cycles 10` only as
a quick smoke test; it is not the gate result. The report is written to
`.local/reports/milestone4.json`.

## Limit

This validates that the worker survives repetitive resets and returns to the
same menu snapshot. It does not yet prove that a loaded race snapshot preserves
race semantics; that requires a controlled race-entry fixture and the
in-race telemetry validation that follows it.
