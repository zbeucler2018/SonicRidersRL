"""Validate repeated process-local resets of the stock controllable race."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from statistics import mean, median
import subprocess
from time import perf_counter

from .backend import BackendConfig, ControllerState, LibretroDolphinBackend
from .fixtures import (
    DEFAULT_COURSE_TRACK,
    FixtureValidationError,
    boot_normal_free_race,
    capture_normal_race_fixture,
    read_race_state,
)


RESET_COUNT = 32
MUTATION_FRAMES = 30
REPLAY_FRAMES = 120
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
    parser.add_argument("--save-dir", type=Path, default=root / ".local/runtime/saves/milestone13")
    parser.add_argument("--report", type=Path, default=root / ".local/reports/milestone13.json")
    parser.add_argument("--resets", type=int, default=RESET_COUNT)
    parser.add_argument("--mutation-frames", type=int, default=MUTATION_FRAMES)
    parser.add_argument("--track", default=DEFAULT_COURSE_TRACK)
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_revision(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> None:
    args = _parse_args()
    if args.resets <= 0 or args.mutation_frames <= 0:
        raise ValueError("--resets and --mutation-frames must both be positive")
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

    game_sha256 = _sha256(args.rom)
    frontend_revision = _git_revision(root)
    dolphin_revision = _git_revision(root / "third_party/dolphin-libretro")
    with LibretroDolphinBackend(config) as backend:
        game_mode, players, menu_input_queries = boot_normal_free_race(backend)
        fixture = capture_normal_race_fixture(
            backend,
            game_mode,
            players,
            game_sha256=game_sha256,
            dolphin_libretro_revision=dolphin_revision,
            frontend_revision=frontend_revision,
            track=args.track,
        )

        reset_durations_ms: list[float] = []
        for _ in range(args.resets):
            backend.step({0: FORWARD_TRACE}, frames=args.mutation_frames)
            started = perf_counter()
            fixture.reset(backend)
            reset_durations_ms.append((perf_counter() - started) * 1_000)

        fixture.reset(backend)
        first_result = backend.step({0: FORWARD_TRACE}, frames=REPLAY_FRAMES)
        first_state = read_race_state(backend, game_mode, players)
        fixture.reset(backend)
        replay_result = backend.step({0: FORWARD_TRACE}, frames=REPLAY_FRAMES)
        replay_state = read_race_state(backend, game_mode, players)
        if first_state != replay_state:
            raise FixtureValidationError("identical P1 trace diverged after normal-race reset")
        if first_result.player_1_nonzero_input_queries <= 0:
            raise FixtureValidationError("Dolphin did not consume the P1 trace")

        report = {
            "fixture": asdict(fixture.metadata),
            "menu_input_queries": menu_input_queries,
            "reset_validation": {
                "count": args.resets,
                "mutation_frames_between_resets": args.mutation_frames,
                "all_resets_exact": True,
                "mean_ms": mean(reset_durations_ms),
                "median_ms": median(reset_durations_ms),
                "max_ms": max(reset_durations_ms),
            },
            "replay_validation": {
                "frames": REPLAY_FRAMES,
                "input": {"left_x": FORWARD_TRACE.left_x, "left_y": FORWARD_TRACE.left_y},
                "p1_nonzero_input_queries": first_result.player_1_nonzero_input_queries,
                "exact_race_state_replay": True,
                "first_mem1_checksum": f"0x{first_state.mem1_checksum:016x}",
                "replay_mem1_checksum": f"0x{replay_state.mem1_checksum:016x}",
            },
            "total_frames": backend.health()["total_frames"],
        }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
