"""
Small TCP proxy used to expose Chromium's DevTools endpoint to the Docker network.

Chromium only binds its DevTools HTTP/WebSocket server to ``127.0.0.1`` and it
also validates the ``Host`` header (non-loopback hosts are rejected).  Since the
codx-junior API runs in a *different* container, neither the endpoint nor the
WebSocket handshake is reachable directly.

This script runs inside the browser container and:

    API container ─► 0.0.0.0:9223 (proxy) ─► 127.0.0.1:9222 (DevTools)

The first HTTP request of every downstream connection has its ``Host`` header
rewritten to a loopback value (required by Chromium), then the connection is
tunnelled byte-for-byte so WebSocket frames and Chrome DevTools Protocol
messages pass through untouched.

Only the Python standard library is used, so it runs on the upstream
LinuxServer.io Chromium image without a custom Docker build.

Environment variables:
    CDP_PROXY_LISTEN_HOST  Host/interface to listen on (default ``0.0.0.0``).
    CDP_PROXY_LISTEN_PORT  Exposed proxy port (default ``9223``).
    CDP_TARGET_HOST        DevTools host (default ``127.0.0.1``).
    CDP_TARGET_PORT        DevTools port (default ``9222``).
    CDP_REWRITE_HOST       Value written in the ``Host`` header (default
                           ``127.0.0.1:9222``).
"""

import asyncio
import logging
import os

LISTEN_HOST = os.environ.get("CDP_PROXY_LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("CDP_PROXY_LISTEN_PORT", "9223"))
TARGET_HOST = os.environ.get("CDP_TARGET_HOST", "127.0.0.1")
TARGET_PORT = int(os.environ.get("CDP_TARGET_PORT", "9222"))
REWRITE_HOST = os.environ.get("CDP_REWRITE_HOST", f"{TARGET_HOST}:{TARGET_PORT}")
CHUNK_SIZE = 64 * 1024
MAX_HEADER_BYTES = 64 * 1024

logging.basicConfig(level=logging.INFO, format="[cdp-proxy] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _rewrite_headers(raw: bytes) -> bytes:
    """
    Replace the HTTP ``Host`` header of a request with :data:`REWRITE_HOST`.

    Args:
        raw: The request line plus headers, ending with ``\\r\\n\\r\\n``.

    Returns:
        The same request with a single loopback ``Host`` header.
    """
    text = raw.decode("latin-1", errors="replace")
    lines = text.split("\r\n")
    if not lines:
        return raw

    rewritten = [lines[0]]
    for line in lines[1:]:
        if not line:
            continue
        if line.lower().startswith("host:"):
            continue
        rewritten.append(line)
    # Insert right after the request line: proxy tools expect Host early.
    rewritten.insert(1, f"Host: {REWRITE_HOST}")
    return ("\r\n".join(rewritten) + "\r\n\r\n").encode("latin-1")


async def _read_http_headers(reader: asyncio.StreamReader) -> bytes:
    """Read the first HTTP request headers (up to the terminating blank line)."""
    data = b""
    while b"\r\n\r\n" not in data and len(data) < MAX_HEADER_BYTES:
        chunk = await reader.read(4096)
        if not chunk:
            break
        data += chunk
    return data


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Copy every chunk from *reader* to *writer* until EOF or error."""
    try:
        while True:
            data = await reader.read(CHUNK_SIZE)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def _handle(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter) -> None:
    """Rewrite the first request's Host header and tunnel the connection."""
    try:
        raw_headers = await _read_http_headers(client_reader)
        if not raw_headers:
            client_writer.close()
            return

        marker = b"\r\n\r\n"
        if marker in raw_headers:
            headers, _, extra = raw_headers.partition(marker)
            raw_headers = _rewrite_headers(headers + marker)
            if extra:
                raw_headers += extra
        else:
            raw_headers = _rewrite_headers(raw_headers + marker)

        target_reader, target_writer = await asyncio.open_connection(TARGET_HOST, TARGET_PORT)
        target_writer.write(raw_headers)
        await target_writer.drain()

        await asyncio.gather(
            _pipe(client_reader, target_writer),
            _pipe(target_reader, client_writer),
        )
    except Exception as ex:
        logger.warning("CDP proxy connection failed: %s", ex)
        try:
            client_writer.close()
        except Exception:
            pass


async def main() -> None:
    """Start the proxy server and serve forever."""
    server = await asyncio.start_server(_handle, LISTEN_HOST, LISTEN_PORT)
    sockets = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    logger.info("CDP proxy listening on %s -> %s:%s", sockets, TARGET_HOST, TARGET_PORT)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
