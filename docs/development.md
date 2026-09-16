# Development setup

The checked-in code has no third-party Python runtime dependencies. `uv`
manages the project interpreter and will become the single place to add them
when an environment or training dependency is actually needed. Its cache is
configured in `uv.toml` to remain beneath ignored repository-local `.local/`.

## One-time setup

```bash
git submodule update --init --recursive
uv sync --dev
scripts/setup_dolphin_core.sh
scripts/build_runner.sh
```

`third_party/dolphin-libretro` is a pinned upstream Git submodule. It supplies
the libretro headers and the exact source revision associated with the backend.
The separately downloaded `dolphin_libretro.so`, Dolphin runtime data, reports,
and compiled runner remain under the ignored `.local/` and `build/` directories.
No ROM or emulator runtime artifact is committed.

The setup script downloads the current Linux core only when it is absent. Each
emulator probe records the core version it actually loaded, so a result is
always tied to both the submodule revision and the binary used for the run.

## Everyday commands

```bash
uv run python -m unittest discover -s tests -v
scripts/build_runner.sh
uv run python -m sonic_riders_rl.normal_race_probe
```

The normal-race probe expects the authorized ROM at
`~/Games/GameCube/SonicRiders/sonic_riders_usa.rvz`. All probe output stays in
the repository-local ignored `.local/` directory.
