"""Sonic Riders emulator-control and read-only telemetry primitives."""

from .backend import (
    BackendConfig,
    ControllerState,
    GameCubeButton,
    LibretroDolphinBackend,
    MemoryRegion,
    Snapshot,
    StepResult,
)
from .telemetry import (
    BigEndianMemory,
    ControllerTelemetry,
    PlayerArrayResolution,
    PlayerTelemetry,
    TelemetryResolutionError,
    read_player_controllers,
    read_players,
    resolve_players_array,
)

__all__ = [
    "BackendConfig",
    "BigEndianMemory",
    "ControllerTelemetry",
    "ControllerState",
    "GameCubeButton",
    "LibretroDolphinBackend",
    "MemoryRegion",
    "PlayerArrayResolution",
    "PlayerTelemetry",
    "Snapshot",
    "StepResult",
    "TelemetryResolutionError",
    "read_players",
    "read_player_controllers",
    "resolve_players_array",
]
