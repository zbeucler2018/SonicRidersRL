"""Read-only, version-scoped Sonic Riders telemetry primitives.

This module intentionally stops at typed memory decoding.  It contains no
environment, reward, observation, or event logic.  Field names and offsets are
community-derived until a vanilla GXEE8P race validation promotes them in the
versioned schema.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Protocol

from .backend import MAX_MEMORY_TRANSFER, MemoryRegion


MAX_PLAYERS = 8
PLAYER_STRIDE = 0x1080
CONTROLLER_SIZE = 0x30


class MemoryBackend(Protocol):
    """The minimal emulator capability required by the telemetry layer."""

    @property
    def memory(self) -> MemoryRegion: ...

    def read_memory(self, guest_address: int, length: int) -> bytes: ...


@dataclass(frozen=True)
class PlayerArrayResolution:
    """A runtime ``players[]`` address recovered from the vanilla REL code."""

    guest_base: int
    reference_sites: tuple[int, ...]
    stride: int = PLAYER_STRIDE
    player_count: int = MAX_PLAYERS
    provenance: str = "community-derived; runtime-relocation-resolved"


@dataclass(frozen=True)
class PlayerTelemetry:
    """One read-only Player record with community-derived field names."""

    input_address: int
    character: int
    extreme_gear: int
    ai_control: bool
    player_type: bool
    x: float
    y: float
    z: float
    vertical_speed: float
    speed: float
    current_air: int
    rings: int
    stage_progress: float
    index: int
    lap: int
    placement: int
    level: int
    state: int
    previous_state: int


@dataclass(frozen=True)
class ControllerTelemetry:
    """One raw player input record reached through ``Player.input``.

    The fields and offsets are community-derived. In particular, callers must
    not collapse ``ai_control`` and ``player_type`` into a human/CPU semantic
    label until a normal-flow controllable-race fixture validates that meaning.
    """

    address: int
    time_since_last_input: int
    held_buttons: int
    pressed_buttons: int
    left_stick_x: int
    left_stick_y: int
    right_stick_x: int
    right_stick_y: int
    port: int
    initialization_status: int
    connected: bool


class TelemetryResolutionError(RuntimeError):
    """The expected version-specific runtime code shape was not found."""


class BigEndianMemory:
    """Bounded typed reads over the GameCube's big-endian MEM1 mapping."""

    def __init__(self, backend: MemoryBackend):
        self._backend = backend

    def read_u8(self, guest_address: int) -> int:
        return self._backend.read_memory(guest_address, 1)[0]

    def read_u32(self, guest_address: int) -> int:
        return struct.unpack(">I", self._backend.read_memory(guest_address, 4))[0]

    def read_s32(self, guest_address: int) -> int:
        return struct.unpack(">i", self._backend.read_memory(guest_address, 4))[0]

    def read_f32(self, guest_address: int) -> float:
        return struct.unpack(">f", self._backend.read_memory(guest_address, 4))[0]


# In doldecomp/sonicriders' _Main REL, this is the sequence at REL offset
# 0x7a8 that takes the address of players[] and indexes it by 0x1080:
#
#   lis   r4, players@ha
#   addi  r3, r4, players@l
#   rlwinm. r0, r0, 0, 24, 24
#   mulli r4, r5, 0x1080
#   add   r30, r3, r4
#
# The two immediate values are relocation-dependent.  Everything after them is
# fixed and makes this materially safer than a broad "find a plausible struct"
# scan.  It is still version-specific and must fail closed for another build.
_PLAYER_REFERENCE_PREFIX = b"\x3c\x80"
_PLAYER_REFERENCE_SECOND_OP = b"\x38\x64"
_PLAYER_REFERENCE_SUFFIX = b"\x54\x00\x06\x31\x1c\x85\x10\x80\x7f\xc3\x22\x14"
_PLAYER_REFERENCE_SIZE = 8 + len(_PLAYER_REFERENCE_SUFFIX)


def resolve_players_array(backend: MemoryBackend) -> PlayerArrayResolution:
    """Resolve the relocatable vanilla ``players[]`` base from live MEM1 code.

    The game loads ``_Main.rel`` dynamically, so a fixed guest address would
    be brittle.  The resolver only accepts the exact GXEE8P code shape above,
    reconstructs the PowerPC ``@ha``/``@l`` address pair, and validates that
    the full eight-player allocation falls inside the MEM1 descriptor.
    """

    memory = backend.memory
    chunk_size = min(MAX_MEMORY_TRANSFER, memory.size)
    if chunk_size <= 0:
        raise TelemetryResolutionError("MEM1 is empty")

    sites_by_target: dict[int, list[int]] = {}
    overlap = b""
    for offset in range(0, memory.size, chunk_size):
        chunk = backend.read_memory(memory.guest_base + offset, min(chunk_size, memory.size - offset))
        window = overlap + chunk
        window_guest_base = memory.guest_base + offset - len(overlap)
        search_from = 0
        while True:
            suffix_offset = window.find(_PLAYER_REFERENCE_SUFFIX, search_from)
            if suffix_offset < 0:
                break
            reference_offset = suffix_offset - 8
            search_from = suffix_offset + 1
            if reference_offset < 0:
                continue
            reference = window[reference_offset : reference_offset + _PLAYER_REFERENCE_SIZE]
            if (
                reference[:2] != _PLAYER_REFERENCE_PREFIX
                or reference[4:6] != _PLAYER_REFERENCE_SECOND_OP
                or len(reference) != _PLAYER_REFERENCE_SIZE
            ):
                continue

            high = int.from_bytes(reference[2:4], "big")
            low = int.from_bytes(reference[6:8], "big", signed=True)
            target = ((high << 16) + low) & 0xFFFF_FFFF
            if not _contains(memory, target, MAX_PLAYERS * PLAYER_STRIDE):
                continue
            sites_by_target.setdefault(target, []).append(window_guest_base + reference_offset)

        overlap = window[-(_PLAYER_REFERENCE_SIZE - 1) :]

    if not sites_by_target:
        raise TelemetryResolutionError(
            "GXEE8P players[] reference was not found; confirm that the vanilla _Main REL is loaded"
        )
    if len(sites_by_target) != 1:
        candidates = ", ".join(f"0x{target:08x}" for target in sorted(sites_by_target))
        raise TelemetryResolutionError(f"ambiguous GXEE8P players[] references: {candidates}")
    target, sites = next(iter(sites_by_target.items()))
    return PlayerArrayResolution(guest_base=target, reference_sites=tuple(sorted(set(sites))))


def read_players(backend: MemoryBackend, resolution: PlayerArrayResolution) -> tuple[PlayerTelemetry, ...]:
    """Decode all eight player slots in one bounded MEM1 read."""

    if resolution.stride != PLAYER_STRIDE or resolution.player_count != MAX_PLAYERS:
        raise ValueError("this reader only supports the GXEE8P eight-player 0x1080-byte layout")
    total_size = resolution.stride * resolution.player_count
    if not _contains(backend.memory, resolution.guest_base, total_size):
        raise TelemetryResolutionError("resolved player array is outside the active MEM1 mapping")
    raw = backend.read_memory(resolution.guest_base, total_size)
    return tuple(_decode_player(raw, index * resolution.stride) for index in range(resolution.player_count))


def read_player_controllers(
    backend: MemoryBackend, players: tuple[PlayerTelemetry, ...]
) -> tuple[ControllerTelemetry | None, ...]:
    """Decode the in-MEM1 controller referenced by each player record.

    A null pointer represents a slot without an attached controller record.
    Any non-null pointer outside MEM1 fails closed rather than following an
    arbitrary guest address.
    """

    controllers: list[ControllerTelemetry | None] = []
    for player in players:
        if player.input_address == 0:
            controllers.append(None)
            continue
        if not _contains(backend.memory, player.input_address, CONTROLLER_SIZE):
            raise TelemetryResolutionError(
                f"player {player.index} controller pointer 0x{player.input_address:08x} is outside MEM1"
            )
        raw = backend.read_memory(player.input_address, CONTROLLER_SIZE)
        controllers.append(_decode_controller(player.input_address, raw))
    return tuple(controllers)


def validate_menu_player_order(players: tuple[PlayerTelemetry, ...]) -> None:
    """Check the deterministic fresh-boot GXEE8P menu initialization invariant.

    The title/menu initializes the eight slots with character IDs 0 through 7.
    This is a structural validation of the resolved base plus stride, not a
    claim that character IDs remain ordered once a race or save data is active.
    """

    expected = tuple(range(MAX_PLAYERS))
    actual = tuple(player.character for player in players)
    if actual != expected:
        raise TelemetryResolutionError(
            f"unexpected fresh-menu character sequence: expected {expected}, received {actual}"
        )


def _contains(memory: MemoryRegion, guest_address: int, length: int) -> bool:
    return (
        length >= 0
        and guest_address >= memory.guest_base
        and guest_address + length <= memory.guest_base + memory.size
    )


def _decode_player(raw: bytes, offset: int) -> PlayerTelemetry:
    return PlayerTelemetry(
        input_address=struct.unpack_from(">I", raw, offset)[0],
        character=raw[offset + 0x0BA],
        extreme_gear=raw[offset + 0x0BB],
        ai_control=bool(raw[offset + 0x0BC]),
        player_type=bool(raw[offset + 0x0BD]),
        x=struct.unpack_from(">f", raw, offset + 0x1E4)[0],
        y=struct.unpack_from(">f", raw, offset + 0x1E8)[0],
        z=struct.unpack_from(">f", raw, offset + 0x1EC)[0],
        vertical_speed=struct.unpack_from(">f", raw, offset + 0xAA4)[0],
        speed=struct.unpack_from(">f", raw, offset + 0xAAC)[0],
        current_air=struct.unpack_from(">i", raw, offset + 0x984)[0],
        rings=struct.unpack_from(">I", raw, offset + 0xB98)[0],
        stage_progress=struct.unpack_from(">f", raw, offset + 0xBC4)[0],
        index=raw[offset + 0x1029],
        lap=raw[offset + 0x102A],
        placement=raw[offset + 0x102D],
        level=raw[offset + 0x102E],
        state=raw[offset + 0x1034],
        previous_state=raw[offset + 0x1035],
    )


def _decode_controller(address: int, raw: bytes) -> ControllerTelemetry:
    return ControllerTelemetry(
        address=address,
        time_since_last_input=struct.unpack_from(">I", raw, 0x00)[0],
        held_buttons=struct.unpack_from(">I", raw, 0x08)[0],
        pressed_buttons=struct.unpack_from(">I", raw, 0x0C)[0],
        left_stick_x=struct.unpack_from(">b", raw, 0x18)[0],
        left_stick_y=struct.unpack_from(">b", raw, 0x19)[0],
        right_stick_x=struct.unpack_from(">b", raw, 0x1C)[0],
        right_stick_y=struct.unpack_from(">b", raw, 0x1D)[0],
        port=raw[0x1E],
        initialization_status=struct.unpack_from(">I", raw, 0x24)[0],
        connected=bool(raw[0x28]),
    )
