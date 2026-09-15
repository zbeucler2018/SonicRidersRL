# Milestone 9 architecture decision: Null renderer rejected on this core build

## Decision

Retain `Hardware` as the only exposed worker renderer. Do not add a `Null`
backend configuration because the pinned release core crashes before the
runner's first-frame handshake when asked to use it.

## Why an experiment, not a replacement

The pinned Dolphin-libretro source maps any non-Hardware/non-Software renderer
selection to Dolphin's Null graphics backend. Its normal release option list
does not advertise Null, so stock frontend availability does not establish
compatibility with this host/core/game combination.

Hardware is already validated for boot, visual diagnostics, and exact
snapshot/replay. Null is a PRD performance/state-only gate, not a prerequisite
architecture and not a reason to remove the proven mode.

## Result

On the pinned core `2606.0.393+ed70219e8b`, a direct runner invocation with
`--renderer Null` logged `Using GFX backend: Null`, reached the retail disc
boot path, and then exited with signal 11 (exit status 139) before emitting
`READY`. The Python backend observed the same failed startup.

This is a fundamental compatibility failure for the chosen release core,
not an optimization opportunity. The experiment was removed from the public
backend API after confirmation.

## Alternatives rejected

- **Making Null the default before a live validation:** would repeat the
  abandoned-prototype assumption the implementation note warns against.
- **A separate Null-specific runner or patch rescue:** would fork control
  semantics and consume effort on a crashing path, contrary to the project's
  stock-behavior preference.
- **Treating absence of video callbacks as proof of state-only correctness:**
  the probe also checks GXEE8P identification, MEM1, input propagation,
  snapshot restore, and bounded stepping.
