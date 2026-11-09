"""Tests for the pure-Python RFB client (handshake, auth, framebuffer, input)."""

import socket
import socketserver
import struct
import threading

import pytest

from codx.junior.computer.vnc import (
    KEYSYMS,
    RFBClient,
    RFBPixelFormat,
    _des_block,
    keysym_for,
    keysym_for_char,
    vnc_auth_response,
)


def test_des_known_vector():
    # Classic FIPS test vector.
    assert _des_block(0x0123456789ABCDEF, 0x133457799BBCDFF1) == 0x85E813540F0AB405


def test_vnc_auth_response_is_16_bytes_and_deterministic():
    challenge = bytes(range(16))
    first = vnc_auth_response("secret", challenge)
    second = vnc_auth_response("secret", challenge)
    assert len(first) == 16
    assert first == second
    assert first != vnc_auth_response("other", challenge)


def test_keysyms():
    assert keysym_for("Return") == KEYSYMS["return"]
    assert keysym_for_char("A") == (ord("a"), True)
    assert keysym_for_char("!") == (ord("1"), True)
    assert keysym_for_char("a") == (ord("a"), False)
    assert keysym_for_char("\u00e9")[0] == 0x01000000 | 0xE9


class _FakeRFBServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _FakeRFBHandler(socketserver.BaseRequestHandler):
    """Minimal RFB 3.8 server: None auth, 4x3 framebuffer, one Raw update."""

    def handle(self):
        sock = self.request
        sock.sendall(b"RFB 003.008\n")
        assert self._read(12).startswith(b"RFB 003.008")
        sock.sendall(bytes([1, 1]))  # one security type: None
        assert self._read(1) == b"\x01"
        sock.sendall(struct.pack(">I", 0))  # SecurityResult OK
        assert self._read(1) == b"\x01"  # ClientInit shared

        pixel_format = RFBPixelFormat().pack()
        name = b"fake"
        sock.sendall(
            struct.pack(">HH", 4, 3)
            + pixel_format
            + struct.pack(">I", len(name))
            + name
        )
        # SetPixelFormat (20 bytes) + SetEncodings (4 + 3*4)
        assert len(self._read(20)) == 20
        assert len(self._read(16)) == 16
        request = self._read(10)
        assert request[0] == 3  # FramebufferUpdateRequest

        # 4x3 pixels, BGRX order for the requested 32-bpp format.
        colors = [
            (0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 255, 255),
            (0, 0, 0), (10, 20, 30), (40, 50, 60), (70, 80, 90),
            (11, 22, 33), (44, 55, 66), (77, 88, 99), (12, 34, 56),
        ]
        pixels = b"".join(bytes((b, g, r, 0)) for r, g, b in colors)
        sock.sendall(
            struct.pack(">BBH", 0, 0, 1)
            + struct.pack(">HHHHi", 0, 0, 4, 3, 0)
            + pixels
        )

    def _read(self, size):
        data = b""
        while len(data) < size:
            chunk = self.request.recv(size - len(data))
            if not chunk:
                break
            data += chunk
        return data


@pytest.fixture
def fake_server():
    server = _FakeRFBServer(("127.0.0.1", 0), _FakeRFBHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def test_client_handshake_and_screenshot(fake_server):
    from PIL import Image
    import io

    client = RFBClient("127.0.0.1", port=fake_server, timeout=5)
    try:
        png, info = client.screenshot()
    finally:
        client.close()
    assert info == {"width": 4, "height": 3}
    image = Image.open(io.BytesIO(png)).convert("RGB")
    assert image.size == (4, 3)
    assert image.getpixel((0, 0)) == (0, 0, 255)
    assert image.getpixel((1, 0)) == (0, 255, 0)
    assert image.getpixel((1, 1)) == (10, 20, 30)


def test_client_reports_unsupported_security_type():
    class Server(_FakeRFBServer):
        pass

    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.sendall(b"RFB 003.008\n")
            self.request.recv(12)
            self.request.sendall(bytes([1, 19]))  # VeNCrypt only
            self.request.recv(1)

    server = Server(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = RFBClient("127.0.0.1", port=server.server_address[1], timeout=5)
        with pytest.raises(Exception):
            client.connect()
        client.close()
    finally:
        server.shutdown()
        server.server_close()