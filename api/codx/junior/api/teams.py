"""
Teams API router.

Provides CRUD endpoints for hybrid teams (AI profiles + human users) scoped to
the active project. Teams are persisted **per project** (exactly like chats)
and are managed by :class:`codx.junior.teams.team_manager.TeamManager`.

The active session is read from ``request.state.codx_junior_session`` (the same
convention used by ``codx/junior/api/chat.py``).

```mermaid
flowchart TD
    LIST[GET /api/teams] --> LM[TeamManager.list_teams]
    READ[GET /api/teams/{team_id}] --> FM[TeamManager.find_by_id]
    CREATE[POST /api/teams] --> SV[TeamManager.save_team]
    UPDATE[PUT /api/teams/{team_id}] --> SV
    DELETE[DELETE /api/teams/{team_id}] --> DL[TeamManager.delete_team]
    ADDM[POST /api/teams/{team_id}/members] --> AM[TeamManager.add_members]
    REMV[DELETE /api/teams/{team_id}/members] --> RM[TeamManager.remove_members]
```
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from codx.junior.engine import CODXJuniorSession
from codx.junior.model.model import CodxUser
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.teams.model import Team, TeamMembers
from codx.junior.teams.team_manager import TeamManager

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_session(request: Request) -> CODXJuniorSession:
    """Return the session bound to the current request."""
    session = getattr(request.state, "codx_junior_session", None)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project session not available for this request.",
        )
    return session


def _get_team_manager(session: CODXJuniorSession) -> TeamManager:
    """Instantiate a :class:`TeamManager` from the active session's settings."""
    return TeamManager(settings=session.settings)


def _actor(user: Optional[CodxUser]) -> Optional[str]:
    """Return the acting user's username, or ``None``."""
    return user.username if user and getattr(user, "username", None) else None


def _split_csv(value: Optional[str]) -> List[str]:
    """Split a comma-separated query parameter into a clean list."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


async def _read_members(request: Request) -> TeamMembers:
    """
    Resolve team members from a JSON body and/or query parameters.

    A JSON body (``{"profiles": [...], "users": [...]}``) is preferred; any
    ``profiles``/``users`` query parameters are merged in so clients that
    cannot send a body on DELETE still work.

    :param request: The incoming request.
    :return: A populated :class:`TeamMembers` object.
    """
    profiles: List[str] = []
    users: List[str] = []

    try:
        body = await request.json()
    except ValueError:
        body = None

    if isinstance(body, dict):
        profiles.extend(body.get("profiles") or [])
        users.extend(body.get("users") or [])

    profiles.extend(_split_csv(request.query_params.get("profiles")))
    users.extend(_split_csv(request.query_params.get("users")))

    return TeamMembers(profiles=profiles, users=users)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/teams", response_model=List[Team])
def list_teams(
    request: Request,
    user: CodxUser = Depends(get_authenticated_user),
) -> List[Team]:
    """Return all teams for the active project."""
    session = _get_session(request)
    teams = _get_team_manager(session).list_teams()
    logger.info(
        "User '%s' listed %d teams for project '%s'",
        _actor(user) or "anonymous",
        len(teams),
        session.settings.project_id,
    )
    return teams


@router.post("/teams", response_model=Team)
async def create_team(
    request: Request,
    user: CodxUser = Depends(get_authenticated_user),
) -> Team:
    """
    Create a new team for the active project.

    The request body is a JSON object matching the :class:`Team` schema
    (``name`` is required; ``description``, ``color``, ``icon``, ``profiles``,
    ``users`` and ``tags`` are optional). A fresh id is always assigned by the
    server.

    Example body:

    ```json
    {
      "name": "Engineering",
      "description": "Builds and reviews the product",
      "color": "#6366f1",
      "icon": "fa-solid fa-robot"
    }
    ```
    """
    session = _get_session(request)
    body = await request.json()
    try:
        team = Team(**(body or {}))
    except (TypeError, ValueError) as exc:
        logger.warning("Invalid team payload from user '%s': %s", _actor(user), exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not team.name or not team.name.strip():
        raise HTTPException(status_code=422, detail="Field 'name' must not be empty.")

    # Always allocate a fresh id for a new team and stamp ownership.
    team.id = None
    team.created_by = _actor(user)
    team.updated_by = _actor(user)

    saved_team = _get_team_manager(session).save_team(team)

    logger.info(
        "User '%s' created team '%s' (id=%s) in project '%s'",
        _actor(user) or "anonymous",
        saved_team.name,
        saved_team.id,
        session.settings.project_id,
    )
    return saved_team


@router.get("/teams/{team_id}", response_model=Team)
def get_team(
    team_id: str,
    request: Request,
    user: CodxUser = Depends(get_authenticated_user),
) -> Team:
    """
    Return a single team by id.

    :raises HTTPException 404: when no team with the given id exists.
    """
    session = _get_session(request)
    team = _get_team_manager(session).find_by_id(team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found.")
    return team


@router.put("/teams/{team_id}", response_model=Team)
async def update_team(
    team_id: str,
    request: Request,
    user: CodxUser = Depends(get_authenticated_user),
) -> Team:
    """
    Update an existing team (partial update applied over the stored team).

    Fields present in the body are applied on top of the stored team, so
    omitted fields keep their previous value. ``id``, ``project_id`` and
    ``created_at`` cannot be changed by the client.

    :raises HTTPException 404: when no team with the given id exists.
    :raises HTTPException 422: when the resulting name is empty.
    """
    session = _get_session(request)
    manager = _get_team_manager(session)
    existing = manager.find_by_id(team_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found.")

    body = await request.json()
    merged = existing.model_dump()
    merged.update({key: value for key, value in (body or {}).items() if key in Team.model_fields})
    merged["id"] = team_id
    merged["project_id"] = session.settings.project_id
    merged["created_at"] = existing.created_at
    merged["created_by"] = existing.created_by
    merged["updated_by"] = _actor(user)

    updated_team = Team(**merged)
    if not updated_team.name or not updated_team.name.strip():
        raise HTTPException(status_code=422, detail="Field 'name' must not be empty.")

    saved_team = manager.save_team(updated_team)

    logger.info(
        "User '%s' updated team '%s' in project '%s'",
        _actor(user) or "anonymous",
        team_id,
        session.settings.project_id,
    )
    return saved_team


@router.delete("/teams/{team_id}")
def delete_team(
    team_id: str,
    request: Request,
    user: CodxUser = Depends(get_authenticated_user),
) -> dict:
    """
    Delete a team by id.

    :raises HTTPException 404: when no team with the given id exists.
    """
    session = _get_session(request)
    deleted = _get_team_manager(session).delete_team(team_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found.")

    logger.info(
        "User '%s' deleted team '%s' from project '%s'",
        _actor(user) or "anonymous",
        team_id,
        session.settings.project_id,
    )
    return {"message": f"Team '{team_id}' deleted successfully."}


@router.post("/teams/{team_id}/members", response_model=Team)
async def add_team_members(
    team_id: str,
    request: Request,
    user: CodxUser = Depends(get_authenticated_user),
) -> Team:
    """
    Add AI profiles and/or human users to a team.

    Members are resolved from a JSON body (preferred) and/or
    ``profiles``/``users`` comma-separated query parameters. Duplicates are
    ignored.

    Example: ``{ "profiles": ["software_developer"], "users": ["alice"] }``.

    :raises HTTPException 404: when no team with the given id exists.
    """
    session = _get_session(request)
    members = await _read_members(request)

    try:
        team = _get_team_manager(session).add_members(
            team_id,
            profiles=members.profiles,
            users=members.users,
            actor=_actor(user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    logger.info(
        "User '%s' added members to team '%s': profiles=%s users=%s",
        _actor(user) or "anonymous",
        team_id,
        members.profiles,
        members.users,
    )
    return team


@router.delete("/teams/{team_id}/members", response_model=Team)
async def remove_team_members(
    team_id: str,
    request: Request,
    user: CodxUser = Depends(get_authenticated_user),
) -> Team:
    """
    Remove AI profiles and/or human users from a team.

    Members are resolved from a JSON body and/or ``profiles``/``users``
    comma-separated query parameters, so DELETE callers that cannot send a body
    still work.

    Example: ``{ "profiles": ["software_developer"], "users": ["alice"] }``.

    :raises HTTPException 404: when no team with the given id exists.
    """
    session = _get_session(request)
    members = await _read_members(request)

    try:
        team = _get_team_manager(session).remove_members(
            team_id,
            profiles=members.profiles,
            users=members.users,
            actor=_actor(user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    logger.info(
        "User '%s' removed members from team '%s': profiles=%s users=%s",
        _actor(user) or "anonymous",
        team_id,
        members.profiles,
        members.users,
    )
    return team


# Made with ❤️ by codx-junior