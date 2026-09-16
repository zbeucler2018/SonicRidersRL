"""Validate the first normal-route behavior of GXEE8P stage progress."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from math import dist
import hashlib
import json
from pathlib import Path
import subprocess

from .backend import BackendConfig, ControllerState, LibretroDolphinBackend
from .fixtures import (
    DEFAULT_COURSE_TRACK,
    FixtureValidationError,
    RaceState,
    boot_normal_free_race,
    capture_normal_race_fixture,
    read_race_state,
)


TRACE_FRAMES = 120
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
    parser.add_argument("--save-dir", type=Path, default=root / ".local/runtime/saves/milestone14")
    parser.add_argument("--report", type=Path, default=root / ".local/reports/milestone14.json")
    parser.add_argument("--frames", type=int, default=TRACE_FRAMES)
    parser.add_argument("--track", default=DEFAULT_COURSE_TRACK)
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_revision(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()


def _p0(state: RaceState):
    return state.players[0]


def main() -> None:
    args = _parse_args()
    if args.frames <= 0:
        raise ValueError("--frames must be positive")
    root = _project_root()
    if not args.rom.is_file():
        raise FileNotFoundError(args.rom)
    config = BackendConfig(
        runner_path=args.runner,
        core_path=args.core,
        rom_path=args.rom,
        system_dir=args.system_dir,
        save_dir=args.save_dir,
    )
    with LibretroDolphinBackend(config) as backend:
        game_mode, players, menu_input_queries = boot_normal_free_race(backend)
        fixture = capture_normal_race_fixture(
            backend,
            game_mode,
            players,
            game_sha256=_sha256(args.rom),
            dolphin_libretro_revision=_git_revision(root / "third_party/dolphin-libretro"),
            frontend_revision=_git_revision(root),
            track=args.track,
        )
        baseline = fixture.baseline

        fixture.reset(backend)
        backend.step(frames=args.frames)
        neutral = read_race_state(backend, game_mode, players)

        fixture.reset(backend)
        input_result = backend.step({0: FORWARD_TRACE}, frames=args.frames)
        forward = read_race_state(backend, game_mode, players)

        fixture.reset(backend)
        backend.step({0: FORWARD_TRACE}, frames=args.frames)
        replay = read_race_state(backend, game_mode, players)

        baseline_p0 = _p0(baseline)
        neutral_p0 = _p0(neutral)
        neutral_position_distance = dist(
            (baseline_p0.x, baseline_p0.y, baseline_p0.z),
            (neutral_p0.x, neutral_p0.y, neutral_p0.z),
        )
        neutral_stage_progress_delta = neutral_p0.stage_progress - baseline_p0.stage_progress
        if neutral.game_mode != baseline.game_mode:
            raise FixtureValidationError("neutral trace changed the active race mode")
        if neutral_position_distance > 0.1 or abs(neutral_stage_progress_delta) > 0.01:
            raise FixtureValidationError("neutral P1 trace advanced from the start line")
        if input_result.player_1_nonzero_input_queries <= 0:
            raise FixtureValidationError("Dolphin did not consume the forward P1 trace")
        if replay != forward:
            raise FixtureValidationError("forward normal-route trace did not replay exactly")

        forward_p0 = _p0(forward)
        stage_progress_delta = forward_p0.stage_progress - baseline_p0.stage_progress
        position_distance = dist(
            (baseline_p0.x, baseline_p0.y, baseline_p0.z),
            (forward_p0.x, forward_p0.y, forward_p0.z),
        )
        if stage_progress_delta <= 0.01:
            raise FixtureValidationError(
                f"forward P1 trace did not advance stage progress: delta={stage_progress_delta}"
            )
        if position_distance <= 0.1 or forward_p0.speed <= 0.1:
            raise FixtureValidationError("forward P1 trace did not produce normal-route movement")

        report = {
            "fixture": asdict(fixture.metadata),
            "menu_input_queries": menu_input_queries,
            "trace": {
                "frames": args.frames,
                "input": asdict(FORWARD_TRACE),
                "neutral_p0_position_distance": neutral_position_distance,
                "neutral_p0_stage_progress_delta": neutral_stage_progress_delta,
                "exact_forward_replay": True,
                "p1_nonzero_input_queries": input_result.player_1_nonzero_input_queries,
                "p0_position_distance": position_distance,
                "p0_speed": forward_p0.speed,
                "p0_stage_progress_start": baseline_p0.stage_progress,
                "p0_stage_progress_end": forward_p0.stage_progress,
                "p0_stage_progress_delta": stage_progress_delta,
                "forward_mem1_checksum": f"0x{forward.mem1_checksum:016x}",
                "replay_mem1_checksum": f"0x{replay.mem1_checksum:016x}",
            },
            "total_frames": backend.health()["total_frames"],
        }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
