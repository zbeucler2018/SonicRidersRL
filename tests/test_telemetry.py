import struct
import unittest

from sonic_riders_rl.backend import MemoryRegion
from sonic_riders_rl.telemetry import (
    BigEndianMemory,
    CONTROLLER_SIZE,
    GameModeTelemetry,
    MAX_PLAYERS,
    PLAYER_STRIDE,
    TelemetryResolutionError,
    read_game_mode,
    read_player_controllers,
    read_players,
    resolve_game_mode,
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


def install_game_mode_reference(
    backend: FakeMemoryBackend, code_address: int, game_mode: int, mode_detail: int
) -> None:
    game_mode_high = ((game_mode + 0x8000) >> 16) & 0xFFFF
    mode_detail_high = ((mode_detail + 0x8000) >> 16) & 0xFFFF
    reference = (
        b"\x3c\x80"
        + game_mode_high.to_bytes(2, "big")
        + b"\x3c\x60"
        + mode_detail_high.to_bytes(2, "big")
        + b"\x38\x84"
        + (game_mode & 0xFFFF).to_bytes(2, "big")
        + b"\x80\x03"
        + (mode_detail & 0xFFFF).to_bytes(2, "big")
        + bytes.fromhex("808400007c0400502c0000024081019438000005981e001448000188")
    )
    backend.write(code_address, reference)


class TelemetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = FakeMemoryBackend()
        self.player_base = 0x80010040
        self.controller_base = 0x80019000
        install_player_reference(self.backend, 0x80002000, self.player_base)
        for index in range(MAX_PLAYERS):
            start = self.player_base + index * PLAYER_STRIDE
            controller = self.controller_base + index * CONTROLLER_SIZE
            self.backend.write(start, struct.pack(">I", controller))
            self.backend.write(start + 0x0BA, bytes((index,)))
            self.backend.write(start + 0x0BD, bytes((index & 1,)))
            controller_raw = bytearray(CONTROLLER_SIZE)
            struct.pack_into(">I", controller_raw, 0x00, 100 + index)
            struct.pack_into(">I", controller_raw, 0x08, 0x100 + index)
            struct.pack_into(">I", controller_raw, 0x0C, 0x200 + index)
            struct.pack_into(">b", controller_raw, 0x18, -20 + index)
            struct.pack_into(">b", controller_raw, 0x19, 20 - index)
            struct.pack_into(">b", controller_raw, 0x1C, -10 + index)
            struct.pack_into(">b", controller_raw, 0x1D, 10 - index)
            controller_raw[0x1E] = index
            struct.pack_into(">I", controller_raw, 0x24, 0xFFFF_FFFF)
            controller_raw[0x28] = 1
            self.backend.write(controller, bytes(controller_raw))
        self.backend.write(self.player_base + 0x1E4, struct.pack(">f", 12.5))
        self.backend.write(self.player_base + 0x984, struct.pack(">i", 12345))
        self.backend.write(self.player_base + 0xB98, struct.pack(">I", 42))
        self.backend.write(self.player_base + 0xBC4, struct.pack(">f", 321.25))

    def test_resolves_relocatable_game_mode_pair_and_decodes_big_endian_values(self) -> None:
        game_mode_address = 0x8001A234
        mode_detail_address = 0x80005678
        install_game_mode_reference(
            self.backend, 0x80003000, game_mode_address, mode_detail_address
        )
        self.backend.write(game_mode_address, struct.pack(">I", 700))
        self.backend.write(mode_detail_address, struct.pack(">I", 703))

        resolution = resolve_game_mode(self.backend)
        self.assertEqual(resolution.game_mode_address, game_mode_address)
        self.assertEqual(resolution.mode_detail_address, mode_detail_address)
        self.assertEqual(resolution.reference_sites, (0x80003000,))
        self.assertEqual(
            read_game_mode(self.backend, resolution),
            GameModeTelemetry(game_mode=700, mode_detail=703, mode_detail_delta=3),
        )

    def test_game_mode_resolver_rejects_distinct_signature_targets(self) -> None:
        install_game_mode_reference(self.backend, 0x80003000, 0x80001234, 0x80005678)
        install_game_mode_reference(self.backend, 0x80003100, 0x8000789A, 0x80009ABC)
        with self.assertRaises(TelemetryResolutionError):
            resolve_game_mode(self.backend)

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
        self.assertEqual(players[1].player_type, True)

    def test_decodes_bounded_player_controller_records(self) -> None:
        players = read_players(self.backend, resolve_players_array(self.backend))
        controllers = read_player_controllers(self.backend, players)
        controller = controllers[3]
        assert controller is not None
        self.assertEqual(controller.address, self.controller_base + 3 * CONTROLLER_SIZE)
        self.assertEqual(controller.time_since_last_input, 103)
        self.assertEqual(controller.held_buttons, 0x103)
        self.assertEqual(controller.pressed_buttons, 0x203)
        self.assertEqual(controller.left_stick_x, -17)
        self.assertEqual(controller.right_stick_y, 7)
        self.assertEqual(controller.port, 3)
        self.assertEqual(controller.initialization_status, 0xFFFF_FFFF)
        self.assertTrue(controller.connected)

    def test_controller_decoder_rejects_a_non_mem1_player_pointer(self) -> None:
        self.backend.write(self.player_base, struct.pack(">I", 0x7FFF_FFF0))
        players = read_players(self.backend, resolve_players_array(self.backend))
        with self.assertRaises(TelemetryResolutionError):
            read_player_controllers(self.backend, players)

    def test_resolver_fails_closed_without_the_exact_version_signature(self) -> None:
        backend = FakeMemoryBackend()
        with self.assertRaises(TelemetryResolutionError):
            resolve_players_array(backend)
        with self.assertRaises(TelemetryResolutionError):
            resolve_game_mode(backend)

    def test_big_endian_memory_helpers(self) -> None:
        self.backend.write(0x80000300, bytes.fromhex("01020304c0600000"))
        memory = BigEndianMemory(self.backend)
        self.assertEqual(memory.read_u8(0x80000300), 1)
        self.assertEqual(memory.read_u32(0x80000300), 0x01020304)
        self.assertEqual(memory.read_f32(0x80000304), -3.5)


if __name__ == "__main__":
    unittest.main()
