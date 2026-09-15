"""Validate raw player/controller telemetry against injected P1 inputs.

This remains a read-only telemetry probe. It validates the retail game's
controller record from Player 0's live input pointer, but does not infer a
human/CPU policy role from the two separate player control flags.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .backend import BackendConfig, ControllerState, GameCubeButton, LibretroDolphinBackend
from .race_probe import RACE_BOOT_FRAMES
from .telemetry import read_player_controllers, read_players, resolve_players_array


GAME_BUTTON_START_MASK = 1 << 8
GAME_STICK_MAX = 100


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
    parser.add_argument("--save-dir", type=Path, default=root / ".local/runtime/saves/milestone7")
    parser.add_argument("--boot-frames", type=int, default=RACE_BOOT_FRAMES)
    parser.add_argument("--report", type=Path, default=root / ".local/reports/milestone7.json")
    return parser.parse_args()


def _controller_zero(backend: LibretroDolphinBackend):
    resolution = resolve_players_array(backend)
    players = read_players(backend, resolution)
    controllers = read_player_controllers(backend, players)
    controller = controllers[0]
    if controller is None:
        raise AssertionError("player 0 has no input pointer")
    return resolution, players, controller


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
        boot = backend.step(frames=args.boot_frames)
        health = backend.health()
        assert health["game_id_GXEE8P"], "Dolphin did not identify GXEE8P"
        resolution, players_before, controller_before = _controller_zero(backend)
        assert controller_before.connected, "player 0 controller is not connected"
        assert controller_before.port == 0, "player 0 does not reference GameCube port 0"

        snapshot = backend.snapshot()
        start_step = backend.step(
            {0: ControllerState(buttons=GameCubeButton.START.mask)}, frames=1
        )
        _, players_start, controller_start = _controller_zero(backend)
        assert start_step.player_1_nonzero_input_queries > 0, "Dolphin did not query P1 Start"
        assert controller_start.address == controller_before.address
        assert (controller_start.held_buttons | controller_start.pressed_buttons) & GAME_BUTTON_START_MASK

        backend.restore(snapshot)
        stick_step = backend.step({0: ControllerState(left_x=32767)}, frames=1)
        _, players_stick, controller_stick = _controller_zero(backend)
        assert stick_step.player_1_nonzero_input_queries > 0, "Dolphin did not query P1 stick"
        assert controller_stick.address == controller_before.address
        assert controller_stick.left_stick_x == GAME_STICK_MAX

        report = {
            "game_id": "GXEE8P",
            "core_library_version": backend.library_version,
            "fixture": {
                "kind": "stock attract-mode race",
                "boot_frames": boot.frames,
                "snapshot_size": snapshot.size,
                "snapshot_checksum": f"0x{snapshot.checksum:016x}",
            },
            "player_array": {
                "guest_base": f"0x{resolution.guest_base:08x}",
                "reference_sites": [f"0x{site:08x}" for site in resolution.reference_sites],
            },
            "player_0_before": asdict(players_before[0]),
            "controller_0_before": asdict(controller_before),
            "p1_start": {
                "nonzero_input_queries": start_step.player_1_nonzero_input_queries,
                "player_0": asdict(players_start[0]),
                "controller_0": asdict(controller_start),
                "game_start_bit_observed": True,
            },
            "p1_stick": {
                "nonzero_input_queries": stick_step.player_1_nonzero_input_queries,
                "player_0": asdict(players_stick[0]),
                "controller_0": asdict(controller_stick),
                "left_stick_x": controller_stick.left_stick_x,
            },
            "control_semantics": {
                "ai_control": "raw field only; not an ownership label",
                "player_type": "raw field only; not an ownership label",
            },
            "total_frames": backend.health()["total_frames"],
        }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
