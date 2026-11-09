#!/usr/bin/env python3
"""
In-container computer agent for Linux desktop sessions.

The agent is mounted read-only at ``/codx/computer_agent.py`` and invoked with
``docker exec -i <container> python3 /codx/computer_agent.py``.  It reads one
JSON command from stdin and writes one JSON response to stdout, so the API can
drive the desktop without exposing another network service.

Design constraints
------------------
* No third-party dependency is required besides **Pillow** (present in the
  LinuxServer.io webtop images).  Input and window management use ``xdotool``;
  clipboard uses ``xclip``; both are part of the webtop image.
* Every command is a plain function so it can be reused/tested.  The API never
  interpolates user values into a shell: commands are passed as argv lists and
  text is sent to ``xdotool type`` through a separate argument.
* The response is always valid JSON, including on error, so the caller can show
  a useful message instead of a traceback.

Actions
-------
``screenshot``, ``screen_size``, ``click``, ``double_click``, ``right_click``,
``move``, ``drag``, ``scroll``, ``type``, ``key``, ``hotkey``, ``wait``,
``clipboard_get``, ``clipboard_set``, ``windows``, ``active_window``,
``focus_window``, ``close_window``, ``open_app``, ``list_apps``,
``run_command``, ``mouse_position``, ``ping``.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import base64
import binascii
import ctypes
import ctypes.util
import io
import json
import os
import shlex
import shutil
import struct
import subprocess
import sys
import time
import zlib
from typing import Any, Dict, List, Optional, Tuple

DISPLAY = os.environ.get("DISPLAY", ":1")
#: Keep screenshots affordable: 1600 px wide is enough for the model and the UI.
DEFAULT_MAX_WIDTH = 1600
#: Hard cap on command output returned to the model.
MAX_COMMAND_OUTPUT = 20000


# ---------------------------------------------------------------------------
# Process helpers
# ---------------------------------------------------------------------------
def _env() -> Dict[str, str]:
    """Environment for child processes (always a usable DISPLAY)."""
    env = dict(os.environ)
    env.setdefault("DISPLAY", DISPLAY)
    return env


def _run(
    args: List[str],
    timeout: float = 30,
    input_text: Optional[str] = None,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """Run a command with a timeout and captured output."""
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=max(1.0, float(timeout)),
        input=input_text,
        env=_env(),
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(args[:3])} failed ({result.returncode}): "
            f"{(result.stderr or result.stdout or '').strip()[:500]}"
        )
    return result


def _require(tool: str) -> str:
    """Return the path of *tool* or raise a helpful error."""
    path = shutil.which(tool)
    if not path:
        raise RuntimeError(
            f"'{tool}' is not installed in the desktop container; "
            "use a LinuxServer.io webtop image or install it"
        )
    return path


def _int(value: Any, default: int = 0) -> int:
    """Parse an integer from JSON (accepts floats and numeric strings)."""
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default



# ---------------------------------------------------------------------------
# X11 fallback (Kasmweb images ship libX11 + libXtst but not xdotool)
# ---------------------------------------------------------------------------
class X11:
    """Tiny ctypes wrapper around Xlib/XTest used when xdotool is absent.

    Kasmweb workspace images expose a standard X11 desktop (Xvnc + XFCE) and
    include ``libX11`` and ``libXtst``, but not ``xdotool``.  This fallback lets
    the same agent drive them: XTest injects pointer/key events, XQueryPointer
    reads the cursor and Xlib reports the screen size.
    """

    _instance = None

    def __init__(self) -> None:
        x11_name = ctypes.util.find_library("X11") or "libX11.so.6"
        xtst_name = ctypes.util.find_library("Xtst") or "libXtst.so.6"
        self.x11 = ctypes.CDLL(x11_name)
        self.xtst = ctypes.CDLL(xtst_name)
        self.x11.XOpenDisplay.restype = ctypes.c_void_p
        self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.display = self.x11.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError(
                f"Cannot open X display '{DISPLAY}'; is DISPLAY exported?"
            )
        self.x11.XDefaultScreen.restype = ctypes.c_int
        self.x11.XDefaultScreen.argtypes = [ctypes.c_void_p]
        self.screen = self.x11.XDefaultScreen(self.display)
        self.x11.XDefaultRootWindow.restype = ctypes.c_ulong
        self.x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self.root = self.x11.XDefaultRootWindow(self.display)
        self.x11.XDisplayWidth.restype = ctypes.c_int
        self.x11.XDisplayWidth.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.x11.XDisplayHeight.restype = ctypes.c_int
        self.x11.XDisplayHeight.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.x11.XFlush.argtypes = [ctypes.c_void_p]
        self.x11.XStringToKeysym.restype = ctypes.c_ulong
        self.x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
        self.x11.XKeysymToKeycode.restype = ctypes.c_ubyte
        self.x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.xtst.XTestFakeMotionEvent.restype = ctypes.c_int
        self.xtst.XTestFakeMotionEvent.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong
        ]
        self.xtst.XTestFakeButtonEvent.restype = ctypes.c_int
        self.xtst.XTestFakeButtonEvent.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong
        ]
        self.xtst.XTestFakeKeyEvent.restype = ctypes.c_int
        self.xtst.XTestFakeKeyEvent.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong
        ]
        self.x11.XQueryPointer.restype = ctypes.c_int
        self.x11.XQueryPointer.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong,
            ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_uint),
        ]

    @classmethod
    def get(cls) -> "X11":
        """Return the shared display wrapper."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def width(self) -> int:
        return int(self.x11.XDisplayWidth(self.display, self.screen))

    @property
    def height(self) -> int:
        return int(self.x11.XDisplayHeight(self.display, self.screen))

    def flush(self) -> None:
        self.x11.XFlush(self.display)

    def move(self, x: int, y: int) -> None:
        self.xtst.XTestFakeMotionEvent(self.display, self.screen, int(x), int(y), 0)
        self.flush()

    def button(self, number: int, down: bool) -> None:
        self.xtst.XTestFakeButtonEvent(self.display, int(number), 1 if down else 0, 0)
        self.flush()

    def keycode(self, keysym: int) -> int:
        return int(self.x11.XKeysymToKeycode(self.display, int(keysym)))

    def key_event(self, keycode: int, down: bool) -> None:
        self.xtst.XTestFakeKeyEvent(self.display, int(keycode), 1 if down else 0, 0)
        self.flush()

    def pointer(self) -> Dict[str, int]:
        root = ctypes.c_ulong()
        child = ctypes.c_ulong()
        root_x = ctypes.c_int()
        root_y = ctypes.c_int()
        win_x = ctypes.c_int()
        win_y = ctypes.c_int()
        mask = ctypes.c_uint()
        ok = self.x11.XQueryPointer(
            self.display, self.root,
            ctypes.byref(root), ctypes.byref(child),
            ctypes.byref(root_x), ctypes.byref(root_y),
            ctypes.byref(win_x), ctypes.byref(win_y),
            ctypes.byref(mask),
        )
        if not ok:
            return {"x": 0, "y": 0}
        return {"x": int(root_x.value), "y": int(root_y.value)}


#: X11 keysyms used by the fallback input implementation.
X11_KEYS = {
    "shift": 0xFFE1, "ctrl": 0xFFE3, "control": 0xFFE3,
    "alt": 0xFFE9, "super": 0xFFEB, "meta": 0xFFEB, "cmd": 0xFFEB,
    "return": 0xFF0D, "enter": 0xFF0D, "tab": 0xFF09,
    "escape": 0xFF1B, "esc": 0xFF1B, "backspace": 0xFF08,
    "delete": 0xFFFF, "insert": 0xFF63, "home": 0xFF50,
    "end": 0xFF57, "pageup": 0xFF55, "pagedown": 0xFF56,
    "page_up": 0xFF55, "page_down": 0xFF56,
    "up": 0xFF52, "down": 0xFF54, "left": 0xFF51, "right": 0xFF53,
    "space": 0x20, "caps_lock": 0xFFE5, "num_lock": 0xFF7F,
}
for _index in range(1, 13):
    X11_KEYS[f"f{_index}"] = 0xFFBE + (_index - 1)

_X11_SHIFTED = {
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6",
    "&": "7", "*": "8", "(": "9", ")": "0", "_": "-", "+": "=",
    "{": "[", "}": "]", "|": "\\", ":": ";", '"': "'", "<": ",",
    ">": ".", "?": "/", "~": "`",
}


def _has_xdotool() -> bool:
    """True when xdotool is available (LinuxServer images)."""
    return bool(shutil.which("xdotool"))


def _x11() -> X11:
    """Return the shared X11 wrapper."""
    return X11.get()


def _x11_keysym(char: str) -> Tuple[int, bool]:
    """Return ``(keysym, shift)`` for a printable character."""
    if char in _X11_SHIFTED:
        return ord(_X11_SHIFTED[char]), True
    if "A" <= char <= "Z":
        return ord(char.lower()), True
    if char == " ":
        return 0x20, False
    code = ord(char)
    if code > 0x7E:
        # X11 Unicode keysym convention.
        return 0x01000000 | code, False
    return code, False


def _x11_press_keysym(keysym: int, shift: bool = False) -> None:
    """Press and release a keysym with optional Shift."""
    display = _x11()
    shift_code = display.keycode(X11_KEYS["shift"])
    code = display.keycode(keysym)
    if not code:
        return
    if shift:
        display.key_event(shift_code, True)
    display.key_event(code, True)
    display.key_event(code, False)
    if shift:
        display.key_event(shift_code, False)


def _x11_press_combo(combo: str) -> None:
    """Press a key combo through XTest."""
    parts = [part.strip().lower() for part in str(combo or "").split("+") if part.strip()]
    if not parts:
        raise ValueError("key combo is empty")
    display = _x11()
    modifiers = []
    target = None
    for part in parts:
        if part in ("ctrl", "control") and target is None:
            modifiers.append(X11_KEYS["ctrl"])
        elif part == "shift" and target is None:
            modifiers.append(X11_KEYS["shift"])
        elif part in ("alt", "option") and target is None:
            modifiers.append(X11_KEYS["alt"])
        elif part in ("super", "meta", "cmd", "command", "win") and target is None:
            modifiers.append(X11_KEYS["super"])
        else:
            target = X11_KEYS.get(part)
            if target is None:
                if len(part) == 1:
                    target, _ = _x11_keysym(part)
                else:
                    target = int(display.x11.XStringToKeysym(part.encode("utf-8")))
            if not target:
                raise ValueError(f"Unknown key '{part}'")
    if target is None:
        target = modifiers.pop() if modifiers else 0
    modifier_codes = [display.keycode(item) for item in modifiers]
    for code in modifier_codes:
        display.key_event(code, True)
    if target:
        code = display.keycode(target)
        display.key_event(code, True)
        display.key_event(code, False)
    for code in reversed(modifier_codes):
        display.key_event(code, False)


def _x11_type_text(text: str) -> None:
    """Type text through XTest."""
    for char in str(text or ""):
        if char == "\n":
            _x11_press_keysym(X11_KEYS["return"])
        elif char == "\t":
            _x11_press_keysym(X11_KEYS["tab"])
        else:
            keysym, shift = _x11_keysym(char)
            _x11_press_keysym(keysym, shift)
        time.sleep(0.003)


def _x11_window_list() -> Dict[str, Any]:
    """List windows through wmctrl when xdotool is unavailable."""
    root = _x11().root
    active = 0
    try:
        result = _run(["xprop", "-root", "_NET_ACTIVE_WINDOW"])
        value = (result.stdout or "").split("#")[-1].strip().split(",")[0]
        active = int(value, 0) if value else 0
    except Exception:
        active = 0
    windows = []
    for line in (_run(["wmctrl", "-l"]).stdout or "").splitlines():
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        window_id, _desktop, _host, title = parts
        try:
            info = _run(["xwininfo", "-id", window_id])
            geometry = {}
            for item in (info.stdout or "").splitlines():
                if ":" not in item:
                    continue
                key, _, value = item.partition(":")
                key = key.strip().lower()
                if key.startswith("absolute upper-left"):
                    geometry["x" if key.endswith("x") else "y"] = int(value.strip())
                elif key in ("width", "height"):
                    geometry[key] = int(value.strip())
            windows.append({
                "id": window_id,
                "title": title,
                "x": geometry.get("x", 0),
                "y": geometry.get("y", 0),
                "width": geometry.get("width", 0),
                "height": geometry.get("height", 0),
                "active": bool(active and int(window_id, 16) == active),
            })
        except Exception:
            continue
    return {"windows": windows[:60], "active": hex(active) if active else None}


def _xwd_screenshot() -> Tuple[bytes, int, int]:
    """
    Capture the root window with xwd and encode it as PNG.

    XWD is the only screenshot tool guaranteed by Kasmweb images.  The header
    and pixel layout are parsed directly; no Pillow/ImageMagick dependency.
    """
    result = subprocess.run(
        ["xwd", "-root", "-silent", "-display", DISPLAY],
        capture_output=True,
        timeout=30,
        env=_env(),
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "xwd failed").decode("utf-8", "replace")[:500])
    data = result.stdout
    if len(data) < 100:
        raise RuntimeError("xwd returned a truncated header")
    fields = struct.unpack(">25I", data[:100])
    header_size, pixmap_width, pixmap_height = fields[0], fields[4], fields[5]
    byte_order, bits_per_pixel, bytes_per_line = fields[7], fields[11], fields[12]
    red_mask, green_mask, blue_mask = fields[14], fields[15], fields[16]
    ncolors = fields[19]
    pixels_offset = header_size + ncolors * 12
    if pixmap_width <= 0 or pixmap_height <= 0:
        raise RuntimeError("xwd reported an empty image")
    bpp_bytes = max(1, bits_per_pixel // 8)
    pixel_data = data[pixels_offset:]
    rows = []
    for y in range(pixmap_height):
        row = bytearray()
        line = y * bytes_per_line
        for x in range(pixmap_width):
            offset = line + x * bpp_bytes
            chunk = pixel_data[offset:offset + bpp_bytes]
            if len(chunk) < bpp_bytes:
                raise RuntimeError("xwd pixel data is truncated")
            pixel = int.from_bytes(chunk, "little" if byte_order == 0 else "big")
            red = (pixel & red_mask)
            green = (pixel & green_mask)
            blue = (pixel & blue_mask)
            if red_mask:
                red = (red >> (red_mask.bit_length() - 8)) if red_mask.bit_length() > 8 else red << (8 - red_mask.bit_length())
            if green_mask:
                green = (green >> (green_mask.bit_length() - 8)) if green_mask.bit_length() > 8 else green << (8 - green_mask.bit_length())
            if blue_mask:
                blue = (blue >> (blue_mask.bit_length() - 8)) if blue_mask.bit_length() > 8 else blue << (8 - blue_mask.bit_length())
            row.extend((int(red) & 0xFF, int(green) & 0xFF, int(blue) & 0xFF))
        rows.append(bytes(row))
    return _encode_png(pixmap_width, pixmap_height, rows), pixmap_width, pixmap_height


def _encode_png(width: int, height: int, rows: List[bytes]) -> bytes:
    """Encode RGB rows as a PNG without Pillow."""
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + row for row in rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------------------
# Display / screenshot
# ---------------------------------------------------------------------------
def screen_size() -> Dict[str, Any]:
    """Return the X11 display size in pixels."""
    if _has_xdotool():
        result = _run([_require("xdotool"), "getdisplaygeometry"], check=True)
        width, height = (result.stdout or "").split()
        return {"width": int(width), "height": int(height)}
    display = _x11()
    return {"width": display.width, "height": display.height}


def screenshot(max_width: int = DEFAULT_MAX_WIDTH) -> Dict[str, Any]:
    """Capture the whole desktop and return a base64 PNG data URI.

    Pillow (X11 grab) is used when available; Kasmweb images ship ``xwd``
    instead, so the fallback parses XWD and encodes PNG in pure Python.
    """
    try:
        from PIL import Image, ImageGrab
    except Exception:
        png, width, height = _xwd_screenshot()
        return {
            "width": width,
            "height": height,
            "image_width": width,
            "image_height": height,
            "mime": "image/png",
            "data": "data:image/png;base64," + base64.b64encode(png).decode("ascii"),
            "backend": "xwd",
        }

    image = ImageGrab.grab(xdisplay=DISPLAY)
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    width, height = image.size
    max_width = max(320, _int(max_width, DEFAULT_MAX_WIDTH))
    if width > max_width:
        ratio = max_width / float(width)
        image = image.resize(
            (max_width, max(1, int(round(height * ratio)))),
            Image.LANCZOS,
        )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return {
        "width": width,
        "height": height,
        "image_width": image.size[0],
        "image_height": image.size[1],
        "mime": "image/png",
        "data": f"data:image/png;base64,{payload}",
        "backend": "pillow",
    }


# ---------------------------------------------------------------------------
# Mouse
# ---------------------------------------------------------------------------
def move(x: int, y: int) -> Dict[str, Any]:
    """Move the pointer to absolute display coordinates."""
    if _has_xdotool():
        _run([_require("xdotool"), "mousemove", "--sync", str(_int(x)), str(_int(y))], check=True)
    else:
        _x11().move(_int(x), _int(y))
    return {"x": _int(x), "y": _int(y)}


def click(
    x: int = 0,
    y: int = 0,
    button: str = "left",
    clicks: int = 1,
    interval_ms: int = 80,
    move_first: bool = True,
) -> Dict[str, Any]:
    """Click a mouse button (1=left, 2=middle, 3=right) at x,y."""
    number = {"left": 1, "middle": 2, "right": 3}.get(
        str(button or "left").lower(), _int(button, 1)
    )
    clicks = max(1, min(3, _int(clicks, 1)))
    if _has_xdotool():
        cmd = [_require("xdotool")]
        if move_first:
            cmd.extend(["mousemove", "--sync", str(_int(x)), str(_int(y))])
        cmd.extend(["click", "--repeat", str(clicks), "--delay",
                    str(max(1, _int(interval_ms, 80))), str(number)])
        _run(cmd, check=True)
    else:
        display = _x11()
        display.move(_int(x), _int(y))
        for _ in range(clicks):
            display.button(number, True)
            time.sleep(max(0.001, _int(interval_ms, 80) / 1000.0))
            display.button(number, False)
            time.sleep(0.08)
    return {"x": _int(x), "y": _int(y), "button": button, "clicks": clicks}


def drag(
    from_x: int,
    from_y: int,
    to_x: int,
    to_y: int,
    duration_ms: int = 500,
    button: str = "left",
) -> Dict[str, Any]:
    """Press, move and release the pointer (drag & drop / selection)."""
    button_number = {"left": "1", "middle": "2", "right": "3"}.get(
        str(button or "left").lower(), "1"
    )
    steps = max(2, min(40, _int(duration_ms, 500) // 25))
    start_x, start_y = _int(from_x), _int(from_y)
    end_x, end_y = _int(to_x), _int(to_y)
    if _has_xdotool():
        xdotool = _require("xdotool")
        _run([xdotool, "mousemove", "--sync", str(start_x), str(start_y)], check=True)
        _run([xdotool, "mousedown", button_number], check=True)
        try:
            for step in range(1, steps + 1):
                x = start_x + (end_x - start_x) * step // steps
                y = start_y + (end_y - start_y) * step // steps
                _run([xdotool, "mousemove", "--sync", str(x), str(y)])
                time.sleep(max(0.005, (_int(duration_ms, 500) / 1000.0) / steps))
        finally:
            _run([xdotool, "mouseup", button_number], check=True)
    else:
        display = _x11()
        number = _int(button_number, 1)
        display.move(start_x, start_y)
        display.button(number, True)
        try:
            for step in range(1, steps + 1):
                x = start_x + (end_x - start_x) * step // steps
                y = start_y + (end_y - start_y) * step // steps
                display.move(x, y)
                time.sleep(max(0.005, (_int(duration_ms, 500) / 1000.0) / steps))
        finally:
            display.button(number, False)
    return {"from": [start_x, start_y], "to": [end_x, end_y]}


def scroll(
    x: int = 0,
    y: int = 0,
    amount: int = 3,
    direction: str = "down",
) -> Dict[str, Any]:
    """Scroll the wheel at x,y (positive amount scrolls down by default)."""
    amount = max(1, min(50, abs(_int(amount, 3))))
    direction = str(direction or "down").lower()
    if direction in ("up", "left"):
        button = "4" if direction == "up" else "6"
    else:
        button = "5" if direction == "down" else "7"
    if _has_xdotool():
        xdotool = _require("xdotool")
        _run([xdotool, "mousemove", "--sync", str(_int(x)), str(_int(y))], check=True)
        _run([xdotool, "click", "--repeat", str(amount), "--delay", "25", button], check=True)
    else:
        display = _x11()
        display.move(_int(x), _int(y))
        number = _int(button, 4)
        for _ in range(amount):
            display.button(number, True)
            time.sleep(0.02)
            display.button(number, False)
    return {"x": _int(x), "y": _int(y), "amount": amount, "direction": direction}


def mouse_position() -> Dict[str, Any]:
    """Return the current pointer position."""
    if not _has_xdotool():
        position = _x11().pointer()
        return {"x": position["x"], "y": position["y"], "screen": 0, "window": None}
    result = _run([_require("xdotool"), "getmouselocation", "--shell"], check=True)
    values = {}
    for line in (result.stdout or "").splitlines():
        key, _, value = line.partition("=")
        if key:
            values[key.strip()] = value.strip()
    return {
        "x": _int(values.get("X")),
        "y": _int(values.get("Y")),
        "screen": values.get("SCREEN"),
        "window": values.get("WINDOW"),
    }


# ---------------------------------------------------------------------------
# Keyboard / clipboard
# ---------------------------------------------------------------------------
_KEY_ALIASES = {
    "cmd": "super",
    "command": "super",
    "win": "super",
    "meta": "super",
    "control": "ctrl",
    "option": "alt",
    "escape": "Escape",
    "esc": "Escape",
    "return": "Return",
    "enter": "Return",
    "tab": "Tab",
    "space": "space",
    "backspace": "BackSpace",
    "delete": "Delete",
    "del": "Delete",
    "insert": "Insert",
    "home": "Home",
    "end": "End",
    "pageup": "Prior",
    "page_up": "Prior",
    "pagedown": "Next",
    "page_down": "Next",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
}


def normalize_key(combo: str) -> str:
    """Normalize a key combo (``cmd+shift+t`` -> ``super+shift+t``)."""
    parts = [part.strip() for part in str(combo or "").replace(" ", "").split("+") if part.strip()]
    if not parts:
        raise ValueError("key combo is empty")
    return "+".join(_KEY_ALIASES.get(part.lower(), part) for part in parts)


def key(combo: str) -> Dict[str, Any]:
    """Press a key combination (ctrl+c, alt+F4, super, Return...)."""
    normalized = normalize_key(combo)
    if _has_xdotool():
        _run([_require("xdotool"), "key", "--clearmodifiers", normalized], check=True)
    else:
        _x11_press_combo(normalized)
    return {"keys": normalized}


def type_text(text: str, interval_ms: int = 30) -> Dict[str, Any]:
    """Type text into the focused window (newlines press Return)."""
    text = str(text or "")
    if not text:
        return {"typed": 0}
    if not _has_xdotool():
        _x11_type_text(text)
        return {"typed": len(text), "lines": text.count("\n") + 1}
    xdotool = _require("xdotool")
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line:
            _run([
                xdotool, "type", "--clearmodifiers", "--delay",
                str(max(1, _int(interval_ms, 30))), "--", line,
            ], check=True)
        if index < len(lines) - 1:
            _run([xdotool, "key", "--clearmodifiers", "Return"], check=True)
    return {"typed": len(text), "lines": len(lines)}


def clipboard_get() -> Dict[str, Any]:
    """Read the X11 clipboard."""
    result = _run([_require("xclip"), "-selection", "clipboard", "-o"])
    return {"text": result.stdout}


def clipboard_set(text: str) -> Dict[str, Any]:
    """Write the X11 clipboard."""
    result = _run(
        [_require("xclip"), "-selection", "clipboard"],
        input_text=str(text or ""),
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "xclip failed").strip())
    return {"chars": len(str(text or ""))}


# ---------------------------------------------------------------------------
# Windows / applications
# ---------------------------------------------------------------------------
def _window_info(window_id: str) -> Optional[Dict[str, Any]]:
    """Return name + geometry of one X11 window (None when it vanished)."""
    xdotool = _require("xdotool")
    try:
        name = _run([xdotool, "getwindowname", window_id]).stdout.strip()
        geometry = _run([xdotool, "getwindowgeometry", "--shell", window_id]).stdout
    except Exception:
        return None
    values: Dict[str, str] = {}
    for line in geometry.splitlines():
        key, _, value = line.partition("=")
        if key:
            values[key.strip()] = value.strip()
    if not values.get("WIDTH"):
        return None
    return {
        "id": window_id,
        "title": name,
        "x": _int(values.get("X")),
        "y": _int(values.get("Y")),
        "width": _int(values.get("WIDTH")),
        "height": _int(values.get("HEIGHT")),
    }


def list_windows(include_hidden: bool = False) -> Dict[str, Any]:
    """List top-level windows with their geometry."""
    if not _has_xdotool():
        return _x11_window_list()
    xdotool = _require("xdotool")
    args = [xdotool, "search", "--name", ".*"]
    if not include_hidden:
        args.insert(2, "--onlyvisible")
    result = _run(args)
    windows = []
    for window_id in (result.stdout or "").split():
        info = _window_info(window_id)
        if not info:
            continue
        if info["width"] < 40 or info["height"] < 40:
            continue
        windows.append(info)
    try:
        active_id = _run([xdotool, "getactivewindow"]).stdout.strip()
    except Exception:
        active_id = ""
    for window in windows:
        window["active"] = window["id"] == active_id
    return {"windows": windows[:60], "active": active_id or None}


def active_window() -> Dict[str, Any]:
    """Return the focused window."""
    if not _has_xdotool():
        listed = _x11_window_list()
        active = next((item for item in listed["windows"] if item.get("active")), None)
        return {"window": active}
    xdotool = _require("xdotool")
    result = _run([xdotool, "getactivewindow"])
    window_id = (result.stdout or "").strip()
    if not window_id:
        return {"window": None}
    return {"window": _window_info(window_id)}


def focus_window(window_id: str = None, title: str = None) -> Dict[str, Any]:
    """Activate a window by id or by (partial) title."""
    if not _has_xdotool():
        target = str(window_id or "").strip()
        if not target and title:
            listed = _x11_window_list()
            match = next((item for item in listed["windows"] if str(title).lower() in item["title"].lower()), None)
            if not match:
                raise RuntimeError(f"No visible window matching '{title}'")
            target = match["id"]
        if not target:
            raise ValueError("window_id or title is required")
        _run(["wmctrl", "-i", "-a", target], check=True)
        return {"window": {"id": target, "title": title or ""}}
    xdotool = _require("xdotool")
    target = str(window_id or "").strip()
    if not target:
        if not title:
            raise ValueError("window_id or title is required")
        found = _run([xdotool, "search", "--onlyvisible", "--name", str(title)]).stdout.split()
        if not found:
            raise RuntimeError(f"No visible window matching '{title}'")
        target = found[-1]
    _run([xdotool, "windowactivate", "--sync", target], check=True)
    _run([xdotool, "windowraise", target])
    return {"window": _window_info(target) or {"id": target}}


def close_window(window_id: str = None, title: str = None) -> Dict[str, Any]:
    """Close a window politely (WM_DELETE_WINDOW)."""
    if not _has_xdotool():
        target = str(window_id or "").strip()
        if not target and title:
            listed = _x11_window_list()
            match = next((item for item in listed["windows"] if str(title).lower() in item["title"].lower()), None)
            if not match:
                raise RuntimeError(f"No visible window matching '{title}'")
            target = match["id"]
        if not target:
            raise ValueError("window_id or title is required")
        _run(["wmctrl", "-i", "-c", target], check=True)
        return {"window_id": target}
    xdotool = _require("xdotool")
    target = str(window_id or "").strip()
    if not target:
        if not title:
            raise ValueError("window_id or title is required")
        found = _run([xdotool, "search", "--onlyvisible", "--name", str(title)]).stdout.split()
        if not found:
            raise RuntimeError(f"No visible window matching '{title}'")
        target = found[-1]
    _run([xdotool, "windowclose", target], check=True)
    return {"window_id": target}


def _desktop_entries() -> List[Dict[str, Any]]:
    """Parse .desktop files into launchable applications."""
    entries = []
    for root in ("/usr/share/applications", "/usr/local/share/applications"):
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not name.endswith(".desktop"):
                continue
            path = os.path.join(root, name)
            data: Dict[str, str] = {}
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, _, value = line.partition("=")
                        data.setdefault(key.strip(), value.strip())
            except OSError:
                continue
            if data.get("NoDisplay", "").lower() == "true" or not data.get("Exec"):
                continue
            entries.append({
                "id": name[:-8],
                "name": data.get("Name") or name[:-8],
                "exec": data.get("Exec"),
                "categories": data.get("Categories", ""),
            })
    return entries[:200]


def list_apps(query: str = "") -> Dict[str, Any]:
    """List installed .desktop applications (optional substring filter)."""
    query = str(query or "").strip().lower()
    apps = _desktop_entries()
    if query:
        apps = [
            app for app in apps
            if query in app["name"].lower() or query in app["id"].lower()
            or query in app["exec"].lower()
        ]
    return {"apps": apps}


def open_app(app: str = None, command: str = None, args: str = "") -> Dict[str, Any]:
    """Launch an application by .desktop id/name or by shell command."""
    value = str(app or command or "").strip()
    if not value:
        raise ValueError("app or command is required")
    if command:
        shell_command = f"{command} {args}".strip()
        process = subprocess.Popen(
            ["/bin/bash", "-lc", shell_command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=_env(),
        )
        return {"pid": process.pid, "command": shell_command}

    matches = [
        entry for entry in _desktop_entries()
        if value.lower() in (entry["id"].lower(), entry["name"].lower())
        or value.lower() in entry["name"].lower()
    ]
    if not matches:
        raise RuntimeError(f"No installed application matches '{value}'")
    entry = matches[0]
    if shutil.which("gtk-launch"):
        process = subprocess.Popen(
            ["gtk-launch", entry["id"]],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=_env(),
        )
        return {"pid": process.pid, "app": entry["id"], "name": entry["name"]}
    # Fallback: strip %U/%f placeholders from the Exec line and launch it.
    exec_line = " ".join(
        token for token in shlex.split(entry["exec"]) if not token.startswith("%")
    )
    process = subprocess.Popen(
        ["/bin/bash", "-lc", exec_line],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        env=_env(),
    )
    return {"pid": process.pid, "app": entry["id"], "name": entry["name"]}


def wait(seconds: float = 1) -> Dict[str, Any]:
    """Pause for *seconds* (bounded) inside the desktop container."""
    seconds = max(0.0, min(120.0, float(seconds or 1)))
    time.sleep(seconds)
    return {"waited": seconds}


def run_command(command: str, cwd: str = None, timeout: float = 60) -> Dict[str, Any]:
    """Run a shell command inside the desktop container."""
    command = str(command or "").strip()
    if not command:
        raise ValueError("command is required")
    result = _run(
        ["/bin/bash", "-lc", command],
        timeout=min(300, max(1, float(timeout or 60))),
    )
    stdout = (result.stdout or "")[:MAX_COMMAND_OUTPUT]
    stderr = (result.stderr or "")[:MAX_COMMAND_OUTPUT]
    return {
        "exit_code": result.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "truncated": len(result.stdout or "") > MAX_COMMAND_OUTPUT,
    }


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
def dispatch(command: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one JSON command and return its result."""
    action = str(command.get("action") or "").strip().lower()
    params = dict(command or {})
    params.pop("action", None)
    # "double_click"/"right_click" are sugar over click.
    if action == "double_click":
        params.setdefault("clicks", 2)
        action = "click"
    elif action == "right_click":
        params.setdefault("button", "right")
        action = "click"
    elif action == "press":
        action = "key"
    elif action == "type_text":
        action = "type"

    handlers = {
        "ping": lambda: {"message": "pong", "display": DISPLAY},
        "screen_size": screen_size,
        "screenshot": screenshot,
        "move": move,
        "click": click,
        "drag": drag,
        "scroll": scroll,
        "mouse_position": mouse_position,
        "type": type_text,
        "key": key,
        "hotkey": key,
        "clipboard_get": clipboard_get,
        "clipboard_set": clipboard_set,
        "windows": list_windows,
        "list_windows": list_windows,
        "active_window": active_window,
        "focus_window": focus_window,
        "close_window": close_window,
        "list_apps": list_apps,
        "open_app": open_app,
        "run_command": run_command,
        "wait": wait,
    }
    handler = handlers.get(action)
    if handler is None:
        raise ValueError(f"Unknown action '{action}'")
    # Filter to accepted keyword arguments so the model can send extra fields.
    import inspect

    signature = inspect.signature(handler)
    accepted = {
        key: value for key, value in params.items()
        if key in signature.parameters
    }
    return handler(**accepted)


def main() -> int:
    """Read one command from stdin, print one JSON response."""
    try:
        raw = sys.stdin.read()
        command = json.loads(raw or "{}")
        if not isinstance(command, dict):
            raise ValueError("command must be a JSON object")
        result = dispatch(command)
        response = {"ok": True, **result}
    except Exception as ex:
        response = {"ok": False, "error": str(ex)}
    sys.stdout.write(json.dumps(response, ensure_ascii=False))
    sys.stdout.flush()
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
