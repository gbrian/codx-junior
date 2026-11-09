"""
WebSocket ↔ TCP bridge for the built-in noVNC viewer.

The human should not need a separate VNC client, and the browser must not embed
a raw TCP host/port (which is not reachable from the public origin).  The API
issues a short-lived, single-use ticket bound to one session's VNC endpoint; the
client opens ``/api/computers/{id}/vnc?ticket=...`` and the endpoint tunnels raw
RFB bytes between the WebSocket and the container/remote host.

The ticket pattern mirrors the container-shell one (``api/infra.py``): the
long-lived JWT never appears in a WebSocket URL, and the endpoint only connects
to the host/port captured when the authenticated HTTP request issued it.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_TICKET_TTL = 60
#: Keep the bridge bounded; 1080p raw frames are ~8 MB.
MAX_FRAME_BYTES = 16 * 1024 * 1024


@dataclass
class VncTicket:
    """One-time permission to open a VNC WebSocket for a session."""

    value: str
    session_id: str
    host: str
    port: int
    user: str = ""
    created_at: float = field(default_factory=time.time)
    # In-process references used to mark the human active when their RFB
    # pointer/keyboard events cross the bridge.  Tickets are process-local, so
    # these objects are safe to keep (they are never serialized).
    session: Any = None
    manager: Any = None
    expires_at: float = 0.0
    used: bool = False


class VncTicketStore:
    """In-memory, single-use, expiring VNC tickets."""

    def __init__(self, ttl: int = DEFAULT_TICKET_TTL):
        self.ttl = max(10, int(ttl or DEFAULT_TICKET_TTL))
        self._tickets: Dict[str, VncTicket] = {}
        self._lock = threading.Lock()

    def issue(
        self,
        session_id: str,
        host: str,
        port: int,
        user: str = "",
        session: Any = None,
        manager: Any = None,
    ) -> VncTicket:
        """Create a ticket for one session endpoint."""
        if not host:
            raise ValueError("Cannot issue a VNC ticket without a host")
        now = time.time()
        ticket = VncTicket(
            value=secrets.token_urlsafe(32),
            session_id=str(session_id),
            host=str(host),
            port=int(port or 5900),
            user=user or "",
            created_at=now,
            session=session,
            manager=manager,
            expires_at=now + self.ttl,
        )
        with self._lock:
            self._prune(now)
            self._tickets[ticket.value] = ticket
        return ticket

    def consume(self, value: str) -> Optional[VncTicket]:
        """Redeem a ticket (returns None when missing, used or expired)."""
        if not value:
            return None
        now = time.time()
        with self._lock:
            ticket = self._tickets.pop(value, None)
            if ticket is None or ticket.used or ticket.expires_at < now:
                return None
            ticket.used = True
            return ticket

    def _prune(self, now: float) -> None:
        """Drop expired tickets (called while holding the lock)."""
        expired = [key for key, ticket in self._tickets.items() if ticket.expires_at < now]
        for key in expired:
            self._tickets.pop(key, None)


#: Process-wide ticket store.
vnc_tickets = VncTicketStore()


async def bridge_vnc(
    websocket,
    host: str,
    port: int,
    on_input=None,
) -> None:
    """
    Tunnel one WebSocket to a raw VNC TCP connection.

    Both directions are pumped concurrently; whichever closes first cancels the
    other.  Binary WebSocket frames carry RFB bytes unchanged (which is exactly
    what noVNC's ``RFB`` expects from its URL).
    """
    reader = writer = None
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, int(port)),
            timeout=10,
        )
    except Exception as ex:
        logger.warning("Could not connect to VNC %s:%s: %s", host, port, ex)
        try:
            await websocket.close(code=1011, reason="VNC endpoint unreachable")
        except Exception:
            pass
        return

    async def client_to_vnc() -> None:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                return
            data = message.get("bytes")
            if data is None and message.get("text") is not None:
                data = message["text"].encode("utf-8")
            if data:
                if len(data) > MAX_FRAME_BYTES:
                    raise RuntimeError("VNC frame too large")
                # RFB client→server KeyEvent (4) / PointerEvent (5): the human
                # is driving the shared machine.  noVNC sends one message per
                # frame, so inspecting the first byte is enough to keep the AI
                # yielding while the user types or clicks.
                if on_input is not None and data and data[0] in (4, 5):
                    try:
                        on_input()
                    except Exception:
                        logger.debug("VNC input callback failed", exc_info=True)
                writer.write(data)
                await writer.drain()

    async def vnc_to_client() -> None:
        while True:
            data = await reader.read(65536)
            if not data:
                return
            await websocket.send_bytes(data)

    tasks = [
        asyncio.create_task(client_to_vnc()),
        asyncio.create_task(vnc_to_client()),
    ]
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in done:
            try:
                task.result()
            except Exception:
                pass
    except Exception as ex:
        logger.debug("VNC bridge ended: %s", ex)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
