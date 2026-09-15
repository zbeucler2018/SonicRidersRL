# Milestone 10: attract-transition control mapping result

This read-only investigation tested the apparent two-player transition reached
from the stock attract race. It adds no environment or game mutation code.

## Observed mapping

At the snapshot boundary following the input-triggered loading transition:

| Player slots | `ai_control` | `player_type` | Controller port |
|---|---:|---:|---:|
| 0 | 0 | 0 | 0 |
| 1 | 0 | 0 | 1 |
| 2–3 | 1 | 1 | 2–3 |
| 4–7 | 1 | 1 | 0 |

After 1,200 frames, the first two slots reverted to `ai_control=1` while
retaining `player_type=0`. P0 and P1 inputs still changed full MEM1 (input
records are live), but did not change decoded racer positions from the same
post-countdown snapshot.

## Result

The attract transition is a valuable input/controller mapping fixture but not
a direct-steering fixture. The control path through retail game memory is
validated; human-racer ownership is not.

The next milestone should establish a menu-driven normal race configuration
and use a snapshot differential to prove P1 stick input changes Player 0's
position/orientation relative to neutral.
