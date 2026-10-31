"""
Management router — cross-project dashboard for management.

The ``Team Command Center`` screen answers one question for management: *what is
happening, what is stuck, who is loaded and when will it be delivered*, across
**every project**, for a time window.

Route layout
------------
GET   /api/management/overview          – Pulse: metrics, attention, activity,
                                          forecast, team load and cost
POST  /api/management/tasks/query       – Work: filtered, sorted, paginated tasks
GET   /api/management/blockers          – attention queue
GET   /api/management/delivery          – forecast per board + burndown
GET   /api/management/team-load         – capacity and workload per assignee
GET   /api/management/cost              – AI consumption and budget
PATCH /api/management/tasks/{task_id}   – update one task
PUT   /api/management/tasks/{task_id}   – same (the client HTTP layer has no PATCH)
POST  /api/management/assistant         – rule-based answer over the same numbers

This module needs no registration: ``codx.junior.api.discover_routers`` imports
every module of this package that exports ``router`` and mounts it under
``/api``.

Access
------
Every route requires an authenticated user and is scoped to the projects that
user can see (``find_all_user_projects``); admins see every project. Nothing is
computed for a project the caller has no access to.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from codx.junior.api import get_current_session  # noqa: F401 - parity with other routers
from codx.junior.management_manager import ManagementManager
from codx.junior.model.management import (
    ManagementAssistantRequest,
    ManagementAssistantResponse,
    ManagementBlockersResponse,
    ManagementCostResponse,
    ManagementDeliveryResponse,
    ManagementOverview,
    ManagementTaskQueryRequest,
    ManagementTaskQueryResponse,
    ManagementTaskUpdate,
    ManagementTaskUpdateResponse,
    ManagementTeamResponse,
)
from codx.junior.model.model import CodxUser
from codx.junior.security.user_management import get_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/management", tags=["management"])

# Query parameters: ``from`` is a reserved keyword, so the parameter is named
# ``from_date`` while the alias keeps the client contract (``?from=...``).
FromQuery = Query(None, alias="from", description="Inclusive start date YYYY-MM-DD")
ToQuery = Query(None, alias="to", description="Inclusive end date YYYY-MM-DD")


def _manager(user: CodxUser) -> ManagementManager:
    """Build a manager scoped to the caller's visible projects."""
    return ManagementManager(user=user)


@router.get(
    "/overview",
    response_model=ManagementOverview,
    summary="Everything the management Pulse section renders",
)
def get_overview(
    from_date: Optional[str] = FromQuery,
    to_date: Optional[str] = ToQuery,
    user: CodxUser = Depends(get_authenticated_user),
) -> ManagementOverview:
    """
    Return the cross-project overview for the window (default: last 7 days).

    Includes headline metrics, the attention queue, the activity feed, the
    delivery forecast per board, team load and AI cost — everything the first
    screen draws, in a single round trip.
    """
    return _manager(user).overview(from_date, to_date)


@router.post(
    "/tasks/query",
    response_model=ManagementTaskQueryResponse,
    summary="Filtered, sorted and paginated tasks across every project",
)
def query_tasks(
    body: ManagementTaskQueryRequest,
    user: CodxUser = Depends(get_authenticated_user),
) -> ManagementTaskQueryResponse:
    """
    Return one page of tasks plus the reference data the filters need.

    Filtering, sorting and pagination are all performed server-side over the
    whole dataset, so the counts the UI shows are true totals and never a
    reduction over a single page.
    """
    return _manager(user).tasks(body)


@router.get(
    "/blockers",
    response_model=ManagementBlockersResponse,
    summary="Attention queue: on hold, overdue, due today, unowned and stalled",
)
def get_blockers(
    from_date: Optional[str] = FromQuery,
    to_date: Optional[str] = ToQuery,
    project_id: Optional[str] = Query(None, description="Restrict to one project"),
    user: CodxUser = Depends(get_authenticated_user),
) -> ManagementBlockersResponse:
    """Return the attention queue, most severe first."""
    return _manager(user).blockers(from_date, to_date, project_id)


@router.get(
    "/delivery",
    response_model=ManagementDeliveryResponse,
    summary="Forecast per board and burndown of the selected board",
)
def get_delivery(
    from_date: Optional[str] = FromQuery,
    to_date: Optional[str] = ToQuery,
    board_id: Optional[str] = Query(
        None, description="Board identity '<project_id>::<board>' (default: first board)"
    ),
    user: CodxUser = Depends(get_authenticated_user),
) -> ManagementDeliveryResponse:
    """
    Return the delivery forecast for every board and the burndown series of the
    requested one.

    Velocity — and therefore the ETA — is measured inside the requested window.
    """
    return _manager(user).delivery(from_date, to_date, board_id)


@router.get(
    "/team-load",
    response_model=ManagementTeamResponse,
    summary="Capacity and workload per assignee (humans and AI agents)",
)
def get_team_load(
    from_date: Optional[str] = FromQuery,
    to_date: Optional[str] = ToQuery,
    user: CodxUser = Depends(get_authenticated_user),
) -> ManagementTeamResponse:
    """
    Return capacity, workload and attributed AI cost per assignee.

    ``Chat`` stores no estimates, so load is counted in *active tasks*
    (``CODX_JUNIOR_MANAGEMENT_CAPACITY_TASKS`` open tasks = 100%).
    """
    return _manager(user).team_load(from_date, to_date)


@router.get(
    "/cost",
    response_model=ManagementCostResponse,
    summary="AI consumption and budget for the window",
)
def get_cost(
    from_date: Optional[str] = FromQuery,
    to_date: Optional[str] = ToQuery,
    project_id: Optional[str] = Query(None, description="Restrict to one project"),
    model: Optional[str] = Query(None, description="Restrict to one model"),
    user: CodxUser = Depends(get_authenticated_user),
) -> ManagementCostResponse:
    """
    Return spend, tokens, model and user breakdowns plus the budget projection.

    The numbers come from the analytics store: they are real consumption, not a
    computed estimate.
    """
    return _manager(user).cost(from_date, to_date, project_id, model)


@router.patch(
    "/tasks/{task_id}",
    response_model=ManagementTaskUpdateResponse,
    summary="Update one task",
)
@router.put(
    "/tasks/{task_id}",
    response_model=ManagementTaskUpdateResponse,
    summary="Update one task (PUT, for clients without PATCH)",
)
def update_task(
    task_id: str,
    body: ManagementTaskUpdate,
    user: CodxUser = Depends(get_authenticated_user),
) -> ManagementTaskUpdateResponse:
    """
    Apply a partial update to one task in the project that owns it.

    ``blocked`` is accepted for parity with the UI and translated into a status
    change (``true`` -> ``onhold``, ``false`` -> back to ``doing``), because
    ``Chat`` has no blocked field.

    Raises HTTP 404 when the task does not exist in any visible project.
    """
    try:
        task = _manager(user).update_task(task_id, body)
    except ValueError as ex:
        raise HTTPException(status_code=404, detail=str(ex)) from ex
    return ManagementTaskUpdateResponse(task=task)


@router.post(
    "/assistant",
    response_model=ManagementAssistantResponse,
    summary="Ask about the current window",
)
def ask_assistant(
    body: ManagementAssistantRequest,
    user: CodxUser = Depends(get_authenticated_user),
) -> ManagementAssistantResponse:
    """
    Answer a question about the window from the same numbers the screen renders.

    The answer is rule-based (blockers, cost, team load, delivery, overdue,
    completed) and every source it used is returned so the UI can navigate to
    that section.
    """
    return _manager(user).ask(body.question, body.from_, body.to)


# Made with ❤️ by codx-junior