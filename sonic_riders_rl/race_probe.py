"""Validate real-race telemetry and snapshot replay in Sonic Riders' attract demo.

The vanilla NTSC-U boot sequence reliably reaches a race demonstration after
9,000 caller-driven ``retro_run()`` calls. The fixture has eight active AI
racers, so it is useful for validating the physical player layout and
race-state reset without pretending it is yet a user-controlled race setup.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from math import dist, isfinite
from pathlib import Path

from .backend import BackendConfig, ControllerState, GameCubeButton, LibretroDolphinBackend
from .telemetry import PlayerArrayResolution, PlayerTelemetry, read_players, resolve_players_array


RACE_BOOT_FRAMES = 9_000
ROSTER_SIZE = 8


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
    parser.add_argument("--save-dir", type=Path, default=root / ".local/runtime/saves/milestone5")
    parser.add_argument("--boot-frames", type=int, default=RACE_BOOT_FRAMES)
    parser.add_argument("--report", type=Path, default=root / ".local/reports/milestone5.json")
    return parser.parse_args()


def _validate_active_demo_roster(players: tuple[PlayerTelemetry, ...]) -> None:
    """Check independent, structural facts of the eight-racer demo fixture."""

    if len(players) != ROSTER_SIZE:
        raise AssertionError(f"expected {ROSTER_SIZE} player slots, received {len(players)}")
    if tuple(player.index for player in players) != tuple(range(ROSTER_SIZE)):
        raise AssertionError("player index fields do not enumerate the eight slots")
    if not all(player.ai_control for player in players):
        raise AssertionError("the stock attract demo unexpectedly contains a non-AI racer")
    if sorted(player.placement for player in players) != list(range(ROSTER_SIZE)):
        raise AssertionError("race placements are not a permutation of 0 through 7")
    for player in players:
        values = (player.x, player.y, player.z, player.vertical_speed, player.speed, player.stage_progress)
        if not all(isfinite(value) for value in values):
            raise AssertionError(f"non-finite telemetry in player slot {player.index}")


def _validate_motion(
    before: tuple[PlayerTelemetry, ...], after: tuple[PlayerTelemetry, ...]
) -> tuple[float, ...]:
    distances = tuple(
        dist((first.x, first.y, first.z), (second.x, second.y, second.z))
        for first, second in zip(before, after, strict=True)
    )
    if not all(distance > 0.001 for distance in distances):
        raise AssertionError(f"not every active racer moved: distances={distances}")
    return distances


def _replay_trace(
    backend: LibretroDolphinBackend, resolution: PlayerArrayResolution
) -> tuple[int, tuple[PlayerTelemetry, ...], int]:
    """Run a short non-neutral P1 trace and return state plus callback evidence.

    The fixture is all-AI, so this is deliberately *not* used to infer a game
    response to P1.  It only keeps the replay trace non-neutral and verifies
    that Dolphin consumed the native controller values while racing.
    """

    trace = (
        (ControllerState(buttons=GameCubeButton.A.mask, left_x=18_000), 60),
        (ControllerState(right_x=-14_000, right_trigger=24_000), 90),
        (ControllerState(buttons=GameCubeButton.Z.mask, left_x=-12_000), 60),
        (ControllerState(), 120),
    )
    nonzero_queries = 0
    for state, frames in trace:
        result = backend.step({0: state}, frames=frames)
        nonzero_queries += result.player_1_nonzero_input_queries
    if nonzero_queries <= 0:
        raise AssertionError("Dolphin did not consume the non-neutral P1 trace")
    return backend.memory_checksum(backend.memory.guest_base, backend.memory.size), read_players(
        backend, resolution
    ), nonzero_queries


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
        assert (health["video_width"], health["video_height"]) == (640, 528)

        capture = backend.capture_frame("attract-demo-race.ppm")
        header = capture.read_bytes()[:32]
        assert header.startswith(b"P6\n640 528\n255\n"), "unexpected debug capture format"

        resolution = resolve_players_array(backend)
        initial = read_players(backend, resolution)
        _validate_active_demo_roster(initial)

        backend.step(frames=120)
        advanced = read_players(backend, resolution)
        movement = _validate_motion(initial, advanced)

        snapshot = backend.snapshot()
        snapshot_checksum = backend.memory_checksum(backend.memory.guest_base, backend.memory.size)
        checksum_a, players_a, input_queries_a = _replay_trace(backend, resolution)
        backend.restore(snapshot)
        assert (
            backend.memory_checksum(backend.memory.guest_base, backend.memory.size) == snapshot_checksum
        ), "race snapshot did not restore its full MEM1 baseline"
        checksum_b, players_b, input_queries_b = _replay_trace(backend, resolution)

        assert checksum_a == checksum_b, "race replay diverged in full MEM1"
        assert players_a == players_b, "race replay diverged in decoded player telemetry"

        report = {
            "game_id": "GXEE8P",
            "core_library_version": backend.library_version,
            "fixture": {
                "kind": "stock attract-mode race",
                "boot_frames": boot.frames,
                "all_racers_ai_controlled": True,
                "debug_capture": str(capture),
                "capture_size": [health["video_width"], health["video_height"]],
            },
            "player_array": {
                "guest_base": f"0x{resolution.guest_base:08x}",
                "reference_sites": [f"0x{site:08x}" for site in resolution.reference_sites],
                "stride": resolution.stride,
                "player_count": resolution.player_count,
            },
            "initial_players": [asdict(player) for player in initial],
            "motion_over_120_frames": list(movement),
            "race_snapshot": {
                "id": snapshot.id,
                "size": snapshot.size,
                "checksum": f"0x{snapshot.checksum:016x}",
                "mem1_checksum": f"0x{snapshot_checksum:016x}",
            },
            "replay": {
                "frames": 330,
                "p1_nonzero_input_queries": [input_queries_a, input_queries_b],
                "mem1_checksums": [f"0x{checksum_a:016x}", f"0x{checksum_b:016x}"],
                "exact_mem1_match": True,
                "exact_player_telemetry_match": True,
            },
            "total_frames": backend.health()["total_frames"],
        }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
