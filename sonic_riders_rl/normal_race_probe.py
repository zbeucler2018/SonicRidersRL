"""Validate a stock, menu-driven, controllable GXEE8P Free Race fixture.

This module is intentionally a validation probe, not an environment.  It
drives the retail menu entirely through port-0 GameCube input, then proves
that a forward P1 stick trace moves the human-owned Player 0 relative to a
neutral trace from one savestate.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from math import dist
import json
from pathlib import Path

from .backend import BackendConfig, ControllerState, LibretroDolphinBackend
from .fixtures import ACTIVE_RACE_DELTA, FREE_RACE_MODE, boot_normal_free_race
from .telemetry import (
    PlayerArrayResolution,
    PlayerTelemetry,
    read_players,
)


NEUTRAL_TRACE_FRAMES = 120
FORWARD_TRACE = ControllerState(left_x=12_000, left_y=-32_768)


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
    parser.add_argument("--save-dir", type=Path, default=root / ".local/runtime/saves/milestone12")
    parser.add_argument("--report", type=Path, default=root / ".local/reports/milestone12.json")
    return parser.parse_args()


def _p0(backend: LibretroDolphinBackend, players: PlayerArrayResolution) -> PlayerTelemetry:
    return read_players(backend, players)[0]


def main() -> None:
    args = _parse_args()
    config = BackendConfig(
        runner_path=args.runner,
        core_path=args.core,
        rom_path=args.rom,
        system_dir=args.system_dir,
        save_dir=args.save_dir,
    )
    with LibretroDolphinBackend(config) as backend:
        game_mode, players, menu_input_queries = boot_normal_free_race(backend)
        fixture_player = _p0(backend, players)
        snapshot = backend.snapshot()

        neutral_result = backend.step(frames=NEUTRAL_TRACE_FRAMES)
        neutral_player = _p0(backend, players)
        backend.restore(snapshot)
        control_result = backend.step({0: FORWARD_TRACE}, frames=NEUTRAL_TRACE_FRAMES)
        control_player = _p0(backend, players)
        control_checksum = backend.memory_checksum(backend.memory.guest_base, backend.memory.size)

        movement = dist(
            (neutral_player.x, neutral_player.y, neutral_player.z),
            (control_player.x, control_player.y, control_player.z),
        )
        if control_result.player_1_nonzero_input_queries <= 0:
            raise AssertionError("Dolphin did not consume the forward P1 trace")
        if movement <= 0.1:
            raise AssertionError(f"forward P1 trace did not move Player 0: distance={movement}")
        if control_player.ai_control:
            raise AssertionError("P1 forward trace was not applied to a human-owned Player 0")

        backend.restore(snapshot)
        replay_result = backend.step({0: FORWARD_TRACE}, frames=NEUTRAL_TRACE_FRAMES)
        replay_player = _p0(backend, players)
        replay_checksum = backend.memory_checksum(backend.memory.guest_base, backend.memory.size)
        if replay_player != control_player or replay_checksum != control_checksum:
            raise AssertionError("normal-race P1 trace did not replay exactly from its snapshot")

        report = {
            "game_id": "GXEE8P",
            "core_library_version": backend.library_version,
            "fixture": {
                "kind": "stock menu-driven normal Free Race",
                "game_mode": FREE_RACE_MODE,
                "race_state_delta": ACTIVE_RACE_DELTA,
                "menu_input_queries": menu_input_queries,
                "p0": asdict(fixture_player),
            },
            "snapshot": asdict(snapshot),
            "trace": {
                "frames": NEUTRAL_TRACE_FRAMES,
                "input": {"left_x": FORWARD_TRACE.left_x, "left_y": FORWARD_TRACE.left_y},
                "neutral_p0": asdict(neutral_player),
                "forward_p0": asdict(control_player),
                "p0_position_distance": movement,
                "neutral_nonzero_input_queries": neutral_result.player_1_nonzero_input_queries,
                "forward_nonzero_input_queries": control_result.player_1_nonzero_input_queries,
                "replay_nonzero_input_queries": replay_result.player_1_nonzero_input_queries,
                "forward_mem1_checksum": f"0x{control_checksum:016x}",
                "replay_mem1_checksum": f"0x{replay_checksum:016x}",
                "exact_replay": True,
            },
            "total_frames": backend.health()["total_frames"],
        }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
