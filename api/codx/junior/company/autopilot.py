"""
Background autopilot loop for companies.

The **API process never dispatches a mission inline**: it writes intent (a
``ready`` mission with ``dispatch_mode=auto``) and the autopilot loop — or a
human pressing "Run cycle" — starts the work. This mirrors the durable
orchestration split (API writes, worker executes) and keeps HTTP requests fast.

Safety
------
* Disabled by default: :class:`~.models.AutonomyPolicy` starts with
  ``enabled=False`` and every company must be enabled explicitly.
* Only ``auto`` missions are dispatched; human-created missions default to
  ``manual``.
* ``max_concurrent_missions`` / ``max_missions_per_cycle`` are enforced by the
  manager, not by this loop.
* A cross-process file lock (``fcntl``) makes sure only one autopilot loop runs
  per installation, even when the API and the background worker are separate
  processes.

The loop is started from :mod:`codx.junior.background` and is a no-op when the
background services are disabled.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import logging
import os
import threading

from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

#: How often the loop looks for due companies (seconds).
AUTOPILOT_TICK_SECONDS = int(
    os.environ.get("CODX_JUNIOR_COMPANY_AUTOPILOT_TICK_SECONDS") or 60
)

#: Set to ``false`` to disable the loop even when background services run.
AUTOPILOT_ENABLED = str(
    os.environ.get("CODX_JUNIOR_COMPANY_AUTOPILOT", "true")
).lower() not in ("0", "false", "no", "off")

_LOCK_FILENAME = ".autopilot.lock"
_thread: Optional[threading.Thread] = None
_stop_event: Optional[threading.Event] = None


def _try_lock(root_path: str):
    """
    Acquire the process-global autopilot lock.

    Args:
        root_path: Companies root (the lock lives next to it).

    Returns:
        An open file handle holding the lock, or ``None`` when another process
        already owns it / locking is unsupported.
    """
    try:
        import fcntl

        os.makedirs(root_path, exist_ok=True)
        handle = open(
            os.path.join(root_path, _LOCK_FILENAME), "a+", encoding="utf-8"
        )
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return handle
        except OSError:
            handle.close()
            return None
    except Exception as ex:  # pragma: no cover - non-POSIX / read-only fs
        logger.debug("Company autopilot lock unavailable: %s", ex)
        return None


def run_once() -> Dict[str, Any]:
    """
    Run one pass over every company whose autopilot is due.

    Returns:
        ``{"reports": [...], "companies": manager.list_companies()}`` when the
        loop could not acquire the lock, or ``{"skipped": True}``.
    """
    from .manager import CompanyManager
    from .store import get_companies_root

    root_path = get_companies_root()
    handle = _try_lock(root_path)
    if handle is None and AUTOPILOT_ENABLED:
        # Another process owns the loop. Do nothing instead of double-dispatching.
        return {"skipped": True, "reason": "another autopilot owns the lock"}
    try:
        manager = CompanyManager(root_path=root_path)
        reports = manager.run_due_cycles(actor="autopilot")
        if reports:
            logger.info("Company autopilot: %d cycle(s) ran", len(reports))
        return {"skipped": False, "reports": reports}
    except Exception as ex:  # pragma: no cover - defensive
        logger.exception("Company autopilot pass failed: %s", ex)
        return {"skipped": False, "error": str(ex), "reports": []}
    finally:
        if handle is not None:
            try:
                handle.close()
            except Exception:
                pass


def _loop(stop_event: threading.Event) -> None:
    """Autopilot loop body (blocking until *stop_event* is set)."""
    logger.info(
        "Company autopilot started (tick=%ss, enabled=%s)",
        AUTOPILOT_TICK_SECONDS,
        AUTOPILOT_ENABLED,
    )
    while not stop_event.is_set():
        try:
            if AUTOPILOT_ENABLED:
                run_once()
        except Exception as ex:  # pragma: no cover - never kill the loop
            logger.exception("Company autopilot tick failed: %s", ex)
        stop_event.wait(max(5, AUTOPILOT_TICK_SECONDS))


def start_company_autopilot(stop_event: Optional[threading.Event] = None) -> Optional[threading.Thread]:
    """
    Start the company autopilot thread once.

    Args:
        stop_event: Event that stops the loop (a new one is created when omitted).

    Returns:
        The running thread, or ``None`` when the autopilot is disabled.
    """
    global _thread, _stop_event

    if not AUTOPILOT_ENABLED:
        logger.info("Company autopilot disabled via CODX_JUNIOR_COMPANY_AUTOPILOT")
        return None
    if _thread and _thread.is_alive():
        return _thread

    _stop_event = stop_event or threading.Event()
    _thread = threading.Thread(
        target=_loop,
        args=(_stop_event,),
        name="CompanyAutopilot",
        daemon=True,
    )
    _thread.start()
    return _thread


def stop_company_autopilot() -> None:
    """Signal the autopilot thread to stop (idempotent)."""
    global _thread, _stop_event

    if _stop_event is not None:
        _stop_event.set()
    if _thread is not None and _thread.is_alive():
        _thread.join(timeout=5)
    _thread = None
    _stop_event = None


# Made with ❤️ by codx-junior
