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
from .fixtures import (
    FixtureMetadata,
    FixtureValidationError,
    NormalRaceFixture,
    RaceState,
    boot_normal_free_race,
    capture_normal_race_fixture,
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
    "FixtureMetadata",
    "FixtureValidationError",
    "GameCubeButton",
    "LibretroDolphinBackend",
    "MemoryRegion",
    "NormalRaceFixture",
    "PlayerArrayResolution",
    "PlayerTelemetry",
    "Snapshot",
    "StepResult",
    "RaceState",
    "TelemetryResolutionError",
    "read_players",
    "boot_normal_free_race",
    "capture_normal_race_fixture",
    "read_player_controllers",
    "resolve_players_array",
]
