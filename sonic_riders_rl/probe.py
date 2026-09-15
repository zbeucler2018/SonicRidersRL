"""End-to-end Milestone 1 validation. Run with ``python -m sonic_riders_rl.probe``."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from .backend import (
    BackendConfig,
    ControllerState,
    GameCubeButton,
    LibretroDolphinBackend,
    MEM1_GUEST_BASE,
    MEM1_SIZE,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", type=Path, default=root / "build/sonic-libretro-runner")
    parser.add_argument("--core", type=Path, default=root / ".local/core/dolphin_libretro.so")
    parser.add_argument(
        "--rom",
        type=Path,
        default=Path("~/Games/GameCube/SonicRiders/sonic_riders_usa.rvz").expanduser(),
    )
    parser.add_argument("--system-dir", type=Path, default=root / ".local/runtime/system")
    parser.add_argument("--save-dir", type=Path, default=root / ".local/runtime/saves/milestone1")
    parser.add_argument("--boot-frames", type=int, default=600)
    parser.add_argument("--stress-frames", type=int, default=10_000)
    parser.add_argument("--stress-chunk-frames", type=int, default=1_000)
    parser.add_argument("--report", type=Path, default=root / ".local/reports/milestone1.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = BackendConfig(
        runner_path=args.runner,
        core_path=args.core,
        rom_path=args.rom,
        system_dir=args.system_dir,
        save_dir=args.save_dir,
        command_timeout_seconds=120.0,
    )
    with LibretroDolphinBackend(config) as backend:
        boot = backend.step(frames=args.boot_frames)
        health = backend.health()
        assert health["game_id_GXEE8P"], "Dolphin did not identify the loaded disc as GXEE8P"
        assert backend.memory.guest_base == MEM1_GUEST_BASE
        assert backend.memory.size == MEM1_SIZE
        assert backend.memory.big_endian
        assert health["memory_size"] == MEM1_SIZE

        before_restore = backend.read_memory(MEM1_GUEST_BASE, 65_536)
        snapshot = backend.snapshot()
        injected = ControllerState(
            buttons=GameCubeButton.A.mask | GameCubeButton.Z.mask,
            left_x=32767,
            right_x=-16384,
            right_trigger=32767,
        )
        input_step = backend.step({0: injected}, frames=120)
        assert input_step.player_1_input_queries > 0
        assert input_step.player_1_nonzero_input_queries > 0

        restore_start = perf_counter()
        backend.restore(snapshot)
        restore_milliseconds = (perf_counter() - restore_start) * 1_000
        after_restore = backend.read_memory(MEM1_GUEST_BASE, 65_536)
        assert before_restore == after_restore, "savestate restore did not reproduce the MEM1 sample"

        if args.stress_chunk_frames < 1:
            raise ValueError("--stress-chunk-frames must be positive")
        stress_start = perf_counter()
        stress_results = []
        remaining = args.stress_frames
        while remaining:
            chunk = min(remaining, args.stress_chunk_frames)
            stress_results.append(backend.step(frames=chunk))
            remaining -= chunk
            print(f"stress progress: {args.stress_frames - remaining}/{args.stress_frames} frames", flush=True)
        stress_seconds = perf_counter() - stress_start
        stress_frames = sum(result.frames for result in stress_results)
        assert stress_frames == args.stress_frames
        final_health = backend.health()
        assert final_health["total_frames"] >= 1 + args.boot_frames + 120 + args.stress_frames

        report = {
            "game_id": "GXEE8P",
            "core_library_version": backend.library_version,
            "core_sha256": hashlib.sha256(args.core.read_bytes()).hexdigest(),
            "mem1": {
                "guest_base": hex(backend.memory.guest_base),
                "size": backend.memory.size,
                "big_endian": backend.memory.big_endian,
                "sample_sha256": hashlib.sha256(before_restore).hexdigest(),
            },
            "boot": {"frames": boot.frames, "input_polls": boot.input_polls},
            "input_injection": {
                "frames": input_step.frames,
                "player_1_queries": input_step.player_1_input_queries,
                "player_1_nonzero_queries": input_step.player_1_nonzero_input_queries,
            },
            "savestate": {
                "bytes": snapshot.size,
                "checksum": hex(snapshot.checksum),
                "restore_milliseconds": round(restore_milliseconds, 3),
                "mem1_sample_restored": True,
            },
            "frame_stepping": {
                "stress_frames": stress_frames,
                "control_commands": len(stress_results),
                "frames_per_control_command": args.stress_chunk_frames,
                "elapsed_seconds": round(stress_seconds, 3),
                "frames_per_second": round(stress_frames / stress_seconds, 3),
                "frontend_pacing": "none (one synchronous retro_run call per requested frame)",
            },
            "total_frames": final_health["total_frames"],
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
