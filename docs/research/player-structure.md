# Player Structure Research

Current community reverse engineering describes a `Player` structure with a stride of `0x1080` bytes and an eight-entry player array.

## Selected fields

| Offset | Field | Notes |
|---:|---|---|
| `0x000` | input/controller pointer | Validate vanilla semantics |
| `0x0BA` | character | Character ID |
| `0x0BB` | extremeGear | Gear ID |
| `0x0BC` | aiControl | CPU/player control indicator |
| `0x1E4` | x | `f32` |
| `0x1E8` | y | `f32` |
| `0x1EC` | z | `f32` |
| `0x358` | forward | Vector3F |
| `0x5E6` | current pathfinding point | Route-related |
| `0x624` | rail state | Grind state |
| `0x628` | rail ID | Rail identifier |
| `0x6C8` | turbulence state | Turbulence-related state |
| `0x8AC` | boost duration | Boost state/timer |
| `0x984` | current Air | `s32` |
| `0x988` | Air gain | Air delta gain |
| `0x98C` | Air loss | Air delta loss |
| `0x9F4` | jump charge | Jump mechanic |
| `0x9FF` | trick rank | Trick result/rank |
| `0xA28` | movement flags | Drifting/boosting/etc. |
| `0xAAC` | speed | `f32` |
| `0xB54` | drift-dash frames | Drift mechanic |
| `0xB98` | Rings | Ring count |
| `0xBA8` | player flags | Includes wall/turbulence/pit flags |
| `0xBB0` | status effects | Magnet/invincibility/etc. |
| `0xBC4` | stageProgress | Critical reward/progress candidate |
| `0xF38` | attacked player ptr | Combat relationship; naming requires validation |
| `0xF3C` | attacking player ptr | Combat relationship; naming requires validation |
| `0x1029` | index | Player index |
| `0x102A` | current lap | Lap |
| `0x102D` | placement | Current placement |
| `0x102E` | level | Gear/ring level |
| `0x1034` | state | PlayerState enum |
| `0x1035` | previous state | Previous PlayerState |

## Important player states

Known states include:

```text
StartLine
Death
Retire
Cruise
Jump
Fall
FrontflipRamp
BackflipRamp
HalfPipeTrick
ManualRamp
TurbulenceTrick
PlayerCollide
TurbulenceRide
RailGrind
Fly
AttackingPlayer
AttackedByPlayer
Stun
Run
```

## Movement / status flags

Useful known flags include boosting, drifting, braking, jump charge, rail link, wall bonk, turbulence, Air Pit, magnet and invincibility.

## Stage progress validation

`stageProgress` at `0xBC4` is a high-priority candidate for dense progress reward. Test it across:

- normal racing;
- reverse movement;
- rails;
- Flight and Power routes;
- alternate paths;
- shortcuts;
- turbulence;
- falls and respawns;
- lap boundaries;
- finish crossing.

If it is not route-consistent, replace it with a track-aware progress representation.
