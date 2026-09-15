"""Validate the relocatable GXEE8P game-mode telemetry substrate.

This read-only probe samples the retail state machine at boot-flow and stock
attract-race checkpoints. It intentionally does not navigate menus or
declare that the attract demo is a controllable P1 race.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .backend import BackendConfig, LibretroDolphinBackend
from .race_probe import RACE_BOOT_FRAMES
from .telemetry import read_game_mode, resolve_game_mode


TITLE_BOOT_FRAMES = 600
FREE_RACE_MODE = 700


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_args() -> argparse.Namespace:
    root = _project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", type=Path, default=root / "build/sonic-libretro-runner")
    parser.add_argument("--core", type=Path, default=root / ".local/core/dolphin_libretro.so")
    parser.add_argument(
        "--rom",
        type=Path,
        default=Path("~/Games/GameCube/SonicRiders/sonic_riders_usa.rvz").expanduser(),
    )
    parser.add_argument("--system-dir", type=Path, default=root / ".local/runtime/system")
    parser.add_argument("--save-dir", type=Path, default=root / ".local/runtime/saves/milestone11")
    parser.add_argument("--title-frames", type=int, default=TITLE_BOOT_FRAMES)
    parser.add_argument("--attract-frames", type=int, default=RACE_BOOT_FRAMES)
    parser.add_argument("--report", type=Path, default=root / ".local/reports/milestone11.json")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.title_frames < 1:
        raise ValueError("--title-frames must be positive")
    if args.attract_frames < args.title_frames:
        raise ValueError("--attract-frames must be at least --title-frames")

    config = BackendConfig(
        runner_path=args.runner,
        core_path=args.core,
        rom_path=args.rom,
        system_dir=args.system_dir,
        save_dir=args.save_dir,
    )
    with LibretroDolphinBackend(config) as backend:
        backend.step(frames=args.title_frames)
        health = backend.health()
        assert health["game_id_GXEE8P"], "Dolphin did not identify GXEE8P"

        resolution = resolve_game_mode(backend)
        title = read_game_mode(backend, resolution)

        backend.step(frames=args.attract_frames - args.title_frames)
        attract = read_game_mode(backend, resolution)
        assert attract.game_mode == FREE_RACE_MODE, (
            f"expected stock attract free-race mode {FREE_RACE_MODE}, received {attract.game_mode}"
        )
        assert 0 <= attract.mode_detail_delta <= 4, (
            f"unexpected attract race-state delta {attract.mode_detail_delta}"
        )

        report = {
            "game_id": "GXEE8P",
            "core_library_version": backend.library_version,
            "resolver": {
                "game_mode_address": f"0x{resolution.game_mode_address:08x}",
                "mode_detail_address": f"0x{resolution.mode_detail_address:08x}",
                "reference_sites": [f"0x{site:08x}" for site in resolution.reference_sites],
                "provenance": resolution.provenance,
            },
            "checkpoints": {
                "boot_flow": {"frames": args.title_frames, **asdict(title)},
                "stock_attract_race": {"frames": args.attract_frames, **asdict(attract)},
            },
            "total_frames": backend.health()["total_frames"],
        }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
