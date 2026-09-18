# Worker supervision contract

`LibretroDolphinBackend` owns exactly one synchronous Dolphin runner process.
Any protocol error, runner EOF, exited process, or command timeout makes that
worker unusable. The backend immediately detaches and best-effort terminates
the process, then force-kills it if it does not exit within the cleanup
deadline. It clears the memory map and library metadata so callers cannot
continue using partial worker state.

Recovery is explicit:

```python
backend.relaunch()
# boot the stock menu flow and capture a new fixture here
```

`relaunch()` starts only a fresh emulator worker. It does not replay a trace,
recreate a normal-race fixture, or restore game state. A caller must perform
its normal boot/setup flow again.

Snapshots carry an internal worker-generation value. A snapshot from a closed,
failed, or replaced worker is rejected with `BackendError` before any restore
command is sent. This also invalidates a `NormalRaceFixture`, whose
runner-owned snapshot must be recaptured after relaunch.

The contract is intentionally local and synchronous. It is a foundation for a
future supervisor that can assign one backend per worker process; it is not yet
a rollout scheduler, heartbeat service, or RL environment.
