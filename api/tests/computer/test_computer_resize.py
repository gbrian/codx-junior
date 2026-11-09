"""Desktop resize: resolution math, xrandr script, RFB SetDesktopSize, backends."""

import asyncio
import socketserver
import struct
import threading

import pytest

from codx.junior.browser.model import BrowserSession
from codx.junior.computer.backend import (
    READ_ONLY_ACTIONS,
    DockerExecBackend,
    VncBackend,
)
from codx.junior.computer.resize import (
    fit_resolution,
    parse_resolution,
    resolution_from_client,
    xrandr_resize_script,
)
from codx.junior.computer.vnc import (
    RFB_SET_DESKTOP_SIZE,
    RFBClient,
    RFBPixelFormat,
    pack_set_desktop_size,
)


# ---------------------------------------------------------------------------
# Resolution math
# ---------------------------------------------------------------------------
def test_fit_resolution_clamps_and_keeps_aspect():
    assert fit_resolution(1920, 1080) == (1920, 1080)
    assert fit_resolution(1281, 801) == (1280, 800)
    assert fit_resolution(100, 100) == (640, 640)
    assert fit_resolution(10000, 2000) == (7680, 1536)
    assert fit_resolution(4000, 100) == (7680, 480)


def test_fit_resolution_rejects_invalid_sizes():
    with pytest.raises(ValueError):
        fit_resolution(0, 0)
    with pytest.raises(ValueError):
        fit_resolution("wide", "tall")


def test_resolution_from_client_applies_the_pixel_scale():
    assert resolution_from_client(1280, 800) == (1280, 800)
    assert resolution_from_client(1280, 800, scale=2) == (2560, 1600)
    # Out of range values are clamped instead of raising.
    assert resolution_from_client(100, 100, scale=0.1) == (640, 640)


def test_parse_resolution():
    assert parse_resolution("1920x1080") == (1920, 1080)
    assert parse_resolution(" 1366 X 768 ") == (1366, 768)
    assert parse_resolution("1280:720") == (1280, 720)
    assert parse_resolution([800, 600]) == (800, 600)
    assert parse_resolution("nope") is None


def test_xrandr_script_only_interpolates_numbers():
    script = xrandr_resize_script(1601, 901)
    assert "1600x900" in script
    assert "--output" in script
    assert "--fb" in script
    assert "applied:" in script


def test_resize_is_not_a_read_only_action():
    assert "resize" not in READ_ONLY_ACTIONS


# ---------------------------------------------------------------------------
# RFB SetDesktopSize
# ---------------------------------------------------------------------------
def test_pack_set_desktop_size_layout():
    payload = pack_set_desktop_size(1600, 900)
    assert len(payload) == 24
    assert payload[0] == RFB_SET_DESKTOP_SIZE
    assert struct.unpack(">HH", payload[2:6]) == (1600, 900)
    assert payload[6] == 1  # one screen
    assert struct.unpack(">IHHHHI", payload[8:24]) == (0, 0, 0, 1600, 900, 0)


class _ResizeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _ResizeHandler(socketserver.BaseRequestHandler):
    """RFB 3.8 server that honours SetDesktopSize and confirms 10x5."""

    requested = {}

    def handle(self):
        sock = self.request
        sock.sendall(b"RFB 003.008\n")
        self._read(12)
        sock.sendall(bytes([1, 1]))  # one security type: None
        self._read(1)
        sock.sendall(struct.pack(">I", 0))  # SecurityResult OK
        self._read(1)  # ClientInit shared
        name = b"resize"
        sock.sendall(
            struct.pack(">HH", 8, 6)
            + RFBPixelFormat().pack()
            + struct.pack(">I", len(name))
            + name
        )
        self._read(20)  # SetPixelFormat
        self._read(16)  # SetEncodings: Raw + DesktopSize + ExtendedDesktopSize
        message = self._read(24)  # SetDesktopSize: header + one screen
        type(self).requested = {
            "type": message[0],
            "width": struct.unpack(">H", message[2:4])[0],
            "height": struct.unpack(">H", message[4:6])[0],
            "screens": message[6],
        }
        sock.sendall(
            struct.pack(">BBH", 0, 0, 1)
            + struct.pack(">HHHHi", 0, 0, 10, 5, -308)
            + struct.pack(">BBI", 1, 0, 1)  # one screen, reason=this client
            + struct.pack(">IHHHHI", 1, 0, 0, 10, 5, 0)
        )

    def _read(self, size):
        data = b""
        while len(data) < size:
            chunk = self.request.recv(size - len(data))
            if not chunk:
                break
            data += chunk
        return data


def test_client_confirms_set_desktop_size():
    server = _ResizeServer(("127.0.0.1", 0), _ResizeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = None
    try:
        client = RFBClient("127.0.0.1", port=server.server_address[1], timeout=5)
        client.connect()
        info = client.set_desktop_size(1600, 900)
    finally:
        if client is not None:
            client.close()
        server.shutdown()
        server.server_close()

    assert _ResizeHandler.requested == {
        "type": RFB_SET_DESKTOP_SIZE,
        "width": 1600,
        "height": 900,
        "screens": 1,
    }
    assert (info["width"], info["height"]) == (10, 5)
    assert info["applied"] is True
    assert info["supported"] is True
    assert client.supports_extended_desktop_size is True
    assert client.screens[0]["id"] == 1


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
def test_docker_backend_resizes_through_the_agent():
    session = BrowserSession(name="Linux", kind="linux", container_name="desk")
    backend = DockerExecBackend(session)
    calls = []

    def fake_exec(command):
        calls.append(command)
        if command.get("action") == "screen_size":
            return {"width": 1600, "height": 900}
        return {"exit_code": 0, "stdout": "applied:HDMI-1:1600x900", "stderr": ""}

    backend._exec = fake_exec
    result = asyncio.run(backend.execute("resize", width=1600, height=900))

    assert calls[0]["action"] == "run_command"
    assert "1600x900" in calls[0]["command"]
    assert result["applied"] is True
    assert (result["width"], result["height"]) == (1600, 900)
    assert backend.resize_support()["supported"] is True


def test_docker_backend_reports_when_xrandr_cannot_resize():
    session = BrowserSession(name="Linux", kind="linux", container_name="desk")
    backend = DockerExecBackend(session)

    def fake_exec(command):
        if command.get("action") == "screen_size":
            return {"width": 1024, "height": 768}
        return {"exit_code": 5, "stdout": "unsupported", "stderr": ""}

    backend._exec = fake_exec
    result = asyncio.run(backend.execute("resize", width=1600, height=900))

    assert result["applied"] is False
    assert (result["width"], result["height"]) == (1024, 768)
    assert "scaled" in result["message"]


class _StubClient:
    """Minimal RFB client double used by the VNC backend tests."""

    connected = True
    supports_extended_desktop_size = True

    def __init__(self, width=1024, height=768):
        self.width = width
        self.height = height
        self.calls = []

    def set_desktop_size(self, width, height, **kwargs):
        self.calls.append((width, height))
        self.width, self.height = width, height
        return {"width": width, "height": height, "supported": True, "applied": True, "screens": []}


def test_vnc_backend_uses_set_desktop_size():
    session = BrowserSession(name="VM", kind="windows", vnc_host="127.0.0.1")
    backend = VncBackend(session)
    backend._client = _StubClient()

    assert backend.resize_support() == {"supported": True, "mode": "rfb"}

    result = asyncio.run(backend.execute("resize", width=1281, height=801))

    assert backend._client.calls == [(1280, 800)]
    assert (result["width"], result["height"]) == (1280, 800)
    assert result["applied"] is True


def test_resize_requires_a_size():
    session = BrowserSession(name="VM", kind="windows", vnc_host="127.0.0.1")
    backend = VncBackend(session)
    backend._client = _StubClient()
    with pytest.raises(Exception):
        asyncio.run(backend.execute("resize"))