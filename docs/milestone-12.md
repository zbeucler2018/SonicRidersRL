# Milestone 12: normal menu-driven controllable P1 fixture

Run the validation after building the runner:

```bash
scripts/build_runner.sh
python3 -m sonic_riders_rl.normal_race_probe
```

The probe uses only caller-driven frames and port-0 GameCube input. It writes
its report and any Dolphin runtime files beneath `.local/` in the repository.

It verifies all of the following without writing retail game memory:

- the stock GXEE8P title flow reaches Free Race through the normal menus;
- the active-race checkpoint has `game_mode=700` and mode-detail delta `3`;
- Player 0 has `ai_control=False` and a connected controller on port 0;
- a negative P1 left-stick Y trace moves Player 0 relative to a neutral trace
  from the same savestate; and
- replaying that trace from the savestate reproduces both Player 0 telemetry
  and a full-MEM1 checksum exactly.

The fixture is a validation probe, not an RL environment. It does not add
observations, rewards, Gymnasium/PettingZoo adapters, policies, or training.

## Validated result

With `dolphin_libretro.so` `2606.0.393+ed70219e8b`, the complete probe reached
the active stock Free Race checkpoint after 6,219 caller-driven frames. Player
0 was assigned character 0, had `ai_control=False`, and referenced connected
controller port 0.

From the 92,880,283-byte in-memory savestate, 120 neutral frames left Player
0 at the start line. The same 120 frames with left-stick `(x=12000,
y=-32768)` moved Player 0 by `31.158614658355877` world units and raised its
speed to `0.41816988587379456`. Replaying that forward trace from the same
savestate reproduced Player 0 telemetry and the full-MEM1 checksum
`0x614ac0a7c7ba6482` exactly.
