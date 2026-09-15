import struct
import unittest

from sonic_riders_rl.backend import MemoryRegion
from sonic_riders_rl.telemetry import (
    BigEndianMemory,
    MAX_PLAYERS,
    PLAYER_STRIDE,
    TelemetryResolutionError,
    read_players,
    resolve_players_array,
    validate_menu_player_order,
)


class FakeMemoryBackend:
    def __init__(self) -> None:
        self.memory = MemoryRegion(guest_base=0x80000000, size=0x40000, big_endian=True)
        self.data = bytearray(self.memory.size)

    def read_memory(self, guest_address: int, length: int) -> bytes:
        start = guest_address - self.memory.guest_base
        return bytes(self.data[start : start + length])

    def write(self, guest_address: int, payload: bytes) -> None:
        start = guest_address - self.memory.guest_base
        self.data[start : start + len(payload)] = payload


def install_player_reference(backend: FakeMemoryBackend, code_address: int, target: int) -> None:
    high = ((target + 0x8000) >> 16) & 0xFFFF
    low = target & 0xFFFF
    reference = (
        b"\x3c\x80"
        + high.to_bytes(2, "big")
        + b"\x38\x64"
        + low.to_bytes(2, "big")
        + b"\x54\x00\x06\x31\x1c\x85\x10\x80\x7f\xc3\x22\x14"
    )
    backend.write(code_address, reference)


class TelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = FakeMemoryBackend()
        self.player_base = 0x80010040
        install_player_reference(self.backend, 0x80002000, self.player_base)
        for index in range(MAX_PLAYERS):
            start = self.player_base + index * PLAYER_STRIDE
            self.backend.write(start + 0x0BA, bytes((index,)))
        self.backend.write(self.player_base + 0x1E4, struct.pack(">f", 12.5))
        self.backend.write(self.player_base + 0x984, struct.pack(">i", 12345))
        self.backend.write(self.player_base + 0xB98, struct.pack(">I", 42))
        self.backend.write(self.player_base + 0xBC4, struct.pack(">f", 321.25))

    def test_resolves_relocatable_player_base_and_decodes_big_endian_fields(self) -> None:
        resolution = resolve_players_array(self.backend)
        self.assertEqual(resolution.guest_base, self.player_base)
        self.assertEqual(resolution.reference_sites, (0x80002000,))
        players = read_players(self.backend, resolution)
        validate_menu_player_order(players)
        self.assertEqual(players[0].x, 12.5)
        self.assertEqual(players[0].current_air, 12345)
        self.assertEqual(players[0].rings, 42)
        self.assertEqual(players[0].stage_progress, 321.25)

    def test_resolver_fails_closed_without_the_exact_version_signature(self) -> None:
        backend = FakeMemoryBackend()
        with self.assertRaises(TelemetryResolutionError):
            resolve_players_array(backend)

    def test_big_endian_memory_helpers(self) -> None:
        self.backend.write(0x80000300, bytes.fromhex("01020304c0600000"))
        memory = BigEndianMemory(self.backend)
        self.assertEqual(memory.read_u8(0x80000300), 1)
        self.assertEqual(memory.read_u32(0x80000300), 0x01020304)
        self.assertEqual(memory.read_f32(0x80000304), -3.5)


if __name__ == "__main__":
    unittest.main()
