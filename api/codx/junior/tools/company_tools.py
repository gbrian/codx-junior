"""
Company tool for AI profiles.

One unified tool (``company_management``) exposes the company operating system to
the AI profiles: they can create a company, shape its organization, compose
hybrid teams, link projects, write missions, dispatch work, accept/reject the
outcome and run autonomy cycles.

Why one tool with many actions
------------------------------
The repository already uses this pattern for ``team_management``,
``profile_management`` and ``project_manager``: one schema keeps the prompt
small and gives the model a single, coherent mental model instead of a dozen
nearly identical tools.

Safety
------
* Every operation goes through :class:`~codx.junior.company.manager.CompanyManager`,
  so the validation, journal and dispatch rules are the same as the API/UI.
* ``delete_company`` and turning autonomy **on** require ``confirm=true``: a
  model cannot delete an organization or start autonomous spending by accident.
* Missions created by the tool default to ``dispatch_mode="manual"``; the model
  must either set ``dispatch_mode="auto"`` or call ``dispatch_mission``.
* The autopilot still respects the company policy (concurrency, budget,
  human acceptance). The tool never bypasses it.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import json
import logging

from typing import Any, Dict, List, Optional

from codx.junior.company.manager import (
    CompanyConflict,
    CompanyDispatchError,
    CompanyManager,
    CompanyNotFound,
    CompanyValidationError,
)
from codx.junior.company.models import CompanyMember, MISSION_PRIORITIES

from .model import ToolResponse

logger = logging.getLogger(__name__)


#: Canonical actions.
VALID_ACTIONS = [
    "list",
    "get",
    "create",
    "update",
    "delete",
    "references",
    "snapshot",
    "add_org_unit",
    "update_org_unit",
    "delete_org_unit",
    "add_team",
    "update_team",
    "delete_team",
    "add_team_members",
    "remove_team_members",
    "set_team_lead",
    "link_project",
    "unlink_project",
    "add_mission",
    "update_mission",
    "delete_mission",
    "dispatch_mission",
    "accept_mission",
    "reject_mission",
    "transition_mission",
    "sync",
    "configure_autonomy",
    "run_cycle",
]

#: Tolerant aliases so a slightly different verb never crashes the run.
ACTION_ALIASES = {
    "companies": "list",
    "list_companies": "list",
    "get_company": "get",
    "create_company": "create",
    "update_company": "update",
    "delete_company": "delete",
    "report": "snapshot",
    "dashboard": "snapshot",
    "org": "snapshot",
    "create_org_unit": "add_org_unit",
    "create_department": "add_org_unit",
    "create_function": "add_org_unit",
    "create_team": "add_team",
    "members": "add_team_members",
    "add_member": "add_team_members",
    "remove_member": "remove_team_members",
    "lead": "set_team_lead",
    "set_lead": "set_team_lead",
    "projects": "references",
    "add_project": "link_project",
    "create_mission": "add_mission",
    "dispatch": "dispatch_mission",
    "run": "dispatch_mission",
    "accept": "accept_mission",
    "reject": "reject_mission",
    "transition": "transition_mission",
    "autonomy": "configure_autonomy",
    "cycle": "run_cycle",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _actor(session: Any = None) -> str:
    """Return the acting username for the audit trail."""
    user = getattr(session, "user", None) if session is not None else None
    return str(getattr(user, "username", "") or "ai-profile")


def _json(payload: Any) -> str:
    """Pretty JSON used as the LLM-facing part of a response."""
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)


def _company_md(company: Any) -> str:
    """Render a compact company summary for the chat."""
    counts = company.counts()
    lines = [
        f"### {company.name}",
        f"`{company.id}` · **{company.status}** · owner `{company.owner or 'unassigned'}`",
    ]
    if company.mission:
        lines.append(f"> {company.mission}")
    lines += [
        "",
        f"- Projects: **{counts['projects']}** · Teams: **{counts['teams']}** · "
        f"Org units: **{counts['org_units']}**",
        f"- People: **{counts['humans']} human(s)** + **{counts['ai']} AI profile(s)**",
        f"- Missions: **{counts['missions']}** total · **{counts['open_missions']}** open · "
        f"**{counts['running']}** running · **{counts['review']}** in review",
        f"- Autopilot: **{'on' if company.autonomy.enabled else 'off'}** "
        f"({company.autonomy.level}, every {company.autonomy.interval_minutes} min)",
    ]
    return "\n".join(lines)


def _mission_md(company: Any, mission: Any) -> str:
    """Render a compact mission summary for the chat."""
    team = company.team(mission.team_id)
    project = company.project(mission.project_id)
    lines = [
        f"### {mission.title}",
        f"`{mission.id}` · **{mission.status}** · priority **{mission.priority}**",
        f"- Team: {team.name if team else '(unassigned)'}",
        f"- Project: {project.name if project else mission.project_id or '(unassigned)'}",
        f"- Dispatch: {mission.dispatch_mode} · run: `{mission.run_id or '-'}` "
        f"({mission.run_status or 'not started'})",
    ]
    if mission.last_error:
        lines.append(f"- Last error: {mission.last_error}")
    return "\n".join(lines)


def _error(message: str) -> ToolResponse:
    """Build a consistent tool error response."""
    return ToolResponse(
        user_response=f"❌ {message}",
        llm_response=f"ERROR: {message}",
    )


def _resolve_action(action: str) -> Optional[str]:
    """Normalize an action name, returning ``None`` when unknown."""
    action = (action or "").strip().lower()
    action = ACTION_ALIASES.get(action, action)
    return action if action in VALID_ACTIONS else None


def _manager() -> CompanyManager:
    """Build the default company manager."""
    return CompanyManager()


def _member_refs(values: Optional[List[Any]]) -> List[CompanyMember]:
    """Parse a member list, raising a readable validation error."""
    return CompanyMember.parse_list(values or [])


def _lead_from_args(
    lead: Optional[str],
    lead_kind: Optional[str],
    lead_name: Optional[str],
) -> tuple:
    """Resolve the lead reference from the different accepted arguments."""
    if lead_name:
        return (lead_kind or "profile"), lead_name
    if lead:
        text = str(lead).strip()
        if ":" in text:
            kind, name = text.split(":", 1)
            return kind, name
        return lead_kind or "profile", text
    return lead_kind or "profile", ""


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------


def _action_list(company_id: Optional[str] = None, query: Optional[str] = None) -> ToolResponse:
    """List companies, optionally filtered."""
    manager = _manager()
    companies = manager.list_companies()
    if query:
        wanted = query.strip().lower()
        companies = [
            company
            for company in companies
            if wanted in company["name"].lower()
            or wanted in (company.get("description") or "").lower()
            or wanted in (company.get("slug") or "").lower()
        ]
    if not companies:
        return ToolResponse(
            user_response="No companies yet. Create one with action='create'.",
            llm_response=_json({"companies": []}),
        )
    lines = [f"## Companies ({len(companies)})", ""]
    for company in companies:
        counts = company.get("counts") or {}
        lines.append(
            f"- **{company['name']}** (`{company['id']}`) · {company['status']} · "
            f"{counts.get('projects', 0)} projects · {counts.get('teams', 0)} teams · "
            f"{counts.get('open_missions', 0)} open missions"
        )
    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=_json({"companies": companies}),
    )


def _action_get(company_id: str) -> ToolResponse:
    """Read one company document."""
    company = _manager().get_company(company_id)
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_create(
    action_args: Dict[str, Any], session: Any = None
) -> ToolResponse:
    """Create a company (optionally from a template)."""
    manager = _manager()
    payload = {
        key: action_args.get(key)
        for key in (
            "name",
            "description",
            "mission",
            "vision",
            "values",
            "website",
            "logo",
            "color",
            "status",
            "owner",
            "tags",
        )
        if action_args.get(key) is not None
    }
    if not payload.get("name"):
        return _error("name is required for action='create'")
    company = manager.create_company(
        payload,
        actor=_actor(session),
        template=action_args.get("template") or "",
        project_ids=action_args.get("project_ids") or [],
    )
    return ToolResponse(
        user_response=_company_md(company)
        + "\n\nUse action='snapshot' to see the organization, teams and missions.",
        llm_response=_json(company.model_dump()),
    )


def _action_update(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Update the company-level fields."""
    manager = _manager()
    patch = {
        key: action_args.get(key)
        for key in (
            "name",
            "description",
            "mission",
            "vision",
            "values",
            "website",
            "logo",
            "color",
            "status",
            "owner",
            "tags",
        )
        if action_args.get(key) is not None
    }
    if not patch:
        return _error("nothing to update: provide at least one company field")
    company = manager.update_company(company_id, patch, actor=_actor(session))
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_delete(
    company_id: str, action_args: Dict[str, Any], session: Any = None
) -> ToolResponse:
    """Delete a company (requires confirm=true)."""
    if not action_args.get("confirm"):
        return _error(
            "Deleting a company requires confirm=true. This removes its "
            "organization, teams, missions and journal (projects are untouched)."
        )
    result = _manager().delete_company(company_id, actor=_actor(session))
    return ToolResponse(
        user_response=f"Company '{result['name']}' deleted.",
        llm_response=_json(result),
    )


def _action_references(action_args: Dict[str, Any]) -> ToolResponse:
    """Return the project/user/profile catalogs."""
    references = _manager().references(project_id=action_args.get("project_id"))
    lines = [
        "## Company references",
        f"- Projects: {len(references['projects'])}",
        f"- Users: {len(references['users'])}",
        f"- AI profiles: {len(references['profiles'])}",
        "",
        "Use these names/ids when composing teams and linking projects.",
    ]
    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=_json(references),
    )


def _action_snapshot(company_id: str, action_args: Dict[str, Any]) -> ToolResponse:
    """Return the full company dashboard payload."""
    snapshot = _manager().snapshot(company_id, journal_limit=action_args.get("journal_limit") or 20)
    company = _manager().get_company(company_id)
    attention = snapshot.get("attention") or []
    lines = [_company_md(company), "", "### Needs attention"]
    if attention:
        for item in attention[:10]:
            lines.append(
                f"- **{item['title']}** · {item['reason']} · {item['status']}"
            )
    else:
        lines.append("- Nothing blocked or overdue.")
    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=_json(snapshot),
    )


def _action_add_org_unit(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Add an org unit."""
    payload = {
        key: action_args.get(key)
        for key in (
            "name",
            "kind",
            "description",
            "parent_id",
            "lead_kind",
            "lead_name",
            "responsibilities",
            "color",
            "icon",
            "order",
        )
        if action_args.get(key) is not None
    }
    if not payload.get("name"):
        return _error("name is required for action='add_org_unit'")
    company = _manager().add_org_unit(company_id, payload, actor=_actor(session))
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_update_org_unit(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Update an org unit."""
    unit_id = action_args.get("unit_id") or action_args.get("org_unit_id")
    if not unit_id:
        return _error("unit_id is required for action='update_org_unit'")
    patch = {
        key: action_args.get(key)
        for key in (
            "name",
            "kind",
            "description",
            "parent_id",
            "lead_kind",
            "lead_name",
            "responsibilities",
            "color",
            "icon",
            "order",
        )
        if action_args.get(key) is not None
    }
    company = _manager().update_org_unit(company_id, unit_id, patch, actor=_actor(session))
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_delete_org_unit(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Delete an org unit."""
    unit_id = action_args.get("unit_id") or action_args.get("org_unit_id")
    if not unit_id:
        return _error("unit_id is required for action='delete_org_unit'")
    company = _manager().delete_org_unit(company_id, unit_id, actor=_actor(session))
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_add_team(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Add a team."""
    lead_kind, lead_name = _lead_from_args(
        action_args.get("lead"),
        action_args.get("lead_kind"),
        action_args.get("lead_name"),
    )
    payload = {
        "name": action_args.get("name") or action_args.get("team_name"),
        "description": action_args.get("description") or "",
        "purpose": action_args.get("purpose") or action_args.get("goal") or "",
        "org_unit_id": action_args.get("org_unit_id") or "",
        "lead_kind": lead_kind,
        "lead_name": lead_name,
        "members": action_args.get("members") or [],
        "project_ids": action_args.get("project_ids") or [],
        "autonomy": action_args.get("team_autonomy") or action_args.get("autonomy") or "supervised",
        "tools": action_args.get("tools") or [],
        "tags": action_args.get("tags") or [],
        "color": action_args.get("color") or "#6366f1",
        "icon": action_args.get("icon") or "fa-solid fa-people-group",
    }
    if not payload["name"]:
        return _error("name is required for action='add_team'")
    company = _manager().add_team(company_id, payload, actor=_actor(session))
    team = company.team_by_name(payload["name"])
    return ToolResponse(
        user_response=_company_md(company)
        + (f"\n\nTeam `{team.name}` has {team.human_count} human(s) and "
           f"{team.ai_count} AI profile(s)." if team else ""),
        llm_response=_json(company.model_dump()),
    )


def _action_update_team(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Update a team."""
    team_id = action_args.get("team_id")
    if not team_id:
        return _error("team_id is required for action='update_team'")
    lead_kind, lead_name = _lead_from_args(
        action_args.get("lead"),
        action_args.get("lead_kind"),
        action_args.get("lead_name"),
    )
    patch = {
        key: action_args.get(key)
        for key in (
            "name",
            "description",
            "purpose",
            "org_unit_id",
            "project_ids",
            "tools",
            "tags",
            "color",
            "icon",
        )
        if action_args.get(key) is not None
    }
    if action_args.get("members") is not None:
        patch["members"] = action_args["members"]
    if lead_name:
        patch["lead_kind"] = lead_kind
        patch["lead_name"] = lead_name
    if action_args.get("team_autonomy") is not None:
        patch["autonomy"] = action_args["team_autonomy"]
    elif action_args.get("autonomy") is not None:
        patch["autonomy"] = action_args["autonomy"]
    company = _manager().update_team(company_id, team_id, patch, actor=_actor(session))
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_delete_team(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Delete a team."""
    team_id = action_args.get("team_id")
    if not team_id:
        return _error("team_id is required for action='delete_team'")
    company = _manager().delete_team(
        company_id,
        team_id,
        actor=_actor(session),
        force=bool(action_args.get("force")),
    )
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_add_team_members(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Add members to a team."""
    team_id = action_args.get("team_id")
    if not team_id:
        return _error("team_id is required for action='add_team_members'")
    members = action_args.get("members") or []
    if not members and action_args.get("member"):
        members = [action_args["member"]]
    if not members:
        return _error("members is required for action='add_team_members'")
    company = _manager().add_team_members(
        company_id, team_id, members, actor=_actor(session)
    )
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_remove_team_members(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Remove members from a team."""
    team_id = action_args.get("team_id")
    if not team_id:
        return _error("team_id is required for action='remove_team_members'")
    members = action_args.get("members") or []
    if not members and action_args.get("member"):
        members = [action_args["member"]]
    if not members:
        return _error("members is required for action='remove_team_members'")
    company = _manager().remove_team_members(
        company_id, team_id, members, actor=_actor(session)
    )
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_set_team_lead(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Change a team lead."""
    team_id = action_args.get("team_id")
    if not team_id:
        return _error("team_id is required for action='set_team_lead'")
    lead_kind, lead_name = _lead_from_args(
        action_args.get("lead"),
        action_args.get("lead_kind"),
        action_args.get("lead_name"),
    )
    if not lead_name:
        return _error("lead (or lead_name) is required for action='set_team_lead'")
    company = _manager().set_team_lead(
        company_id, team_id, lead_kind, lead_name, actor=_actor(session)
    )
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_link_project(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Link a project to the company."""
    project_id = action_args.get("project_id")
    if not project_id:
        return _error("project_id is required for action='link_project'")
    company = _manager().link_project(
        company_id,
        project_id,
        actor=_actor(session),
        name=action_args.get("project_name") or action_args.get("name") or "",
        role=action_args.get("role") or "",
        description=action_args.get("description") or "",
        team_id=action_args.get("team_id") or "",
        priority=action_args.get("priority") or "medium",
        budget_cxjcoins=action_args.get("budget_cxjcoins") or 0.0,
    )
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_unlink_project(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Unlink a project from the company."""
    project_id = action_args.get("project_id")
    if not project_id:
        return _error("project_id is required for action='unlink_project'")
    company = _manager().unlink_project(
        company_id,
        project_id,
        actor=_actor(session),
        force=bool(action_args.get("force")),
    )
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_add_mission(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Add a mission."""
    payload = {
        key: action_args.get(key)
        for key in (
            "title",
            "objective",
            "acceptance",
            "priority",
            "team_id",
            "project_id",
            "owner_kind",
            "owner_name",
            "dispatch_mode",
            "budget_cxjcoins",
            "due_date",
            "tags",
        )
        if action_args.get(key) is not None
    }
    if not payload.get("title"):
        return _error("title is required for action='add_mission'")
    if action_args.get("status"):
        payload["status"] = action_args["status"]
    company = _manager().add_mission(company_id, payload, actor=_actor(session))
    mission = company.missions[-1]
    return ToolResponse(
        user_response=_mission_md(company, mission),
        llm_response=_json(mission.model_dump()),
    )


def _action_update_mission(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Update a mission."""
    mission_id = action_args.get("mission_id")
    if not mission_id:
        return _error("mission_id is required for action='update_mission'")
    patch = {
        key: action_args.get(key)
        for key in (
            "title",
            "objective",
            "acceptance",
            "priority",
            "team_id",
            "project_id",
            "owner_kind",
            "owner_name",
            "dispatch_mode",
            "budget_cxjcoins",
            "due_date",
            "tags",
            "status",
        )
        if action_args.get(key) is not None
    }
    company = _manager().update_mission(
        company_id, mission_id, patch, actor=_actor(session)
    )
    mission = company.get_mission(mission_id)
    return ToolResponse(
        user_response=_mission_md(company, mission) if mission else _company_md(company),
        llm_response=_json(mission.model_dump() if mission else company.model_dump()),
    )


def _action_delete_mission(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Delete a mission."""
    mission_id = action_args.get("mission_id")
    if not mission_id:
        return _error("mission_id is required for action='delete_mission'")
    company = _manager().delete_mission(
        company_id,
        mission_id,
        actor=_actor(session),
        force=bool(action_args.get("force")),
    )
    return ToolResponse(
        user_response=_company_md(company),
        llm_response=_json(company.model_dump()),
    )


def _action_dispatch_mission(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Dispatch a mission to its project."""
    mission_id = action_args.get("mission_id")
    if not mission_id:
        return _error("mission_id is required for action='dispatch_mission'")
    company = _manager().dispatch_mission(
        company_id,
        mission_id,
        actor=_actor(session),
        force=bool(action_args.get("force")),
    )
    mission = company.get_mission(mission_id)
    return ToolResponse(
        user_response=_mission_md(company, mission) if mission else _company_md(company),
        llm_response=_json(mission.model_dump() if mission else company.model_dump()),
    )


def _action_accept_mission(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Accept a mission in review."""
    mission_id = action_args.get("mission_id")
    if not mission_id:
        return _error("mission_id is required for action='accept_mission'")
    company = _manager().accept_mission(
        company_id,
        mission_id,
        result=action_args.get("result") or "",
        actor=_actor(session),
    )
    mission = company.get_mission(mission_id)
    return ToolResponse(
        user_response=_mission_md(company, mission) if mission else _company_md(company),
        llm_response=_json(mission.model_dump() if mission else company.model_dump()),
    )


def _action_reject_mission(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Reject a mission in review."""
    mission_id = action_args.get("mission_id")
    if not mission_id:
        return _error("mission_id is required for action='reject_mission'")
    company = _manager().reject_mission(
        company_id,
        mission_id,
        reason=action_args.get("reason") or action_args.get("last_error") or "",
        actor=_actor(session),
    )
    mission = company.get_mission(mission_id)
    return ToolResponse(
        user_response=_mission_md(company, mission) if mission else _company_md(company),
        llm_response=_json(mission.model_dump() if mission else company.model_dump()),
    )


def _action_transition_mission(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Move a mission through the explicit status machine."""
    mission_id = action_args.get("mission_id")
    status = action_args.get("status")
    if not mission_id or not status:
        return _error("mission_id and status are required for action='transition_mission'")
    company = _manager().transition_mission(
        company_id,
        mission_id,
        status,
        actor=_actor(session),
        force=bool(action_args.get("force")),
    )
    mission = company.get_mission(mission_id)
    return ToolResponse(
        user_response=_mission_md(company, mission) if mission else _company_md(company),
        llm_response=_json(mission.model_dump() if mission else company.model_dump()),
    )


def _action_sync(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Mirror run statuses onto the missions."""
    result = _manager().sync_missions(company_id, actor=_actor(session))
    return ToolResponse(
        user_response=(
            f"Synced {result['checked']} running mission(s); "
            f"{result['changed']} changed."
        ),
        llm_response=_json(result),
    )


def _action_configure_autonomy(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Configure the autopilot (enabling it requires confirm=true)."""
    patch = {
        key: action_args.get(key)
        for key in (
            "enabled",
            "level",
            "interval_minutes",
            "max_concurrent_missions",
            "max_missions_per_cycle",
            "daily_budget_cxjcoins",
            "require_human_acceptance",
        )
        if action_args.get(key) is not None
    }
    if not patch:
        return _error("nothing to configure: provide at least one autonomy field")
    enabling = patch.get("enabled") is True and patch.get("level") != "off"
    if enabling and not action_args.get("confirm"):
        return _error(
            "Enabling the autopilot requires confirm=true. It may dispatch "
            "missions and spend AI budget automatically."
        )
    company = _manager().update_autonomy(company_id, patch, actor=_actor(session))
    return ToolResponse(
        user_response=(
            f"Autopilot: {'on' if company.autonomy.enabled else 'off'} "
            f"({company.autonomy.level}, every {company.autonomy.interval_minutes} min)."
        ),
        llm_response=_json(company.autonomy.model_dump()),
    )


def _action_run_cycle(company_id: str, action_args: Dict[str, Any], session: Any = None) -> ToolResponse:
    """Run one autonomy cycle."""
    result = _manager().cycle(
        company_id,
        actor=_actor(session),
        force=bool(action_args.get("force", False)),
    )
    lines = [
        f"### Autopilot cycle: {result.get('status')}",
        result.get("summary") or result.get("message") or "",
    ]
    for item in result.get("dispatched") or []:
        lines.append(f"- dispatched **{item['title']}** (run `{item.get('run_id')}`)")
    for item in result.get("failed") or []:
        lines.append(f"- failed **{item['title']}**: {item['error']}")
    return ToolResponse(
        user_response="\n".join(line for line in lines if line),
        llm_response=_json(result),
    )


# ---------------------------------------------------------------------------
# Tool entry point
# ---------------------------------------------------------------------------


def company_management(
    action: str,
    company_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    mission: Optional[str] = None,
    vision: Optional[str] = None,
    values: Optional[List[str]] = None,
    website: Optional[str] = None,
    logo: Optional[str] = None,
    color: Optional[str] = None,
    status: Optional[str] = None,
    owner: Optional[str] = None,
    template: Optional[str] = None,
    project_ids: Optional[List[str]] = None,
    project_id: Optional[str] = None,
    project_name: Optional[str] = None,
    role: Optional[str] = None,
    team_id: Optional[str] = None,
    unit_id: Optional[str] = None,
    org_unit_id: Optional[str] = None,
    mission_id: Optional[str] = None,
    members: Optional[List[Any]] = None,
    member: Optional[str] = None,
    lead: Optional[str] = None,
    lead_kind: Optional[str] = None,
    lead_name: Optional[str] = None,
    kind: Optional[str] = None,
    purpose: Optional[str] = None,
    goal: Optional[str] = None,
    responsibilities: Optional[List[str]] = None,
    team_autonomy: Optional[str] = None,
    autonomy: Optional[str] = None,
    tools: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    title: Optional[str] = None,
    objective: Optional[str] = None,
    acceptance: Optional[str] = None,
    priority: Optional[str] = None,
    dispatch_mode: Optional[str] = None,
    budget_cxjcoins: Optional[float] = None,
    due_date: Optional[str] = None,
    result: Optional[str] = None,
    reason: Optional[str] = None,
    enabled: Optional[bool] = None,
    level: Optional[str] = None,
    interval_minutes: Optional[int] = None,
    max_concurrent_missions: Optional[int] = None,
    max_missions_per_cycle: Optional[int] = None,
    daily_budget_cxjcoins: Optional[float] = None,
    require_human_acceptance: Optional[bool] = None,
    confirm: Optional[bool] = None,
    force: Optional[bool] = None,
    journal_limit: Optional[int] = None,
    query: Optional[str] = None,
    **kwargs: Any,
) -> ToolResponse:
    """
    Operate a codx-junior company: organization, hybrid teams, projects and missions.

    A **company** is the top-level container above projects. It owns an org chart
    (departments/functions), hybrid teams made of human users **and** AI
    profiles, the projects those teams work on, and the missions being executed.
    Missions are dispatched to the linked project's durable orchestration
    runtime, so the AI team works on the real board and the result comes back
    for review.

    Actions:
        - ``list``: companies (optional ``query`` filter).
        - ``get``: one company document.
        - ``create``: create a company. ``template='saas'`` seeds a codx-junior
          cloud organization. ``project_ids`` links projects at creation.
        - ``update``: company-level fields (name, mission, vision, status...).
        - ``delete``: delete a company (requires ``confirm=true``).
        - ``references``: discovered projects, users and AI profiles.
        - ``snapshot``: full dashboard (counts, teams, projects, missions,
          attention, journal).
        - ``add_org_unit`` / ``update_org_unit`` / ``delete_org_unit``.
        - ``add_team`` / ``update_team`` / ``delete_team``.
        - ``add_team_members`` / ``remove_team_members`` / ``set_team_lead``.
        - ``link_project`` / ``unlink_project``.
        - ``add_mission`` / ``update_mission`` / ``delete_mission``.
        - ``dispatch_mission``: start a mission's orchestration run.
        - ``accept_mission`` / ``reject_mission`` / ``transition_mission``.
        - ``sync``: mirror run statuses onto the missions.
        - ``configure_autonomy``: enable/configure the autopilot (enabling
          requires ``confirm=true``).
        - ``run_cycle``: run one autonomy cycle now.

    Args:
        action: One of :data:`VALID_ACTIONS`.
        company_id: Target company id (or slug).
        name: Company/team/org unit name (depending on the action).
        description / mission / vision / values / website / logo / color /
            status / owner: Company fields.
        template: ``saas`` or ``blank`` on create.
        project_ids: Projects to link / team projects.
        project_id / project_name / role: Project linking fields.
        team_id / unit_id / org_unit_id / mission_id: Target ids.
        members: Team roster (names, ``kind:name`` or objects).
        member: Single member alias for add/remove.
        lead / lead_kind / lead_name: Team lead (``user:alice`` or profile).
        kind: Org unit kind (department/function/division).
        purpose / goal: Team purpose.
        responsibilities: Org unit responsibilities.
        team_autonomy / autonomy: Team autonomy level.
        tools / tags: Extra tools and tags.
        title / objective / acceptance / priority / dispatch_mode /
            budget_cxjcoins / due_date: Mission fields.
        result: Outcome on ``accept_mission``.
        reason: Feedback on ``reject_mission``.
        enabled / level / interval_minutes / max_concurrent_missions /
            max_missions_per_cycle / daily_budget_cxjcoins /
            require_human_acceptance: Autopilot fields.
        confirm: Required to delete a company or enable the autopilot.
        force: Bypass a guard (delete/transition/cycle).
        journal_limit: ``snapshot`` journal size.
        query: ``list`` filter.
        **kwargs: Injected by the agent runtime (``session``).

    Returns:
        :class:`ToolResponse` with the human-facing summary and the structured
        result for the model.

    Example:
        >>> company_management("create", name="codx-junior cloud",
        ...                    template="saas", project_ids=["proj_123"])
        >>> company_management("snapshot", company_id="cmp-...")
        >>> company_management("add_mission", company_id="cmp-...",
        ...                    title="Ship provisioning", team_id="team-...",
        ...                    project_id="proj_123", dispatch_mode="auto")
        >>> company_management("dispatch_mission", company_id="cmp-...",
        ...                    mission_id="msn-...")
    """
    session = kwargs.get("session")
    action_name = _resolve_action(action)
    if action_name is None:
        return _error(
            f"Invalid action '{action}'. Valid actions: {', '.join(VALID_ACTIONS)}"
        )

    # Gather every argument once; handlers pick what they need.
    args: Dict[str, Any] = {
        "company_id": company_id,
        "name": name,
        "description": description,
        "mission": mission,
        "vision": vision,
        "values": values,
        "website": website,
        "logo": logo,
        "color": color,
        "status": status,
        "owner": owner,
        "template": template,
        "project_ids": project_ids,
        "project_id": project_id,
        "project_name": project_name,
        "role": role,
        "team_id": team_id,
        "unit_id": unit_id,
        "org_unit_id": org_unit_id,
        "mission_id": mission_id,
        "members": members,
        "member": member,
        "lead": lead,
        "lead_kind": lead_kind,
        "lead_name": lead_name,
        "kind": kind,
        "purpose": purpose,
        "goal": goal,
        "responsibilities": responsibilities,
        "team_autonomy": team_autonomy,
        "autonomy": autonomy,
        "tools": tools,
        "tags": tags,
        "title": title,
        "objective": objective,
        "acceptance": acceptance,
        "priority": priority,
        "dispatch_mode": dispatch_mode,
        "budget_cxjcoins": budget_cxjcoins,
        "due_date": due_date,
        "result": result,
        "reason": reason,
        "enabled": enabled,
        "level": level,
        "interval_minutes": interval_minutes,
        "max_concurrent_missions": max_concurrent_missions,
        "max_missions_per_cycle": max_missions_per_cycle,
        "daily_budget_cxjcoins": daily_budget_cxjcoins,
        "require_human_acceptance": require_human_acceptance,
        "confirm": confirm,
        "force": force,
        "journal_limit": journal_limit,
        "query": query,
    }

    target = (company_id or "").strip()
    if not target and action_name not in ("list", "create", "references"):
        return _error(f"company_id is required for action='{action_name}'")

    try:
        if action_name == "list":
            return _action_list(query=query)
        if action_name == "references":
            return _action_references(args)
        if action_name == "create":
            return _action_create(args, session=session)
        if action_name == "get":
            return _action_get(target)
        if action_name == "update":
            return _action_update(target, args, session=session)
        if action_name == "delete":
            return _action_delete(target, args, session=session)
        if action_name == "snapshot":
            return _action_snapshot(target, args)
        if action_name == "add_org_unit":
            return _action_add_org_unit(target, args, session=session)
        if action_name == "update_org_unit":
            return _action_update_org_unit(target, args, session=session)
        if action_name == "delete_org_unit":
            return _action_delete_org_unit(target, args, session=session)
        if action_name == "add_team":
            return _action_add_team(target, args, session=session)
        if action_name == "update_team":
            return _action_update_team(target, args, session=session)
        if action_name == "delete_team":
            return _action_delete_team(target, args, session=session)
        if action_name == "add_team_members":
            return _action_add_team_members(target, args, session=session)
        if action_name == "remove_team_members":
            return _action_remove_team_members(target, args, session=session)
        if action_name == "set_team_lead":
            return _action_set_team_lead(target, args, session=session)
        if action_name == "link_project":
            return _action_link_project(target, args, session=session)
        if action_name == "unlink_project":
            return _action_unlink_project(target, args, session=session)
        if action_name == "add_mission":
            return _action_add_mission(target, args, session=session)
        if action_name == "update_mission":
            return _action_update_mission(target, args, session=session)
        if action_name == "delete_mission":
            return _action_delete_mission(target, args, session=session)
        if action_name == "dispatch_mission":
            return _action_dispatch_mission(target, args, session=session)
        if action_name == "accept_mission":
            return _action_accept_mission(target, args, session=session)
        if action_name == "reject_mission":
            return _action_reject_mission(target, args, session=session)
        if action_name == "transition_mission":
            return _action_transition_mission(target, args, session=session)
        if action_name == "sync":
            return _action_sync(target, args, session=session)
        if action_name == "configure_autonomy":
            return _action_configure_autonomy(target, args, session=session)
        if action_name == "run_cycle":
            return _action_run_cycle(target, args, session=session)
        return _error(f"Action '{action_name}' is not implemented")
    except (CompanyNotFound, CompanyConflict, CompanyValidationError) as ex:
        return _error(str(ex))
    except CompanyDispatchError as ex:
        return _error(f"Dispatch failed: {ex}")
    except Exception as ex:  # pragma: no cover - defensive
        logger.exception("company_management failed: %s", ex)
        return _error(f"Unexpected error: {ex}")


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------


COMPANY_MANAGEMENT_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "company_management",
        "description": (
            "Operate a codx-junior COMPANY: the top-level entity that owns an "
            "organization (departments/functions), hybrid teams of human users AND "
            "AI profiles, the projects those teams work on, and the missions being "
            "executed. Missions are dispatched to the linked project's durable "
            "orchestration runtime, so the AI team works on the real board and the "
            "result comes back for review. Use this tool to run a company like "
            "'codx-junior cloud': define the org, compose teams, link projects, "
            "create missions, dispatch them, accept/reject outcomes and enable the "
            "guard-railed autopilot. "
            "Create a company with template='saas' for a ready organization. "
            "Actions: list, get, create, update, delete, references, snapshot, "
            "add_org_unit, update_org_unit, delete_org_unit, add_team, update_team, "
            "delete_team, add_team_members, remove_team_members, set_team_lead, "
            "link_project, unlink_project, add_mission, update_mission, "
            "delete_mission, dispatch_mission, accept_mission, reject_mission, "
            "transition_mission, sync, configure_autonomy, run_cycle. "
            "Enabling the autopilot and deleting a company require confirm=true."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": VALID_ACTIONS,
                    "description": "Operation to perform (see the description).",
                },
                "company_id": {
                    "type": "string",
                    "description": "Target company id (or slug). Required for every action except list/create/references.",
                },
                "name": {
                    "type": "string",
                    "description": "Company name on create; team/org unit name on add/update.",
                },
                "description": {"type": "string", "description": "Free-form description."},
                "mission": {"type": "string", "description": "Company mission statement."},
                "vision": {"type": "string", "description": "Company vision statement."},
                "values": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Company operating values.",
                },
                "website": {"type": "string", "description": "Company website."},
                "logo": {"type": "string", "description": "Company logo URL."},
                "color": {"type": "string", "description": "UI accent colour (hex)."},
                "status": {
                    "type": "string",
                    "description": "Company status (active/paused/archived) or mission status on update_mission.",
                },
                "owner": {"type": "string", "description": "Company owner username."},
                "template": {
                    "type": "string",
                    "enum": ["blank", "saas"],
                    "description": "Starter organization for create. 'saas' seeds a codx-junior cloud org.",
                },
                "project_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Projects to link on create, or the projects of a team.",
                },
                "project_id": {"type": "string", "description": "Project id for link/unlink/mission."},
                "project_name": {"type": "string", "description": "Display name when linking a project."},
                "role": {"type": "string", "description": "Role of the project inside the company."},
                "team_id": {"type": "string", "description": "Team id."},
                "unit_id": {"type": "string", "description": "Org unit id."},
                "org_unit_id": {
                    "type": "string",
                    "description": "Owning org unit id for a team (and alias of unit_id).",
                },
                "mission_id": {"type": "string", "description": "Mission id."},
                "members": {
                    "type": "array",
                    "description": (
                        "Team roster: names ('analyst'), references ('user:alice') "
                        "or objects {'kind':'user'|'profile','name':...,'role':...}."
                    ),
                    "items": {"type": ["string", "object"]},
                },
                "member": {"type": "string", "description": "Single member alias for add/remove."},
                "lead": {
                    "type": "string",
                    "description": "Team lead: 'profile:orchestrator' or 'user:alice'.",
                },
                "lead_kind": {"type": "string", "description": "Lead kind: user | profile."},
                "lead_name": {"type": "string", "description": "Lead username/profile name."},
                "kind": {
                    "type": "string",
                    "description": "Org unit kind: department | function | division.",
                },
                "purpose": {"type": "string", "description": "Team purpose/outcome."},
                "goal": {"type": "string", "description": "Alias of purpose."},
                "responsibilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Org unit responsibilities.",
                },
                "team_autonomy": {
                    "type": "string",
                    "description": "Team autonomy: manual | supervised | autonomous.",
                },
                "autonomy": {
                    "type": "string",
                    "description": "Alias of team_autonomy on team actions.",
                },
                "tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Extra tool names granted to a team.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Discovery tags.",
                },
                "title": {"type": "string", "description": "Mission title."},
                "objective": {"type": "string", "description": "Mission objective."},
                "acceptance": {"type": "string", "description": "Mission acceptance criteria."},
                "priority": {
                    "type": "string",
                    "enum": list(MISSION_PRIORITIES),
                    "description": "Priority for a mission or project.",
                },
                "dispatch_mode": {
                    "type": "string",
                    "enum": ["manual", "auto"],
                    "description": "Who may dispatch a mission: manual (human) or auto (autopilot).",
                },
                "budget_cxjcoins": {"type": "number", "description": "AI budget in cxjcoins."},
                "due_date": {"type": "string", "description": "Mission due date (ISO)."},
                "result": {"type": "string", "description": "Outcome summary when accepting a mission."},
                "reason": {"type": "string", "description": "Why a mission is rejected."},
                "enabled": {"type": "boolean", "description": "Enable/disable the autopilot."},
                "level": {
                    "type": "string",
                    "enum": ["off", "supervised", "autonomous"],
                    "description": "Autopilot level.",
                },
                "interval_minutes": {
                    "type": "integer",
                    "description": "Minutes between automatic cycles (5-1440).",
                },
                "max_concurrent_missions": {
                    "type": "integer",
                    "description": "Maximum missions running at once.",
                },
                "max_missions_per_cycle": {
                    "type": "integer",
                    "description": "Missions dispatched by one cycle.",
                },
                "daily_budget_cxjcoins": {
                    "type": "number",
                    "description": "Soft daily AI budget (0 = no limit).",
                },
                "require_human_acceptance": {
                    "type": "boolean",
                    "description": "Completed runs wait in review for a human.",
                },
                "confirm": {
                    "type": "boolean",
                    "description": "Required to delete a company or enable the autopilot.",
                },
                "force": {
                    "type": "boolean",
                    "description": "Bypass a guard (forced delete/transition/cycle).",
                },
                "journal_limit": {
                    "type": "integer",
                    "description": "Journal entries returned by snapshot.",
                },
                "query": {"type": "string", "description": "Case-insensitive filter for list."},
            },
            "required": ["action"],
        },
    },
}


# Made with ❤️ by codx-junior
