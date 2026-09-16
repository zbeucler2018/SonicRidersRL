"""Replay and verify a viewer trace from the stock normal-race fixture."""
from __future__ import annotations
import argparse, json
from dataclasses import asdict
from pathlib import Path
from .backend import BackendConfig, ControllerState, LibretroDolphinBackend
from .fixtures import boot_normal_free_race
from .telemetry import read_game_mode, read_players

def main() -> None:
    root = Path(__file__).resolve().parents[1]; p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace", type=Path); args = p.parse_args(); trace = json.loads(args.trace.read_text())
    if trace.get("format") != "sonic-riders-input-trace-v1": raise ValueError("unsupported trace format")
    config = BackendConfig(root / "build/sonic-libretro-runner", root / ".local/core/dolphin_libretro.so", Path("~/Games/GameCube/SonicRiders/sonic_riders_usa.rvz"), root / ".local/runtime/system", root / ".local/runtime/saves/trace-replay")
    with LibretroDolphinBackend(config) as backend:
        mode, players, _ = boot_normal_free_race(backend); backend.snapshot()
        for index, step in enumerate(trace["steps"]):
            backend.step({0: ControllerState(**step["controller"])}, frames=trace["frames_per_step"])
            if asdict(read_players(backend, players)[0]) != step["player_0"] or asdict(read_game_mode(backend, mode)) != step["game_mode"]:
                raise AssertionError(f"trace diverged at step {index}")
    print(f"exact replay: {len(trace['steps'])} steps")
if __name__ == "__main__": main()
