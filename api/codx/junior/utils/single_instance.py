"""
Cross-process single-instance guard.

Background workers (chat-turn recovery, the harness watchdog, ...) are started
from the FastAPI startup hook, which uvicorn runs **once per worker process**.
When the API runs with several workers, every worker would start its own copy
of the sweeper: duplicated polling, duplicated restarts and wasted resources
(per-turn ``flock`` claims keep the WORK correct, but the supervision loops must
still be single).

This module elects one owner across processes with an exclusive, non-blocking
``flock`` on a temp-file lock. The lock is held for the process lifetime and the
kernel releases it automatically on death, so a new worker takes over after a
crash without any stale-lock cleanup.

On platforms without ``fcntl`` the guard degrades to "always acquire": the
workers stay correct (their per-item locks still apply) and only their
supervision loops may duplicate.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:  # pragma: no cover - platform dependent
    import fcntl
except Exception:  # pragma: no cover - non-POSIX
    fcntl = None


def lock_path(name: str) -> str:
    """Return the temp lock path of *name*."""
    safe = "".join(char if char.isalnum() or char in "-_" else "-" for char in name)
    return os.path.join(tempfile.gettempdir(), f"codx-junior-{safe}.lock")


def acquire_single_instance(name: str) -> Optional[Any]:
    """
    Try to become the single instance of *name* across processes.

    Args:
        name: Logical name of the worker (used in the lock file name).

    Returns:
        An open file handle holding the lock (keep it alive for as long as the
        instance runs and close it in ``release_single_instance``), or ``None``
        when another process already owns it.
    """
    if fcntl is None:  # pragma: no cover - non-POSIX
        logger.warning(
            "Single-instance guard unavailable (no fcntl); '%s' may run in several processes",
            name,
        )
        return object()

    path = lock_path(name)
    try:
        handle = open(path, "a+", encoding="utf-8")
    except OSError as ex:  # pragma: no cover - defensive
        logger.warning("Single-instance guard: cannot open %s: %s", path, ex)
        return None
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    try:
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()))
        handle.flush()
    except OSError:  # pragma: no cover - best effort
        pass
    logger.info("Single-instance guard: '%s' acquired by pid %s", name, os.getpid())
    return handle


def release_single_instance(handle: Optional[Any]) -> None:
    """Release a handle returned by :func:`acquire_single_instance`."""
    if handle is None:
        return
    close = getattr(handle, "close", None)
    if callable(close):
        try:
            close()
        except Exception:  # pragma: no cover - defensive
            pass
