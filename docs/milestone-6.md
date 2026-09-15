# Milestone 6: game-visible P1 input validation

This milestone proves that native P1 input reaches the retail game state. It
does not add an environment, semantic events, observations, rewards, or any
RL framework integration.

## Probe

```bash
scripts/build_runner.sh
python3 -m sonic_riders_rl.game_input_probe
```

The probe reaches the stock attract-mode race, snapshots it in memory, and
compares a 600-frame neutral trace with a one-frame GameCube Start pulse
followed by 599 neutral frames. It requires:

- Dolphin to query a non-neutral P1 Start value;
- the Start trace to replay exactly from the same snapshot;
- different full-MEM1 checksums for Start and neutral; and
- different SHA-256 fingerprints of their captured 640x528 PPM frames.

The result is saved as `.local/reports/milestone6.json`; the three diagnostic
frames remain in the worker save directory under ignored `.local/`.

## Scope boundary

The attract-mode racers are AI-controlled. The probe demonstrates that P1
causes a deterministic visible game transition, not that P1's stick steers a
racer. A normal-flow menu/race configuration that produces a human-controlled
slot is still required before promoting player-0 position response or
stage-progress semantics to `vanilla-validated`.
