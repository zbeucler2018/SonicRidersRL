# Milestone 3: snapshot replay determinism

## Scope

`python -m sonic_riders_rl.determinism_probe`:

1. boots vanilla `GXEE8P` to the controlled menu state;
2. resolves and validates the relocatable player array;
3. captures an in-memory savestate;
4. runs a 330-frame four-port controller trace;
5. checksums full MEM1, checksums `players[]`, and decodes players;
6. restores the same snapshot and reruns the exact trace; and
7. requires all three outcomes to be equal.

No wall-clock pacing, rendered observation, environment interface, reward, or
trainer is involved.

## Run it

```bash
scripts/build_runner.sh
python3 -m unittest discover -s tests -v
python3 -m sonic_riders_rl.determinism_probe
```

The report is written to `.local/reports/milestone3.json`.

## Limit

This proves exact replay for a controlled menu-state snapshot within one worker
process. The next determinism gate is a reproducible race-start snapshot with
validated position, speed, Air, Rings, lap, placement, player-state, and
stage-progress fields. Do not interpret this milestone as that later gate.
