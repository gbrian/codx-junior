"""
REST surface of the company entity (``/api/companies``).

The company is **global** (one company can own projects across the
installation), so these endpoints do not require a project session. They do
require an authenticated user; destructive/write operations are limited to the
company owner or an admin.

Route map
---------
```text
GET    /api/companies                          list companies
POST   /api/companies                          create (optional template)
GET    /api/companies/references               projects / users / profiles pickers
GET    /api/companies/{company_id}             company document
PUT    /api/companies/{company_id}             update company-level fields
DELETE /api/companies/{company_id}             delete company

GET    /api/companies/{id}/snapshot            dashboard payload (incl. members)
GET    /api/companies/{id}/journal             audit journal

GET    /api/companies/{id}/members             human roster + company roles
POST   /api/companies/{id}/members             add/onboard a person (company admin)
PUT    /api/companies/{id}/members/{username}  change role/title (company admin)
DELETE /api/companies/{id}/members/{username}  remove a person (company admin)
POST   /api/companies/{id}/assistant           always-present company assistant

POST   /api/companies/{id}/org-units           add org unit
PUT    /api/companies/{id}/org-units/{unit}    update org unit
DELETE /api/companies/{id}/org-units/{unit}    delete org unit

POST   /api/companies/{id}/teams               add team
PUT    /api/companies/{id}/teams/{team}        update team
DELETE /api/companies/{id}/teams/{team}        delete team
GET    /api/companies/{id}/teams/{team}        resolved roster
POST   /api/companies/{id}/teams/{team}/members
DELETE /api/companies/{id}/teams/{team}/members
PUT    /api/companies/{id}/teams/{team}/lead

POST   /api/companies/{id}/projects            link project
DELETE /api/companies/{id}/projects/{project}  unlink project

POST   /api/companies/{id}/missions            add mission
PUT    /api/companies/{id}/missions/{mission}  update mission
DELETE /api/companies/{id}/missions/{mission}  delete mission
POST   /api/companies/{id}/missions/{mission}/dispatch
POST   /api/companies/{id}/missions/{mission}/accept
POST   /api/companies/{id}/missions/{mission}/reject
POST   /api/companies/{id}/missions/{mission}/transition
POST   /api/companies/{id}/missions/sync       mirror runs onto missions

PUT    /api/companies/{id}/autonomy            configure the autopilot
POST   /api/companies/{id}/cycle               run one cycle now
```

Diagram
-------
```mermaid
flowchart LR
    UI[CompanyView.vue] -->|/api/companies| API
    Tool[company_management] --> Manager
    API --> Manager[CompanyManager]
    Manager --> Store[(company.json + journal.jsonl)]
    Manager -->|dispatch| Run[Durable orchestration run]
    Run --> Worker[Project worker]
    Worker --> Board[Project board / tasks]
```

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import logging

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from codx.junior.company.manager import (
    CompanyConflict,
    CompanyDispatchError,
    CompanyManager,
    CompanyNotFound,
    CompanyStoreError,
    CompanyValidationError,
)
from codx.junior.model.model import CodxUser
from codx.junior.model.user import (
    COMPANY_ROLES,
    COMPANY_ROLE_ADMIN,
    COMPANY_ROLE_MANAGER,
)
from codx.junior.security.user_management import (
    UserSecurityManager,
    get_authenticated_user,
)
from codx.junior.company.assistant import CompanyAssistant

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request payloads
# ---------------------------------------------------------------------------


class CompanyCreateRequest(BaseModel):
    """Create a company (optionally from a starter template)."""

    name: str = Field(description="Company name (unique slug derived from it)")
    description: str = ""
    mission: str = ""
    vision: str = ""
    values: List[str] = Field(default_factory=list)
    website: str = ""
    logo: str = ""
    color: str = "#6366f1"
    status: str = "active"
    owner: str = ""
    tags: List[str] = Field(default_factory=list)
    template: str = Field(
        default="",
        description="Optional starter: 'saas' (codx-junior cloud) or 'blank'",
    )
    project_ids: List[str] = Field(
        default_factory=list, description="Projects to link at creation time"
    )


class CompanyUpdateRequest(BaseModel):
    """Company-level update (org/teams/projects/missions have their own routes)."""

    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    mission: Optional[str] = None
    vision: Optional[str] = None
    values: Optional[List[str]] = None
    website: Optional[str] = None
    logo: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    tags: Optional[List[str]] = None


class OrgUnitRequest(BaseModel):
    """Create/update an org unit (department, function or division)."""

    name: str = ""
    kind: str = "department"
    description: str = ""
    parent_id: str = ""
    lead_kind: str = "user"
    lead_name: str = ""
    responsibilities: List[str] = Field(default_factory=list)
    color: str = "#6366f1"
    icon: str = ""
    order: int = 0


class TeamRequest(BaseModel):
    """Create/update a hybrid team."""

    name: str = ""
    description: str = ""
    purpose: str = ""
    org_unit_id: str = ""
    lead_kind: str = "profile"
    lead_name: str = ""
    members: List[Any] = Field(default_factory=list)
    project_ids: List[str] = Field(default_factory=list)
    autonomy: str = "supervised"
    tools: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    color: str = "#6366f1"
    icon: str = "fa-solid fa-people-group"


class MembersRequest(BaseModel):
    """Add/remove team members."""

    members: List[Any] = Field(
        default_factory=list,
        description="member names, 'user:alice' / 'profile:analyst' or objects",
    )


class LeadRequest(BaseModel):
    """Change a team lead."""

    kind: str = "profile"
    name: str = ""


class ProjectLinkRequest(BaseModel):
    """Link a project to the company."""

    project_id: str
    name: str = ""
    role: str = ""
    description: str = ""
    team_id: str = ""
    priority: str = "medium"
    status: str = "active"
    budget_cxjcoins: float = 0.0


class MissionRequest(BaseModel):
    """Create/update a mission."""

    title: str = ""
    objective: str = ""
    acceptance: str = ""
    status: Optional[str] = None
    priority: str = "medium"
    team_id: str = ""
    project_id: str = ""
    owner_kind: str = "user"
    owner_name: str = ""
    dispatch_mode: str = "manual"
    budget_cxjcoins: float = 0.0
    due_date: str = ""
    tags: List[str] = Field(default_factory=list)


class TransitionRequest(BaseModel):
    """Move a mission through the status machine."""

    status: str
    force: bool = False


class AcceptRequest(BaseModel):
    """Accept a mission in review."""

    result: str = ""


class RejectRequest(BaseModel):
    """Reject a mission in review."""

    reason: str = ""


class AutonomyRequest(BaseModel):
    """Configure the autopilot policy."""

    enabled: Optional[bool] = None
    level: Optional[str] = None
    interval_minutes: Optional[int] = None
    max_concurrent_missions: Optional[int] = None
    max_missions_per_cycle: Optional[int] = None
    daily_budget_cxjcoins: Optional[float] = None
    require_human_acceptance: Optional[bool] = None


class CycleRequest(BaseModel):
    """Run one autonomy cycle."""

    force: bool = Field(
        default=True,
        description="Run even when the autopilot is disabled or not due",
    )


class DeleteRequest(BaseModel):
    """Generic force flag for destructive operations."""

    force: bool = False


class CompanyMemberRequest(BaseModel):
    """
    Add (or onboard) a human member of a company.

    Company admins can either enroll an existing codx-junior user (no password)
    or create the account on the fly (password required by the security
    manager).
    """

    username: str = Field(description="Login name")
    role: str = Field(
        default="member", description="Company role: admin | manager | member"
    )
    title: str = ""
    email: str = ""
    password: str = ""
    user_role: str = Field(
        default="user",
        description="Global role for a newly created account (user by default)",
    )


class CompanyMemberUpdateRequest(BaseModel):
    """Change the company role/title of an existing member."""

    role: Optional[str] = None
    title: Optional[str] = None


class AssistantRequest(BaseModel):
    """One turn of the always-present company assistant."""

    message: str = ""
    view: str = Field(
        default="", description="Company view the manager is looking at"
    )
    history: List[Dict[str, Any]] = Field(
        default_factory=list, description="Previous turns (role/content)"
    )
    state: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Conversation state returned by the previous turn. It is how the "
            "assistant asks one question at a time instead of dumping a form."
        ),
    )
    language: str = Field(
        default="",
        description=(
            "Browser/request language (e.g. 'es-ES'). Used by the AI fallback "
            "when the rule-based assistant does not understand the message."
        ),
    )
    form_id: str = Field(
        default="", description="Set when submitting a form rendered by the assistant"
    )
    values: Dict[str, Any] = Field(
        default_factory=dict, description="Values submitted from the assistant form"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _manager() -> CompanyManager:
    """Build the company manager (cheap; catalogs are lazy)."""
    return CompanyManager()


def _actor(user: Optional[CodxUser]) -> str:
    """Return the username used for the audit trail."""
    return str(getattr(user, "username", "") or "system")


def _fail(ex: Exception) -> HTTPException:
    """Map manager errors onto HTTP errors."""
    if isinstance(ex, CompanyNotFound):
        return HTTPException(status_code=404, detail=str(ex))
    if isinstance(ex, CompanyConflict):
        return HTTPException(status_code=409, detail=str(ex))
    if isinstance(ex, CompanyDispatchError):
        return HTTPException(status_code=502, detail=str(ex))
    if isinstance(ex, (CompanyValidationError, ValueError)):
        return HTTPException(status_code=400, detail=str(ex))
    if isinstance(ex, CompanyStoreError):
        return HTTPException(status_code=500, detail=str(ex))
    logger.exception("Company API error: %s", ex)
    return HTTPException(status_code=500, detail=str(ex))


def _run(operation):
    """Execute a manager operation, translating its errors into HTTP errors."""
    try:
        return operation()
    except HTTPException:
        raise
    except Exception as ex:
        raise _fail(ex)


def _company_role(company: Any, user: Optional[CodxUser]) -> str:
    """
    Return *user*'s effective role inside *company*.

    Resolution order: global admin → company owner → membership role. A company
    without an owner is treated as open (fresh install / migration) so the first
    authenticated user can finish configuring it.
    """
    if company is None:
        return COMPANY_ROLE_ADMIN
    if user and getattr(user, "role", "") == "admin":
        return COMPANY_ROLE_ADMIN
    username = _actor(user)
    owner = getattr(company, "owner", "") or ""
    if owner and owner == username:
        return COMPANY_ROLE_ADMIN
    memberships = getattr(user, "companies", None) or []
    membership = next(
        (
            item
            for item in memberships
            if getattr(item, "company_id", "") == getattr(company, "id", "")
        ),
        None,
    )
    if membership is not None:
        return membership.role
    return ""


def _assert_can_edit(company: Any, user: Optional[CodxUser]) -> None:
    """
    Refuse writes from users that neither own the company nor are admins.

    Company admins and managers may manage the work; only company admins may
    add/remove users (see ``_assert_company_admin``). A company without an owner
    is editable by any authenticated user (fresh install / migration); once it
    has one, roles are enforced.
    """
    if company is None:
        return
    owner = getattr(company, "owner", "") or ""
    if not owner:
        return
    role = _company_role(company, user)
    if role in (COMPANY_ROLE_ADMIN, COMPANY_ROLE_MANAGER):
        return
    raise HTTPException(
        status_code=403,
        detail=(
            f"Company '{company.name}' is owned by '{owner}'. "
            "Ask a company admin to grant you access."
        ),
    )


def _assert_company_admin(company: Any, user: Optional[CodxUser]) -> None:
    """Refuse user management from anyone but a company/global admin."""
    if company is None:
        return
    # A company without an owner is still being bootstrapped (fresh install or
    # a document created before the role model); the first authenticated user
    # may finish configuring it.
    if not (getattr(company, "owner", "") or ""):
        return
    if _company_role(company, user) != COMPANY_ROLE_ADMIN:
        raise HTTPException(
            status_code=403,
            detail=(
                "Only company admins can add or change company users. "
                "Ask an admin of this company."
            ),
        )


def _get_editable(company_id: str, user: Optional[CodxUser]):
    """Load a company and enforce ownership for a write operation."""
    manager = _manager()
    company = manager.get_company(company_id)
    _assert_can_edit(company, user)
    return manager, company


def _company_payload(request: CompanyCreateRequest) -> Dict[str, Any]:
    """Convert the create request into a company payload."""
    return request.model_dump(exclude={"template", "project_ids"})


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------


@router.get("/companies")
def api_list_companies(
    include_archived: bool = Query(default=True),
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """List every company (newest first is by name; summary payload)."""
    return _run(lambda: _manager().list_companies(include_archived=include_archived))


@router.get("/companies/references")
def api_company_references(
    project_id: Optional[str] = Query(default=None),
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """
    Return the catalogs a company editor needs.

    Declared before ``/companies/{company_id}`` so "references" is never parsed
    as a company id.
    """
    return _run(lambda: _manager().references(project_id=project_id))


@router.post("/companies", status_code=201)
def api_create_company(
    payload: CompanyCreateRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Create a company, optionally seeded from a starter template."""
    manager = _manager()
    company_payload = _company_payload(payload)
    # The creator owns the company unless an explicit owner is supplied. The
    # ``owner`` field is what the authorization helpers, the UI badge and the
    # assistant use; the membership (below) is the role index.
    company_payload["owner"] = company_payload.get("owner") or _actor(user)
    created = _run(
        lambda: manager.create_company(
            company_payload,
            actor=_actor(user),
            template=payload.template,
            project_ids=payload.project_ids,
        )
    )
    # Make the creator a company admin from the first second: the membership is
    # what the UI, the company assistant and the authorization helpers read.
    username = _actor(user)
    if username and username != "system":
        try:
            UserSecurityManager().add_company_member(
                company_id=created.id,
                username=username,
                role=COMPANY_ROLE_ADMIN,
                title="Owner",
            )
        except Exception:
            # Auth may be disabled or the user may live outside global settings;
            # the company.owner field still grants admin rights.
            logger.exception("Could not enroll '%s' in company '%s'", username, created.id)
    return created


@router.get("/companies/{company_id}")
def api_get_company(
    company_id: str,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Return one company document."""
    return _run(lambda: _manager().get_company(company_id))


@router.put("/companies/{company_id}")
def api_update_company(
    company_id: str,
    payload: CompanyUpdateRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Update the company-level fields."""
    manager, company = _run(lambda: _get_editable(company_id, user))
    changes = payload.model_dump(exclude_unset=True)
    # Ownership transfer is an administrative act: a company manager must not
    # be able to promote themselves by re-assigning the owner.
    if "owner" in changes and changes.get("owner") != company.owner:
        _assert_company_admin(company, user)
    return _run(
        lambda: manager.update_company(
            company_id,
            changes,
            actor=_actor(user),
        )
    )


@router.delete("/companies/{company_id}")
def api_delete_company(
    company_id: str,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Delete a company and its journal (company admins only)."""
    manager, company = _run(lambda: _get_editable(company_id, user))
    _assert_company_admin(company, user)
    return _run(lambda: manager.delete_company(company_id, actor=_actor(user)))


@router.get("/companies/{company_id}/snapshot")
def api_company_snapshot(
    company_id: str,
    journal_limit: int = Query(default=30, ge=0, le=500),
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Return the full dashboard payload for a company."""
    return _run(
        lambda: _manager().snapshot(company_id, journal_limit=journal_limit)
    )


@router.get("/companies/{company_id}/journal")
def api_company_journal(
    company_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Return the audit journal (newest last)."""
    return _run(lambda: _manager().journal(company_id, limit=limit))


# ---------------------------------------------------------------------------
# People / company users
# ---------------------------------------------------------------------------


@router.get("/companies/{company_id}/members")
def api_company_members(
    company_id: str,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Return the human roster of a company (with company roles)."""
    manager = _manager()
    company = _run(lambda: manager.get_company(company_id))
    return {
        "company_id": company.id,
        "members": _run(lambda: manager.company_members(company)),
        "can_add_users": (
            not (company.owner or "")
            or _company_role(company, user) == COMPANY_ROLE_ADMIN
        ),
    }


@router.post("/companies/{company_id}/members", status_code=201)
def api_add_company_member(
    company_id: str,
    payload: CompanyMemberRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """
    Add a human to the company.

    A company admin may either enroll an existing user or create the account on
    the fly (``password`` supplied). This is the endpoint behind the People view
    and the assistant's "add user" form.
    """
    manager = _manager()
    company = _run(lambda: manager.get_company(company_id))
    _assert_company_admin(company, user)
    if payload.role not in COMPANY_ROLES:
        raise HTTPException(status_code=400, detail=f"invalid company role '{payload.role}'")
    if payload.user_role not in ("user", "manager", "company_admin"):
        raise HTTPException(status_code=400, detail=f"invalid user role '{payload.user_role}'")
    security = UserSecurityManager()
    created = _run(
        lambda: security.create_company_user(
            company_id=company.id,
            username=payload.username,
            password=payload.password,
            email=payload.email,
            role=payload.role,
            title=payload.title,
            user_role=payload.user_role,
        )
    )
    return {
        **created,
        "members": _run(lambda: manager.company_members(company)),
    }


@router.put("/companies/{company_id}/members/{username}")
def api_update_company_member(
    company_id: str,
    username: str,
    payload: CompanyMemberUpdateRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Change the role/title of an existing company member."""
    manager = _manager()
    company = _run(lambda: manager.get_company(company_id))
    _assert_company_admin(company, user)
    security = UserSecurityManager()
    if payload.role is not None and payload.role not in COMPANY_ROLES:
        raise HTTPException(status_code=400, detail=f"invalid company role '{payload.role}'")
    current = next(
        (
            member
            for member in _run(lambda: manager.company_members(company))
            if member["username"] == username
        ),
        None,
    )
    if current is None:
        raise HTTPException(status_code=404, detail=f"User '{username}' is not a company member")
    new_role = payload.role or current.get("company_role") or "member"
    if current.get("owner") and new_role != COMPANY_ROLE_ADMIN:
        raise HTTPException(
            status_code=409,
            detail="The company owner always stays an admin. Transfer ownership first.",
        )
    if current.get("company_role") == COMPANY_ROLE_ADMIN and new_role != COMPANY_ROLE_ADMIN:
        admins = [
            member for member in _run(lambda: manager.company_members(company))
            if member.get("company_role") == COMPANY_ROLE_ADMIN
        ]
        if len(admins) <= 1:
            raise HTTPException(
                status_code=409,
                detail="The last company admin must stay an admin. Promote another admin first.",
            )
    membership = _run(
        lambda: security.add_company_member(
            company_id=company.id,
            username=username,
            role=payload.role or current.get("company_role") or "member",
            title=payload.title if payload.title is not None else current.get("title", ""),
        )
    )
    return {
        "membership": membership,
        "members": _run(lambda: manager.company_members(company)),
    }


@router.delete("/companies/{company_id}/members/{username}")
def api_delete_company_member(
    company_id: str,
    username: str,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """
    Remove a human from the company.

    The owner and the last company admin cannot be removed, so a company can
    never end up without someone able to administer it.
    """
    manager = _manager()
    company = _run(lambda: manager.get_company(company_id))
    _assert_company_admin(company, user)
    if username == company.owner:
        raise HTTPException(
            status_code=409,
            detail="The company owner cannot be removed. Transfer ownership first.",
        )
    members = _run(lambda: manager.company_members(company))
    target = next((member for member in members if member["username"] == username), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"User '{username}' is not a company member")
    if target.get("company_role") == COMPANY_ROLE_ADMIN:
        admins = [member for member in members if member.get("company_role") == COMPANY_ROLE_ADMIN]
        if len(admins) <= 1:
            raise HTTPException(
                status_code=409,
                detail="The last company admin cannot be removed. Promote another admin first.",
            )
    removed = _run(lambda: UserSecurityManager().remove_company_member(company.id, username))
    return {
        "removed": removed,
        "members": _run(lambda: manager.company_members(company)),
    }


# ---------------------------------------------------------------------------
# Assistant
# ---------------------------------------------------------------------------


@router.post("/companies/{company_id}/assistant")
def api_company_assistant(
    company_id: str,
    payload: AssistantRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """
    One turn of the always-present company assistant.

    The assistant is intentionally a **company-native** endpoint: it receives the
    current view and the conversation history, resolves the company context and
    either answers with the live data, executes a permitted action (team
    management, add user, mission review) or returns a form schema the UI must
    render inside the assistant window.

    Settings dialogs are never opened by the main company screen; the assistant
    either renders the form itself (returned as ``form``) or proposes the
    concrete action to confirm.
    """
    manager = _manager()
    company = _run(lambda: manager.get_company(company_id))
    role = _company_role(company, user)
    # An unowned company is still being bootstrapped: the first authenticated
    # user can finish configuring it (same rule as the write helpers).
    if not (company.owner or ""):
        role = COMPANY_ROLE_ADMIN
    can_manage = role in (COMPANY_ROLE_ADMIN, COMPANY_ROLE_MANAGER)
    can_admin = role == COMPANY_ROLE_ADMIN
    assistant = CompanyAssistant(manager=manager)
    return _run(
        lambda: assistant.respond(
            company=company,
            message=payload.message,
            view=payload.view,
            actor=_actor(user),
            can_manage=can_manage,
            can_admin=can_admin,
            history=payload.history,
            state=payload.state,
            form_id=payload.form_id,
            values=payload.values,
            user=user,
            language=payload.language,
        )
    )


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------


@router.post("/companies/{company_id}/org-units", status_code=201)
def api_add_org_unit(
    company_id: str,
    payload: OrgUnitRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Add a department/function to the organization."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.add_org_unit(
            company_id, payload.model_dump(exclude_unset=True), actor=_actor(user)
        )
    )


@router.put("/companies/{company_id}/org-units/{unit_id}")
def api_update_org_unit(
    company_id: str,
    unit_id: str,
    payload: OrgUnitRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Update an org unit."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.update_org_unit(
            company_id,
            unit_id,
            payload.model_dump(exclude_unset=True),
            actor=_actor(user),
        )
    )


@router.delete("/companies/{company_id}/org-units/{unit_id}")
def api_delete_org_unit(
    company_id: str,
    unit_id: str,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Delete an org unit (children and teams are detached)."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.delete_org_unit(company_id, unit_id, actor=_actor(user))
    )


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


@router.post("/companies/{company_id}/teams", status_code=201)
def api_add_team(
    company_id: str,
    payload: TeamRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Add a hybrid team."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.add_team(
            company_id, payload.model_dump(exclude_unset=True), actor=_actor(user)
        )
    )


@router.get("/companies/{company_id}/teams/{team_id}")
def api_resolve_team(
    company_id: str,
    team_id: str,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Return a team with its resolved roster and availability."""
    return _run(lambda: _manager().resolve_team(company_id, team_id))


@router.put("/companies/{company_id}/teams/{team_id}")
def api_update_team(
    company_id: str,
    team_id: str,
    payload: TeamRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Update a team (including a full roster replacement)."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.update_team(
            company_id,
            team_id,
            payload.model_dump(exclude_unset=True),
            actor=_actor(user),
        )
    )


@router.delete("/companies/{company_id}/teams/{team_id}")
def api_delete_team(
    company_id: str,
    team_id: str,
    force: bool = Query(default=False),
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Delete a team (refuses while it owns open missions unless forced)."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.delete_team(
            company_id, team_id, actor=_actor(user), force=force
        )
    )


@router.post("/companies/{company_id}/teams/{team_id}/members")
def api_add_team_members(
    company_id: str,
    team_id: str,
    payload: MembersRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Add/update humans and AI profiles in a team."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.add_team_members(
            company_id, team_id, payload.members, actor=_actor(user)
        )
    )


@router.delete("/companies/{company_id}/teams/{team_id}/members")
def api_remove_team_members(
    company_id: str,
    team_id: str,
    members: str = Query(
        default="", description="Comma separated member references"
    ),
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Remove members from a team."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    refs = [ref.strip() for ref in (members or "").split(",") if ref.strip()]
    return _run(
        lambda: manager.remove_team_members(
            company_id, team_id, refs, actor=_actor(user)
        )
    )


@router.put("/companies/{company_id}/teams/{team_id}/lead")
def api_set_team_lead(
    company_id: str,
    team_id: str,
    payload: LeadRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Change a team lead."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.set_team_lead(
            company_id, team_id, payload.kind, payload.name, actor=_actor(user)
        )
    )


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@router.post("/companies/{company_id}/projects", status_code=201)
def api_link_project(
    company_id: str,
    payload: ProjectLinkRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Link a discovered codx-junior project to the company."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.link_project(
            company_id,
            payload.project_id,
            actor=_actor(user),
            **payload.model_dump(exclude={"project_id"}),
        )
    )


@router.delete("/companies/{company_id}/projects/{project_id}")
def api_unlink_project(
    company_id: str,
    project_id: str,
    force: bool = Query(default=False),
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Unlink a project (refuses while open missions run there unless forced)."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.unlink_project(
            company_id, project_id, actor=_actor(user), force=force
        )
    )


# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------


@router.post("/companies/{company_id}/missions", status_code=201)
def api_add_mission(
    company_id: str,
    payload: MissionRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Add a mission."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    values = payload.model_dump(exclude_unset=True)
    if values.get("status") is None:
        values.pop("status", None)
    return _run(
        lambda: manager.add_mission(company_id, values, actor=_actor(user))
    )


@router.put("/companies/{company_id}/missions/{mission_id}")
def api_update_mission(
    company_id: str,
    mission_id: str,
    payload: MissionRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Update a mission."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.update_mission(
            company_id,
            mission_id,
            payload.model_dump(exclude_unset=True),
            actor=_actor(user),
        )
    )


@router.delete("/companies/{company_id}/missions/{mission_id}")
def api_delete_mission(
    company_id: str,
    mission_id: str,
    force: bool = Query(default=False),
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Delete a mission (running missions require force)."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.delete_mission(
            company_id, mission_id, actor=_actor(user), force=force
        )
    )


@router.post("/companies/{company_id}/missions/{mission_id}/dispatch")
def api_dispatch_mission(
    company_id: str,
    mission_id: str,
    force: bool = Query(default=False),
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Dispatch a mission to its project's orchestration runtime."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.dispatch_mission(
            company_id, mission_id, actor=_actor(user), force=force
        )
    )


@router.post("/companies/{company_id}/missions/{mission_id}/accept")
def api_accept_mission(
    company_id: str,
    mission_id: str,
    payload: AcceptRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Accept the outcome of a mission in review."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.accept_mission(
            company_id, mission_id, result=payload.result, actor=_actor(user)
        )
    )


@router.post("/companies/{company_id}/missions/{mission_id}/reject")
def api_reject_mission(
    company_id: str,
    mission_id: str,
    payload: RejectRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Reject the outcome of a mission in review (returns it to ready)."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.reject_mission(
            company_id, mission_id, reason=payload.reason, actor=_actor(user)
        )
    )


@router.post("/companies/{company_id}/missions/{mission_id}/transition")
def api_transition_mission(
    company_id: str,
    mission_id: str,
    payload: TransitionRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Move a mission through the explicit status machine."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.transition_mission(
            company_id,
            mission_id,
            payload.status,
            actor=_actor(user),
            force=payload.force,
        )
    )


@router.post("/companies/{company_id}/missions/sync")
def api_sync_missions(
    company_id: str,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Mirror the orchestration runs onto the company missions."""
    return _run(
        lambda: _manager().sync_missions(company_id, actor=_actor(user))
    )


# ---------------------------------------------------------------------------
# Autonomy
# ---------------------------------------------------------------------------


@router.put("/companies/{company_id}/autonomy")
def api_update_autonomy(
    company_id: str,
    payload: AutonomyRequest,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Configure the company autopilot."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    return _run(
        lambda: manager.update_autonomy(
            company_id,
            payload.model_dump(exclude_unset=True),
            actor=_actor(user),
        )
    )


@router.post("/companies/{company_id}/cycle")
def api_run_cycle(
    company_id: str,
    payload: CycleRequest = None,
    user: Optional[CodxUser] = Depends(get_authenticated_user),
):
    """Run one autonomy cycle (human-triggered unless the autopilot is due)."""
    manager, _ = _run(lambda: _get_editable(company_id, user))
    force = True if payload is None else payload.force
    return _run(
        lambda: manager.cycle(company_id, actor=_actor(user), force=force)
    )


# Made with ❤️ by codx-junior
