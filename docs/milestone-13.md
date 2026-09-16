# Milestone 13: verified normal-race reset fixture

Run the validation after the standard setup:

```bash
scripts/build_runner.sh
uv run python -m sonic_riders_rl.normal_race_reset_probe
```

The probe hashes the authorized ROM, follows the stock GXEE8P menu to the
human-controlled Free Race, captures one in-memory snapshot, deliberately
advances P1 between resets, and restores that snapshot repeatedly. It writes
the version-bound fixture manifest and timing report to
`.local/reports/milestone13.json`.

The reset token is intentionally local to its one native runner process. It is
not a disk save and cannot be reused after that worker exits. Each future
worker will bootstrap its own fixture once, then call `fixture.reset(backend)`
for fast episode resets.

## Validated result

With `dolphin_libretro.so` `2606.0.393+ed70219e8b` and source revision
`ed70219e8bf86717d505b56a830d14ee7e7acce5`, the probe recorded the authorized
GXEE8P RVZ SHA-256, schema `GXEE8P/vanilla_ntscu_v1@1`, the selected character
and gear, mode/player count, serial-state checksum, and full-MEM1 baseline
checksum. The default course is recorded honestly as
`default-course-unresolved`; identifying it belongs to later track telemetry,
not this reset milestone.

After 30 caller-driven forward-input frames before each reset, 32 consecutive
restores exactly reproduced raw race mode, all eight decoded racer records,
and the full 24 MiB MEM1 checksum. Restore latency was 49.33 ms mean, 47.62 ms
median, and 89.87 ms maximum on this host. Two identical 120-frame P1 forward
traces from the same fixture also produced the identical full race state and
MEM1 checksum `0x097ae59e38abd7df`.
