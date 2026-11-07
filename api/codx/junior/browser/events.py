"""Best-effort Socket.IO events for browser co-browsing.

Activity used to be polled every 7 seconds.  The browser runtime now publishes
each user/AI action and every control change, so the UI can update in place.
The broadcast is deliberately best-effort: a missing Socket.IO layer (tests,
CLI, background worker) must never break a browser action.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

BROWSER_ACTIVITY_EVENT = "codx-junior-browser-activity"
BROWSER_CONTROL_EVENT = "codx-junior-browser-control"
BROWSER_STATUS_EVENT = "codx-junior-browser-status"


def broadcast(event: str, data: Dict[str, Any]) -> None:
    """Publish *data* on *event* through the project's Socket.IO channel."""
    try:
        from codx.junior.sio.session_channel import SessionChannel
        from codx.junior.sio.sio import sio

        SessionChannel(sio=sio).send_event(event, dict(data or {}))
    except Exception as ex:  # pragma: no cover - depends on the running app
        logger.debug("Could not broadcast browser event %s: %s", event, ex)


def broadcast_activity(session_id: str, entry: Dict[str, Any]) -> None:
    """Publish one activity entry (the client appends it without a poll)."""
    broadcast(BROWSER_ACTIVITY_EVENT, {"session_id": session_id, "entry": entry})


def broadcast_control(session: Any) -> None:
    """Publish the new control lease of a session."""
    try:
        data = session.to_dict() if hasattr(session, "to_dict") else dict(session or {})
    except Exception:
        data = {}
    broadcast(BROWSER_CONTROL_EVENT, {
        "session_id": getattr(session, "id", None),
        "controller": getattr(session, "controller", None),
        "handoff_reason": getattr(session, "handoff_reason", None),
        "user_active_until": getattr(session, "user_active_until", None),
        "session": data,
    })
