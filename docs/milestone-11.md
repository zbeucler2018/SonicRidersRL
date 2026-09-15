# Milestone 11: game-mode telemetry

This milestone adds a read-only, relocation-safe way to inspect the retail
game-mode state machine. It is not a menu driver or an environment API.

## Run it

```bash
scripts/build_runner.sh
python3 -m unittest discover -s tests -v
python3 -m sonic_riders_rl.game_mode_probe
```

The probe starts the stock GXEE8P disc, resolves both mode words after the REL
is loaded, records boot-flow and stock-attract checkpoints, and requires the
latter to be the retail Free Race mode (`700`). It writes the result to
`.local/reports/milestone11.json`.

`mode_detail_delta` is the signed `mode_detail - game_mode` difference. It
matches the community race-state convention only in a race mode; it remains
raw telemetry during boot and menus.

## Validated result

With `dolphin_libretro.so` `2606.0.393+ed70219e8b`, the paired reference at
`0x8059ea88` resolved game-mode words at `0x806129a0` and `0x806129a4`.

| Checkpoint | Caller-driven frames | Game mode | Mode detail | Delta |
|---|---:|---:|---:|---:|
| Boot flow | 600 | 2000 | 0 | -2000 |
| Stock attract race | 9,000 | 700 | 703 | 3 |

The boot-flow value is deliberately not named: this milestone proves address
identity and records the raw state, rather than inferring a menu semantic.
