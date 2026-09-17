# Milestone 15: human debug viewer

Start the viewer after the normal setup:

```bash
uv run python -m sonic_riders_rl.debug_viewer
```

Open the printed `http://127.0.0.1:8765` URL on the Ubuntu host. The game frame
is rendered into the left canvas; the right panel separately shows raw race
mode and live Player 0 telemetry. It never draws debug text over the game.

Controls: `WASD` maps to the left stick, `Z` is A, `X` is B, `Enter` is Start,
`Q`/`E` are analog triggers, and `R` restores the normal-race fixture. When
present, the host's Sunshine/Moonlight virtual controller is read directly from
`/dev/input/js1` and combined with keyboard input; its raw axes/buttons appear
in the right panel for mapping checks. The viewer is a deliberately human-paced
debugging tool, not a training runner. It polls controls and advances one
emulated frame at 60 Hz by default, then captures video separately every two
frames (30 Hz). This avoids the earlier four-frame/15 Hz input cadence, which
could add noticeable avoidable input delay on top of remote-streaming latency.

Smoke validation served a 640x528 PPM game frame and live Free Race telemetry
(`game_mode=700`, state delta `3`) through separate localhost endpoints.
