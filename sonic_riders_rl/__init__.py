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
    PlayerArrayResolution,
    PlayerTelemetry,
    TelemetryResolutionError,
    read_players,
    resolve_players_array,
)

__all__ = [
    "BackendConfig",
    "BigEndianMemory",
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
    "resolve_players_array",
]
