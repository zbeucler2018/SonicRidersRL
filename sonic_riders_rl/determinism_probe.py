"""Replay one controller trace twice from one snapshot and compare outcomes."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .backend import BackendConfig, ControllerState, GameCubeButton, LibretroDolphinBackend
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
    parser.add_argument("--save-dir", type=Path, default=root / ".local/runtime/saves/milestone3")
    parser.add_argument("--boot-frames", type=int, default=600)
    parser.add_argument("--report", type=Path, default=root / ".local/reports/milestone3.json")
    return parser.parse_args()


def _trace() -> tuple[tuple[dict[int, ControllerState], int], ...]:
    """A deliberately non-neutral, four-port trace with no wall-clock pacing."""

    return (
        (
            {
                0: ControllerState(buttons=GameCubeButton.A.mask),
                1: ControllerState(buttons=GameCubeButton.B.mask),
                2: ControllerState(left_trigger=32767),
                3: ControllerState(right_trigger=32767),
            },
            30,
        ),
        (
            {
                0: ControllerState(left_x=24576, left_y=-8192),
                1: ControllerState(left_x=-24576, right_x=16384),
                2: ControllerState(right_y=-16384, left_trigger=12000),
                3: ControllerState(right_x=-16384, right_trigger=12000),
            },
            120,
        ),
        ({}, 180),
    )


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
        assert backend.health()["game_id_GXEE8P"], "Dolphin did not identify GXEE8P"
        resolution = resolve_players_array(backend)
        validate_menu_player_order(read_players(backend, resolution))
        snapshot = backend.snapshot()
        trace = _trace()

        def play_trace() -> tuple[int, int, tuple[object, ...]]:
            for controllers, frames in trace:
                backend.step(controllers, frames=frames)
            return (
                backend.memory_checksum(backend.memory.guest_base, backend.memory.size),
                backend.memory_checksum(
                    resolution.guest_base, resolution.stride * resolution.player_count
                ),
                read_players(backend, resolution),
            )

        first_mem1, first_players_memory, first_players = play_trace()
        backend.restore(snapshot)
        second_mem1, second_players_memory, second_players = play_trace()
        assert first_mem1 == second_mem1, "MEM1 diverged after identical restored replay"
        assert first_players_memory == second_players_memory, "player array diverged after replay"
        assert first_players == second_players, "typed player telemetry diverged after replay"

        report = {
            "game_id": "GXEE8P",
            "core_library_version": backend.library_version,
            "snapshot": {"bytes": snapshot.size, "checksum": f"0x{snapshot.checksum:016x}"},
            "trace": {
                "commands": len(trace),
                "frames": sum(frames for _, frames in trace),
                "ports": [0, 1, 2, 3],
            },
            "outcome": {
                "mem1_fnv1a64": f"0x{first_mem1:016x}",
                "players_fnv1a64": f"0x{first_players_memory:016x}",
                "typed_players_equal": True,
                "sample_player_0": asdict(first_players[0]),
            },
            "total_frames": backend.health()["total_frames"],
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
