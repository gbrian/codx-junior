"""
Inter-process file lock used by the orchestration store and cost roll-up.

Two writers can touch the same project from different processes:

* the API process (a chat turn, a run control endpoint),
* the background process (orchestration worker, project checker).

``fcntl.flock`` gives an advisory lock that the OS releases automatically when
the process dies, which is exactly the crash-safety property the run worker
needs. A process-local ``threading.Lock`` is layered on top because two threads
of the same process opening the same file separately would otherwise not
serialize reliably across all platforms.

The module degrades to a process-local lock when ``fcntl`` is unavailable
(non-POSIX development environments); production runs on Linux.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Dict, Iterator, Optional

logger = logging.getLogger(__name__)

try:  # pragma: no cover - platform dependent
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - non POSIX
    fcntl = None  # type: ignore

# One threading lock per absolute lock path. The guard protects the map itself.
_THREAD_LOCKS: Dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()

DEFAULT_TIMEOUT_SECONDS = 30.0
_POLL_SECONDS = 0.05


def _thread_lock(path: str) -> threading.Lock:
    """Return (creating if needed) the process-local lock for *path*."""
    with _THREAD_LOCKS_GUARD:
        lock = _THREAD_LOCKS.get(path)
        if lock is None:
            lock = threading.Lock()
            _THREAD_LOCKS[path] = lock
        return lock


def _ensure_parent(path: str) -> None:
    """Create the parent folder of *path* if it does not exist."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


@contextmanager
def interprocess_lock(
    path: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Iterator[None]:
    """
    Hold an exclusive lock on *path* for the duration of the context.

    Args:
        path: Lock file path. It does not need to exist; it is created.
        timeout: Maximum seconds to wait. ``0`` means try once and raise.

    Yields:
        None.

    Raises:
        TimeoutError: When the lock cannot be acquired within *timeout*.

    Example:
        >>> with interprocess_lock("/proj/.codx/.cost.lock"):
        ...     update_root_cost()
    """
    path = os.path.abspath(path)
    _ensure_parent(path)
    local_lock = _thread_lock(path)

    deadline = time.monotonic() + max(0.0, float(timeout))
    acquired_local = local_lock.acquire(
        timeout=max(0.0, deadline - time.monotonic())
    )
    if not acquired_local:
        raise TimeoutError(f"Timed out waiting for local lock '{path}'")

    handle: Optional[object] = None
    try:
        if fcntl is not None:
            handle = open(path, "a+", encoding="utf-8")
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except (BlockingIOError, OSError):
                    if time.monotonic() >= deadline:
                        raise TimeoutError(
                            f"Timed out waiting for inter-process lock '{path}'"
                        )
                    time.sleep(_POLL_SECONDS)
        yield
    finally:
        if handle is not None:
            try:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError as ex:  # pragma: no cover - defensive
                logger.warning("Could not release file lock '%s': %s", path, ex)
            finally:
                try:
                    handle.close()
                except OSError:  # pragma: no cover - defensive
                    pass
        local_lock.release()

# Made with ❤️ by codx-junior
