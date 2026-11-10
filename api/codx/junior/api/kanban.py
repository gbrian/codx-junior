"""
Kanban search and board-manager REST surface.

Endpoints
---------
* ``GET  /api/kanban/search``            project-wide task search (filters+paging)
* ``GET  /api/kanban/manager``           manager config/state of every board
* ``POST /api/kanban/manager/run``       queue an immediate review ("Run now")

The board catalogue itself keeps using ``GET/POST /api/kanban``. A review is
always executed by the background worker: ``run`` only records the intent and
returns immediately, so the HTTP request never waits for an AI turn.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from codx.junior.kanban.search import DEFAULT_LIMIT, MAX_LIMIT, search_tasks

logger = logging.getLogger(__name__)

router = APIRouter()


class ManagerRunRequest(BaseModel):
    """Ask the worker to review one board now."""

    board: str = Field(description="Board title or document id")


def _session(request: Request):
    """Return the session injected by the codx_path middleware."""
    session = getattr(request.state, "codx_junior_session", None)
    if session is None:
        raise HTTPException(
            status_code=400,
            detail="codx_path is required (query string or x-codx-path header)",
        )
    return session


def _as_bool(value: Optional[str], default: bool = True) -> bool:
    """Parse a query-string boolean."""
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _as_int(value: Optional[str], default: int, minimum: int, maximum: int) -> int:
    """Parse and clamp a query-string integer."""
    try:
        number = int(str(value)) if value is not None and str(value).strip() else default
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))


@router.get("/kanban/search")
def api_kanban_search(
    request: Request,
    q: str = "",
    board: str = "",
    column: str = "",
    status: str = "",
    priority: str = "",
    profile: str = "",
    assignee: str = "",
    include_done: Optional[str] = None,
    limit: Optional[str] = None,
    offset: Optional[str] = None,
):
    """
    Search every task of the project (all boards and sprints).

    The search is project scoped on purpose: the Kanban section is the working
    set of one project, and cross-project results would need the same permission
    walk as the project list. ``q`` terms are AND matched over the name,
    description, board/column/status/priority, profiles, people, tags and the
    last message.
    """
    try:
        session = _session(request)
        manager = session.get_chat_manager()
        return search_tasks(
            manager,
            q,
            board=board,
            column=column,
            status=status,
            priority=priority,
            profile=profile,
            assignee=assignee,
            include_done=_as_bool(include_done, True),
            limit=_as_int(limit, DEFAULT_LIMIT, 1, MAX_LIMIT),
            offset=_as_int(offset, 0, 0, 10_000_000),
        )
    except HTTPException:
        raise
    except Exception as ex:
        logger.exception("api_kanban_search failed: %s", ex)
        raise HTTPException(status_code=500, detail=f"Task search failed: {ex}")


@router.get("/kanban/manager")
def api_board_manager_status(request: Request):
    """Return the board-manager configuration and runtime state."""
    try:
        from codx.junior.board_manager.service import BoardManagerService

        session = _session(request)
        return BoardManagerService(
            settings=session.settings,
            chat_manager=session.get_chat_manager(),
            event_manager=getattr(session, "event_manager", None),
        ).status()
    except HTTPException:
        raise
    except Exception as ex:
        logger.exception("api_board_manager_status failed: %s", ex)
        raise HTTPException(
            status_code=500, detail=f"Cannot read board manager status: {ex}"
        )


@router.post("/kanban/manager/run")
def api_board_manager_run(payload: ManagerRunRequest, request: Request):
    """
    Queue an immediate review of one board.

    The endpoint returns as soon as the intent is persisted; the background
    worker performs the review. The response contains the updated state so the
    UI can show "queued" (and ``worker_present`` tells whether a worker is
    actually running to pick it up).
    """
    try:
        from codx.junior.board_manager.service import BoardManagerService

        session = _session(request)
        service = BoardManagerService(
            settings=session.settings,
            chat_manager=session.get_chat_manager(),
            event_manager=getattr(session, "event_manager", None),
            user=getattr(session, "user", None),
        )
        result = service.request_run(payload.board)
        result["worker_present"] = service.store.worker_present()
        return result
    except HTTPException:
        raise
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as ex:
        logger.exception("api_board_manager_run failed: %s", ex)
        raise HTTPException(
            status_code=500, detail=f"Cannot queue the board manager review: {ex}"
        )

# Made with ❤️ by codx-junior
