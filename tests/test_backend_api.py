import unittest
from pathlib import Path

from sonic_riders_rl.backend import (
    BackendConfig,
    ControllerState,
    GameCubeButton,
    LibretroDolphinBackend,
    MEM1_GUEST_BASE,
    MEM1_SIZE,
    StepResult,
)


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

    def test_step_result_preserves_per_port_input_accounting(self) -> None:
        result = StepResult(
            frames=1,
            total_frames=1,
            input_polls=1,
            input_queries_by_port=(1, 2, 3, 4),
            nonzero_input_queries_by_port=(5, 6, 7, 8),
        )
        self.assertEqual(result.player_1_input_queries, 1)
        self.assertEqual(result.player_1_nonzero_input_queries, 5)


class CaptureValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = LibretroDolphinBackend(
            BackendConfig(
                runner_path=Path("runner"),
                core_path=Path("core"),
                rom_path=Path("rom"),
                system_dir=Path("system"),
                save_dir=Path("saves"),
            )
        )

    def test_capture_rejects_nonlocal_or_non_ppm_filenames_before_launch(self) -> None:
        for filename in ("frame.png", "nested/frame.ppm", "../outside.ppm"):
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                self.backend.capture_frame(filename)


if __name__ == "__main__":
    unittest.main()
