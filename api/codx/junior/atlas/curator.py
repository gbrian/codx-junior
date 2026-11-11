"""
Background refresh for the atlas.

The atlas refreshes itself before a query, so it is correct without a watcher.
This curator only removes the first-query latency: after a file change it waits
for a short quiet period (the editor writes several files in a row) and then
rebuilds the index in a daemon thread.

It is deliberately tiny: no queue server, no extra process. The same function
can be called by the change manager or by a host that already watches files.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_TIMERS: Dict[str, threading.Timer] = {}
_DEFAULT_DELAY_SECONDS = 3.0


def _project_key(settings: Any) -> str:
    return str(
        getattr(settings, "project_id", None)
        or getattr(settings, "codx_path", None)
        or getattr(settings, "abs_project_path", None)
        or getattr(settings, "project_name", "unknown")
    )


def schedule_atlas_refresh(
    settings: Any,
    files: Optional[List[str]] = None,
    delay: float = _DEFAULT_DELAY_SECONDS,
) -> bool:
    """
    Schedule one debounced atlas refresh for ``settings``.

    Returns False when the atlas is disabled for the project. The refresh is a
    best-effort background operation: it never raises into the file-change
    path and it is cancelled if another change arrives before the delay.
    """
    if settings is None:
        return False
    if not bool(getattr(settings, "project_atlas_enabled", False)):
        return False

    key = _project_key(settings)
    delay = max(0.5, float(delay or _DEFAULT_DELAY_SECONDS))

    def _refresh() -> None:
        try:
            from .query import ProjectAtlas

            with ProjectAtlas(settings) as atlas:
                atlas.ensure(force=False)
                logger.debug(
                    "Atlas background refresh done for %s (%d changed file(s))",
                    getattr(settings, "project_name", key),
                    len(files or []),
                )
        except Exception as ex:  # pragma: no cover - background best effort
            logger.warning("Atlas background refresh failed for %s: %s", key, ex)
        finally:
            with _LOCK:
                _TIMERS.pop(key, None)

    with _LOCK:
        existing = _TIMERS.get(key)
        if existing is not None and existing.is_alive():
            # A refresh is already queued. Do not push it back on every tool
            # call: the first query schedules it and later calls just wait.
            return True
        timer = threading.Timer(delay, _refresh)
        timer.daemon = True
        _TIMERS[key] = timer
        timer.start()
    return True


def cancel_atlas_refresh(settings: Any) -> None:
    """Cancel a pending refresh (used by tests and project shutdown)."""
    key = _project_key(settings)
    with _LOCK:
        timer = _TIMERS.pop(key, None)
    if timer is not None:
        timer.cancel()
