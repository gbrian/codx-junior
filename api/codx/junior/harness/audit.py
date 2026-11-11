"""
Append-only audit journal for the codx-junior harness.

Every piece of harness work is registered here:

* ``task_requested`` — the user gave the ``codx-junior`` profile a task,
* ``run_created`` / ``run_started`` / ``run_completed`` / ``run_failed`` /
  ``run_stopped`` / ``run_budget_exhausted`` / ``run_stalled`` — run lifecycle,
* ``step_dispatched`` / ``step_started`` / ``step_finished`` /
  ``step_retried`` — every plan step executed by a worker,
* ``notification_sent`` — the user was notified of a completion,
* ``worker_started`` / ``worker_stalled`` / ``worker_restarted`` /
  ``worker_recovered`` — harness process supervision,
* ``error`` — anything that went wrong while advancing a run.

Storage: ``<project>/.codx/harness/audit.jsonl`` — one JSON object per line,
written with ``O_APPEND`` under a module lock, so concurrent processes append
whole lines atomically. The writer never raises: auditing must never break the
work it records.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

HARNESS_DIR_NAME = "harness"
AUDIT_FILE_NAME = "audit.jsonl"

# Global writer lock: one lock per path so unrelated projects never contend.
_LOCKS: Dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()

MAX_RECORD_FIELDS = 64
MAX_FIELD_LEN = 4000


def harness_dir(codx_path: str) -> str:
    """Return the harness folder of a project (``<project>/.codx/harness``)."""
    return os.path.join(str(codx_path or ""), ".codx", HARNESS_DIR_NAME)


def audit_path(codx_path: str) -> str:
    """Return the audit journal path of a project."""
    return os.path.join(harness_dir(codx_path), AUDIT_FILE_NAME)


def utcnow_iso() -> str:
    """Current UTC time as an ISO-8601 string with microseconds."""
    return datetime.now(timezone.utc).isoformat()


def _lock_for(codx_path: str) -> threading.Lock:
    """Return (creating if needed) the writer lock of a project."""
    path = str(codx_path or "")
    with _LOCKS_GUARD:
        lock = _LOCKS.get(path)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[path] = lock
        return lock


class HarnessAuditLog:
    """Append-only audit journal of one project."""

    def __init__(self, codx_path: str) -> None:
        self.codx_path = str(codx_path or "")

    # -- write ------------------------------------------------------------

    def record(self, event_type: str, **data: Any) -> Optional[Dict[str, Any]]:
        """
        Append one audit entry (never raises).

        Args:
            event_type: Short machine-readable event name.
            **data: Free-form event payload (values must be JSON-serialisable;
                they are truncated to keep the journal bounded).

        Returns:
            The recorded entry, or None when writing failed.
        """
        try:
            entry: Dict[str, Any] = {
                "ts": utcnow_iso(),
                "event": str(event_type or "event"),
            }
            for key, value in list(data.items())[:MAX_RECORD_FIELDS]:
                entry[str(key)[:80]] = _truncate(value)
            line = json.dumps(entry, ensure_ascii=False, default=str)
            path = audit_path(self.codx_path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with _lock_for(self.codx_path):
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                    fh.flush()
                    os.fsync(fh.fileno())
            return entry
        except Exception as ex:  # pragma: no cover - audit must never break work
            logger.warning("Harness audit: could not record '%s': %s", event_type, ex)
            return None

    # -- read -------------------------------------------------------------

    def read(
        self,
        *,
        limit: int = 200,
        offset: int = 0,
        event: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read journal entries, newest first.

        Args:
            limit: Maximum entries to return (1-2000).
            offset: Entries to skip from the newest one.
            event: Optional event name filter.

        Returns:
            List of decoded entries.
        """
        path = audit_path(self.codx_path)
        entries: List[Dict[str, Any]] = []
        limit = max(1, min(int(limit or 200), 2000))
        offset = max(0, int(offset or 0))
        try:
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError:
            return []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except (ValueError, TypeError):
                continue
            if event and entry.get("event") != event:
                continue
            if offset > 0:
                offset -= 1
                continue
            entries.append(entry)
            if len(entries) >= limit:
                break
        return entries

    def exists(self) -> bool:
        """Return True when the journal file exists."""
        return os.path.isfile(audit_path(self.codx_path))


def record_audit(codx_path: str, event_type: str, **data: Any) -> Optional[Dict[str, Any]]:
    """
    Record one audit entry for a project (module-level convenience, never raises).

    Safe to call from any process/thread at any time, even when the project has
    no harness folder yet (it is created on demand).
    """
    try:
        return HarnessAuditLog(codx_path).record(event_type, **data)
    except Exception:  # pragma: no cover - defensive
        return None


def _truncate(value: Any) -> Any:
    """Make one payload value JSON-safe and bounded."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, (dict, list, tuple)):
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            text = str(value)
        if len(text) <= MAX_FIELD_LEN:
            try:
                return json.loads(text)
            except (ValueError, TypeError):
                return text[:MAX_FIELD_LEN]
        return text[:MAX_FIELD_LEN]
    text = str(value)
    return text[:MAX_FIELD_LEN] if len(text) > MAX_FIELD_LEN else text
