"""
REST surface of durable orchestration runs.

The API process **never executes a turn**: it creates the run / writes control
intent and reads the persisted state. The background worker advances the run, so
no endpoint depends on the 30 s HTTP timeout.

Endpoints (``codx_path`` is the usual query/header parameter):

* ``GET    /api/orchestration``                     list runs
* ``POST   /api/orchestration``                     create a run (new or attached main task)
* ``GET    /api/orchestration/{run_id}``            full detail (plan, results, cards, worker)
* ``POST   /api/orchestration/{run_id}/steps``      add a step
* ``POST   /api/orchestration/{run_id}/finish``     mark completed + delivery report
* ``POST   /api/orchestration/{run_id}/pause``      pause
* ``POST   /api/orchestration/{run_id}/start``      start/resume/reopen
* ``POST   /api/orchestration/{run_id}/resume``     resume
* ``POST   /api/orchestration/{run_id}/stop``       stop + cancel in-flight turns
* ``POST   /api/orchestration/{run_id}/tick``       wake the worker (admin)

Every mutation is persisted before the response; the worker picks the run up on
its next tick. ``worker.present`` in the detail tells whether a background
worker is actually running for the project.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from codx.junior.api import require_admin
from codx.junior.model.model import CodxUser
from codx.junior.orchestration.models import (
    PlanError,
    RunConfig,
    RunCorrupt,
    RunLocked,
    RunNotFound,
)
from codx.junior.security.user_management import get_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class RunCreateRequest(BaseModel):
    """Create a run: a new main task, or attach to an existing one."""

    name: str = Field(default="", description="Run name (defaults to the main task name).")
    objective: str = Field(default="", description="What the run must achieve.")
    main_chat_id: Optional[str] = Field(
        default=None,
        description="Existing chat to promote to main task. When omitted a new main task is created.",
    )
    budget_cxjcoins: float = Field(default=0.0, description="Hard run budget (0 = no hard budget).")
    per_step_budget: float = Field(default=0.0, description="Optional per-step cap.")
    supervisor_reserve: float = Field(default=0.0, description="Cost reserved for verification/report.")
    max_steps: Optional[int] = None
    max_rounds: Optional[int] = None
    max_parallel: Optional[int] = None
    verification: Optional[str] = Field(default=None, description="supervisor | none")
    board: Optional[str] = Field(default=None, description="Board title for the step cards.")
    sprint: Optional[str] = Field(default=None, description="Sprint title (default 'Run: <name>').")
    profiles: Optional[List[str]] = Field(default=None, description="Supervisor profile(s).")


class StepAddRequest(BaseModel):
    """One plan step."""

    id: Optional[str] = None
    title: str
    objective: str
    acceptance: str = ""
    profile: str = ""
    depends_on: List[str] = Field(default_factory=list)
    files: List[str] = Field(default_factory=list)
    context: str = ""
    priority: str = "medium"
    mode: str = ""


class FinishRequest(BaseModel):
    """Completion payload (becomes the delivery report)."""

    summary: str


class ControlRequest(BaseModel):
    """Optional reason for pause/stop."""

    reason: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session(request: Request):
    """Return the session injected by the codx_path middleware."""
    session = getattr(request.state, "codx_junior_session", None)
    if session is None:
        raise HTTPException(
            status_code=400,
            detail="codx_path is required (query string or x-codx-path header)",
        )
    return session


def _service(request: Request):
    """Build an OrchestrationService for the request project."""
    from codx.junior.orchestration.service import OrchestrationService

    session = _session(request)
    return OrchestrationService(
        settings=session.settings,
        chat_manager=session.get_chat_manager(),
        event_manager=session.event_manager,
        user=getattr(session, "user", None),
    )


def _username(user: Optional[CodxUser]) -> str:
    """Return the username for audit fields."""
    return str(getattr(user, "username", "") or "")


def _failure(ex: Exception) -> HTTPException:
    """Map orchestration errors onto HTTP errors."""
    if isinstance(ex, RunNotFound):
        return HTTPException(status_code=404, detail=str(ex))
    if isinstance(ex, RunLocked):
        return HTTPException(status_code=409, detail=str(ex))
    if isinstance(ex, (PlanError, ValueError)):
        return HTTPException(status_code=400, detail=str(ex))
    if isinstance(ex, RunCorrupt):
        return HTTPException(status_code=500, detail=str(ex))
    logger.exception("Orchestration API error: %s", ex)
    return HTTPException(status_code=500, detail=str(ex))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/orchestration")
def api_list_runs(request: Request, status: Optional[str] = None):
    """List the runs of the project (newest first)."""
    try:
        return {"runs": _service(request).list_runs(status=status)}
    except Exception as ex:
        raise _failure(ex)


@router.post("/orchestration", status_code=201)
def api_create_run(
    payload: RunCreateRequest,
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """
    Create a run.

    When ``main_chat_id`` is set that task becomes the run dashboard; otherwise a
    new main task is created on the run board.
    """
    try:
        service = _service(request)
        main_chat = None
        if payload.main_chat_id:
            main_chat = service.get_chat(payload.main_chat_id)
            if main_chat is None:
                raise HTTPException(status_code=404, detail="Main chat not found")
        config = RunConfig(
            budget_cxjcoins=payload.budget_cxjcoins,
            per_step_budget=payload.per_step_budget,
            supervisor_reserve=payload.supervisor_reserve,
            max_steps=payload.max_steps or 30,
            max_rounds=payload.max_rounds or 40,
            max_parallel=payload.max_parallel or 2,
            verification=payload.verification or "supervisor",
            board=payload.board or "Orchestration",
            sprint=payload.sprint or "",
            supervisor_profiles=payload.profiles or ["orchestrator"],
        )
        run = service.create_run(
            name=payload.name,
            objective=payload.objective,
            config=config,
            main_chat=main_chat,
            created_by=_username(user),
            start=True,
            persist_main=True,
        )
        return service.status(run.run_id, include_events=False)
    except HTTPException:
        raise
    except Exception as ex:
        raise _failure(ex)


@router.get("/orchestration/{run_id}")
def api_run_detail(run_id: str, request: Request):
    """Return the full run detail (plan, results, cards, worker presence)."""
    try:
        return _service(request).status(run_id)
    except Exception as ex:
        raise _failure(ex)


@router.post("/orchestration/{run_id}/steps")
def api_add_step(
    run_id: str,
    payload: StepAddRequest,
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Add one step to the plan."""
    try:
        service = _service(request)
        service.add_step(run_id, payload.model_dump())
        return service.status(run_id, include_events=False)
    except Exception as ex:
        raise _failure(ex)


@router.post("/orchestration/{run_id}/finish")
def api_finish_run(
    run_id: str,
    payload: FinishRequest,
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Mark a run completed and publish the delivery report."""
    try:
        service = _service(request)
        service.finish(run_id, payload.summary)
        return service.status(run_id, include_events=False)
    except Exception as ex:
        raise _failure(ex)


@router.post("/orchestration/{run_id}/pause")
def api_pause_run(
    run_id: str,
    request: Request,
    payload: Optional[ControlRequest] = None,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Pause a run (the in-flight turn is allowed to finish)."""
    try:
        service = _service(request)
        service.pause(run_id, reason=(payload.reason if payload else ""))
        return service.status(run_id, include_events=False)
    except Exception as ex:
        raise _failure(ex)


@router.post("/orchestration/{run_id}/start")
def api_start_run(
    run_id: str,
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """
    Start a run: resume a paused run, or reopen a stopped/failed one.

    This is the UI's single "start" action. An already running run is returned
    unchanged, so the caller can retry safely.
    """
    try:
        service = _service(request)
        service.start(run_id)
        return service.status(run_id, include_events=False)
    except Exception as ex:
        raise _failure(ex)


@router.post("/orchestration/{run_id}/resume")
def api_resume_run(
    run_id: str,
    request: Request,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Resume a paused run."""
    try:
        service = _service(request)
        service.resume(run_id)
        return service.status(run_id, include_events=False)
    except Exception as ex:
        raise _failure(ex)


@router.post("/orchestration/{run_id}/stop")
def api_stop_run(
    run_id: str,
    request: Request,
    payload: Optional[ControlRequest] = None,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Stop a run and cancel its in-flight turns."""
    try:
        service = _service(request)
        service.stop(run_id, reason=(payload.reason if payload else ""))
        return service.status(run_id, include_events=False)
    except Exception as ex:
        raise _failure(ex)


@router.post("/orchestration/{run_id}/tick")
def api_wake_run(
    run_id: str,
    request: Request,
    user: CodxUser = Depends(require_admin),
):
    """
    Ask the background worker to advance the run now.

    The endpoint only writes a wake flag: runs execute in the background
    process, so the HTTP request returns immediately even when a worker turn
    takes minutes.
    """
    try:
        service = _service(request)
        service.request_tick(run_id)
        payload = service.status(run_id, include_events=False)
        payload["note"] = (
            "Wake requested; the background worker advances the run on its next tick."
            if payload.get("worker", {}).get("present")
            else "Wake requested, but no background worker is present for this project."
        )
        return payload
    except Exception as ex:
        raise _failure(ex)

# Made with ❤️ by codx-junior
