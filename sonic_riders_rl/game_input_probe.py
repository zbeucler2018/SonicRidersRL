"""Prove that a P1 input changes Sonic Riders' visible game state.

This deliberately uses the stock attract-mode race fixture because it is the
first stable live state available without memory writes or a menu script. The
demo's ``ai_control`` flags remain set, so this is an application-level input-path
probe, not a claim that it proves steering a human racer.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .backend import (
    BackendConfig,
    ControllerState,
    GameCubeButton,
    LibretroDolphinBackend,
    Snapshot,
)
from .race_probe import RACE_BOOT_FRAMES


TRACE_FRAMES = 600


@dataclass(frozen=True)
class TraceEvidence:
    mem1_checksum: int
    frame_sha256: str
    p1_nonzero_queries: int


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
    parser.add_argument("--save-dir", type=Path, default=root / ".local/runtime/saves/milestone6")
    parser.add_argument("--boot-frames", type=int, default=RACE_BOOT_FRAMES)
    parser.add_argument("--report", type=Path, default=root / ".local/reports/milestone6.json")
    return parser.parse_args()


def _run_trace(
    backend: LibretroDolphinBackend,
    snapshot: Snapshot,
    *,
    first_frame: ControllerState | None,
    capture_name: str,
) -> TraceEvidence:
    backend.restore(snapshot)
    nonzero_queries = 0
    if first_frame is not None:
        first = backend.step({0: first_frame}, frames=1)
        nonzero_queries += first.player_1_nonzero_input_queries
        backend.step(frames=TRACE_FRAMES - 1)
    else:
        backend.step(frames=TRACE_FRAMES)
    capture = backend.capture_frame(capture_name)
    return TraceEvidence(
        mem1_checksum=backend.memory_checksum(backend.memory.guest_base, backend.memory.size),
        frame_sha256=hashlib.sha256(capture.read_bytes()).hexdigest(),
        p1_nonzero_queries=nonzero_queries,
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
        snapshot = backend.snapshot()
        baseline = backend.memory_checksum(backend.memory.guest_base, backend.memory.size)

        neutral = _run_trace(backend, snapshot, first_frame=None, capture_name="neutral.ppm")
        start_a = _run_trace(
            backend,
            snapshot,
            first_frame=ControllerState(buttons=GameCubeButton.START.mask),
            capture_name="p1-start-a.ppm",
        )
        start_b = _run_trace(
            backend,
            snapshot,
            first_frame=ControllerState(buttons=GameCubeButton.START.mask),
            capture_name="p1-start-b.ppm",
        )

        assert start_a.p1_nonzero_queries > 0, "Dolphin did not consume P1 Start"
        assert start_a == start_b, "P1 Start trace was not exactly repeatable from the snapshot"
        assert start_a.mem1_checksum != neutral.mem1_checksum, "P1 Start did not alter game MEM1"
        assert start_a.frame_sha256 != neutral.frame_sha256, "P1 Start did not alter visible output"

        backend.restore(snapshot)
        assert (
            backend.memory_checksum(backend.memory.guest_base, backend.memory.size) == baseline
        ), "fixture snapshot did not restore the original MEM1 baseline"

        report = {
            "game_id": "GXEE8P",
            "core_library_version": backend.library_version,
            "fixture": {
                "kind": "stock attract-mode race",
                "boot_frames": boot.frames,
                "all_ai_control_flags_set": True,
                "snapshot_size": snapshot.size,
                "snapshot_checksum": f"0x{snapshot.checksum:016x}",
                "baseline_mem1_checksum": f"0x{baseline:016x}",
            },
            "trace": {
                "frames": TRACE_FRAMES,
                "p1_first_frame": "GameCube Start",
                "p1_nonzero_input_queries": start_a.p1_nonzero_queries,
                "neutral_mem1_checksum": f"0x{neutral.mem1_checksum:016x}",
                "start_mem1_checksum": f"0x{start_a.mem1_checksum:016x}",
                "neutral_frame_sha256": neutral.frame_sha256,
                "start_frame_sha256": start_a.frame_sha256,
                "exact_start_replay": True,
                "differs_from_neutral_mem1": True,
                "differs_from_neutral_frame": True,
            },
            "total_frames": backend.health()["total_frames"],
        }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
