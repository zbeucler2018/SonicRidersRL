# Milestone 5: real-race telemetry and snapshot replay

This milestone promotes the existing player-structure reconnaissance from a
menu-only invariant to a stock, moving retail race fixture. It adds no
environment, observation, event, reward, Gymnasium, PettingZoo, or training
code.

## What the probe does

`python3 -m sonic_riders_rl.race_probe`:

1. boots the authorized GXEE8P image and advances exactly 9,000 frontend calls;
2. confirms the hardware video callback reports 640x528 and saves a diagnostic
   PPM frame below the worker's ignored `.local/` directory;
3. resolves the relocated vanilla `players[]` reference again in live race
   code;
4. validates all eight records have slot indices 0–7, `ai_control` set, finite high-priority
   numeric fields, a placement permutation 0–7, and independent motion over
   120 more frames;
5. snapshots the live race, replays the same 330-frame non-neutral P1 trace
   twice, and requires exact full-MEM1 and decoded-player equality; and
6. writes the evidence to `.local/reports/milestone5.json`.

The trace makes the core consume native P1 digital/stick/trigger values while
the race is running. The fixture is the stock attract demo, whose eight
`ai_control` flags are set, so it is not evidence that those inputs steer racer
0 or a complete human/CPU classification.

Fresh boots reliably reach the demo race but are not asserted to be bitwise
identical before its snapshot. The probe's determinism assertion begins after
the in-memory race snapshot, as required by the serialized-state contract.

## Run it

```bash
scripts/build_runner.sh
python3 -m unittest discover -s tests -v
python3 -m sonic_riders_rl.race_probe
```

The final command takes roughly the time needed to emulate 9,450 frames on the
host. Its elapsed wall time is never part of the fixture: every state change is
driven by explicit frame counts.

## Scope and remaining validation

This validates a real eight-racer state, race snapshot restore, and exact
replay for the pinned core/image. It does **not** yet validate:

- a menu-to-race setup with a human-controlled P1;
- game-level response of P1 movement/buttons in that controlled race;
- semantic interpretation of `stage_progress`, Air, Rings, lap, or player
  state across route variants; or
- state-only/Null rendering performance.

Those are the next reverse-engineering and backend validation tasks; pixel
observations and RL integrations remain out of scope.
