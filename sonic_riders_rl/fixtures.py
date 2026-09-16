"""Process-local, stock Sonic Riders fixtures built on emulator primitives.

This module deliberately owns no observations, rewards, Gymnasium adapters, or
training code. A fixture is a validated in-memory snapshot token and is valid
only in the worker process that created it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .backend import ControllerState, GameCubeButton, LibretroDolphinBackend, Snapshot
from .telemetry import (
    GameModeResolution,
    GameModeTelemetry,
    PlayerArrayResolution,
    PlayerTelemetry,
    read_game_mode,
    read_player_controllers,
    read_players,
    resolve_game_mode,
    resolve_players_array,
)


TITLE_BOOT_FRAMES = 600
MENU_ADVANCE_COUNT = 11
MENU_SETTLE_FRAMES = 300
CHARACTER_CONFIRM_SETTLE_FRAMES = 1_260
COURSE_CONFIRM_SETTLE_FRAMES = 900
PRESS_FRAMES = 2
FREE_RACE_MODE = 700
ACTIVE_RACE_DELTA = 3
MEMORY_SCHEMA_VERSION = "GXEE8P/vanilla_ntscu_v1@1"
DEFAULT_COURSE_TRACK = "default-course-unresolved"


class FixtureValidationError(RuntimeError):
    """A restored fixture no longer matches its recorded race state."""


@dataclass(frozen=True)
class RaceState:
    """The reset-critical game telemetry sampled from one stock race state."""

    game_mode: GameModeTelemetry
    players: tuple[PlayerTelemetry, ...]
    mem1_checksum: int


@dataclass(frozen=True)
class FixtureMetadata:
    """Version-bound information required to reproduce one reset fixture."""

    game_id: str
    game_sha256: str
    core_library_version: str
    dolphin_libretro_revision: str
    frontend_revision: str
    track: str
    mode: str
    game_mode: int
    race_state_delta: int
    character: int
    gear: int
    player_count: int
    memory_schema_version: str
    snapshot_checksum: int
    snapshot_size: int
    baseline_mem1_checksum: int


@dataclass(frozen=True)
class NormalRaceFixture:
    """A validated active Free Race state held in one worker's memory.

    ``snapshot.id`` is allocated by the native runner, so this object cannot
    cross a process boundary or survive a worker restart. Recreate it by
    booting the stock menu flow in each worker; thereafter ``reset`` is the
    fast per-episode operation.
    """

    snapshot: Snapshot
    metadata: FixtureMetadata
    baseline: RaceState
    game_mode_resolution: GameModeResolution
    players_resolution: PlayerArrayResolution

    def reset(self, backend: LibretroDolphinBackend) -> RaceState:
        """Restore and verify the exact reset-critical state for this worker."""

        backend.restore(self.snapshot)
        restored = read_race_state(backend, self.game_mode_resolution, self.players_resolution)
        if restored.game_mode != self.baseline.game_mode:
            raise FixtureValidationError(
                f"race mode changed across restore: expected {self.baseline.game_mode}, "
                f"received {restored.game_mode}"
            )
        if restored.players != self.baseline.players:
            raise FixtureValidationError("player telemetry changed across restore")
        if restored.mem1_checksum != self.baseline.mem1_checksum:
            raise FixtureValidationError(
                "MEM1 checksum changed across restore: "
                f"expected 0x{self.baseline.mem1_checksum:016x}, "
                f"received 0x{restored.mem1_checksum:016x}"
            )
        return restored


def boot_normal_free_race(
    backend: LibretroDolphinBackend,
) -> tuple[GameModeResolution, PlayerArrayResolution, int]:
    """Drive a fresh USA retail boot to the active, human-owned Free Race."""

    backend.step(frames=TITLE_BOOT_FRAMES)
    if not backend.health()["game_id_GXEE8P"]:
        raise FixtureValidationError("Dolphin did not identify GXEE8P")
    game_mode = resolve_game_mode(backend)
    players = resolve_players_array(backend)

    input_queries = _press(backend, GameCubeButton.START)
    backend.step(frames=10)
    for _ in range(MENU_ADVANCE_COUNT):
        input_queries += _press(backend, GameCubeButton.A)
        backend.step(frames=MENU_SETTLE_FRAMES)

    input_queries += _press(backend, GameCubeButton.START)
    backend.step(frames=CHARACTER_CONFIRM_SETTLE_FRAMES)
    staged = read_game_mode(backend, game_mode)
    if (staged.game_mode, staged.mode_detail_delta) != (FREE_RACE_MODE, 2):
        raise FixtureValidationError(f"expected staged Free Race (700, 2), received {staged}")

    input_queries += _press(backend, GameCubeButton.A)
    backend.step(frames=COURSE_CONFIRM_SETTLE_FRAMES)
    active = read_game_mode(backend, game_mode)
    if (active.game_mode, active.mode_detail_delta) != (FREE_RACE_MODE, ACTIVE_RACE_DELTA):
        raise FixtureValidationError(f"expected active Free Race (700, 3), received {active}")

    player = read_players(backend, players)[0]
    controller = read_player_controllers(backend, (player,))[0]
    if player.ai_control:
        raise FixtureValidationError("normal-flow Player 0 is still AI-controlled")
    if controller is None or not controller.connected or controller.port != 0:
        raise FixtureValidationError("normal-flow Player 0 is not connected to GameCube port 0")
    return game_mode, players, input_queries


def capture_normal_race_fixture(
    backend: LibretroDolphinBackend,
    game_mode: GameModeResolution,
    players: PlayerArrayResolution,
    *,
    game_sha256: str,
    dolphin_libretro_revision: str,
    frontend_revision: str,
    track: str = DEFAULT_COURSE_TRACK,
) -> NormalRaceFixture:
    """Capture the active normal-race reset state and its reproducibility data."""

    baseline = read_race_state(backend, game_mode, players)
    p0 = baseline.players[0]
    if baseline.game_mode.game_mode != FREE_RACE_MODE:
        raise FixtureValidationError(f"expected Free Race game mode, received {baseline.game_mode}")
    if baseline.game_mode.mode_detail_delta != ACTIVE_RACE_DELTA:
        raise FixtureValidationError(f"expected active race state, received {baseline.game_mode}")
    if p0.ai_control:
        raise FixtureValidationError("cannot capture an AI-owned Player 0 fixture")

    snapshot = backend.snapshot()
    metadata = FixtureMetadata(
        game_id="GXEE8P",
        game_sha256=game_sha256,
        core_library_version=backend.library_version,
        dolphin_libretro_revision=dolphin_libretro_revision,
        frontend_revision=frontend_revision,
        track=track,
        mode="Free Race",
        game_mode=baseline.game_mode.game_mode,
        race_state_delta=baseline.game_mode.mode_detail_delta,
        character=p0.character,
        gear=p0.extreme_gear,
        player_count=players.player_count,
        memory_schema_version=MEMORY_SCHEMA_VERSION,
        snapshot_checksum=snapshot.checksum,
        snapshot_size=snapshot.size,
        baseline_mem1_checksum=baseline.mem1_checksum,
    )
    return NormalRaceFixture(snapshot, metadata, baseline, game_mode, players)


def read_race_state(
    backend: LibretroDolphinBackend,
    game_mode: GameModeResolution,
    players: PlayerArrayResolution,
) -> RaceState:
    """Read every currently decoded racer plus reset-critical race mode data."""

    return RaceState(
        game_mode=read_game_mode(backend, game_mode),
        players=read_players(backend, players),
        mem1_checksum=backend.memory_checksum(backend.memory.guest_base, backend.memory.size),
    )


def _press(backend: LibretroDolphinBackend, button: GameCubeButton) -> int:
    result = backend.step({0: ControllerState(buttons=button.mask)}, frames=PRESS_FRAMES)
    if result.player_1_nonzero_input_queries <= 0:
        raise FixtureValidationError(f"Dolphin did not consume P1 {button.name}")
    return result.player_1_nonzero_input_queries
