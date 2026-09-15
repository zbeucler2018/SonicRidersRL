# Milestone 2 architecture decision: relocatable telemetry reconnaissance

## Goal

Build the smallest read-only game-memory layer needed to investigate vanilla
Sonic Riders safely. This milestone remains below environments, rewards,
observations, events, Gymnasium, PettingZoo, and training.

## Decision

Resolve the vanilla `players[]` address from a version-specific instruction
signature in the loaded `_Main.rel` module instead of storing a fixed guest
address.

The public `doldecomp/sonicriders` source at commit
`4f42e59cb5b6089a2aba413d344f804e5362f06f` identifies an `_Main` code
sequence which takes `players[]`, multiplies an index by `0x1080`, and indexes
the result. The runtime resolver matches that full opcode sequence, reconstructs
the relocated PowerPC `@ha`/`@l` address pair, and rejects missing or ambiguous
matches. It then bounds-checks eight `0x1080`-byte records against the MEM1
descriptor before reading them.

On this host's clean `GXEE8P` boot, the resolver found the reference at
`0x803FC4A8` and the current array base at `0x80609440`. That address is
evidence from one run, not a schema constant.

The schema is stored at
`schemas/GXEE8P/vanilla_ntscu_v1.yaml`. It labels the array base and fresh-menu
layout as vanilla-validated, while every gameplay field remains explicitly
`unvalidated-in-race` until tested in a real race.

## Rejected alternatives

- A fixed `0x80609440` address: `_Main.rel` is relocatable, so this would be
  a fragile accident of one allocation.
- A generic scan for plausible floats or player-like data: it has poor failure
  modes and could silently bind a wrong structure.
- Tournament Edition absolute addresses: its `Player` layout is useful
  community evidence, but the mod's loader and memory placement are not proof
  for vanilla NTSC-U.
- Dolphin hooks or a private fork: direct, bounded MEM1 reads and an upstream
  code signature already provide the needed observation boundary.

## Input and write hardening

The runner now reports input callback activity independently for ports 0–3 and
maps libretro's `RETRO_DEVICE_INDEX_ANALOG_BUTTON` L2/R2 values to the native
GameCube trigger fields. This lets a probe distinguish four controller paths
rather than merely observing Player 1 callbacks.

The only write validation mutates one byte at `0x80000000` after creating an
in-memory savestate, reads the changed byte, and restores before any emulation
frame executes. It is a transport test, not a game-state manipulation feature.
