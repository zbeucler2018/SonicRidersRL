# Milestone 9: Null renderer compatibility result

The PRD requires a Null/state-only renderer evaluation, but does not require
that it succeed or become the architecture. This milestone tested the pinned
release core directly and records the negative result.

## Validation command

```bash
timeout 20s build/sonic-libretro-runner --server \
  --core .local/core/dolphin_libretro.so \
  --rom /home/service/Games/GameCube/SonicRiders/sonic_riders_usa.rvz \
  --system-dir .local/runtime/system \
  --save-dir .local/runtime/saves/milestone9-null-direct \
  --renderer Null
```

With core `2606.0.393+ed70219e8b`, Dolphin logged `Using GFX backend: Null`
and recognized GXEE8P, then crashed with exit status 139 before `READY`.
`--renderer` was a temporary experimental runner option and was removed after
this result, so the command is preserved as validation evidence rather than a
current supported invocation.

## Outcome

`Null` is not exposed through `BackendConfig`; Hardware remains the supported
and validated state/control mode. No Dolphin patch, Docker workaround, or
second runner was added. A future renderer experiment needs a different pinned
upstream build or a separately justified emulator architecture.
