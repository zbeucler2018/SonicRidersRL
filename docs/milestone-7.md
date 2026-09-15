# Milestone 7: player-control telemetry validation

This milestone adds the smallest safe decoder needed to observe the game's own
player/controller bridge. It does not implement a normal-flow menu script,
environment, observation, reward, event detector, or RL library.

## New raw fields

For each of the eight version-resolved player records, telemetry now exposes:

- `input_address` (`0x000`);
- `ai_control` (`0x0BC`); and
- `player_type` (`0x0BD`).

`read_player_controllers()` follows non-null `input_address` values only when
their full 0x30-byte records fit within MEM1. It returns raw timing, held/edge
buttons, sticks, controller port, and connection fields.

## Run it

```bash
scripts/build_runner.sh
python3 -m unittest discover -s tests -v
python3 -m sonic_riders_rl.control_telemetry_probe
```

The live probe starts from the stock attract-mode race and verifies that:

1. Player 0 points to an in-MEM1, connected controller record on port 0.
2. A caller-injected P1 Start frame appears as the game-internal Start bit.
3. A caller-injected full-right P1 stick frame appears as `left_stick_x=100`.

It writes `.local/reports/milestone7.json`.

## Semantic boundary

The raw `ai_control` and `player_type` bytes are not interchangeable. The
attract fixture demonstrates combinations such as `ai_control=1`,
`player_type=0`, so callers must not use either as a complete human/CPU label.
A normal-flow controllable race remains necessary before assigning that
meaning or claiming direct P1 steering.
