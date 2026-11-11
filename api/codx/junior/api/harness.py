"""
REST surface of the codx-junior harness.

Exposes the observability and audit layer of the native harness:

* ``GET /api/harness/audit``    — the append-only audit journal of the project
  (every registered request, run, step and completion, newest first).
* ``GET /api/harness/status``   — harness health: orchestration worker presence,
  active runs and the watchdog state for the project.

Both endpoints are read-only: the journal is written by the orchestration
runtime, the chat engine and the watchdog, never through HTTP.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter()


def _session(request: Request):
    """Return the session injected by the codx_path middleware."""
    session = getattr(request.state, "codx_junior_session", None)
    if session is None:
        raise HTTPException(
            status_code=400,
            detail="codx_path is required (query string or x-codx-path header)",
        )
    return session


@router.get("/harness/audit")
def harness_audit(
    request: Request,
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    event: Optional[str] = Query(default=None),
    run_id: Optional[str] = Query(default=None),
    chat_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """
    Read the harness audit journal of the project (newest first).

    The journal registers every piece of harness work: ``task_requested``,
    run lifecycle events (``run_created`` ... ``run_completed``), step
    dispatches and finishes, notifications and worker supervision
    (``worker_stalled`` / ``worker_restarted`` / ``worker_recovered``).

    ``run_id`` and ``chat_id`` scope the journal to one harness task, which is
    what the diagnostic view uses to explain why a task is where it is.
    """
    from codx.junior.harness.audit import HarnessAuditLog, audit_path

    session = _session(request)
    codx_path = str(getattr(session.settings, "codx_path", "") or "")
    journal = HarnessAuditLog(codx_path)
    return {
        "codx_path": codx_path,
        "exists": journal.exists(),
        "path": audit_path(codx_path),
        "total": None,
        "entries": journal.read(
            limit=limit,
            offset=offset,
            event=event,
            run_id=run_id,
            chat_id=chat_id,
        ),
    }


@router.get("/harness/status")
def harness_status(request: Request) -> Dict[str, Any]:
    """
    Harness health of the project: worker presence, active runs and watchdog.
    """
    session = _session(request)
    codx_path = str(getattr(session.settings, "codx_path", "") or "")

    worker: Dict[str, Any] = {}
    active_runs: List[str] = []
    try:
        from codx.junior.orchestration.store import RunStore

        store = RunStore(codx_path)
        worker = store.worker_status()
        active_runs = store.active_run_ids()
    except Exception as ex:  # pragma: no cover - defensive
        logger.warning("Harness status: could not read worker state: %s", ex)

    watchdog: Dict[str, Any] = {}
    try:
        from codx.junior.harness.watchdog import (
            get_harness_watchdog,
            watchdog_enabled,
        )

        instance = get_harness_watchdog()
        watchdog = (instance.status if instance is not None else {}) or {}
        watchdog["enabled"] = watchdog_enabled()
    except Exception as ex:  # pragma: no cover - defensive
        logger.warning("Harness status: could not read watchdog state: %s", ex)

    return {
        "codx_path": codx_path,
        "worker": worker,
        "worker_running": bool(worker.get("present")),
        "active_runs": active_runs,
        "active_run_count": len(active_runs),
        "watchdog": watchdog,
    }
