"""Live validation for the post-substrate telemetry reconnaissance milestone."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .backend import (
    BackendConfig,
    ControllerState,
    GameCubeButton,
    LibretroDolphinBackend,
    MEM1_GUEST_BASE,
)
from .telemetry import read_players, resolve_players_array, validate_menu_player_order


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
    parser.add_argument("--save-dir", type=Path, default=root / ".local/runtime/saves/milestone2")
    parser.add_argument("--boot-frames", type=int, default=600)
    parser.add_argument("--report", type=Path, default=root / ".local/reports/milestone2.json")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.boot_frames < 1:
        raise ValueError("--boot-frames must be positive")
    config = BackendConfig(
        runner_path=args.runner,
        core_path=args.core,
        rom_path=args.rom,
        system_dir=args.system_dir,
        save_dir=args.save_dir,
    )
    with LibretroDolphinBackend(config) as backend:
        backend.step(frames=args.boot_frames)
        health = backend.health()
        assert health["game_id_GXEE8P"], "Dolphin did not identify GXEE8P"

        resolution = resolve_players_array(backend)
        players = read_players(backend, resolution)
        validate_menu_player_order(players)

        # This write never advances emulation while mutated.  It proves the
        # bounded write channel, then restores the exact pre-write savestate.
        snapshot = backend.snapshot()
        original = backend.read_memory(MEM1_GUEST_BASE, 1)
        changed = bytes((original[0] ^ 0x01,))
        backend.write_memory(MEM1_GUEST_BASE, changed)
        assert backend.read_memory(MEM1_GUEST_BASE, 1) == changed
        backend.restore(snapshot)
        assert backend.read_memory(MEM1_GUEST_BASE, 1) == original

        # Ports 0 and 1 prove distinct digital buttons. Ports 2 and 3 use
        # only analog triggers, covering the libretro analog-button path.
        controls = {
            0: ControllerState(buttons=GameCubeButton.A.mask),
            1: ControllerState(buttons=GameCubeButton.B.mask),
            2: ControllerState(left_trigger=32767),
            3: ControllerState(right_trigger=32767),
        }
        input_step = backend.step(controls, frames=120)
        assert all(count > 0 for count in input_step.input_queries_by_port)
        assert all(count > 0 for count in input_step.nonzero_input_queries_by_port)

        report = {
            "game_id": "GXEE8P",
            "core_library_version": backend.library_version,
            "player_array": {
                "guest_base": f"0x{resolution.guest_base:08x}",
                "reference_sites": [f"0x{site:08x}" for site in resolution.reference_sites],
                "stride": resolution.stride,
                "player_count": resolution.player_count,
                "provenance": resolution.provenance,
                "fresh_menu_character_ids": [player.character for player in players],
            },
            "sample_player_0": asdict(players[0]),
            "bounded_write_restore": {
                "guest_address": f"0x{MEM1_GUEST_BASE:08x}",
                "bytes": 1,
                "restored": True,
            },
            "four_port_input": {
                "frames": input_step.frames,
                "queries_by_port": input_step.input_queries_by_port,
                "nonzero_queries_by_port": input_step.nonzero_input_queries_by_port,
                "port_controls": ["A", "B", "L trigger", "R trigger"],
            },
            "total_frames": backend.health()["total_frames"],
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
