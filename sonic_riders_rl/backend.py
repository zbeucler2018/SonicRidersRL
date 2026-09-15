"""Small Python API for one synchronous Dolphin-libretro worker process.

This package deliberately exposes emulator primitives only.  It contains no
game telemetry, observations, rewards, Gymnasium adapter, or RL code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
import select
import subprocess
import threading
from typing import Mapping


MEM1_GUEST_BASE = 0x8000_0000
MEM1_SIZE = 24 * 1024 * 1024
MAX_MEMORY_TRANSFER = 1024 * 1024


class GameCubeButton(IntEnum):
    """Libretro joypad IDs used by Dolphin's stock GameCube mapping."""

    B = 0
    Y = 1
    START = 3
    DPAD_UP = 4
    DPAD_DOWN = 5
    DPAD_LEFT = 6
    DPAD_RIGHT = 7
    A = 8
    X = 9
    L = 10
    Z = 11  # Dolphin maps the libretro R button to the GameCube Z button.
    R = Z  # Libretro name retained as an alias for callers that need raw IDs.
    L_ANALOG = 12
    R_ANALOG = 13

    @property
    def mask(self) -> int:
        return 1 << int(self)


@dataclass(frozen=True)
class ControllerState:
    """One GameCube pad's native digital and signed-16-bit analog state."""

    buttons: int = 0
    left_x: int = 0
    left_y: int = 0
    right_x: int = 0
    right_y: int = 0
    left_trigger: int = 0
    right_trigger: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.buttons < 2**32:
            raise ValueError("buttons must fit in an unsigned 32-bit bitmask")
        for name in (
            "left_x",
            "left_y",
            "right_x",
            "right_y",
            "left_trigger",
            "right_trigger",
        ):
            value = getattr(self, name)
            if not -32768 <= value <= 32767:
                raise ValueError(f"{name} must be in [-32768, 32767]")


@dataclass(frozen=True)
class MemoryRegion:
    guest_base: int
    size: int
    big_endian: bool


@dataclass(frozen=True)
class Snapshot:
    """An in-memory savestate retained by one backend worker process."""

    id: int
    size: int
    checksum: int


@dataclass(frozen=True)
class StepResult:
    frames: int
    total_frames: int
    input_polls: int
    input_queries_by_port: tuple[int, int, int, int]
    nonzero_input_queries_by_port: tuple[int, int, int, int]

    @property
    def player_1_input_queries(self) -> int:
        """Number of input-state callback reads for GameCube port 0 (P1)."""

        return self.input_queries_by_port[0]

    @property
    def player_1_nonzero_input_queries(self) -> int:
        """Number of non-neutral input values returned for GameCube port 0 (P1)."""

        return self.nonzero_input_queries_by_port[0]


@dataclass(frozen=True)
class BackendConfig:
    runner_path: Path
    core_path: Path
    rom_path: Path
    system_dir: Path
    save_dir: Path
    startup_timeout_seconds: float = 60.0
    command_timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        for name in ("runner_path", "core_path", "rom_path", "system_dir", "save_dir"):
            object.__setattr__(self, name, Path(getattr(self, name)).expanduser().resolve())
        if self.startup_timeout_seconds <= 0 or self.command_timeout_seconds <= 0:
            raise ValueError("timeouts must be positive")


class BackendError(RuntimeError):
    pass


class LibretroDolphinBackend:
    """A one-process-per-worker, caller-paced Dolphin libretro backend."""

    def __init__(self, config: BackendConfig):
        self.config = config
        self._process: subprocess.Popen[str] | None = None
        self._stderr = None
        self._lock = threading.RLock()
        self._memory: MemoryRegion | None = None
        self._library_version: str | None = None

    @property
    def memory(self) -> MemoryRegion:
        if self._memory is None:
            raise BackendError("backend has not been launched")
        return self._memory

    @property
    def library_version(self) -> str:
        if self._library_version is None:
            raise BackendError("backend has not been launched")
        return self._library_version

    def launch(self) -> MemoryRegion:
        with self._lock:
            if self._process is not None:
                raise BackendError("backend is already launched")
            for path in (self.config.runner_path, self.config.core_path, self.config.rom_path):
                if not path.is_file():
                    raise FileNotFoundError(path)
            self.config.system_dir.mkdir(parents=True, exist_ok=True)
            self.config.save_dir.mkdir(parents=True, exist_ok=True)
            stderr_path = self.config.save_dir / "runner.stderr.log"
            self._stderr = stderr_path.open("w", encoding="utf-8")
            command = [
                str(self.config.runner_path),
                "--server",
                "--core",
                str(self.config.core_path),
                "--rom",
                str(self.config.rom_path),
                "--system-dir",
                str(self.config.system_dir),
                "--save-dir",
                str(self.config.save_dir),
            ]
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self._stderr,
                text=True,
                bufsize=1,
            )
            try:
                fields = self._fields(self._read_line(self.config.startup_timeout_seconds), "READY")
                self._memory = MemoryRegion(
                    guest_base=int(fields["map_base"], 0),
                    size=int(fields["map_size"]),
                    big_endian=bool(int(fields["map_flags"], 0) & 0x2),
                )
                self._library_version = fields["version"]
                return self._memory
            except Exception:
                self.close()
                raise

    def step(
        self, controllers: Mapping[int, ControllerState] | None = None, *, frames: int = 1
    ) -> StepResult:
        if not 1 <= frames <= 1_000_000:
            raise ValueError("frames must be in [1, 1_000_000]")
        states = [ControllerState() for _ in range(4)]
        for port, state in (controllers or {}).items():
            if not 0 <= port < 4:
                raise ValueError("Milestone 1 supports GameCube controller ports 0 through 3")
            if not isinstance(state, ControllerState):
                raise TypeError("controller values must be ControllerState instances")
            states[port] = state
        command_fields = ["STEP", str(frames)]
        for state in states:
            command_fields.extend(
                str(value)
                for value in (
                    state.buttons,
                    state.left_x,
                    state.left_y,
                    state.right_x,
                    state.right_y,
                    state.left_trigger,
                    state.right_trigger,
                )
            )
        fields = self._command(" ".join(command_fields), "OK STEPPED")
        return StepResult(
            frames=int(fields["frames"]),
            total_frames=int(fields["total_frames"]),
            input_polls=int(fields["polls"]),
            input_queries_by_port=tuple(int(fields[f"p{port}_queries"]) for port in range(4)),
            nonzero_input_queries_by_port=tuple(
                int(fields[f"p{port}_nonzero"]) for port in range(4)
            ),
        )

    def read_memory(self, guest_address: int, length: int) -> bytes:
        self._validate_memory_range(guest_address, length)
        if length > MAX_MEMORY_TRANSFER:
            raise ValueError(f"read size exceeds {MAX_MEMORY_TRANSFER} bytes")
        line = self._command(f"READ 0x{guest_address:x} {length}", "DATA")
        return bytes.fromhex(line)

    def write_memory(self, guest_address: int, data: bytes) -> None:
        self._validate_memory_range(guest_address, len(data))
        if not data:
            raise ValueError("write data must not be empty")
        if len(data) > MAX_MEMORY_TRANSFER:
            raise ValueError(f"write size exceeds {MAX_MEMORY_TRANSFER} bytes")
        self._command(f"WRITE 0x{guest_address:x} {data.hex()}", "OK WROTE")

    def snapshot(self) -> Snapshot:
        fields = self._command("SNAPSHOT", "OK SNAPSHOT")
        return Snapshot(
            id=int(fields["id"]), size=int(fields["size"]), checksum=int(fields["checksum"], 0)
        )

    def restore(self, snapshot: Snapshot) -> None:
        self._command(f"RESTORE {snapshot.id}", "OK RESTORED")

    def health(self) -> dict[str, int | bool]:
        fields = self._command("HEALTH", "OK HEALTH")
        return {
            "total_frames": int(fields["total_frames"]),
            "memory_size": int(fields["memory_size"]),
            "map_base": int(fields["map_base"], 0),
            "map_size": int(fields["map_size"]),
            "big_endian": bool(int(fields["map_flags"], 0) & 0x2),
            "game_id_GXEE8P": fields["game_id_GXEE8P"] == "1",
        }

    def close(self) -> None:
        with self._lock:
            process = self._process
            self._process = None
            if process is not None:
                try:
                    if process.poll() is None:
                        self._command_raw(process, "QUIT", "OK BYE", timeout=10.0)
                except (BackendError, OSError):
                    process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=15)
            if self._stderr is not None:
                self._stderr.close()
                self._stderr = None
            self._memory = None
            self._library_version = None

    def __enter__(self) -> "LibretroDolphinBackend":
        self.launch()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _command(self, command: str, prefix: str) -> dict[str, str] | str:
        with self._lock:
            if self._process is None:
                raise BackendError("backend has not been launched")
            return self._command_raw(
                self._process, command, prefix, timeout=self.config.command_timeout_seconds
            )

    def _command_raw(
        self, process: subprocess.Popen[str], command: str, prefix: str, *, timeout: float
    ) -> dict[str, str] | str:
        if process.stdin is None:
            raise BackendError("runner stdin is unavailable")
        process.stdin.write(command + "\n")
        process.stdin.flush()
        line = self._read_line(timeout, process)
        if line.startswith("ERROR "):
            raise BackendError(line.removeprefix("ERROR "))
        if prefix == "DATA":
            if not line.startswith("DATA "):
                raise BackendError(f"unexpected runner response: {line}")
            return line.removeprefix("DATA ")
        return self._fields(line, prefix)

    def _read_line(self, timeout: float, process: subprocess.Popen[str] | None = None) -> str:
        process = process or self._process
        if process is None or process.stdout is None:
            raise BackendError("runner stdout is unavailable")
        readable, _, _ = select.select([process.stdout], [], [], timeout)
        if not readable:
            raise BackendError(f"runner did not respond within {timeout} seconds")
        line = process.stdout.readline()
        if not line:
            raise BackendError(f"runner exited unexpectedly with status {process.poll()}")
        return line.rstrip("\n")

    @staticmethod
    def _fields(line: str, prefix: str) -> dict[str, str]:
        if not line.startswith(prefix):
            raise BackendError(f"unexpected runner response: {line}")
        fields: dict[str, str] = {}
        for item in line[len(prefix) :].strip().split():
            key, separator, value = item.partition("=")
            if not separator:
                raise BackendError(f"malformed runner response: {line}")
            fields[key] = value
        return fields

    def _validate_memory_range(self, guest_address: int, length: int) -> None:
        if length < 0:
            raise ValueError("memory length must not be negative")
        region = self.memory
        if guest_address < region.guest_base or guest_address + length > region.guest_base + region.size:
            raise ValueError("memory access is outside the exposed MEM1 range")
