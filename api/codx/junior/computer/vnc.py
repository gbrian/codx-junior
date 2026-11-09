"""
Minimal pure-Python RFB (VNC) client used to drive Windows/macOS/remote desktops.

Why a local client instead of a dependency?
-------------------------------------------
The API already needs to *view* and *drive* VNC desktops:
Windows and macOS run inside QEMU (dockurr images) and expose a standard RFB
server; a remote Mac may expose Screen Sharing.  ``vncdotool`` would add a
runtime dependency and still needs a framebuffer-to-PNG step.  This module
implements the small, well specified subset we need:

* RFB 3.3/3.7/3.8 handshake, ``None`` and classic VNC-password security;
* a requested 32-bpp little-endian true-colour pixel format;
* Raw, DesktopSize and ExtendedDesktopSize encodings (no Tight/ZRLE decoder
  needed), so a resize initiated by the server or by the viewer is applied;
* ``SetDesktopSize`` (message 251) to resize the desktop at runtime, which is
  what lets the built-in viewer fit the screen to its panel;
* pointer and keyboard events with X11 keysyms;
* screenshot capture through Pillow.

The client is synchronous on purpose: it runs inside ``asyncio.to_thread`` and
is serialized by the session runtime lock, exactly like the X11 backend.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import io
import socket
import struct
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

RFB_ENCODING_RAW = 0
RFB_ENCODING_DESKTOP_SIZE = -223
RFB_ENCODING_LAST_RECT = -224
RFB_ENCODING_EXTENDED_DESKTOP_SIZE = -308

#: Client message that asks the server to change the framebuffer size.
RFB_SET_DESKTOP_SIZE = 251

# X11 keysyms
KEYSYMS = {
    "backspace": 0xFF08,
    "tab": 0xFF09,
    "return": 0xFF0D,
    "enter": 0xFF0D,
    "escape": 0xFF1B,
    "esc": 0xFF1B,
    "insert": 0xFF63,
    "delete": 0xFFFF,
    "home": 0xFF50,
    "end": 0xFF57,
    "pageup": 0xFF55,
    "page_up": 0xFF55,
    "prior": 0xFF55,
    "pagedown": 0xFF56,
    "page_down": 0xFF56,
    "next": 0xFF56,
    "left": 0xFF51,
    "up": 0xFF52,
    "right": 0xFF53,
    "down": 0xFF54,
    "space": 0x20,
    "ctrl": 0xFFE3,
    "control": 0xFFE3,
    "shift": 0xFFE1,
    "alt": 0xFFE9,
    "super": 0xFFEB,
    "meta": 0xFFEB,
    "cmd": 0xFFEB,
    "command": 0xFFEB,
    "win": 0xFFEB,
    "caps_lock": 0xFFE5,
    "num_lock": 0xFF7F,
    "print": 0xFF61,
    "menu": 0xFF67,
    "pause": 0xFF13,
}
for _index in range(1, 13):
    KEYSYMS[f"f{_index}"] = 0xFFBE + (_index - 1)

# Characters produced with Shift on a US keyboard.
SHIFTED_CHARS = {
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6",
    "&": "7", "*": "8", "(": "9", ")": "0", "_": "-", "+": "=",
    "{": "[", "}": "]", "|": "\\", ":": ";", '"': "'", "<": ",",
    ">": ".", "?": "/", "~": "`",
}


class RFBError(RuntimeError):
    """Raised when the VNC handshake or protocol fails."""


def even_dimension(value: Any) -> int:
    """
    Round a pixel dimension down to an even number of at least 2 pixels.

    Args:
        value: Any numeric value (JSON, form field or int).

    Returns:
        int: Even dimension; invalid input becomes 2.
    """
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return 2
    number = max(2, number)
    return number - (number % 2)


def pack_set_desktop_size(
    width: Any,
    height: Any,
    screens: Optional[Iterable[Dict[str, Any]]] = None,
) -> bytes:
    """
    Encode a ``SetDesktopSize`` client message (RFB message type 251).

    Args:
        width: Requested framebuffer width (rounded to even).
        height: Requested framebuffer height (rounded to even).
        screens: Optional screen layout (``id``, ``x``, ``y``, ``width``,
            ``height``, ``flags``).  A single full-size screen is sent when
            omitted, which is what single-monitor desktops expect.

    Returns:
        bytes: The message ready to be written to the socket.
    """
    width = even_dimension(width)
    height = even_dimension(height)
    layout = [dict(screen) for screen in (screens or [])]
    if not layout:
        layout = [{"id": 0, "x": 0, "y": 0, "width": width, "height": height, "flags": 0}]
    payload = struct.pack(
        ">BBHHBB",
        RFB_SET_DESKTOP_SIZE,
        0,
        width,
        height,
        len(layout),
        0,
    )
    for screen in layout:
        payload += struct.pack(
            ">IHHHHI",
            int(screen.get("id") or 0),
            int(screen.get("x") or 0),
            int(screen.get("y") or 0),
            even_dimension(screen.get("width") or width),
            even_dimension(screen.get("height") or height),
            int(screen.get("flags") or 0),
        )
    return payload


# ---------------------------------------------------------------------------
# DES (VNC authentication is single DES with a bit-reversed password key)
# ---------------------------------------------------------------------------
_PC1 = [
    57, 49, 41, 33, 25, 17, 9, 1, 58, 50, 42, 34, 26, 18,
    10, 2, 59, 51, 43, 35, 27, 19, 11, 3, 60, 52, 44, 36,
    63, 55, 47, 39, 31, 23, 15, 7, 62, 54, 46, 38, 30, 22,
    14, 6, 61, 53, 45, 37, 29, 21, 13, 5, 28, 20, 12, 4,
]
_PC2 = [
    14, 17, 11, 24, 1, 5, 3, 28, 15, 6, 21, 10,
    23, 19, 12, 4, 26, 8, 16, 7, 27, 20, 13, 2,
    41, 52, 31, 37, 47, 55, 30, 40, 51, 45, 33, 48,
    44, 49, 39, 56, 34, 53, 46, 42, 50, 36, 29, 32,
]
_IP = [
    58, 50, 42, 34, 26, 18, 10, 2, 60, 52, 44, 36, 28, 20, 12, 4,
    62, 54, 46, 38, 30, 22, 14, 6, 64, 56, 48, 40, 32, 24, 16, 8,
    57, 49, 41, 33, 25, 17, 9, 1, 59, 51, 43, 35, 27, 19, 11, 3,
    61, 53, 45, 37, 29, 21, 13, 5, 63, 55, 47, 39, 31, 23, 15, 7,
]
_FP = [
    40, 8, 48, 16, 56, 24, 64, 32, 39, 7, 47, 15, 55, 23, 63, 31,
    38, 6, 46, 14, 54, 22, 62, 30, 37, 5, 45, 13, 53, 21, 61, 29,
    36, 4, 44, 12, 52, 20, 60, 28, 35, 3, 43, 11, 51, 19, 59, 27,
    34, 2, 42, 10, 50, 18, 58, 26, 33, 1, 41, 9, 49, 17, 57, 25,
]
_E = [
    32, 1, 2, 3, 4, 5, 4, 5, 6, 7, 8, 9,
    8, 9, 10, 11, 12, 13, 12, 13, 14, 15, 16, 17,
    16, 17, 18, 19, 20, 21, 20, 21, 22, 23, 24, 25,
    24, 25, 26, 27, 28, 29, 28, 29, 30, 31, 32, 1,
]
_P = [
    16, 7, 20, 21, 29, 12, 28, 17, 1, 15, 23, 26, 5, 18, 31, 10,
    2, 8, 24, 14, 32, 27, 3, 9, 19, 13, 30, 6, 22, 11, 4, 25,
]
_SHIFTS = [1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1]
_SBOX = [
    # S1
    [14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7,
     0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8,
     4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0,
     15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13],
    # S2
    [15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10,
     3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5,
     0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15,
     13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9],
    # S3
    [10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8,
     13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1,
     13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7,
     1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12],
    # S4
    [7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15,
     13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9,
     10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4,
     3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14],
    # S5
    [2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9,
     14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6,
     4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14,
     11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3],
    # S6
    [12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11,
     10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8,
     9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6,
     4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13],
    # S7
    [4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1,
     13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6,
     1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2,
     6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12],
    # S8
    [13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7,
     1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2,
     7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8,
     2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11],
]


def _bits(value: int, length: int) -> List[int]:
    """Return *length* bits, most significant first."""
    return [(value >> (length - 1 - index)) & 1 for index in range(length)]


def _permute(value: int, table: List[int], input_bits: int) -> int:
    bits = _bits(value, input_bits)
    result = 0
    for position in table:
        result = (result << 1) | bits[position - 1]
    return result


def _des_subkeys(key: int) -> List[int]:
    """Derive the 16 DES subkeys from a 64-bit key."""
    permuted = _permute(key, _PC1, 64)
    c = permuted >> 28
    d = permuted & 0x0FFFFFFF
    subkeys = []
    for shift in _SHIFTS:
        c = ((c << shift) | (c >> (28 - shift))) & 0x0FFFFFFF
        d = ((d << shift) | (d >> (28 - shift))) & 0x0FFFFFFF
        subkeys.append(_permute((c << 28) | d, _PC2, 56))
    return subkeys


def _des_block(block: int, key: int) -> int:
    """Encrypt one 64-bit block with DES."""
    subkeys = _des_subkeys(key)
    permuted = _permute(block, _IP, 64)
    left, right = permuted >> 32, permuted & 0xFFFFFFFF
    for subkey in subkeys:
        expanded = _permute(right, _E, 32) ^ subkey
        substituted = 0
        for box in range(8):
            chunk = (expanded >> (42 - 6 * box)) & 0x3F
            row = ((chunk & 0x20) >> 4) | (chunk & 1)
            column = (chunk >> 1) & 0x0F
            substituted = (substituted << 4) | _SBOX[box][row * 16 + column]
        left, right = right, left ^ _permute(substituted, _P, 32)
    return _permute((right << 32) | left, _FP, 64)


def _reverse_bits(byte: int) -> int:
    """Reverse the 8 bits of one byte (VNC password key convention)."""
    result = 0
    for index in range(8):
        result = (result << 1) | ((byte >> index) & 1)
    return result


def vnc_auth_response(password: str, challenge: bytes) -> bytes:
    """Build the 16-byte response to a VNC authentication challenge."""
    raw = str(password or "").encode("utf-8")[:8].ljust(8, b"\x00")
    key_bytes = bytes(_reverse_bits(byte) for byte in raw)
    key = int.from_bytes(key_bytes, "big")
    return b"".join(
        _des_block(int.from_bytes(challenge[offset:offset + 8], "big"), key).to_bytes(8, "big")
        for offset in (0, 8)
    )


# ---------------------------------------------------------------------------
# Protocol client
# ---------------------------------------------------------------------------
@dataclass
class RFBPixelFormat:
    """The subset of the RFB pixel format we request and decode."""

    bits_per_pixel: int = 32
    depth: int = 24
    big_endian: bool = False
    true_colour: bool = True
    red_max: int = 255
    green_max: int = 255
    blue_max: int = 255
    red_shift: int = 16
    green_shift: int = 8
    blue_shift: int = 0

    def pack(self) -> bytes:
        """Encode the 16-byte RFB pixel format structure."""
        return struct.pack(
            ">BBBBHHHBBBxxx",
            self.bits_per_pixel,
            self.depth,
            int(self.big_endian),
            int(self.true_colour),
            self.red_max,
            self.green_max,
            self.blue_max,
            self.red_shift,
            self.green_shift,
            self.blue_shift,
        )

    @staticmethod
    def unpack(data: bytes) -> "RFBPixelFormat":
        """Decode a 16-byte RFB pixel format structure."""
        bpp, depth, big, true_colour, rmax, gmax, bmax, rshift, gshift, bshift = struct.unpack(
            ">BBBBHHHBBBxxx", data
        )
        return RFBPixelFormat(
            bpp, depth, bool(big), bool(true_colour),
            rmax, gmax, bmax, rshift, gshift, bshift,
        )


class RFBClient:
    """Small synchronous RFB client with a persistent framebuffer."""

    def __init__(
        self,
        host: str,
        port: int = 5900,
        password: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.host = host
        self.port = int(port)
        self.password = password
        self.timeout = timeout
        self._socket: Optional[socket.socket] = None
        self._lock = threading.RLock()
        self.width = 0
        self.height = 0
        self.pixel_format = RFBPixelFormat()
        self._framebuffer = bytearray()
        self._name = ""
        self._full_update = True
        #: Screen layout reported by ExtendedDesktopSize (empty when unknown).
        self.screens: List[Dict[str, int]] = []
        #: True once the server has sent an ExtendedDesktopSize rectangle, which
        #: means it understands SetDesktopSize (runtime resize).
        self.supports_extended_desktop_size = False
        #: Screen id used when requesting a new size (0 = single screen/unknown).
        self.screen_id = 0

    # -- connection --------------------------------------------------------
    @property
    def connected(self) -> bool:
        """True while the TCP socket is open."""
        return self._socket is not None

    def connect(self) -> None:
        """Open the socket and complete the RFB handshake."""
        with self._lock:
            self.close()
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            sock.settimeout(self.timeout)
            self._socket = sock
            try:
                self._handshake(sock)
            except Exception:
                self.close()
                raise

    def close(self) -> None:
        """Close the connection (safe to call repeatedly)."""
        with self._lock:
            if self._socket is not None:
                try:
                    self._socket.close()
                except OSError:
                    pass
            self._socket = None
            self._framebuffer = bytearray()
            self._full_update = True

    def _recv_exact(self, size: int) -> bytes:
        """Read exactly *size* bytes or raise."""
        if self._socket is None:
            raise RFBError("Not connected")
        chunks = []
        remaining = size
        while remaining > 0:
            data = self._socket.recv(remaining)
            if not data:
                raise RFBError("VNC server closed the connection")
            chunks.append(data)
            remaining -= len(data)
        return b"".join(chunks)

    def _handshake(self, sock: socket.socket) -> None:
        """Perform version, security and initialization handshake."""
        version = self._recv_exact(12).decode("ascii", errors="replace")
        if not version.startswith("RFB "):
            raise RFBError(f"Not a VNC server (banner: {version!r})")
        try:
            major, minor = version[4:].strip().split(".")
            server_version = float(f"{int(major)}.{int(minor)}")
        except Exception:
            server_version = 3.8
        client_version = "RFB 003.003\n" if server_version < 3.7 else "RFB 003.008\n"
        sock.sendall(client_version.encode("ascii"))

        security_type = None
        if client_version.endswith("003.003\n"):
            security_type = struct.unpack(">I", self._recv_exact(4))[0]
            if security_type == 0:
                reason = self._read_reason()
                raise RFBError(f"VNC server refused connection: {reason}")
        else:
            count = self._recv_exact(1)[0]
            if count == 0:
                reason = self._read_reason()
                raise RFBError(f"VNC server refused connection: {reason}")
            offered = list(self._recv_exact(count))
            security_type = self._select_security(offered)
            sock.sendall(bytes([security_type]))

        if security_type == 2:
            if not self.password:
                raise RFBError(
                    "This VNC server requires a password; set vnc_password on the session"
                )
            challenge = self._recv_exact(16)
            sock.sendall(vnc_auth_response(self.password, challenge))
            result = struct.unpack(">I", self._recv_exact(4))[0]
            if result != 0:
                raise RFBError(f"VNC authentication failed: {self._read_reason()}")
        elif security_type == 1 and server_version >= 3.7:
            # RFB 3.8 sends SecurityResult for "None" as well.
            result = struct.unpack(">I", self._recv_exact(4))[0]
            if result != 0:
                raise RFBError(f"VNC server rejected the connection: {self._read_reason()}")
        elif security_type not in (1,):
            raise RFBError(
                f"Unsupported VNC security type {security_type}; use 'None' or "
                "legacy VNC password authentication"
            )

        # ClientInit: shared desktop.
        sock.sendall(b"\x01")
        header = self._recv_exact(24)
        self.width, self.height = struct.unpack(">HH", header[:4])
        self.pixel_format = RFBPixelFormat.unpack(header[4:20])
        name_length = struct.unpack(">I", header[20:24])[0]
        self._name = self._recv_exact(name_length).decode("utf-8", errors="replace") if name_length else ""
        if not self.width or not self.height:
            raise RFBError("VNC server reported an empty framebuffer")

        # Ask for a format we can decode without generic per-pixel math.
        self.pixel_format = RFBPixelFormat()
        sock.sendall(b"\x00\x00\x00\x00" + self.pixel_format.pack())
        # Raw + DesktopSize + ExtendedDesktopSize: the last one makes the server
        # report resizes (whoever triggered them) and accept SetDesktopSize.
        sock.sendall(
            struct.pack(">BxH", 3, 3)
            + struct.pack(">i", RFB_ENCODING_RAW)
            + struct.pack(">i", RFB_ENCODING_DESKTOP_SIZE)
            + struct.pack(">i", RFB_ENCODING_EXTENDED_DESKTOP_SIZE)
        )
        self._framebuffer = bytearray(self.width * self.height * 4)
        self._full_update = True

    def _select_security(self, offered: Iterable[int]) -> int:
        """Pick a supported security type from the server's list."""
        offered = list(offered)
        if 1 in offered:
            return 1
        if 2 in offered:
            return 2
        raise RFBError(
            "No supported VNC security type (offered: "
            + ", ".join(str(item) for item in offered)
            + "). Enable 'None' or 'VNC password' authentication."
        )

    def _read_reason(self) -> str:
        """Read the length-prefixed failure reason."""
        try:
            length = struct.unpack(">I", self._recv_exact(4))[0]
            return self._recv_exact(length).decode("utf-8", errors="replace")
        except Exception:
            return "unknown reason"

    # -- framebuffer -------------------------------------------------------
    def request_update(self, incremental: Optional[bool] = None) -> None:
        """Ask the server for a framebuffer update (full frame by default)."""
        if not self.connected:
            self.connect()
        incremental = False if incremental is None else bool(incremental)
        self._send(struct.pack(">BBHHHH", 3, 0 if not incremental else 1, 0, 0, self.width, self.height))
        self._read_update()
        if not incremental:
            self._full_update = False

    def _read_update(self) -> None:
        """Read one FramebufferUpdate message and apply its rectangles."""
        message_type = self._recv_exact(1)[0]
        if message_type != 0:
            # Bell / ServerCutText / SetColourMapEntries are not used; skip the
            # well known messages so a chatty server does not desync us.
            if message_type == 3:
                self._recv_exact(3)
                length = struct.unpack(">I", self._recv_exact(4))[0]
                self._recv_exact(length)
                return self._read_update()
            if message_type == 1:
                # SetColourMapEntries: padding, first-colour, count, count*6.
                self._recv_exact(3)
                count = struct.unpack(">H", self._recv_exact(2))[0]
                self._recv_exact(count * 6)
                return self._read_update()
            if message_type == 2:
                # Bell: no payload.
                return self._read_update()
            raise RFBError(f"Unexpected VNC message type {message_type}")

        # The first byte was type 0 (FramebufferUpdate): padding + count.
        self._recv_exact(1)  # padding
        rect_count = struct.unpack(">H", self._recv_exact(2))[0]
        for _ in range(rect_count):
            x, y, width, height, encoding = struct.unpack(">HHHHi", self._recv_exact(12))
            if encoding == RFB_ENCODING_LAST_RECT:
                break
            if encoding == RFB_ENCODING_DESKTOP_SIZE:
                self._resize(width, height)
                continue
            if encoding == RFB_ENCODING_EXTENDED_DESKTOP_SIZE:
                screens = self._read_extended_desktop_size()
                self.supports_extended_desktop_size = True
                self._resize(width, height, screens=screens)
                continue
            if encoding != RFB_ENCODING_RAW:
                raise RFBError(
                    f"VNC server sent unsupported encoding {encoding}; "
                    "the desktop should accept Raw encoding"
                )
            if width <= 0 or height <= 0:
                continue
            row_bytes = width * 4
            pixels = self._recv_exact(row_bytes * height)
            if not self._framebuffer or len(self._framebuffer) != self.width * self.height * 4:
                self._resize(self.width, self.height)
            for row in range(height):
                target = ((y + row) * self.width + x) * 4
                self._framebuffer[target:target + row_bytes] = pixels[row * row_bytes:(row + 1) * row_bytes]

    def _read_extended_desktop_size(self) -> List[Dict[str, int]]:
        """Read the screen layout of an ExtendedDesktopSize pseudo-rectangle."""
        count = self._recv_exact(1)[0]
        self._recv_exact(1)  # padding
        self._recv_exact(4)  # reason: server, this client or another client
        screens: List[Dict[str, int]] = []
        for _ in range(max(0, count)):
            screen_id, x, y, width, height, flags = struct.unpack(">IHHHHI", self._recv_exact(16))
            screens.append({
                "id": screen_id,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "flags": flags,
            })
        return screens

    def _resize(
        self,
        width: int,
        height: int,
        screens: Optional[List[Dict[str, int]]] = None,
    ) -> None:
        """Resize the local framebuffer after a desktop-size pseudo-rectangle."""
        if width <= 0 or height <= 0:
            return
        self.width, self.height = width, height
        self._framebuffer = bytearray(width * height * 4)
        self._full_update = True
        if screens is not None:
            self.screens = screens
            if screens:
                self.screen_id = int(screens[0].get("id") or 0)

    def set_desktop_size(
        self,
        width: Any,
        height: Any,
        timeout: float = 8.0,
    ) -> Dict[str, Any]:
        """
        Ask the server to change the framebuffer size (RFB ``SetDesktopSize``).

        KasmVNC, TigerVNC, x11vnc with XRandR and the dockurr VMs accept the
        request and answer with an ExtendedDesktopSize rectangle carrying the
        layout they applied.  Old servers simply never answer, which is why the
        wait is bounded.

        Args:
            width: Requested width in pixels (rounded to even).
            height: Requested height in pixels (rounded to even).
            timeout: Seconds to wait for the server confirmation.

        Returns:
            Dict[str, Any]: ``width``/``height`` actually in use, ``supported``,
            ``applied`` and the ``screens`` layout.

        Raises:
            RFBError: When the server does not confirm the change (it probably
                only supports the size it was started with).
        """
        with self._lock:
            if not self.connected:
                self.connect()
            target_width = even_dimension(width)
            target_height = even_dimension(height)
            wanted = (target_width, target_height)
            layout = [{
                "id": int(self.screen_id or 0),
                "x": 0,
                "y": 0,
                "width": target_width,
                "height": target_height,
                "flags": 0,
            }]
            previous_timeout = None
            if self._socket is not None:
                previous_timeout = self._socket.gettimeout()
                self._socket.settimeout(max(1.0, float(timeout or 8.0)))
            try:
                self._send(pack_set_desktop_size(target_width, target_height, layout))
                self._read_update()
            except (OSError, socket.timeout) as ex:
                raise RFBError(
                    "The VNC server did not confirm the new desktop size; it probably "
                    "does not support ExtendedDesktopSize. Keep the live view scaled "
                    "or resize the desktop from inside the guest instead."
                ) from ex
            finally:
                if self._socket is not None and previous_timeout is not None:
                    try:
                        self._socket.settimeout(previous_timeout)
                    except OSError:  # pragma: no cover - socket already gone
                        pass
            applied = (self.width, self.height) == wanted
            return {
                "width": self.width,
                "height": self.height,
                "requested_width": target_width,
                "requested_height": target_height,
                "supported": bool(self.supports_extended_desktop_size or applied),
                "applied": applied,
                "screens": list(self.screens),
            }

    def _send(self, payload: bytes) -> None:
        """Send bytes to the server."""
        if self._socket is None:
            raise RFBError("Not connected")
        self._socket.sendall(payload)

    def screenshot(self) -> Tuple[bytes, Dict[str, Any]]:
        """Capture the current framebuffer as PNG bytes."""
        with self._lock:
            if not self.connected:
                self.connect()
            self.request_update()
            try:
                from PIL import Image
            except Exception as ex:  # pragma: no cover - image dependent
                raise RFBError("Pillow is required to decode VNC screenshots") from ex
            image = Image.frombytes(
                "RGB",
                (self.width, self.height),
                bytes(self._framebuffer),
                "raw",
                "BGRX",
            )
            buffer = io.BytesIO()
            image.save(buffer, format="PNG", optimize=True)
            return buffer.getvalue(), {"width": self.width, "height": self.height}

    # -- input -------------------------------------------------------------
    def pointer(self, x: int, y: int, mask: int) -> None:
        """Send a PointerEvent."""
        self._send(struct.pack(">BBHH", 5, mask & 0xFF, max(0, int(x)), max(0, int(y))))

    def click(self, x: int = 0, y: int = 0, button: str = "left", clicks: int = 1) -> None:
        """Click at absolute coordinates (1=left, 2=middle, 3=right)."""
        mask = {"left": 1, "middle": 2, "right": 4}.get(str(button).lower(), 1)
        clicks = max(1, min(3, int(clicks)))
        for _ in range(clicks):
            self.pointer(x, y, mask)
            time.sleep(0.03)
            self.pointer(x, y, 0)
            time.sleep(0.08)

    def move(self, x: int, y: int) -> None:
        """Move the pointer."""
        self.pointer(x, y, 0)

    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int, duration_ms: int = 500) -> None:
        """Press, move and release the pointer."""
        steps = max(2, min(40, int(duration_ms or 500) // 25))
        self.pointer(from_x, from_y, 1)
        for step in range(1, steps + 1):
            x = from_x + (to_x - from_x) * step // steps
            y = from_y + (to_y - from_y) * step // steps
            self.pointer(x, y, 1)
            time.sleep(max(0.005, (int(duration_ms or 500) / 1000.0) / steps))
        self.pointer(to_x, to_y, 0)

    def scroll(self, x: int = 0, y: int = 0, amount: int = 3, direction: str = "down") -> None:
        """Scroll the wheel at x,y using RFB wheel buttons."""
        amount = max(1, min(50, abs(int(amount or 3))))
        direction = str(direction or "down").lower()
        mask = 8 if direction in ("up", "left") else 16
        for _ in range(amount):
            self.pointer(x, y, mask)
            time.sleep(0.02)
            self.pointer(x, y, 0)

    def key(self, keysym: int, down: bool = True) -> None:
        """Send one KeyEvent."""
        self._send(struct.pack(">BBHI", 4, 1 if down else 0, 0, keysym & 0xFFFFFFFF))

    def tap(self, keysym: int, modifiers: Iterable[int] = ()) -> None:
        """Press and release a key with modifiers."""
        modifiers = list(modifiers)
        for modifier in modifiers:
            self.key(modifier, True)
        self.key(keysym, True)
        self.key(keysym, False)
        for modifier in reversed(modifiers):
            self.key(modifier, False)
        time.sleep(0.03)

    def press(self, combo: str) -> None:
        """Press a key combination (``ctrl+shift+t``)."""
        parts = [part.strip().lower() for part in str(combo or "").split("+") if part.strip()]
        if not parts:
            raise ValueError("key combo is empty")
        modifiers = []
        target = None
        for part in parts:
            if part in ("ctrl", "control") and target is None:
                modifiers.append(KEYSYMS["ctrl"])
            elif part in ("shift",) and target is None:
                modifiers.append(KEYSYMS["shift"])
            elif part in ("alt", "option") and target is None:
                modifiers.append(KEYSYMS["alt"])
            elif part in ("super", "meta", "cmd", "command", "win") and target is None:
                modifiers.append(KEYSYMS["super"])
            else:
                target = keysym_for(part)
        if target is None:
            # The combo was only modifiers: press the last one.
            target = modifiers.pop() if modifiers else 0
            if not target:
                return
        self.tap(target, modifiers)

    def type_text(self, text: str) -> None:
        """Type text using X11 keysyms (US layout for shifted symbols)."""
        for char in str(text or ""):
            if char == "\n":
                self.tap(KEYSYMS["return"])
                continue
            if char == "\t":
                self.tap(KEYSYMS["tab"])
                continue
            keysym, shift = keysym_for_char(char)
            self.tap(keysym, [KEYSYMS["shift"]] if shift else [])
            time.sleep(0.003)


def keysym_for(name: str) -> int:
    """Return the X11 keysym for a named key or a single character."""
    key = str(name or "").strip().lower()
    if key in KEYSYMS:
        return KEYSYMS[key]
    if len(key) == 1:
        return keysym_for_char(key)[0]
    raise ValueError(f"Unknown key '{name}'")


def keysym_for_char(char: str) -> Tuple[int, bool]:
    """Return ``(keysym, needs_shift)`` for one character."""
    if char in SHIFTED_CHARS:
        return ord(SHIFTED_CHARS[char]), True
    if "A" <= char <= "Z":
        return ord(char.lower()), True
    code = ord(char)
    if 0x20 <= code <= 0x7E:
        return code, False
    # Unicode keysym (X11 convention).
    return 0x01000000 | code, False