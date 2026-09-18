import subprocess
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from sonic_riders_rl.backend import (
    BackendConfig,
    BackendError,
    LibretroDolphinBackend,
    Snapshot,
)


def make_backend() -> LibretroDolphinBackend:
    return LibretroDolphinBackend(
        BackendConfig(
            runner_path=Path("runner"),
            core_path=Path("core"),
            rom_path=Path("rom"),
            system_dir=Path("system"),
            save_dir=Path("saves"),
        )
    )


class WorkerSupervisionTests(unittest.TestCase):
    def test_protocol_failure_discards_worker_and_invalidates_snapshots(self) -> None:
        backend = make_backend()
        process = MagicMock()
        process.poll.return_value = None
        backend._process = process
        backend._worker_generation = 4

        with patch.object(
            backend, "_command_raw", side_effect=BackendError("runner timed out")
        ), self.assertRaisesRegex(BackendError, "runner timed out"):
            backend._command("STEP 1", "OK STEPPED")

        process.terminate.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=15)
        self.assertIsNone(backend._process)
        self.assertEqual(backend._worker_generation, 5)

    def test_stale_snapshot_fails_before_sending_restore_command(self) -> None:
        backend = make_backend()
        backend._process = MagicMock()
        backend._worker_generation = 8
        stale = Snapshot(id=3, size=12, checksum=99, worker_generation=7)

        with patch.object(backend, "_command") as command, self.assertRaisesRegex(
            BackendError, "older worker generation"
        ):
            backend.restore(stale)

        command.assert_not_called()

    def test_relaunch_is_explicit_and_does_not_recreate_fixture(self) -> None:
        backend = make_backend()
        with patch.object(backend, "close") as close, patch.object(
            backend, "launch", return_value=MagicMock()
        ) as launch:
            result = backend.relaunch()

        close.assert_called_once_with()
        launch.assert_called_once_with()
        self.assertIsNotNone(result)

    def test_dead_process_is_cleaned_before_explicit_launch(self) -> None:
        backend = make_backend()
        dead = MagicMock()
        dead.poll.return_value = 17
        backend._process = dead
        backend._worker_generation = 2

        with patch.object(Path, "is_file", return_value=True), patch.object(
            Path, "mkdir"
        ), patch.object(Path, "open"), patch("subprocess.Popen") as popen:
            popen_process = MagicMock()
            popen_process.poll.return_value = None
            popen.return_value = popen_process
            popen_process.stdout = MagicMock()
            with patch.object(
                backend, "_read_line", return_value="READY map_base=0x80000000 map_size=25165824 map_flags=2 version=v"
            ):
                backend.launch()

        dead.wait.assert_called_once_with(timeout=15)
        self.assertEqual(backend._worker_generation, 4)


if __name__ == "__main__":
    unittest.main()
