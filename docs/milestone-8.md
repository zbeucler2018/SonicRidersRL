# Milestone 8: active-race frame semantics

This milestone defines the backend's low-level frame contract. It does not add
an environment interface, action repeat policy, observations, rewards, events,
or training code.

## Canonical frame

After active-race entry, one requested backend frame is one `retro_run()` call.
On the pinned Dolphin core and GXEE8P image, that call produces exactly one
video callback and one game-side Player 0 controller-clock tick.

## Run it

```bash
scripts/build_runner.sh
python3 -m sonic_riders_rl.frame_semantics_probe
```

The probe reaches the stock attract-mode race and issues 1-, 60-, and
300-frame requests. For every request it requires equal deltas in:

- requested/returned runner frames;
- runner total frames;
- core video callbacks; and
- `Player.input->timeSinceLastInput`.

It also requires nonzero Player 0 displacement and a changed raw
`stage_progress` candidate. The report is `.local/reports/milestone8.json`.

The first two startup calls can occur before video output begins, so boot is
not used to define the equality. `retro_run()` remains the canonical frontend
operation throughout; the steady-state probe establishes its game/frame
meaning for Sonic Riders.
