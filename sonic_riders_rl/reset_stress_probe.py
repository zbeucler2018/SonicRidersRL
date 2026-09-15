"""Stress fast snapshot resets without introducing an RL environment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from .backend import BackendConfig, ControllerState, LibretroDolphinBackend
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
    parser.add_argument("--save-dir", type=Path, default=root / ".local/runtime/saves/milestone4")
    parser.add_argument("--boot-frames", type=int, default=600)
    parser.add_argument("--cycles", type=int, default=10_000)
    parser.add_argument("--frames-per-cycle", type=int, default=1)
    parser.add_argument("--health-every", type=int, default=100)
    parser.add_argument("--report", type=Path, default=root / ".local/reports/milestone4.json")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.boot_frames < 1 or args.cycles < 1 or args.frames_per_cycle < 1:
        raise ValueError("boot frames, cycles, and frames per cycle must be positive")
    if args.health_every < 1:
        raise ValueError("--health-every must be positive")
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
        baseline_checksum = backend.memory_checksum(backend.memory.guest_base, backend.memory.size)
        snapshot = backend.snapshot()

        start = perf_counter()
        health_checks = 0
        # Non-neutral input makes this a short rollout rather than a no-op
        # restore loop. The next restore starts every cycle from the same state.
        rollout = {0: ControllerState(left_x=16384, right_trigger=12000)}
        for cycle in range(1, args.cycles + 1):
            backend.restore(snapshot)
            result = backend.step(rollout, frames=args.frames_per_cycle)
            assert result.frames == args.frames_per_cycle
            if cycle % args.health_every == 0 or cycle == args.cycles:
                health = backend.health()
                assert health["game_id_GXEE8P"]
                health_checks += 1
                print(f"reset stress progress: {cycle}/{args.cycles}", flush=True)
        elapsed_seconds = perf_counter() - start

        backend.restore(snapshot)
        restored_checksum = backend.memory_checksum(backend.memory.guest_base, backend.memory.size)
        assert restored_checksum == baseline_checksum, "final reset did not reproduce the baseline MEM1"
        final_health = backend.health()
        report = {
            "game_id": "GXEE8P",
            "core_library_version": backend.library_version,
            "snapshot": {"bytes": snapshot.size, "checksum": f"0x{snapshot.checksum:016x}"},
            "reset_stress": {
                "cycles": args.cycles,
                "frames_per_cycle": args.frames_per_cycle,
                "total_rollout_frames": args.cycles * args.frames_per_cycle,
                "health_checks": health_checks,
                "elapsed_seconds": round(elapsed_seconds, 3),
                "cycles_per_second": round(args.cycles / elapsed_seconds, 3),
                "baseline_mem1_fnv1a64": f"0x{baseline_checksum:016x}",
                "final_restore_matches_baseline": True,
            },
            "total_frames": final_health["total_frames"],
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
