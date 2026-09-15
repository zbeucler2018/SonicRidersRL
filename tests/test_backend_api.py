import unittest

from sonic_riders_rl.backend import ControllerState, GameCubeButton, MEM1_GUEST_BASE, MEM1_SIZE


class ControllerStateTests(unittest.TestCase):
    def test_button_masks_are_composable(self) -> None:
        state = ControllerState(buttons=GameCubeButton.A.mask | GameCubeButton.START.mask)
        self.assertEqual(state.buttons, (1 << GameCubeButton.A) | (1 << GameCubeButton.START))
        self.assertEqual(GameCubeButton.Z, GameCubeButton.R)

    def test_rejects_out_of_range_axis(self) -> None:
        with self.assertRaises(ValueError):
            ControllerState(left_x=32768)

    def test_mem1_constants_match_gamecube_mapping(self) -> None:
        self.assertEqual(MEM1_GUEST_BASE, 0x80000000)
        self.assertEqual(MEM1_SIZE, 0x01800000)


if __name__ == "__main__":
    unittest.main()
