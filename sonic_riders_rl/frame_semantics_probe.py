"""Empirically validate steady-state Sonic Riders frame semantics."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from math import dist
from pathlib import Path

from .backend import BackendConfig, LibretroDolphinBackend
from .race_probe import RACE_BOOT_FRAMES
from .telemetry import PlayerArrayResolution, read_player_controllers, read_players, resolve_players_array


FRAME_REQUESTS = (1, 60, 300)


@dataclass(frozen=True)
class FrameSample:
    total_frames: int
    video_frames: int
    controller_time_since_last_input: int
    stage_progress: float
    x: float
    y: float
    z: float


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
    parser.add_argument("--save-dir", type=Path, default=root / ".local/runtime/saves/milestone8")
    parser.add_argument("--boot-frames", type=int, default=RACE_BOOT_FRAMES)
    parser.add_argument("--report", type=Path, default=root / ".local/reports/milestone8.json")
    return parser.parse_args()


def _sample(backend: LibretroDolphinBackend, resolution: PlayerArrayResolution) -> FrameSample:
    players = read_players(backend, resolution)
    controller = read_player_controllers(backend, players)[0]
    if controller is None:
        raise AssertionError("player 0 has no controller record")
    health = backend.health()
    player = players[0]
    return FrameSample(
        total_frames=health["total_frames"],
        video_frames=health["video_frames"],
        controller_time_since_last_input=controller.time_since_last_input,
        stage_progress=player.stage_progress,
        x=player.x,
        y=player.y,
        z=player.z,
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
        boot = backend.step(frames=args.boot_frames)
        health = backend.health()
        assert health["game_id_GXEE8P"], "Dolphin did not identify GXEE8P"
        resolution = resolve_players_array(backend)
        before = _sample(backend, resolution)
        checks = []
        for requested in FRAME_REQUESTS:
            result = backend.step(frames=requested)
            after = _sample(backend, resolution)
            total_delta = after.total_frames - before.total_frames
            video_delta = after.video_frames - before.video_frames
            controller_delta = (
                after.controller_time_since_last_input - before.controller_time_since_last_input
            )
            displacement = dist((before.x, before.y, before.z), (after.x, after.y, after.z))
            assert result.frames == requested
            assert total_delta == requested
            assert video_delta == requested
            assert controller_delta == requested
            assert displacement > 0.0
            assert after.stage_progress != before.stage_progress
            checks.append(
                {
                    "requested_frames": requested,
                    "step_result_frames": result.frames,
                    "total_frame_delta": total_delta,
                    "video_frame_delta": video_delta,
                    "controller_clock_delta": controller_delta,
                    "position_displacement": displacement,
                    "stage_progress_delta": after.stage_progress - before.stage_progress,
                    "before": asdict(before),
                    "after": asdict(after),
                }
            )
            before = after

        report = {
            "game_id": "GXEE8P",
            "core_library_version": backend.library_version,
            "fixture": {"kind": "stock attract-mode race", "boot_frames": boot.frames},
            "canonical_step": "one requested retro_run call after active-race entry",
            "checks": checks,
            "total_frames": backend.health()["total_frames"],
        }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
