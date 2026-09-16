# Milestone 15 architecture decision: local human debug viewer

The viewer is a localhost-only browser page backed by the existing libretro
worker. It renders raw PPM game frames into a left canvas and presents telemetry
in a separate right panel; debug text is never overlaid on game video. Keyboard
input drives P1 and `R` restores a process-local normal-race snapshot.

This tool is intentionally wall-clock paced for human play. Training remains
the synchronous caller-paced backend. No GUI toolkit or host package is added.
