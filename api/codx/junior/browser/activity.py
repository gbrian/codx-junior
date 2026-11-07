"""
Browser activity log — append-only audit trail for co-browsing sessions.

Every action performed on a browser session is written as one JSON object per
line to::

    .codx/browser_sessions/<session_id>/activity.jsonl

Both actors are recorded:

* ``ai``   – a tool call executed by SmolAgent (or another agent).
* ``user`` – an action sent from the web UI / REST API.
* ``system`` – lifecycle events (create / stop / restart / delete / errors).

The log is intentionally independent from the AI analytics store: analytics
tracks LLM token usage and cost, while this file answers "what happened in this
browser, when, and who did it".  The API exposes it through
``GET /api/browsers/{id}/activity`` and joins it with the AI cost of every chat
connected to the session in ``GET /api/browsers/{id}/cost``.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ACTIVITY_FILE = "activity.jsonl"
MAX_READ_LINES = 2000


def _now() -> str:
    """Return a timezone-aware ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


class BrowserActivityLog:
    """Append-only per-session activity log."""

    def __init__(self, session_folder: str):
        """
        Args:
            session_folder: Folder that owns the ``activity.jsonl`` file.
        """
        self.session_folder = session_folder
        self.path = os.path.join(session_folder, ACTIVITY_FILE)

    def record(
        self,
        *,
        actor: str,
        action: str,
        success: bool = True,
        session_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        url: Optional[str] = None,
        title: Optional[str] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
        result: Any = None,
    ) -> Dict[str, Any]:
        """
        Append one activity entry.

        The method is best-effort: logging failures are reported but never
        break a browser action.

        Returns:
            The entry that was written.
        """
        entry: Dict[str, Any] = {
            "ts": _now(),
            "session_id": session_id,
            "chat_id": chat_id,
            "actor": actor or "system",
            "action": action,
            "success": bool(success),
            "params": _safe_params(params),
            "url": url,
            "title": title,
            "duration_ms": round(float(duration_ms), 2) if duration_ms is not None else None,
            "error": error,
        }
        if result is not None:
            try:
                serialized = json.dumps(result, ensure_ascii=False, default=str)
            except Exception:
                serialized = str(result)
            entry["result"] = serialized[:4000]

        try:
            os.makedirs(self.session_folder, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except Exception as ex:
            logger.warning("Could not write browser activity log '%s': %s", self.path, ex)
        return entry

    def read(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Return the most recent *limit* entries (oldest → newest).

        Large logs are read tail-first so activity endpoints stay cheap.
        """
        if not os.path.isfile(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8", errors="replace") as handle:
                lines = handle.readlines()[-max(1, min(int(limit), MAX_READ_LINES)):]
        except Exception as ex:
            logger.warning("Could not read browser activity log '%s': %s", self.path, ex)
            return []

        entries: List[Dict[str, Any]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries


def _safe_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Trim/redact action parameters before persisting them."""
    if not params:
        return {}
    safe: Dict[str, Any] = {}
    for key, value in params.items():
        if key in ("settings", "session", "tool_cache"):
            continue
        if isinstance(value, str):
            safe[key] = value[:2000]
        elif isinstance(value, (int, float, bool)) or value is None:
            safe[key] = value
        else:
            safe[key] = str(value)[:2000]
    return safe


# Made with ❤️ by codx-junior
