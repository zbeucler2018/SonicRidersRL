"""Human-playable local viewer for the normal P1 race fixture.

This is a debugging tool, not the training runtime. Open the printed localhost
URL in a browser; game video is on the left and telemetry is on the right.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
import select
import struct
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from time import monotonic, sleep

from .backend import BackendConfig, ControllerState, GameCubeButton, LibretroDolphinBackend
from .fixtures import boot_normal_free_race
from .telemetry import read_game_mode, read_players


PAGE = b'''<!doctype html><title>Sonic Riders debug viewer</title><style>
body{margin:0;background:#15171a;color:#e8eaed;font:14px system-ui}main{display:flex;gap:16px;padding:16px;align-items:flex-start}canvas{image-rendering:auto;background:#000;max-width:66vw}aside{width:360px;min-height:500px;background:#22262b;padding:14px;border-radius:6px}pre{white-space:pre-wrap;margin:0;color:#b8e7ff}.hint{color:#b7c0cb}</style><main><section><canvas id=g width=640 height=528></canvas><p class=hint>WASD: stick | Z: A | X: B | Enter: Start | Q/E: triggers | R: reset fixture</p></section><aside><h2>Live debug telemetry</h2><pre id=t>Booting...</pre></aside></main><script>
const held=new Set(), c=document.querySelector('#g'),x=c.getContext('2d'),t=document.querySelector('#t');
function send(){let pads=navigator.getGamepads?navigator.getGamepads():[],g=pads&&pads[0];fetch('/keys',{method:'POST',body:JSON.stringify({keys:[...held],gamepad:g?{axes:[g.axes[0]||0,g.axes[1]||0],buttons:g.buttons.map(b=>b.pressed)}:null})})}
addEventListener('keydown',e=>{if(e.key==='r'){fetch('/reset',{method:'POST'});return}if(e.key==='t'){fetch('/record',{method:'POST'});return}if(['w','a','s','d','z','x','q','e','Enter'].includes(e.key)){held.add(e.key);send();e.preventDefault()}});
addEventListener('keyup',e=>{if(held.delete(e.key)){send();e.preventDefault()}});addEventListener('blur',()=>{held.clear();send()});
async function frame(){let b=await (await fetch('/frame')).arrayBuffer(),u=new Uint8Array(b),p=0,n=0;while(n<3){if(u[p]===35){while(u[p++]!==10);}else if(u[p++]===10)n++}let s=new ImageData(new Uint8ClampedArray(640*528*4),640,528);for(let i=0,j=p;i<640*528;i++,j+=3){s.data[i*4]=u[j];s.data[i*4+1]=u[j+1];s.data[i*4+2]=u[j+2];s.data[i*4+3]=255}x.putImageData(s,0,0)}
async function tick(){try{send();await frame();t.textContent=JSON.stringify(await (await fetch('/telemetry')).json(),null,2)}catch(_){ }setTimeout(tick,80)}send();tick();</script>'''


class ViewerState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.keys: set[str] = set()
        self.gamepad: dict[str, object] | None = None
        self.host_axes: dict[int, int] = {}
        self.host_buttons: set[int] = set()
        self.reset_requested = False
        self.record_toggle = False
        self.frame = b"P6\n640 528\n255\n" + bytes(640 * 528 * 3)
        self.telemetry: dict[str, object] = {"status": "booting"}

    def controller(self) -> ControllerState:
        with self.lock:
            keys, gamepad = self.keys.copy(), self.gamepad
            host_axes, host_buttons = self.host_axes.copy(), self.host_buttons.copy()
        axes = gamepad.get("axes", [0, 0]) if gamepad else [0, 0]
        buttons = gamepad.get("buttons", []) if gamepad else []
        def pressed(index: int) -> bool: return index < len(buttons) and bool(buttons[index])
        def axis(index: int) -> int: return int(max(-1, min(1, float(axes[index]))) * 32767) if index < len(axes) else 0
        return ControllerState(
            buttons=(GameCubeButton.A.mask if "z" in keys or pressed(0) or 0 in host_buttons else 0)
            | (GameCubeButton.B.mask if "x" in keys or pressed(1) or 1 in host_buttons else 0)
            | (GameCubeButton.START.mask if "Enter" in keys or pressed(9) or 9 in host_buttons else 0),
            left_x=host_axes.get(0, 0) or axis(0) or 20_000 * (("d" in keys) - ("a" in keys)),
            left_y=host_axes.get(1, 0) or axis(1) or 20_000 * (("s" in keys) - ("w" in keys)),
            left_trigger=32_767 if "q" in keys or pressed(6) or 6 in host_buttons else 0,
            right_trigger=32_767 if "e" in keys or pressed(7) or 7 in host_buttons else 0,
        )


class LinuxJoystick:
    """Tiny dependency-free reader for Linux's stable /dev/input/jsN ABI."""
    _EVENT = struct.Struct("IhBB")
    def __init__(self, path: Path | None):
        self.path = path; self.fd: int | None = None
    def _open(self) -> None:
        if self.fd is None and self.path and self.path.exists():
            try: self.fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)
            except OSError: pass
    def poll(self, state: ViewerState) -> None:
        self._open()
        if self.fd is None: return
        try:
          while select.select([self.fd], [], [], 0)[0]:
            data = os.read(self.fd, self._EVENT.size)
            if len(data) != self._EVENT.size: return
            _, value, event_type, number = self._EVENT.unpack(data); event_type &= 0x7F
            with state.lock:
                if event_type == 1:
                    (state.host_buttons.add if value else state.host_buttons.discard)(number)
                elif event_type == 2: state.host_axes[number] = value
        except OSError:
            self.close()
    def close(self) -> None:
        if self.fd is not None: os.close(self.fd)


def _handler(state: ViewerState):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                self._send(HTTPStatus.OK, "text/html", PAGE)
            elif self.path == "/frame":
                with state.lock: data = state.frame
                self._send(HTTPStatus.OK, "image/x-portable-pixmap", data)
            elif self.path == "/telemetry":
                with state.lock: data = json.dumps(state.telemetry).encode()
                self._send(HTTPStatus.OK, "application/json", data)
            else: self.send_error(HTTPStatus.NOT_FOUND)
        def do_POST(self) -> None:
            if self.path == "/keys":
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                with state.lock:
                    state.keys = set(payload.get("keys", []))
                    state.gamepad = payload.get("gamepad")
                self._send(HTTPStatus.NO_CONTENT, "text/plain", b"")
            elif self.path == "/reset":
                with state.lock: state.reset_requested = True
                self._send(HTTPStatus.NO_CONTENT, "text/plain", b"")
            elif self.path == "/record":
                with state.lock: state.record_toggle = True
                self._send(HTTPStatus.NO_CONTENT, "text/plain", b"")
            else: self.send_error(HTTPStatus.NOT_FOUND)
        def _send(self, status, content_type, data):
            self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        def log_message(self, *_): pass
    return Handler


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--port", type=int, default=8765); p.add_argument("--joystick", type=Path, default=Path("/dev/input/js1")); args = p.parse_args()
    state = ViewerState(); server = ThreadingHTTPServer(("127.0.0.1", args.port), _handler(state))
    config = BackendConfig(root / "build/sonic-libretro-runner", root / ".local/core/dolphin_libretro.so", Path("~/Games/GameCube/SonicRiders/sonic_riders_usa.rvz"), root / ".local/runtime/system", root / ".local/runtime/saves/debug-viewer")
    with LibretroDolphinBackend(config) as backend:
        mode, players, _ = boot_normal_free_race(backend); snapshot = backend.snapshot()
        recording: list[dict[str, object]] = []; recording_active = False; last_trace: str | None = None
        joystick = LinuxJoystick(args.joystick if args.joystick.exists() else None)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"Open http://127.0.0.1:{args.port} (Ctrl-C to stop)", flush=True)
        try:
            while True:
                started = monotonic()
                joystick.poll(state)
                with state.lock:
                    reset = state.reset_requested; state.reset_requested = False
                    toggle = state.record_toggle; state.record_toggle = False
                if toggle:
                    if recording_active:
                        trace_dir = root / ".local/traces"; trace_dir.mkdir(parents=True, exist_ok=True)
                        path = trace_dir / f"viewer-{int(monotonic() * 1000)}.json"
                        path.write_text(json.dumps({"format": "sonic-riders-input-trace-v1", "game_id": "GXEE8P", "frames_per_step": 4, "steps": recording}, indent=2) + "\n")
                        last_trace = str(path); recording_active = False
                    else:
                        backend.restore(snapshot); recording = []; recording_active = True; last_trace = None
                if reset: backend.restore(snapshot)
                controller = state.controller(); backend.step({0: controller}, frames=4)
                p0 = read_players(backend, players)[0]; game = read_game_mode(backend, mode)
                if recording_active: recording.append({"controller": asdict(controller), "player_0": asdict(p0), "game_mode": asdict(game)})
                capture = backend.capture_frame("viewer.ppm").read_bytes()
                with state.lock:
                    state.frame = capture
                    state.telemetry = {"game_mode": asdict(game), "player_0": asdict(p0), "host_joystick": {"path": str(args.joystick), "axes": state.host_axes, "buttons": sorted(state.host_buttons)}, "recording": recording_active, "recorded_steps": len(recording), "last_trace": last_trace, "reset_available": True}
                sleep(max(0, 1 / 15 - (monotonic() - started)))
        except KeyboardInterrupt: pass
        finally: joystick.close(); server.shutdown()

if __name__ == "__main__": main()
