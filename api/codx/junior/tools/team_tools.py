"""
Team management tools for codx-junior.

A **team** groups profiles (the reusable AI roles) under a lead, so a whole
capability can be named, reused and inspected. Teams are stored as two files
inside ``.codx/teams/<Name>/``, mirroring ``.codx/profiles``::

    <Name>.team   # JSON definition (members, tools, model)
    <Name>.md     # Markdown charter (team instructions)

Two tools are exposed:

    - ``team_management``: CRUD plus roster management. Actions: ``list``,
      ``get``, ``create``, ``update``, ``delete``, ``list_members``,
      ``add_member``, ``update_member``, ``remove_member``, ``set_lead`` and
      ``reorder_members``.
    - ``team_context``: read-only. Resolves a team into its composed
      instructions (lead first, linked profiles expanded, tools union) so the
      model can act *as* the team.

Design notes:
    - **One tool, eleven actions.** Keeping the CRUD unified (like
      ``docker_container`` and ``profile_management``) avoids spending prompt
      tokens on eleven separate tool schemas.
    - **The model does the work.** The team shape, the roster operations and
      the serialization live in :mod:`codx.junior.model.team`; this module only
      validates project-wide concerns (profile existence, tool registry, team
      name) and formats the response. The tool schema is generated from the
      model, so it cannot drift from it.
    - **Teams reference profiles, they never copy them.** The composition is
      resolved from ``ProfileManager`` on demand, so a team cannot drift from
      the profiles it composes.
    - **Writes are validated, never guessed.** Team name, lead, members and
      tools are checked before touching disk: a typo cannot silently produce a
      broken team.
    - **Membership has explicit verbs.** ``add_member`` is an upsert (kept for
      convenience), while ``update_member`` refuses to touch a profile that is
      not a member: a typo fails instead of growing the roster.
    - **No rename.** Renaming is ``create`` + ``delete`` so both files move
      together, and the folder name keeps matching the team name.

Made with ❤️ by codx-junior
"""

import json
import logging
import os
import re

from typing import Any, Dict, Iterable, List, Optional

from codx.junior.model.team import Team, TeamMember
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.settings import CODXJuniorSettings
from codx.junior.teams.team_manager import TeamManager
from .model import ToolResponse

# Configure logging
logger = logging.getLogger(__name__)

# Actions exposed by the tool
VALID_ACTIONS = [
    "list",
    "get",
    "create",
    "update",
    "delete",
    "list_members",
    "add_member",
    "update_member",
    "remove_member",
    "set_lead",
    "reorder_members",
]

# Team names double as @mentions (mention regex is ``@[a-zA-Z0-9\-\_\.]+``),
# so spaces and slashes are not allowed: such a name could not be referenced
# and could escape the teams folder.
TEAM_NAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_\-\.]*$"
MAX_TEAM_NAME_LENGTH = 64

# A team is injected as a whole into the context: past this size the roster
# stops being readable for the model.
MAX_MEMBERS = 12
MAX_CONTENT_WARNING_CHARS = 20000


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_team_manager(settings: CODXJuniorSettings) -> TeamManager:
    """
    Build a TeamManager for the project in context.

    Args:
        settings: Project settings.

    Returns:
        A TeamManager rooted at ``<project .codx>/teams``.
    """
    return TeamManager(settings=settings)


def _available_profile_names(settings: CODXJuniorSettings) -> List[str]:
    """
    Return the names of every profile visible from this project.

    Args:
        settings: Project settings.

    Returns:
        Sorted list of profile names (project, parent and built-in).
    """
    manager = ProfileManager(settings=settings)
    return sorted(
        {
            profile.name
            for profile in manager.list_all_profiles()
            if profile and profile.name
        }
    )


def _available_tool_names() -> List[str]:
    """
    Return the names of every tool registered in the runtime.

    Imported lazily: ``codx.junior.tools`` imports this module, so a top-level
    import would be circular.

    Returns:
        Sorted list of tool names.
    """
    from codx.junior.tools import TOOLS

    return sorted(tool["tool_json"]["function"]["name"] for tool in TOOLS)


def _relative_to_project(settings: CODXJuniorSettings, path: str) -> str:
    """
    Render a path relative to the project root when possible.

    Args:
        settings: Project settings.
        path: Absolute or relative path.

    Returns:
        The path relative to the project root, or the original path.
    """
    project_path = getattr(settings, "abs_project_path", None)
    if project_path and path.startswith(project_path):
        return os.path.relpath(path, project_path)
    return path


def _cell(value: Any) -> str:
    """
    Sanitize a value for a Markdown table cell.

    Args:
        value: Any value.

    Returns:
        Single-line text without pipe characters.
    """
    text = str(value if value is not None else "").replace("\n", " ").strip()
    return text.replace("|", "/") or "-"


def _format_teams_table(teams: List[Team]) -> str:
    """
    Render a Markdown table summarising a list of teams.

    Args:
        teams: Teams to render.

    Returns:
        Markdown table with the fields needed to choose a team.
    """
    lines = [
        f"> {len(teams)} team(s)",
        "",
        "**Name** | **Lead** | **Members** | **Tools** | **Goal**",
        "---|---|---|---|---",
    ]
    for team in teams:
        lead = f"@{team.lead}" if team.lead else "-"
        members = ", ".join(f"@{name}" for name in team.profile_names) or "-"
        lines.append(
            f"`{team.name}` | {_cell(lead)} | {_cell(members)} | "
            f"{len(team.tools or [])} | {_cell(team.goal or team.description)}"
        )
    return "\n".join(lines)


def _format_roster_table(
    team: Team,
    members: List[TeamMember],
    missing: Optional[List[str]] = None,
) -> str:
    """
    Render the roster of a team as a Markdown table.

    The rows follow the composition order (lead first, then ``order``), so the
    table reads in the same sequence the model receives.

    Args:
        team: Team that owns the roster.
        members: Ordered members (see ``Team.ordered_members``).
        missing: Member profiles that no longer exist.

    Returns:
        Markdown roster table.
    """
    missing = missing or []
    lines = [
        f"> {len(members)} member(s) — lead: "
        f"{f'@{team.lead}' if team.lead else 'none'}",
        "",
        "**#** | **Profile** | **Role** | **Responsibility** | **Lead** | **Exists**",
        "---|---|---|---|---|---",
    ]
    for index, member in enumerate(members):
        is_lead = "✓" if team.lead and member.profile == team.lead else "-"
        exists = "✗" if member.profile in missing else "✓"
        lines.append(
            f"{index + 1} | `@{member.profile}` | {_cell(member.role)} | "
            f"{_cell(member.responsibility)} | {is_lead} | {exists}"
        )
    return "\n".join(lines)


def _resolved_summary(
    settings: CODXJuniorSettings, resolved: Dict[str, Any]
) -> str:
    """
    Render the resolved composition of a team as Markdown.

    Args:
        settings: Project settings.
        resolved: Result of ``TeamManager.resolve_team``.

    Returns:
        Markdown summary of the resolved profiles, tools and problems.
    """
    profiles = resolved.get("profiles") or []
    lines = [
        "",
        "**Resolved composition**",
        "",
        f"- Profiles: {', '.join(f'`{name}`' for name in profiles) or 'none'}",
        f"- Tools: {', '.join(f'`{tool}`' for tool in resolved.get('tools') or []) or 'none'}",
        f"- Model: `{resolved.get('model') or 'project default'}` | "
        f"knowledge: `{resolved.get('use_knowledge')}`",
    ]
    missing = resolved.get("missing_profiles") or []
    if missing:
        lines.extend([
            "",
            f"> ⚠️ Missing profile(s): {', '.join(f'`{name}`' for name in missing)}. "
            "Fix the roster with action='remove_member' or create the profile first.",
        ])
    return "\n".join(lines)


def _default_charter(team: Team) -> str:
    """
    Build a minimal charter when the caller does not provide one.

    A team without instructions leaves the roster ambiguous ("who does what?"),
    so a deterministic skeleton is generated from the team itself instead of
    blocking the creation.

    Args:
        team: The team being created.

    Returns:
        Markdown charter.
    """
    lines = [f"# {team.name} team", ""]
    if team.goal:
        lines.extend([f"**Goal:** {team.goal}", ""])
    if team.description:
        lines.extend([f"**When to use it:** {team.description}", ""])

    lines.extend(["## How we work"])
    if team.lead:
        lines.append(
            f"1. **@{team.lead}** coordinates: splits the request, assigns it to "
            "the members below and consolidates the final answer."
        )
        lines.append("2. Each member works only inside its responsibility.")
        lines.append(
            "3. The lead reviews the result before replying; conflicting answers "
            "are resolved explicitly, not silently."
        )
    else:
        lines.append("1. Members work only inside their responsibility.")
        lines.append("2. Conflicts are resolved explicitly, not silently.")
    lines.append("")

    members = team.profile_names
    if members:
        lines.extend(["## Responsibilities", ""])
        for profile in members:
            member = team.member(profile)
            role = f" ({member.role})" if member and member.role else ""
            responsibility = (
                f" — {member.responsibility}"
                if member and member.responsibility else ""
            )
            lines.append(f"- **@{profile}**{role}{responsibility}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_team_name(name: str) -> str:
    """
    Validate a team name (folder name + @mention).

    Args:
        name: Candidate team name.

    Returns:
        The stripped, validated name.

    Raises:
        ValueError: If the name is empty, too long, not mention-safe or
            contains path separators.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("team_name is required")
    if len(name) > MAX_TEAM_NAME_LENGTH:
        raise ValueError(
            f"team_name must be at most {MAX_TEAM_NAME_LENGTH} characters "
            f"(got {len(name)})"
        )
    if os.sep in name or (os.altsep and os.altsep in name) or ".." in name:
        raise ValueError(f"team_name cannot contain path separators: {name!r}")
    if not re.match(TEAM_NAME_PATTERN, name):
        raise ValueError(
            f"Invalid team_name {name!r}. Use letters, digits, '_', '-' and '.' "
            "only (the name is also the @mention and the folder name)."
        )
    return name


def _validate_profiles(
    settings: CODXJuniorSettings, names: Iterable[str]
) -> None:
    """
    Validate that the referenced profiles exist.

    Args:
        settings: Project settings.
        names: Profile names to check.

    Raises:
        ValueError: If any profile does not exist.
    """
    available = _available_profile_names(settings)
    unknown = [name for name in names if name and name not in available]
    if unknown:
        raise ValueError(
            f"Unknown profile(s) {unknown}. Available profiles: "
            f"{', '.join(available) or 'none'}"
        )


def _validate_tools(tools: Iterable[str]) -> None:
    """
    Validate the tool names granted to a team.

    Args:
        tools: Tool names as declared in the tool registry.

    Raises:
        ValueError: If any tool name is unknown.
    """
    available = _available_tool_names()
    unknown = [tool for tool in tools if tool and tool not in available]
    if unknown:
        raise ValueError(
            f"Unknown tool(s) {unknown}. Available tools: {', '.join(available)}"
        )


def _validate_content(content: Optional[str]) -> List[str]:
    """
    Validate the Markdown charter of a team.

    Args:
        content: Proposed charter.

    Returns:
        Warnings about the charter size.
    """
    if content and len(content) > MAX_CONTENT_WARNING_CHARS:
        return [
            f"content has {len(content)} characters; the whole team is composed "
            "into the context when it is used. Consider trimming it."
        ]
    return []


def _validate_roster(members: List[TeamMember]) -> List[str]:
    """
    Validate the size of a roster.

    Args:
        members: Team members.

    Returns:
        Warnings about an empty or oversized roster.
    """
    if not members:
        return [
            "The team has no members: add at least one profile with "
            "action='add_member' before using it."
        ]
    if len(members) > MAX_MEMBERS:
        return [
            f"The team has {len(members)} members (recommended maximum "
            f"{MAX_MEMBERS}): every member is composed into the context."
        ]
    return []


def _validate_team(settings: CODXJuniorSettings, team: Team) -> List[str]:
    """
    Validate everything a team references before it is written.

    Args:
        settings: Project settings.
        team: Team about to be saved (the lead is already in the roster).

    Returns:
        Non-fatal warnings.

    Raises:
        ValueError: If a referenced profile or tool does not exist.
    """
    _validate_profiles(settings, team.profile_names)
    _validate_tools(team.tools or [])

    warnings: List[str] = []
    warnings.extend(_validate_roster(team.members or []))
    warnings.extend(_validate_content(team.content))
    if not team.description:
        warnings.append(
            "description is empty: nothing will explain when to use this team."
        )
    return warnings


def _resolve_target_name(team_name: Optional[str], name: Optional[str]) -> str:
    """
    Resolve the team a write targets, rejecting contradictory arguments.

    ``team_name`` identifies the team being read/updated/deleted while ``name``
    is the field value of the definition; both are accepted so the model does
    not have to guess which one to use.

    Args:
        team_name: Explicit target team name.
        name: Team name field.

    Returns:
        The validated team name.

    Raises:
        ValueError: If both are provided and differ.
    """
    if team_name and name and team_name.strip() != name.strip():
        raise ValueError(
            f"Conflicting names: team_name={team_name!r} but name={name!r}"
        )
    return _validate_team_name(team_name or name or "")


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def _action_list(
    manager: TeamManager,
    query: Optional[str] = None,
) -> ToolResponse:
    """
    List the teams of the project.

    Args:
        manager: Project TeamManager.
        query: Case-insensitive substring matched against the name, the
            description, the goal, the tags and the member profile names.

    Returns:
        ToolResponse with the table (user) and the data (model).
    """
    teams = manager.list_teams()

    if query:
        needle = query.strip().lower()
        teams = [
            team for team in teams
            if needle in (team.name or "").lower()
            or needle in (team.description or "").lower()
            or needle in (team.goal or "").lower()
            or any(needle in tag.lower() for tag in (team.tags or []))
            or any(needle in name.lower() for name in team.profile_names)
        ]

    if not teams:
        return ToolResponse(
            user_response="✓ No teams found",
            llm_response=(
                "No teams found. Create one with action='create' "
                f"(they are stored in {_relative_to_project(manager.settings, manager.teams_path)}/)."
            ),
        )

    user_response = "\n".join([
        _format_teams_table(teams),
        "",
        "Editable teams live in "
        f"`{_relative_to_project(manager.settings, manager.teams_path)}/`.",
    ])
    llm_response = json.dumps(
        {
            "count": len(teams),
            "teams": [team.definition() for team in teams],
        },
        indent=2,
    )
    logger.info("team_management: listed %d team(s)", len(teams))
    return ToolResponse(user_response=user_response, llm_response=llm_response)


def _action_get(manager: TeamManager, name: str) -> ToolResponse:
    """
    Return the definition, the charter and the composition of one team.

    Args:
        manager: Project TeamManager.
        name: Exact team name.

    Returns:
        ToolResponse with the definition and the resolved composition.
    """
    team = manager.read_team(name)
    if not team:
        return ToolResponse(
            user_response=f"❌ Team `{name}` not found",
            llm_response=(
                f"Team '{name}' not found. Use action='list' to see the "
                "available teams."
            ),
        )

    resolved = manager.resolve_team(team, include_content=False)
    user_response = "\n".join([
        f"### Team `{team.name}`",
        f"> Definition: "
        f"`{_relative_to_project(manager.settings, manager.team_definition_path(team.name))}`",
        "",
        "```json",
        json.dumps(team.definition(), indent=2),
        "```",
        "",
        f"**Charter** "
        f"(`{_relative_to_project(manager.settings, manager.team_content_path(team.name))}`)",
        "",
        "```markdown",
        team.content or "",
        "```",
        _resolved_summary(manager.settings, resolved),
    ])
    llm_response = json.dumps(
        {**team.definition(include_content=True), "resolved": resolved},
        indent=2,
    )
    logger.info("team_management: read team '%s'", name)
    return ToolResponse(user_response=user_response, llm_response=llm_response)


def _action_list_members(manager: TeamManager, name: str) -> ToolResponse:
    """
    Return the roster of one team, without the definition or the charter.

    ``get`` dumps the whole definition plus the charter, which is noisy when
    the question is only "who is in this team and what do they own?". This
    action answers exactly that and flags members whose profile is missing.

    Args:
        manager: Project TeamManager.
        name: Exact team name.

    Returns:
        ToolResponse with the roster table (user) and the members (model).
    """
    team = manager.read_team(name)
    if not team:
        return ToolResponse(
            user_response=f"❌ Team `{name}` not found",
            llm_response=(
                f"Team '{name}' not found. Use action='list' to see the "
                "available teams."
            ),
        )

    members = team.ordered_members()
    resolved = manager.resolve_team(team, include_content=False)
    missing = resolved.get("missing_profiles") or []

    user_response = "\n".join([
        f"### Roster: `{team.name}`",
        f"> {team.description or 'No description'}",
        "",
        _format_roster_table(team, members, missing),
    ])

    llm_response = json.dumps(
        {
            "team": team.name,
            "lead": team.lead,
            "count": len(members),
            "members": [member.model_dump() for member in members],
            "profile_names": team.profile_names,
            "missing_profiles": missing,
            "available_actions": [
                "add_member", "update_member", "remove_member",
                "set_lead", "reorder_members",
            ],
        },
        indent=2,
    )
    logger.info(
        "team_management: listed %d member(s) of team '%s'", len(members), name
    )
    return ToolResponse(user_response=user_response, llm_response=llm_response)


def _action_create(
    manager: TeamManager,
    name: str,
    description: Optional[str] = None,
    goal: Optional[str] = None,
    lead: Optional[str] = None,
    members: Optional[List[Any]] = None,
    tools: Optional[List[str]] = None,
    llm_model: Optional[str] = None,
    use_knowledge: Optional[bool] = None,
    tags: Optional[List[str]] = None,
    avatar: Optional[str] = None,
    content: Optional[str] = None,
) -> ToolResponse:
    """
    Create a new team (both files) in the project.

    Args:
        manager: Project TeamManager.
        name: Team name (folder name, validated).
        description: When to use the team (1-3 sentences).
        goal: Outcome the team is responsible for.
        lead: Profile name of the team lead (added to the roster when missing).
        members: Roster, as profile names or member objects.
        tools: Extra tool names granted to the whole team.
        llm_model: Optional model override.
        use_knowledge: Whether knowledge context is injected.
        tags: Discovery tags.
        avatar: Optional avatar URL.
        content: Markdown charter. A default one is generated when omitted.

    Returns:
        ToolResponse describing the created team.

    Raises:
        ValueError: If the team already exists or a field is invalid.
    """
    existing = manager.read_team(name)
    if existing:
        raise ValueError(
            f"Team '{name}' already exists at "
            f"'{_relative_to_project(manager.settings, existing.path)}'. "
            "Use action='update' to modify it."
        )

    team = Team(
        name=name,
        description=description or "",
        goal=goal or "",
        lead=lead or "",
        members=Team.parse_members(members),
        tools=list(tools or []),
        llm_model=llm_model or "",
        use_knowledge=True if use_knowledge is None else use_knowledge,
        tags=list(tags or []),
        avatar=avatar or "",
        project_id=manager.settings.project_id,
    )
    team.ensure_lead_in_roster()
    team.content = content.strip() if content else _default_charter(team)

    warnings = _validate_team(manager.settings, team)

    manager.save_team(team)
    logger.info("team_management: created team '%s'", name)
    return _write_response(
        manager=manager,
        team=team,
        title=f"Team created: `{name}`",
        warnings=warnings,
    )


def _action_update(
    manager: TeamManager,
    name: str,
    description: Optional[str] = None,
    goal: Optional[str] = None,
    lead: Optional[str] = None,
    members: Optional[List[Any]] = None,
    tools: Optional[List[str]] = None,
    llm_model: Optional[str] = None,
    use_knowledge: Optional[bool] = None,
    tags: Optional[List[str]] = None,
    avatar: Optional[str] = None,
    content: Optional[str] = None,
) -> ToolResponse:
    """
    Update an existing team, merging the provided fields.

    Fields left as ``None`` keep their current value, so a partial update never
    wipes the rest of the definition or the charter.

    Args:
        manager: Project TeamManager.
        name: Exact name of the team to update.
        description: New description.
        goal: New goal.
        lead: New lead profile (added to the roster when missing).
        members: New roster (replaces the list). Accepts names or objects.
        tools: New extra tool names (replaces the list).
        llm_model: New model override (``""`` inherits the default model).
        use_knowledge: New knowledge flag.
        tags: New tags (replaces the list).
        avatar: New avatar URL.
        content: New charter (replaces the whole ``.md`` file).

    Returns:
        ToolResponse describing the updated team.

    Raises:
        ValueError: If the team does not exist or a field is invalid.
    """
    existing = manager.read_team(name)
    if not existing:
        raise ValueError(
            f"Team '{name}' does not exist. Use action='create' to create it."
        )

    overrides: Dict[str, Any] = {}
    if description is not None:
        overrides["description"] = description
    if goal is not None:
        overrides["goal"] = goal
    if lead is not None:
        overrides["lead"] = lead.strip()
    if members is not None:
        overrides["members"] = members
    if tools is not None:
        overrides["tools"] = list(tools)
    if llm_model is not None:
        overrides["llm_model"] = llm_model
    if use_knowledge is not None:
        overrides["use_knowledge"] = use_knowledge
    if tags is not None:
        overrides["tags"] = list(tags)
    if avatar is not None:
        overrides["avatar"] = avatar
    if content is not None:
        overrides["content"] = content

    if not overrides:
        raise ValueError(
            "Nothing to update: provide at least one field (description, goal, "
            "lead, members, tools, tags, content, ...)"
        )

    # Rebuild the team from its stored definition so the model validators run
    # on the merged result (a plain model_copy would skip them).
    team = Team(**{**existing.model_dump(), **overrides})
    team.name = name

    warnings: List[str] = []
    if team.ensure_lead_in_roster():
        overrides["members"] = team.members
        warnings.append(
            f"@{team.lead} was added to the roster because it is the team lead."
        )
    warnings.extend(_validate_team(manager.settings, team))

    manager.save_team(team)

    logger.info(
        "team_management: updated team '%s' (fields=%s)",
        name,
        ", ".join(sorted(overrides.keys())),
    )
    return _write_response(
        manager=manager,
        team=team,
        title=f"Team updated: `{name}`",
        warnings=warnings,
        changed_fields=sorted(overrides.keys()),
    )


def _action_delete(manager: TeamManager, name: str) -> ToolResponse:
    """
    Delete a team (its folder and both files).

    Args:
        manager: Project TeamManager.
        name: Exact name of the team to delete.

    Returns:
        ToolResponse confirming the deletion.

    Raises:
        ValueError: If the team does not exist.
    """
    existing = manager.read_team(name)
    if not existing:
        raise ValueError(f"Team '{name}' does not exist in this project.")

    folder = _relative_to_project(manager.settings, manager.team_folder(name))
    members = existing.profile_names
    manager.delete_team(name)
    logger.info("team_management: deleted team '%s'", name)

    return ToolResponse(
        user_response="\n".join([
            f"### Team deleted: `{name}`",
            "",
            f"- Folder removed: `{folder}`",
            f"- Members released: "
            f"{', '.join(f'@{profile}' for profile in members) or 'none'}",
            "",
            "> The profiles themselves are untouched: a team only referenced them.",
        ]),
        llm_response=json.dumps(
            {
                "deleted": name,
                "folder": folder,
                "members": members,
            },
            indent=2,
        ),
    )


def _action_add_member(
    manager: TeamManager,
    name: str,
    profile: str,
    role: Optional[str] = None,
    responsibility: Optional[str] = None,
    order: Optional[int] = None,
) -> ToolResponse:
    """
    Add a profile to a team's roster (or update its role when already present).

    This is an **upsert** kept for convenience: when the exact role of an
    existing member must change, prefer ``update_member``, which fails loudly
    if the profile is not in the roster instead of silently adding it.

    Args:
        manager: Project TeamManager.
        name: Exact team name.
        profile: Profile name to add.
        role: Role inside the team.
        responsibility: One line describing what the member owns.
        order: Optional sort order (defaults to the end of the roster).

    Returns:
        ToolResponse describing the new roster.

    Raises:
        ValueError: If the team does not exist or the profile is unknown.
    """
    team = manager.read_team(name)
    if not team:
        raise ValueError(
            f"Team '{name}' does not exist. Use action='create' to create it."
        )

    profile = (profile or "").strip()
    _validate_profiles(manager.settings, [profile])

    action_label = team.upsert_member(
        profile=profile,
        role=role,
        responsibility=responsibility,
        order=order,
    )
    manager.save_team(team)

    warnings = _validate_roster(team.members or [])
    if not team.lead:
        warnings.append("The team has no lead.")

    logger.info(
        "team_management: %s member '%s' in team '%s'", action_label, profile, name
    )
    return _write_response(
        manager=manager,
        team=team,
        title=f"Member {action_label}: `@{profile}` → `{name}`",
        warnings=warnings,
        changed_fields=["members"],
    )


def _action_update_member(
    manager: TeamManager,
    name: str,
    profile: str,
    role: Optional[str] = None,
    responsibility: Optional[str] = None,
    order: Optional[int] = None,
) -> ToolResponse:
    """
    Update the role, responsibility or order of an existing team member.

    Unlike ``add_member``, this action refuses to create anything: a profile
    that is not in the roster is an error, so a typo surfaces instead of
    silently growing the team.

    Args:
        manager: Project TeamManager.
        name: Exact team name.
        profile: Profile name of the member to update.
        role: New role inside the team.
        responsibility: New one-line responsibility.
        order: New sort order in the roster.

    Returns:
        ToolResponse describing the resulting roster.

    Raises:
        ValueError: If the team does not exist, the profile is not a member or
            no field is provided.
    """
    team = manager.read_team(name)
    if not team:
        raise ValueError(
            f"Team '{name}' does not exist. Use action='create' to create it."
        )

    profile = (profile or "").strip()
    if not profile:
        raise ValueError("profile is required for action='update_member'")

    changed = team.update_member(
        profile=profile,
        role=role,
        responsibility=responsibility,
        order=order,
    )
    manager.save_team(team)

    logger.info(
        "team_management: updated member '%s' of team '%s' (fields=%s)",
        profile,
        name,
        ", ".join(changed),
    )
    return _write_response(
        manager=manager,
        team=team,
        title=f"Member updated: `@{profile}` in `{name}`",
        warnings=[],
        changed_fields=[f"members.{field}" for field in changed],
    )


def _action_remove_member(
    manager: TeamManager,
    name: str,
    profile: str,
) -> ToolResponse:
    """
    Remove a profile from a team's roster.

    Removing the lead clears the ``lead`` field and reports it: leaving a lead
    pointing at a profile that is no longer in the team would compose a roster
    the team does not own.

    Args:
        manager: Project TeamManager.
        name: Exact team name.
        profile: Profile name to remove.

    Returns:
        ToolResponse describing the new roster.

    Raises:
        ValueError: If the team does not exist or the profile is not a member.
    """
    team = manager.read_team(name)
    if not team:
        raise ValueError(f"Team '{name}' does not exist in this project.")

    profile = (profile or "").strip()
    lead_cleared = team.remove_member(profile)
    manager.save_team(team)

    warnings: List[str] = []
    if lead_cleared:
        warnings.append(
            f"@{profile} was the team lead: the lead is now empty. "
            "Set a new one with action='set_lead' (profile=...)."
        )

    logger.info(
        "team_management: removed member '%s' from team '%s'", profile, name
    )
    return _write_response(
        manager=manager,
        team=team,
        title=f"Member removed: `@{profile}` ← `{name}`",
        warnings=warnings,
        changed_fields=["members", "lead"] if lead_cleared else ["members"],
    )


def _action_set_lead(
    manager: TeamManager,
    name: str,
    profile: str,
) -> ToolResponse:
    """
    Set the lead of a team.

    The lead is always composed first, so changing it changes the order of the
    team instructions. A lead that is not in the roster is added (a lead
    outside the roster would coordinate a team it does not own), and the
    previous lead's generic ``lead`` role is cleared so the roster does not
    show two leads.

    Args:
        manager: Project TeamManager.
        name: Exact team name.
        profile: Profile name of the new lead.

    Returns:
        ToolResponse describing the resulting roster.

    Raises:
        ValueError: If the team does not exist or the profile is unknown.
    """
    team = manager.read_team(name)
    if not team:
        raise ValueError(
            f"Team '{name}' does not exist. Use action='create' to create it."
        )

    profile = (profile or "").strip()
    if not profile:
        raise ValueError("profile is required for action='set_lead'")
    _validate_profiles(manager.settings, [profile])

    result = team.set_lead(profile)
    if not result["changed"] and not result["added_to_roster"]:
        return _write_response(
            manager=manager,
            team=team,
            title=f"Lead unchanged: `@{profile}` is already the lead of `{name}`",
            warnings=[],
            changed_fields=[],
        )

    warnings: List[str] = []
    if result["added_to_roster"]:
        warnings.append(
            f"@{profile} was added to the roster because it is the new lead."
        )
    if result["cleared_role"]:
        warnings.append(
            f"@{result['previous']} is no longer the lead: its 'lead' role was cleared."
        )

    manager.save_team(team)

    logger.info("team_management: team '%s' lead is now '%s'", name, profile)
    return _write_response(
        manager=manager,
        team=team,
        title=(
            f"Lead changed: `@{result['previous'] or 'none'}` → `@{profile}` "
            f"(`{name}`)"
        ),
        warnings=warnings,
        changed_fields=["lead", "members"],
    )


def _action_reorder_members(
    manager: TeamManager,
    name: str,
    member_order: List[str],
) -> ToolResponse:
    """
    Reorder the roster of a team.

    The roster order drives the sequence of the composed instructions, after
    the lead. Members missing from ``member_order`` keep their previous
    relative order and are appended at the end, so a partial list never drops
    anyone.

    Args:
        manager: Project TeamManager.
        name: Exact team name.
        member_order: Member profile names in the desired order.

    Returns:
        ToolResponse describing the resulting roster.

    Raises:
        ValueError: If the team does not exist, the list is empty, contains
            duplicates or names a profile that is not a member.
    """
    team = manager.read_team(name)
    if not team:
        raise ValueError(f"Team '{name}' does not exist in this project.")

    if not [entry for entry in (member_order or []) if (entry or "").strip()]:
        raise ValueError(
            "member_order is required for action='reorder_members': pass the "
            "member profile names in the desired order"
        )

    appended = team.reorder_members(member_order)
    manager.save_team(team)

    logger.info(
        "team_management: reordered %d member(s) of team '%s'",
        len(member_order or []),
        name,
    )
    warnings: List[str] = []
    if appended:
        warnings.append(
            f"Member(s) not listed were appended at the end: "
            f"{', '.join(f'@{profile}' for profile in appended)}."
        )

    return _write_response(
        manager=manager,
        team=team,
        title=f"Roster reordered: `{name}`",
        warnings=warnings,
        changed_fields=["members.order"],
    )


def _write_response(
    manager: TeamManager,
    team: Team,
    title: str,
    warnings: Optional[List[str]] = None,
    changed_fields: Optional[List[str]] = None,
) -> ToolResponse:
    """
    Build the response shared by every write action.

    Args:
        manager: Project TeamManager.
        team: The persisted team.
        title: Heading of the user-facing block.
        warnings: Non-fatal problems found while validating.
        changed_fields: Fields modified (``None`` on create).

    Returns:
        ToolResponse with the saved paths and the resulting definition.
    """
    settings = manager.settings
    definition_path = _relative_to_project(
        settings, manager.team_definition_path(team.name)
    )
    content_path = _relative_to_project(
        settings, manager.team_content_path(team.name)
    )
    resolved = manager.resolve_team(team, include_content=False)

    members = ", ".join(
        f"@{member.profile}"
        + (f" ({member.role})" if member.role else "")
        for member in team.ordered_members()
    ) or "none"

    lines = [
        f"### {title}",
        "",
        f"- Definition: `{definition_path}`",
        f"- Charter: `{content_path}`",
        f"- Lead: {f'@{team.lead}' if team.lead else 'none'} | Members: {members}",
        f"- Tools: {', '.join(team.tools or []) or 'none'} | "
        f"Model: `{team.llm_model or 'project default'}`",
        f"- Profiles resolved: {len(resolved.get('profiles') or [])} "
        f"(missing: {len(resolved.get('missing_profiles') or [])})",
    ]
    if changed_fields:
        lines.append(f"- Changed: {', '.join(changed_fields)}")
    if warnings:
        lines.extend(["", "> ⚠️ " + "\n> ⚠️ ".join(warnings)])
    lines.extend([
        "",
        "Use `team_context` to compose the team instructions before running a task.",
    ])

    llm_response = json.dumps(
        {
            "saved": team.name,
            "definition_path": definition_path,
            "content_path": content_path,
            "changed_fields": changed_fields or [],
            "warnings": warnings or [],
            "team": team.definition(),
            "resolved": resolved,
        },
        indent=2,
    )
    return ToolResponse(user_response="\n".join(lines), llm_response=llm_response)


# ---------------------------------------------------------------------------
# Tool entry points
# ---------------------------------------------------------------------------


def team_management(
    action: str,
    team_name: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    goal: Optional[str] = None,
    lead: Optional[str] = None,
    members: Optional[List[Any]] = None,
    tools: Optional[List[str]] = None,
    llm_model: Optional[str] = None,
    use_knowledge: Optional[bool] = None,
    tags: Optional[List[str]] = None,
    avatar: Optional[str] = None,
    content: Optional[str] = None,
    profile: Optional[str] = None,
    role: Optional[str] = None,
    responsibility: Optional[str] = None,
    order: Optional[int] = None,
    member_order: Optional[List[str]] = None,
    query: Optional[str] = None,
    **kwargs,
) -> ToolResponse:
    """
    Unified CRUD tool for project teams and their roster.

    A team groups profiles under a lead and is stored as two files inside
    ``.codx/teams/<Name>/``: ``<Name>.team`` (JSON definition) and ``<Name>.md``
    (Markdown charter). Both files are written together by ``TeamManager``.

    The team structure (members with role/responsibility/order plus the lead)
    is the one declared by
    :class:`~codx.junior.model.team.Team`: this tool only orchestrates it.

    Team actions:
        - ``list``: teams of the project (optional ``query`` filter).
        - ``get``: definition, charter and resolved composition of one team.
        - ``create``: creates a new team. Fails if the name already exists.
        - ``update``: merges the provided fields into an existing team;
          omitted fields keep their value.
        - ``delete``: removes the team folder. The profiles are untouched.

    Roster actions:
        - ``list_members``: the roster only (who is in the team, their role,
          responsibility, who leads and whether the profile still exists).
        - ``add_member``: adds a profile to the roster (upsert: it also updates
          the role when the profile is already a member).
        - ``update_member``: edits role/responsibility/order of an existing
          member; fails when the profile is not in the roster.
        - ``remove_member``: removes a profile; clears ``lead`` when it was the
          lead of the team.
        - ``set_lead``: changes the team lead (adds it to the roster when it is
          not a member and clears the previous lead's ``lead`` role).
        - ``reorder_members``: sets the roster order in one call; members not
          listed are appended at the end.

    Args:
        action: One of :data:`VALID_ACTIONS`.
        team_name: Target team name. Required for every action except ``list``.
            Also accepted on ``create`` via ``name``.
        name: Team name field (alias of ``team_name``).
        description: When to use the team (1-3 sentences).
        goal: Outcome the team is responsible for.
        lead: Profile name of the team lead. Always kept in the roster.
        members: Roster as profile names (``["analyst", "software_developer"]``)
            or as objects (``[{"profile": "analyst", "role": "research"}]``).
            Replaces the whole roster on ``update``.
        tools: Extra tool names granted to the whole team, on top of each
            member's own tools.
        llm_model: Model override (empty inherits the project/default model).
        use_knowledge: Whether knowledge context is injected.
        tags: Discovery tags.
        avatar: Avatar URL.
        content: Markdown charter. On ``create`` a default charter is generated
            when omitted; on ``update`` it replaces the whole ``.md`` file.
        profile: ``add_member`` / ``update_member`` / ``remove_member`` /
            ``set_lead`` only. Profile name the action targets.
        role: ``add_member`` / ``update_member`` only. Role inside the team.
        responsibility: ``add_member`` / ``update_member`` only. What the
            member owns.
        order: ``add_member`` / ``update_member`` only. Sort order in the roster.
        member_order: ``reorder_members`` only. Member profile names in the
            desired order.
        query: ``list`` only. Case-insensitive filter on name, description,
            goal, tags and member profile names.
        **kwargs: Internal. Injected by the agent runtime: ``settings``.

    Returns:
        ToolResponse: ``user_response`` for the chat, ``llm_response`` with the
        resulting definition for the model.

    Raises:
        Exception: If the project settings are missing.

    Example:
        >>> team_management("list")
        # Lists every team of the project
        >>> team_management("get", team_name="BackendCrew")
        # Shows the definition, the charter and the resolved profiles
        >>> team_management(
        ...     "create",
        ...     team_name="BackendCrew",
        ...     description="Designs and implements backend features.",
        ...     goal="Ship reviewed backend code",
        ...     lead="software_developer",
        ...     members=["analyst", "software_developer"],
        ...     tags=["backend"],
        ... )
        # Creates .codx/teams/BackendCrew/BackendCrew.team + BackendCrew.md
        >>> team_management("list_members", team_name="BackendCrew")
        # Roster table: profile, role, responsibility, lead, exists
        >>> team_management("add_member", team_name="BackendCrew",
        ...                 profile="analyst", role="research")
        >>> team_management("update_member", team_name="BackendCrew",
        ...                 profile="analyst", responsibility="Owns requirements")
        >>> team_management("set_lead", team_name="BackendCrew", profile="analyst")
        >>> team_management("reorder_members", team_name="BackendCrew",
        ...                 member_order=["analyst", "software_developer"])
        >>> team_management("remove_member", team_name="BackendCrew", profile="analyst")
        >>> team_management("delete", team_name="BackendCrew")
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    if not settings:
        raise Exception("Invalid project settings")

    action = (action or "").strip().lower()
    if action not in VALID_ACTIONS:
        return ToolResponse(
            user_response=(
                f"❌ Invalid action `{action}`. Valid actions: "
                f"{', '.join(VALID_ACTIONS)}"
            ),
            llm_response=(
                f"Invalid action '{action}'. Valid actions: "
                f"{', '.join(VALID_ACTIONS)}"
            ),
        )

    manager = _get_team_manager(settings)

    try:
        if action == "list":
            return _action_list(manager=manager, query=query)

        if action == "get":
            return _action_get(
                manager=manager,
                name=_resolve_target_name(team_name=team_name, name=name),
            )

        if action == "list_members":
            return _action_list_members(
                manager=manager,
                name=_resolve_target_name(team_name=team_name, name=name),
            )

        if action == "create":
            return _action_create(
                manager=manager,
                name=_resolve_target_name(team_name=team_name, name=name),
                description=description,
                goal=goal,
                lead=lead,
                members=members,
                tools=tools,
                llm_model=llm_model,
                use_knowledge=use_knowledge,
                tags=tags,
                avatar=avatar,
                content=content,
            )

        if action == "update":
            return _action_update(
                manager=manager,
                name=_resolve_target_name(team_name=team_name, name=name),
                description=description,
                goal=goal,
                lead=lead,
                members=members,
                tools=tools,
                llm_model=llm_model,
                use_knowledge=use_knowledge,
                tags=tags,
                avatar=avatar,
                content=content,
            )

        if action == "add_member":
            if not profile:
                raise ValueError("profile is required for action='add_member'")
            return _action_add_member(
                manager=manager,
                name=_resolve_target_name(team_name=team_name, name=name),
                profile=profile,
                role=role,
                responsibility=responsibility,
                order=order,
            )

        if action == "update_member":
            if not profile:
                raise ValueError("profile is required for action='update_member'")
            return _action_update_member(
                manager=manager,
                name=_resolve_target_name(team_name=team_name, name=name),
                profile=profile,
                role=role,
                responsibility=responsibility,
                order=order,
            )

        if action == "remove_member":
            if not profile:
                raise ValueError("profile is required for action='remove_member'")
            return _action_remove_member(
                manager=manager,
                name=_resolve_target_name(team_name=team_name, name=name),
                profile=profile,
            )

        if action == "set_lead":
            if not profile:
                raise ValueError("profile is required for action='set_lead'")
            return _action_set_lead(
                manager=manager,
                name=_resolve_target_name(team_name=team_name, name=name),
                profile=profile,
            )

        if action == "reorder_members":
            return _action_reorder_members(
                manager=manager,
                name=_resolve_target_name(team_name=team_name, name=name),
                member_order=member_order or [],
            )

        return _action_delete(
            manager=manager,
            name=_resolve_target_name(team_name=team_name, name=name),
        )

    except ValueError as ex:
        # Validation errors are expected (typos, missing data): report them so
        # the model can correct the call instead of crashing the run.
        logger.warning("team_management(%s): %s", action, ex)
        return ToolResponse(
            user_response=f"❌ {ex}",
            llm_response=f"team_management action '{action}' failed: {ex}",
        )
    except Exception as ex:
        logger.exception("team_management(%s): unexpected error", action)
        return ToolResponse(
            user_response=f"❌ Error: {ex}",
            llm_response=f"team_management action '{action}' failed: {ex}",
        )


def team_context(
    team_name: Optional[str] = None,
    name: Optional[str] = None,
    include_content: bool = True,
    **kwargs,
) -> ToolResponse:
    """
    Compose a team into the instructions the model needs to act as that team.

    The composition follows the team order (lead first), expands the profiles
    linked by each member (``Profile.profiles``), deduplicates them by name and
    unions their tools. Read-only: nothing is written.

    Use it when a request must be handled *by the team* (plan, split, delegate)
    instead of by the current chat alone.

    Args:
        team_name: Exact team name.
        name: Team name (alias of ``team_name``).
        include_content: Include the composed Markdown instructions
            (default ``True``). Set it to ``False`` to inspect the roster and
            the tools without loading every profile.
        **kwargs: Internal. Injected by the agent runtime: ``settings``.

    Returns:
        ToolResponse: ``user_response`` with a summary for the chat,
        ``llm_response`` with the composed instructions for the model.

    Raises:
        Exception: If the project settings are missing.

    Example:
        >>> team_context(team_name="BackendCrew")
        # Returns the roster + the composed instructions of every member
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    if not settings:
        raise Exception("Invalid project settings")

    manager = _get_team_manager(settings)

    try:
        team_name = _resolve_target_name(team_name=team_name, name=name)
        team = manager.read_team(team_name)
        if not team:
            return ToolResponse(
                user_response=f"❌ Team `{team_name}` not found",
                llm_response=(
                    f"Team '{team_name}' not found. Use team_management "
                    "action='list' to see the available teams."
                ),
            )

        resolved = manager.resolve_team(team, include_content=include_content)
        instructions = resolved.get("instructions") or ""

        user_response = "\n".join([
            f"### Team context: `{team.name}`",
            "",
            f"**Members:** " + (", ".join(
                f"@{member.profile}" + (f" ({member.role})" if member.role else "")
                for member in team.ordered_members()
            ) or "none"),
            _resolved_summary(settings, resolved),
            "",
            "```markdown",
            instructions.strip() or "(no content)",
            "```",
        ])

        llm_response = instructions.strip() or (
            f"Team '{team.name}' has no composable content "
            f"(members: {', '.join(resolved.get('profiles') or []) or 'none'})."
        )

        logger.info(
            "team_context: composed team '%s' (%d profile(s))",
            team.name,
            len(resolved.get("profiles") or []),
        )
        return ToolResponse(user_response=user_response, llm_response=llm_response)

    except ValueError as ex:
        logger.warning("team_context: %s", ex)
        return ToolResponse(
            user_response=f"❌ {ex}",
            llm_response=f"team_context failed: {ex}",
        )
    except Exception as ex:
        logger.exception("team_context: unexpected error")
        return ToolResponse(
            user_response=f"❌ Error: {ex}",
            llm_response=f"team_context failed: {ex}",
        )


def _member_property(name: str, action_hint: str) -> Dict[str, Any]:
    """
    Build a member-operation parameter from the model field definition.

    Args:
        name: Member field name (``role``, ``responsibility``, ``order``).
        action_hint: Actions the parameter applies to.

    Returns:
        JSON-schema fragment with the action hint appended to the description.
    """
    schema = dict(TeamMember.tool_properties()[name])
    description = schema.get("description", name)
    schema["description"] = f"{description} ({action_hint})"
    return schema


# Tool JSON definitions
# Team fields come from the model (``Team.tool_properties`` / ``TeamMember``),
# so a field added there is exposed here without touching this file.
TEAM_MANAGEMENT_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "team_management",
        "description": (
            "Create, read, update and delete codx-junior teams and manage their members (roster). "
            "A team groups existing profiles under a lead and is stored as two files in the "
            "project's .codx/teams/<Name>/ folder: <Name>.team (JSON definition) and <Name>.md "
            "(Markdown charter); both are always written together. Teams only REFERENCE profiles, "
            "they never copy their instructions. "
            "A team is a lead plus a list of members, each member carrying its profile name, "
            "role, responsibility and order. "
            "Team actions: 'list', 'get', 'create', 'update', 'delete'. "
            "Member actions: 'list_members' (roster table), 'add_member' (add a profile, or update "
            "it when already present), 'update_member' (change role/responsibility/order of an "
            "existing member, fails if it is not one), 'remove_member', 'set_lead' (change the "
            "lead, adding it to the roster when needed) and 'reorder_members' (set the whole "
            "roster order in one call). "
            "Team name, lead, members and tools are validated before writing. "
            "Use team_context afterwards to compose the team instructions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": VALID_ACTIONS,
                    "description": (
                        "Operation:\n"
                        "  - 'list': list the project teams (read)\n"
                        "  - 'get': read one team's definition, charter and composition (read)\n"
                        "  - 'create': create a new team (fails if it exists)\n"
                        "  - 'update': merge changes into an existing team\n"
                        "  - 'delete': remove the team folder\n"
                        "  - 'list_members': show only the roster of a team (read)\n"
                        "  - 'add_member': add a profile to the roster (upsert: also updates its role)\n"
                        "  - 'update_member': edit role/responsibility/order of an existing member\n"
                        "  - 'remove_member': remove a profile from the roster\n"
                        "  - 'set_lead': change the team lead\n"
                        "  - 'reorder_members': set the roster order in one call"
                    )
                },
                "team_name": {
                    "type": "string",
                    "description": (
                        "Target team name. Required for every action except 'list'. Must be "
                        "mention-safe (letters, digits, '_', '-', '.'), because it is also the "
                        "folder name and the @mention."
                    )
                },
                "name": {
                    "type": "string",
                    "description": (
                        "Team name field (alias of team_name for create/update). Must match "
                        "team_name when both are provided."
                    )
                },
                **Team.tool_properties(),
                "profile": _member_property(
                    "profile",
                    "add_member / update_member / remove_member / set_lead",
                ),
                "role": _member_property("role", "add_member / update_member"),
                "responsibility": _member_property(
                    "responsibility", "add_member / update_member"
                ),
                "order": _member_property("order", "add_member / update_member"),
                "member_order": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "For 'reorder_members': member profile names in the desired order. "
                        "Members left out keep their relative order and are appended at the end."
                    )
                },
                "query": {
                    "type": "string",
                    "description": (
                        "For 'list': case-insensitive filter matched against the name, the "
                        "description, the goal, the tags and the member profile names."
                    )
                }
            },
            "required": ["action"]
        }
    }
}

TEAM_CONTEXT_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "team_context",
        "description": (
            "Compose a team into the instructions needed to act as that team. "
            "Resolves the roster in team order (lead first), expands the profiles each member "
            "links to, deduplicates them by name and unions their tools and model. "
            "Read-only: nothing is written. "
            "Use it when a request must be handled by the whole team (plan, split, delegate, "
            "review) instead of by the current chat alone."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "team_name": {
                    "type": "string",
                    "description": "Exact team name (see team_management action='list')."
                },
                "name": {
                    "type": "string",
                    "description": "Team name (alias of team_name)."
                },
                "include_content": {
                    "type": "boolean",
                    "description": (
                        "Include the composed Markdown instructions (default: true). Set it to "
                        "false to inspect only the roster and the tools."
                    ),
                    "default": True
                }
            },
            "required": []
        }
    }
}

# Made with ❤️ by codx-junior