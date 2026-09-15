# Reverse-Engineering Notes

## Primary sources

Useful public projects include:

- `doldecomp/sonicriders`
- `RidersBoulevard/sonicriderste`
- `babylon-workshop/sonicriderstruecolors`
- `Sewer56/Riders.Tweakbox`
- `Sewer56/SonicRiders.Index`

Tournament Edition-derived structures are a semantic bootstrap, not automatic proof that every offset is identical in the exact vanilla NTSC-U build.

## Validation rule

Every field used by the environment should have a provenance status:

```text
documented
vanilla-validated
derived
experimental
mod-specific
unknown
```

## Player array

Community source indicates:

```text
MaxPlayerCount = 8
MaxControllerCount = 4
Player stride = 0x1080
```

The first four players are controller-capable; all eight can participate in a race.

The immediate task is to resolve the runtime vanilla `players[]` base address and validate the stride using multiple independent high-confidence fields.

## High-priority fields

Start validation with:

```text
position x/y/z
speed
current Air
Rings
current lap
placement
player state
stageProgress
```

These are easy to manipulate or observe while manually playing and give strong confidence in base-address/stride correctness.

## Event derivation

Prefer semantic events derived from consecutive telemetry snapshots rather than game-function hooks.

Examples:

```text
BoostStarted
RingCollected
LevelChanged
TrickLanded
GrindStarted / GrindEnded
TurbulenceEntered / Exited
AttackHit
LapCompleted
WallBonk
```

Only introduce code hooks when memory-state transitions cannot provide reliable attribution.
