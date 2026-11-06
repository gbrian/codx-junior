"""
Profile management tools (CRUD) for codx-junior.

This module exposes the :class:`~codx.junior.profiles.profile_manager.ProfileManager`
as tools so profiles can be listed, inspected, created, updated and deleted
from a chat without hand-editing JSON files.

Storage layout (one folder per profile, handled by ``ProfileManager``)::

    .codx/profiles/<Name>/<Name>.profile   # JSON definition
    .codx/profiles/<Name>/<Name>.md        # Markdown content (instructions)

Design notes:
    - **Two levels of granularity.** ``profile_management`` keeps the whole CRUD
      behind a single action-based tool (one small schema, handy for admin
      profiles), while ``list_profiles`` / ``get_profile`` / ``create_profile``
      / ``update_profile`` / ``delete_profile`` expose **one tool per action**.
      The runtime grants permissions by TOOL NAME (``Profile.tools`` is matched
      against the ``TOOLS`` registry), so per-action permissions require
      per-action tools: a profile can be allowed to list the profiles without
      being allowed to delete them.
    - **Three readings, three intents.** ``list`` returns the profile **JSON
      definition**, ``list_summary`` returns a **compact summary** (name,
      category, ``chat_mode``, tags, truncated description and flags) made to
      *choose* which profiles to use — typically to assign them to a task — and
      ``get`` returns one profile **with** its instructions.
    - **Listing never carries content.** ``list`` / ``list_summary`` /
      ``list_profiles`` / ``list_profiles_summary`` never include the Markdown
      instructions (``content``): they are injected into the system prompt and
      can be arbitrarily large. Reading them is an explicit operation: ``get`` /
      ``get_profile``. Listings expose ``has_content`` instead, so a caller knows
      which profiles have instructions before fetching them.
    - **Writes are validated, never guessed.** Profile name, category,
      ``file_match`` regex, linked profile names and tool names are checked
      before touching the disk, so a typo cannot silently corrupt a profile.
    - **Inherited profiles are read-only.** Profiles coming from parent
      projects or from the built-in set can be read, but never written: writes
      always target the active project's ``.codx/profiles`` folder.
    - **``update`` merges.** Only the provided fields are replaced, so a partial
      update never wipes the rest of the definition.
    - **No rename.** Renaming is ``create`` + ``delete`` so both files move
      together; the folder name must always match the profile name.

Made with ❤️ by codx-junior
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from codx.junior.model.profile import (
    Profile,
    ProfileApiSettings,
)
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.settings import CODXJuniorSettings
from .model import ToolResponse

# Configure logging
logger = logging.getLogger(__name__)

# Actions exposed by the tool
VALID_ACTIONS = ["list", "list_summary", "get", "create", "update", "delete"]

# Categories understood by the client (ProfileCard.vue paints one colour each).
# Kept explicit so a typo fails here instead of rendering an unstyled card.
PROFILE_CATEGORIES = ["assistant", "chat", "agent", "file", "project"]
DEFAULT_CATEGORY = "assistant"

# Profile names double as @mentions (the mention regex is
# ``@[a-zA-Z0-9\-\_\.]+``), so spaces and slashes are not allowed: a name with
# them would become impossible to reference and could escape the profiles path.
PROFILE_NAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_\-\.]*$"
MAX_PROFILE_NAME_LENGTH = 64

# ``file_match`` patterns matching every path hijack every chat with the
# profile's instructions: accepted only with a warning.
BROAD_FILE_MATCH_PATTERNS = (".*", "^.*$", ".+", "^.+$")

# Warn (do not fail) above this size: profile content is injected into the
# system prompt on every conversation where the profile is active.
MAX_CONTENT_WARNING_CHARS = 20000

# A summary listing is read to CHOOSE a profile: the description is truncated
# so a long one cannot turn the selection step into a full definition dump.
MAX_SUMMARY_DESCRIPTION_CHARS = 280


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_profile_manager(settings: CODXJuniorSettings) -> ProfileManager:
    """
    Build a ProfileManager for the project in context.

    Args:
        settings: Project settings.

    Returns:
        A ProfileManager rooted at ``<project .codx>/profiles``.
    """
    return ProfileManager(settings=settings)


def _project_profiles(manager: ProfileManager) -> List[Profile]:
    """
    Return the profiles owned by this project (the editable ones).

    Args:
        manager: Project ProfileManager.

    Returns:
        List of profiles stored in the project's ``.codx/profiles`` folder.
    """
    return [p for p in manager.list_profiles() if p and p.name]


def _find_project_profile(manager: ProfileManager, name: str) -> Optional[Profile]:
    """
    Find a project-owned profile by exact name.

    ``ProfileManager.read_profile`` also resolves built-in profiles (and the
    project is what CRUD must edit), so the project profile list is scanned
    instead of accepting an inherited/base profile.

    Args:
        manager: Project ProfileManager.
        name: Exact profile name.

    Returns:
        The profile, or ``None`` when it is not owned by this project.
    """
    return next((p for p in _project_profiles(manager) if p.name == name), None)


def _find_any_profile(manager: ProfileManager, name: str) -> Optional[Profile]:
    """
    Find any visible profile by exact name (project, parent or built-in).

    Args:
        manager: Project ProfileManager.
        name: Exact profile name.

    Returns:
        The profile, or ``None`` when no visible profile has that name.
    """
    return next((p for p in manager.list_all_profiles() if p and p.name == name), None)


def _profile_paths(manager: ProfileManager, name: str) -> Dict[str, str]:
    """
    Resolve the on-disk paths of the two files that make up a profile.

    Args:
        manager: Project ProfileManager.
        name: Profile name (also the folder name).

    Returns:
        Dict with ``folder``, ``profile`` and ``content`` paths.
    """
    folder = os.path.join(manager.profiles_path, name)
    return {
        "folder": folder,
        "profile": os.path.join(folder, f"{name}.profile"),
        "content": os.path.join(folder, f"{name}.md"),
    }


def _relative_to_project(settings: CODXJuniorSettings, path: str) -> str:
    """
    Render a path relative to the project root when possible.

    Relative paths are what the chat, the user and the knowledge base use, so
    they are preferred over absolute ones.

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


def _profile_definition(profile: Profile, include_content: bool = False) -> Dict[str, Any]:
    """
    Build the portable (editable) definition of a profile.

    Volatile, per-user fields (``user``, ``chat_id``, ``parsed_content``) are
    intentionally left out so the definition can be copied to another project.

    CONTRACT — **the Markdown content is opt-in**: ``content`` is only added
    when ``include_content=True``. Listings never request it (the instructions
    are injected into the system prompt and can be arbitrarily large), so
    ``has_content`` is exposed instead: it tells the caller whether there is
    something to fetch with ``get`` / ``get_profile``.

    Args:
        profile: The profile to describe.
        include_content: Include the Markdown content (``.md``) in the result.

    Returns:
        Dict ready to be JSON-serialised.
    """
    definition: Dict[str, Any] = {
        "name": profile.name,
        "description": profile.description,
        "category": profile.category,
        "file_match": profile.file_match,
        "profiles": profile.profiles or [],
        "tools": profile.tools or [],
        "tags": profile.tags or [],
        "llm_model": profile.llm_model or "",
        "use_knowledge": bool(profile.use_knowledge),
        "chat_mode": profile.chat_mode,
        "avatar": profile.avatar,
        "url": profile.url,
        "api_settings": (
            profile.api_settings.model_dump() if profile.api_settings else None
        ),
        "path": profile.path,
        "project_id": profile.project_id,
        "has_content": bool(profile.content),
    }
    if include_content:
        definition["content"] = profile.content or ""
    return definition


def _format_profiles_table(profiles: List[Profile]) -> str:
    """
    Render a Markdown table summarising a list of profiles.

    Args:
        profiles: Profiles to render.

    Returns:
        Markdown table with the fields needed to choose a profile, plus a
        ``Content`` column flagging which profiles have instructions to fetch
        (their text is never inlined here).
    """
    lines = [
        f"> {len(profiles)} profile(s)",
        "",
        "**Name** | **Category** | **file_match** | **Linked** | **Tools** | **Content** | **Tags**",
        "---|---|---|---|---|---|---",
    ]
    for profile in sorted(profiles, key=lambda p: (p.category or "", p.name)):
        file_match = f"`{profile.file_match}`" if profile.file_match else "-"
        linked = len(profile.profiles or [])
        tools = len(profile.tools or [])
        has_content = "yes" if profile.content else "-"
        tags = ", ".join(profile.tags or []) or "-"
        lines.append(
            f"`{profile.name}` | {profile.category or '-'} | {file_match} | "
            f"{linked} | {tools} | {has_content} | {tags}"
        )
    return "\n".join(lines)


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


def _filter_profiles(
    manager: ProfileManager,
    category: Optional[str] = None,
    query: Optional[str] = None,
    include_inherited: bool = False,
) -> Tuple[List[Profile], str]:
    """
    Select the profiles a listing must return.

    Shared by ``list`` and ``list_summary`` so both listings always agree on
    what "the profiles of the project" means.

    Args:
        manager: Project ProfileManager.
        category: Only profiles of this category.
        query: Case-insensitive substring matched against the name, the
            description and the tags.
        include_inherited: Include profiles inherited from parent projects and
            the built-in set (read-only).

    Returns:
        A ``(profiles, scope)`` tuple, ``scope`` being the label to report.
    """
    profiles = (
        [p for p in manager.list_all_profiles() if p and p.name]
        if include_inherited
        else _project_profiles(manager)
    )

    if category:
        wanted = category.strip().lower()
        profiles = [p for p in profiles if (p.category or "").lower() == wanted]

    if query:
        needle = query.strip().lower()
        profiles = [
            p for p in profiles
            if needle in (p.name or "").lower()
            or needle in (p.description or "").lower()
            or any(needle in tag.lower() for tag in (p.tags or []))
        ]

    return profiles, ("project + inherited" if include_inherited else "project")


def _profile_summary(profile: Profile, editable: bool = True) -> Dict[str, Any]:
    """
    Build the compact view of a profile used to CHOOSE it.

    Only the fields needed to answer "is this profile the right one for this
    task?" are kept, and the description is truncated: a summary listing must
    stay cheap. Full definitions come from ``list``; instructions from ``get``.

    Args:
        profile: The profile to summarise.
        editable: Whether the profile belongs to this project (writes allowed).

    Returns:
        Dict with the selection fields (empty optional fields are omitted).
    """
    description = (profile.description or "").strip()
    if len(description) > MAX_SUMMARY_DESCRIPTION_CHARS:
        description = description[:MAX_SUMMARY_DESCRIPTION_CHARS].rstrip() + "…"

    summary: Dict[str, Any] = {
        "name": profile.name,
        "category": profile.category or "",
        "description": description,
        "has_content": bool(profile.content),
        "editable": editable,
    }
    if profile.tags:
        summary["tags"] = list(profile.tags)
    if profile.chat_mode:
        summary["chat_mode"] = profile.chat_mode
    return summary


def _format_profiles_summary(
    profiles: List[Profile],
    editable_names: Optional[set] = None,
) -> str:
    """
    Render the compact summary table used to choose profiles.

    Args:
        profiles: Profiles to render.
        editable_names: Names of the profiles owned by this project.

    Returns:
        Markdown table with the selection fields only (no instructions).
    """
    editable_names = editable_names or set()
    lines = [
        f"> {len(profiles)} profile(s) — summary (no instructions)",
        "",
        "**Name** | **Category** | **Mode** | **Instructions** | **Editable** | **Tags** | **When to use**",
        "---|---|---|---|---|---|---",
    ]
    for profile in sorted(profiles, key=lambda p: (p.category or "", p.name)):
        lines.append(
            f"`{profile.name}` | {profile.category or '-'} | "
            f"{profile.chat_mode or '-'} | "
            f"{'yes' if profile.content else '-'} | "
            f"{'yes' if profile.name in editable_names else 'no'} | "
            f"{_cell(', '.join(profile.tags or []))} | "
            f"{_cell((profile.description or '').strip() or '-')}"
        )
    return "\n".join(lines)


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


def _notify(settings: CODXJuniorSettings, message: str) -> None:
    """
    Notify the client that the profiles changed (best effort).

    The UI keeps its own profile list, so a mutation must be announced or the
    editor keeps showing the previous state until it is reloaded manually.

    Args:
        settings: Project settings (the active session is injected on them).
        message: Human-readable notification text.
    """
    session = getattr(settings, "_active_session", None)
    event_manager = getattr(session, "event_manager", None)
    if not event_manager:
        logger.debug("profile_management: no active session to notify")
        return
    try:
        event_manager.send_notification(text=message)
    except Exception as ex:
        # Never fail a completed write because the notification failed.
        logger.warning("profile_management: could not send notification: %s", ex)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_profile_name(name: str) -> str:
    """
    Validate a profile name (folder name + @mention).

    Args:
        name: Candidate profile name.

    Returns:
        The stripped, validated name.

    Raises:
        ValueError: If the name is empty, too long, not mention-safe or
            contains path separators.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("profile_name is required")
    if len(name) > MAX_PROFILE_NAME_LENGTH:
        raise ValueError(
            f"profile_name must be at most {MAX_PROFILE_NAME_LENGTH} characters "
            f"(got {len(name)})"
        )
    if os.sep in name or (os.altsep and os.altsep in name) or ".." in name:
        raise ValueError(f"profile_name cannot contain path separators: {name!r}")
    if not re.match(PROFILE_NAME_PATTERN, name):
        raise ValueError(
            f"Invalid profile_name {name!r}. Use letters, digits, '_', '-' and "
            "'.' only (the name is also the @mention and the folder name)."
        )
    return name


def _validate_category(category: str) -> str:
    """
    Validate the profile category.

    Args:
        category: Category to validate.

    Returns:
        The validated category (the default when empty).

    Raises:
        ValueError: If the category is not one the client can render.
    """
    category = (category or DEFAULT_CATEGORY).strip().lower()
    if category not in PROFILE_CATEGORIES:
        raise ValueError(
            f"Invalid category {category!r}. Valid values: "
            f"{', '.join(PROFILE_CATEGORIES)}"
        )
    return category


def _validate_file_match(file_match: str) -> List[str]:
    """
    Validate the ``file_match`` regex and report risky patterns.

    Args:
        file_match: Regex matched against file paths (may be empty).

    Returns:
        Warnings about patterns that are too broad.

    Raises:
        ValueError: If the pattern does not compile.
    """
    if not file_match:
        return []
    try:
        re.compile(file_match)
    except re.error as ex:
        raise ValueError(f"Invalid file_match regex {file_match!r}: {ex}") from ex
    if file_match in BROAD_FILE_MATCH_PATTERNS:
        return [
            f"file_match {file_match!r} matches every path, so the profile will be "
            "applied to every chat. Use a narrower pattern."
        ]
    return []


def _validate_tools(tools: List[str]) -> None:
    """
    Validate the tool names granted to the profile.

    Args:
        tools: Tool names as declared in the tool registry.

    Raises:
        ValueError: If any tool name is unknown.
    """
    unknown = [tool for tool in tools if tool not in _available_tool_names()]
    if unknown:
        raise ValueError(
            f"Unknown tool(s) {unknown}. Available tools: "
            f"{', '.join(_available_tool_names())}"
        )


def _validate_linked_profiles(manager: ProfileManager, linked: List[str]) -> None:
    """
    Validate the names of the profiles linked from this profile.

    Args:
        manager: Project ProfileManager.
        linked: Names of the profiles to link.

    Raises:
        ValueError: If any linked profile does not exist.
    """
    available = sorted({p.name for p in manager.list_all_profiles() if p and p.name})
    unknown = [name for name in linked if name not in available]
    if unknown:
        raise ValueError(
            f"Unknown linked profile(s) {unknown}. Available profiles: "
            f"{', '.join(available)}"
        )


def _validate_content(content: Optional[str]) -> List[str]:
    """
    Validate the Markdown content of a profile.

    Args:
        content: Proposed content.

    Returns:
        Warnings about the content.

    Raises:
        ValueError: If the content is empty.
    """
    if content is None or not content.strip():
        raise ValueError(
            "content is required: it is the profile's instructions (.md file)"
        )
    if len(content) > MAX_CONTENT_WARNING_CHARS:
        return [
            f"content has {len(content)} characters; it is injected into every "
            "chat where the profile is active. Consider trimming it."
        ]
    return []


def _resolve_target_name(profile_name: Optional[str], name: Optional[str]) -> str:
    """
    Resolve the profile a write targets, rejecting contradictory arguments.

    ``profile_name`` identifies the profile being read/updated/deleted while
    ``name`` is the field value of the definition; both are accepted for the
    same purpose so the model does not have to guess which one to use.

    Args:
        profile_name: Explicit target profile name.
        name: Profile name field.

    Returns:
        The validated profile name.

    Raises:
        ValueError: If both are provided and differ.
    """
    if profile_name and name and profile_name.strip() != name.strip():
        raise ValueError(
            f"Conflicting names: profile_name={profile_name!r} but name={name!r}"
        )
    return _validate_profile_name(profile_name or name or "")


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def _action_list(
    manager: ProfileManager,
    category: Optional[str] = None,
    query: Optional[str] = None,
    include_inherited: bool = False,
) -> ToolResponse:
    """
    List profiles, optionally filtered.

    The result carries the profile **JSON definition only**: the Markdown
    instructions (``content``) are NEVER included here. Instructions are
    injected into the system prompt and can be arbitrarily large, so reading
    them is an explicit operation (:func:`_action_get` / ``get_profile``).
    ``has_content`` tells the caller whether there is something to fetch.

    Args:
        manager: Project ProfileManager.
        category: Only profiles of this category.
        query: Case-insensitive substring matched against the name, the
            description and the tags.
        include_inherited: Include profiles inherited from parent projects and
            the built-in set (read-only).

    Returns:
        ToolResponse with the table (user) and the content-free definitions
        (model).
    """
    profiles, scope = _filter_profiles(
        manager=manager,
        category=category,
        query=query,
        include_inherited=include_inherited,
    )

    if not profiles:
        return ToolResponse(
            user_response=f"✓ No profiles found ({scope} scope)",
            llm_response=f"No profiles found (scope={scope}).",
        )

    user_response = "\n".join([
        _format_profiles_table(profiles),
        "",
        f"Scope: **{scope}**. Editable profiles live in "
        f"`{_relative_to_project(manager.settings, manager.profiles_path)}/`.",
        "",
        "Instructions are not shown here: use `get_profile` "
        "(`action='get'`) with the profile name to read a profile's content.",
    ])

    llm_response = json.dumps(
        {
            "scope": scope,
            "count": len(profiles),
            # Definitions never include ``content`` (see _profile_definition).
            "profiles": [_profile_definition(p) for p in profiles],
            "next": (
                "Use get_profile(profile_name=...) (action='get') to read a "
                "profile's content/instructions."
            ),
        },
        indent=2,
    )
    logger.info(
        "profile_management: listed %d profile(s) (%s) without content",
        len(profiles), scope,
    )
    return ToolResponse(user_response=user_response, llm_response=llm_response)


def _action_list_summary(
    manager: ProfileManager,
    category: Optional[str] = None,
    query: Optional[str] = None,
    include_inherited: bool = False,
) -> ToolResponse:
    """
    List the profiles as a compact summary, made to CHOOSE which ones to use.

    Same selection rules as ``list`` but a much lighter payload: name, category,
    ``chat_mode``, tags, a truncated description and two flags
    (``has_content``: the profile has instructions, so it can drive a task;
    ``editable``: it belongs to the current project). Instructions are never
    included: this listing exists to pick the profiles for a task, then ``get``
    reads the chosen ones.

    The response closes with the step that follows the choice, so the model
    knows where the selected names must be passed (``create_task`` /
    ``project_manager``, ``profiles`` argument).

    Args:
        manager: Project ProfileManager.
        category: Only profiles of this category.
        query: Case-insensitive substring matched against the name, the
            description and the tags.
        include_inherited: Include profiles inherited from parent projects and
            the built-in set (read-only).

    Returns:
        ToolResponse with the summary table (user) and the compact profiles
        (model).
    """
    profiles, scope = _filter_profiles(
        manager=manager,
        category=category,
        query=query,
        include_inherited=include_inherited,
    )

    if not profiles:
        return ToolResponse(
            user_response=f"✓ No profiles found ({scope} scope)",
            llm_response=(
                f"No profiles found (scope={scope}). Do not invent a profile "
                "name: list again without filters (include_inherited=true) to "
                "see every available profile."
            ),
        )

    editable_names = {p.name for p in _project_profiles(manager)}
    summaries = [
        _profile_summary(profile, editable=profile.name in editable_names)
        for profile in sorted(profiles, key=lambda p: (p.category or "", p.name))
    ]

    user_response = "\n".join([
        _format_profiles_summary(profiles, editable_names),
        "",
        f"Scope: **{scope}**. `Instructions: -` means the profile has no content, "
        "so it cannot drive a task.",
        "",
        "Read the profiles you keep with `get_profile` before relying on them, "
        "and assign them through the `profiles` argument of `create_task` / "
        "`project_manager`.",
    ])

    llm_response = json.dumps(
        {
            "scope": scope,
            "count": len(summaries),
            # Compact by design: no content, no paths, no api settings.
            "profiles": summaries,
            "next": (
                "Keep the profiles whose category/description/tags fit the task "
                "(prefer has_content=true) and pass their names in the "
                "'profiles' argument of create_task or project_manager "
                "(action='create_task' or action='request_changes'). Use "
                "get_profile(profile_name=...) to read the instructions of the "
                "ones you keep."
            ),
        },
        indent=2,
    )
    logger.info(
        "profile_management: summarised %d profile(s) (%s)", len(summaries), scope
    )
    return ToolResponse(user_response=user_response, llm_response=llm_response)


def _action_get(manager: ProfileManager, name: str) -> ToolResponse:
    """
    Return the definition and the content of one profile.

    This is the ONLY way to read a profile's Markdown instructions: listings
    deliberately omit them.

    Args:
        manager: Project ProfileManager.
        name: Exact profile name.

    Returns:
        ToolResponse with the JSON definition and the Markdown content.
    """
    profile = _find_project_profile(manager, name)
    editable = profile is not None
    if profile is None:
        profile = _find_any_profile(manager, name)
    if profile is None:
        return ToolResponse(
            user_response=f"❌ Profile `{name}` not found",
            llm_response=(
                f"Profile '{name}' not found. Use action='list' "
                "(include_inherited=true) to see the available profiles."
            ),
        )

    paths = _profile_paths(manager, name)
    content_path = _relative_to_project(manager.settings, paths["content"])
    origin = "project" if editable else "inherited (read-only)"

    user_response = "\n".join([
        f"### Profile `{profile.name}`",
        f"> Origin: **{origin}** — definition: "
        f"`{_relative_to_project(manager.settings, profile.path)}`",
        "",
        "```json",
        json.dumps(_profile_definition(profile), indent=2),
        "```",
        "",
        f"**Content** (`{content_path}`)",
        "",
        "```markdown",
        profile.content or "",
        "```",
    ])

    llm_response = json.dumps(
        {
            **_profile_definition(profile, include_content=True),
            "editable": editable,
            "content_path": content_path,
        },
        indent=2,
    )
    logger.info(
        "profile_management: read profile '%s' (editable=%s)", name, editable
    )
    return ToolResponse(user_response=user_response, llm_response=llm_response)


def _action_create(
    manager: ProfileManager,
    name: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
    content: Optional[str] = None,
    file_match: Optional[str] = None,
    profiles: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    llm_model: Optional[str] = None,
    use_knowledge: Optional[bool] = None,
    chat_mode: Optional[str] = None,
    avatar: Optional[str] = None,
    url: Optional[str] = None,
    api_settings: Optional[Dict[str, Any]] = None,
) -> ToolResponse:
    """
    Create a new profile (both files) in the project.

    Args:
        manager: Project ProfileManager.
        name: Profile name (folder name, validated).
        description: When to use the profile (1-3 sentences).
        category: One of :data:`PROFILE_CATEGORIES`.
        content: Markdown instructions (required).
        file_match: Optional regex matched against file paths.
        profiles: Optional names of linked profiles.
        tools: Optional tool names granted to the profile.
        tags: Optional discovery tags.
        llm_model: Optional model override.
        use_knowledge: Whether knowledge context is injected.
        chat_mode: Optional chat mode restriction.
        avatar: Optional avatar URL.
        url: Optional documentation URL.
        api_settings: Optional ``{active, model_name, description}``.

    Returns:
        ToolResponse describing the created profile.

    Raises:
        ValueError: If the profile already exists or a field is invalid.
    """
    existing = _find_any_profile(manager, name)
    if existing:
        raise ValueError(
            f"Profile '{name}' already exists at "
            f"'{_relative_to_project(manager.settings, existing.path)}'. "
            "Use action='update' to modify it."
        )

    category = _validate_category(category or DEFAULT_CATEGORY)
    warnings: List[str] = []
    warnings.extend(_validate_content(content))
    warnings.extend(_validate_file_match(file_match or ""))
    profiles = list(profiles or [])
    tools = list(tools or [])
    _validate_linked_profiles(manager, profiles)
    _validate_tools(tools)
    if not description:
        warnings.append(
            "description is empty: the profile card and the @mention picker will "
            "not explain when to use the profile."
        )

    profile = Profile(
        name=name,
        description=description or "",
        category=category,
        content=content,
        file_match=file_match or "",
        profiles=profiles,
        tools=tools,
        tags=list(tags or []),
        llm_model=llm_model or "",
        use_knowledge=True if use_knowledge is None else use_knowledge,
        chat_mode=chat_mode,
        avatar=avatar or "",
        url=url or "",
        api_settings=ProfileApiSettings(**(api_settings or {})),
        project_id=manager.settings.project_id,
    )
    profile.path = _profile_paths(manager, name)["profile"]

    manager.save_profile(profile)
    _notify(manager.settings, f"Profile '{name}' created")

    logger.info("profile_management: created profile '%s'", name)
    return _write_response(
        settings=manager.settings,
        profile=profile,
        manager=manager,
        title=f"Profile created: `{name}`",
        warnings=warnings,
    )


def _action_update(
    manager: ProfileManager,
    name: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
    content: Optional[str] = None,
    file_match: Optional[str] = None,
    profiles: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    llm_model: Optional[str] = None,
    use_knowledge: Optional[bool] = None,
    chat_mode: Optional[str] = None,
    avatar: Optional[str] = None,
    url: Optional[str] = None,
    api_settings: Optional[Dict[str, Any]] = None,
) -> ToolResponse:
    """
    Update an existing project profile, merging the provided fields.

    Fields left as ``None`` keep their current value, so a partial update never
    wipes the rest of the definition or the Markdown content.

    Args:
        manager: Project ProfileManager.
        name: Exact name of the profile to update.
        description: New description.
        category: New category.
        content: New Markdown instructions (replaces the whole file).
        file_match: New ``file_match`` regex (``""`` clears it).
        profiles: New linked profile names (replaces the list).
        tools: New tool names (replaces the list).
        tags: New tags (replaces the list).
        llm_model: New model override (``""`` inherits the project model).
        use_knowledge: New knowledge flag.
        chat_mode: New chat mode restriction.
        avatar: New avatar URL.
        url: New documentation URL.
        api_settings: New ``{active, model_name, description}``.

    Returns:
        ToolResponse describing the updated profile.

    Raises:
        ValueError: If the profile does not exist in this project or a field is
            invalid.
    """
    existing = _find_project_profile(manager, name)
    if existing is None:
        other = _find_any_profile(manager, name)
        if other:
            raise ValueError(
                f"Profile '{name}' is inherited from "
                f"'{_relative_to_project(manager.settings, other.path)}' and is "
                "read-only. Create a project profile with the same name to "
                "override it (action='create')."
            )
        raise ValueError(
            f"Profile '{name}' does not exist in this project. "
            "Use action='create' to create it."
        )

    warnings: List[str] = []
    overrides: Dict[str, Any] = {}

    if description is not None:
        overrides["description"] = description
    if category is not None:
        overrides["category"] = _validate_category(category)
    if content is not None:
        warnings.extend(_validate_content(content))
        overrides["content"] = content
    if file_match is not None:
        warnings.extend(_validate_file_match(file_match))
        overrides["file_match"] = file_match
    if profiles is not None:
        _validate_linked_profiles(manager, list(profiles))
        overrides["profiles"] = list(profiles)
    if tools is not None:
        _validate_tools(list(tools))
        overrides["tools"] = list(tools)
    if tags is not None:
        overrides["tags"] = list(tags)
    if llm_model is not None:
        overrides["llm_model"] = llm_model
    if use_knowledge is not None:
        overrides["use_knowledge"] = use_knowledge
    if chat_mode is not None:
        overrides["chat_mode"] = chat_mode or None
    if avatar is not None:
        overrides["avatar"] = avatar
    if url is not None:
        overrides["url"] = url
    if api_settings is not None:
        overrides["api_settings"] = ProfileApiSettings(**api_settings)

    if not overrides:
        raise ValueError(
            "Nothing to update: provide at least one field "
            "(description, category, content, file_match, profiles, tools, tags, ...)"
        )

    profile = existing.model_copy(update=overrides)
    profile.name = name
    profile.path = _profile_paths(manager, name)["profile"]
    profile.project_id = manager.settings.project_id

    manager.save_profile(profile)
    _notify(manager.settings, f"Profile '{name}' updated")

    logger.info(
        "profile_management: updated profile '%s' (fields=%s)",
        name,
        ", ".join(sorted(overrides.keys())),
    )
    return _write_response(
        settings=manager.settings,
        profile=profile,
        manager=manager,
        title=f"Profile updated: `{name}`",
        warnings=warnings,
        changed_fields=sorted(overrides.keys()),
    )


def _action_delete(manager: ProfileManager, name: str) -> ToolResponse:
    """
    Delete a project profile (both files and its folder).

    Args:
        manager: Project ProfileManager.
        name: Exact name of the profile to delete.

    Returns:
        ToolResponse confirming the deletion.

    Raises:
        ValueError: If the profile is not owned by this project.
    """
    existing = _find_project_profile(manager, name)
    if existing is None:
        other = _find_any_profile(manager, name)
        if other:
            raise ValueError(
                f"Profile '{name}' is inherited from "
                f"'{_relative_to_project(manager.settings, other.path)}' and "
                "cannot be deleted from this project."
            )
        raise ValueError(f"Profile '{name}' does not exist in this project.")

    # Profiles linked from other definitions would be left dangling: report it
    # so the user can fix the references, but do not block the deletion.
    referenced_by = [
        p.name for p in _project_profiles(manager)
        if p.name != name and name in (p.profiles or [])
    ]

    paths = _profile_paths(manager, name)
    manager.delete_profile(name)
    _notify(manager.settings, f"Profile '{name}' deleted")

    logger.info("profile_management: deleted profile '%s'", name)

    user_lines = [
        f"### Profile deleted: `{name}`",
        "",
        f"- Folder removed: `{_relative_to_project(manager.settings, paths['folder'])}`",
    ]
    if referenced_by:
        user_lines.extend([
            "",
            f"> ⚠️ Still linked from: {', '.join(f'`{p}`' for p in referenced_by)}. "
            "Those links now point to a missing profile.",
        ])

    return ToolResponse(
        user_response="\n".join(user_lines),
        llm_response=json.dumps(
            {
                "deleted": name,
                "folder": _relative_to_project(manager.settings, paths["folder"]),
                "referenced_by": referenced_by,
            },
            indent=2,
        ),
    )


def _write_response(
    settings: CODXJuniorSettings,
    profile: Profile,
    manager: ProfileManager,
    title: str,
    warnings: Optional[List[str]] = None,
    changed_fields: Optional[List[str]] = None,
) -> ToolResponse:
    """
    Build the response shared by ``create`` and ``update``.

    Args:
        settings: Project settings.
        profile: The persisted profile.
        manager: Project ProfileManager.
        title: Heading of the user-facing block.
        warnings: Non-fatal problems found while validating.
        changed_fields: Fields modified by an update (``None`` on create).

    Returns:
        ToolResponse with the saved paths and the resulting definition
        (content-free: read it with ``get`` / ``get_profile``).
    """
    paths = _profile_paths(manager, profile.name)
    definition_path = _relative_to_project(settings, paths["profile"])
    content_path = _relative_to_project(settings, paths["content"])

    lines = [
        f"### {title}",
        "",
        f"- Definition: `{definition_path}`",
        f"- Content: `{content_path}`",
        f"- Category: `{profile.category or '-'}` | "
        f"file_match: `{profile.file_match or 'none'}`",
        f"- Links: profiles `{', '.join(profile.profiles or []) or 'none'}` | "
        f"tools `{', '.join(profile.tools or []) or 'none'}`",
    ]
    if changed_fields:
        lines.append(f"- Changed: {', '.join(changed_fields)}")
    if warnings:
        lines.extend(["", "> ⚠️ " + "\n> ⚠️ ".join(warnings)])
    lines.extend([
        "",
        "Reload the profiles list to see the change in the UI.",
    ])

    llm_response = json.dumps(
        {
            "saved": profile.name,
            "definition_path": definition_path,
            "content_path": content_path,
            "changed_fields": changed_fields or [],
            "warnings": warnings or [],
            "profile": _profile_definition(profile),
        },
        indent=2,
    )
    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=llm_response,
    )


# ---------------------------------------------------------------------------
# Tool entry point
# ---------------------------------------------------------------------------


def profile_management(
    action: str,
    profile_name: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    content: Optional[str] = None,
    file_match: Optional[str] = None,
    profiles: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    llm_model: Optional[str] = None,
    use_knowledge: Optional[bool] = None,
    chat_mode: Optional[str] = None,
    avatar: Optional[str] = None,
    url: Optional[str] = None,
    api_settings: Optional[Dict[str, Any]] = None,
    query: Optional[str] = None,
    include_inherited: bool = False,
    **kwargs,
) -> ToolResponse:
    """
    Unified CRUD tool for project profiles.

    Each profile is stored as two files inside ``.codx/profiles/<Name>/``:
    ``<Name>.profile`` (the JSON definition) and ``<Name>.md`` (the Markdown
    instructions). Both files are written together by ``ProfileManager``, so a
    profile is never left half-saved.

    Actions:
        - ``list``: profiles of the project (optional ``category``/``query``
          filters). ``include_inherited=True`` adds the read-only profiles
          inherited from parent projects and the built-in set. The result is
          the profile JSON **without** its content (``has_content`` flags which
          profiles have instructions).
        - ``list_summary``: compact summary of the profiles (name, category,
          ``chat_mode``, tags, truncated description plus ``has_content`` and
          ``editable`` flags), made to **choose** which profiles to use — e.g.
          to assign them to a task. Accepts the same ``category`` / ``query`` /
          ``include_inherited`` filters and never includes content either.
        - ``get``: full definition (JSON) plus content (Markdown) of one
          profile. This is the only way to read the instructions.
        - ``create``: creates a new profile. Fails if the name already exists.
          ``content`` is required.
        - ``update``: merges the provided fields into an existing project
          profile; omitted fields keep their value.
        - ``delete``: removes the profile folder of a project profile.

    Writes always target the active project's ``.codx/profiles`` folder:
    inherited and built-in profiles are read-only.

    NOTE: this tool bundles every action, so granting it grants the whole CRUD.
    To allow some actions and deny others, grant the fine-grained tools instead
    (``list_profiles``, ``list_profiles_summary``, ``get_profile``,
    ``create_profile``, ``update_profile``, ``delete_profile``).

    Args:
        action: One of :data:`VALID_ACTIONS`.
        profile_name: Target profile name (``get``/``update``/``delete``), also
            accepted on ``create``. On ``create`` it is optional when ``name``
            is provided.
        name: Profile name as a definition field (alias of ``profile_name`` for
            create/update).
        description: When to use the profile (1-3 sentences).
        category: One of ``assistant``, ``chat``, ``agent``, ``file``,
            ``project``. Defaults to ``assistant`` on create.
        content: Markdown instructions. Required on ``create``; replaces the
            whole content file on ``update``. Never returned by ``list``.
        file_match: Regex matched against file paths to auto-attach the
            profile. Empty string disables it.
        profiles: Names of the profiles to link (their content is injected when
            this profile runs).
        tools: Names of the tools granted to the profile. Must exist in the
            tool registry.
        tags: Discovery tags.
        llm_model: Model override (empty inherits the project/default model).
        use_knowledge: Whether knowledge context is injected.
        chat_mode: Chat mode restriction (e.g. ``task``).
        avatar: Avatar URL.
        url: Documentation URL.
        api_settings: ``{active, model_name, description}`` to expose the
            profile through the LLM API.
        query: ``list`` / ``list_summary`` only. Case-insensitive filter on
            name, description and tags.
        include_inherited: ``list`` / ``list_summary`` only. Include read-only
            inherited profiles.
        **kwargs: Internal. Injected by the agent runtime: ``settings``.

    Returns:
        ToolResponse: ``user_response`` for the chat, ``llm_response`` with the
        resulting definition for the model.

    Raises:
        Exception: If the project settings are missing.

    Example:
        >>> profile_management("list", category="assistant")
        # Lists every assistant profile (definitions only, no content)
        >>> profile_management("list_summary", query="code review")
        # Compact summary of the profiles matching "code review"
        >>> profile_management("get", profile_name="TeamManager")
        # Shows the definition AND the instructions
        >>> profile_management(
        ...     "create",
        ...     profile_name="Reviewer",
        ...     description="Reviews diffs for correctness and security.",
        ...     category="assistant",
        ...     content="# Reviewer Profile\\n\\n## Role\\n...",
        ...     tags=["code-review"],
        ... )
        # Creates .codx/profiles/Reviewer/Reviewer.profile + Reviewer.md
        >>> profile_management("update", profile_name="Reviewer", file_match=r"\\\\.diff$")
        # Updates only the file_match field
        >>> profile_management("delete", profile_name="Reviewer")
        # Removes the profile folder
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

    manager = _get_profile_manager(settings)

    try:
        if action == "list":
            return _action_list(
                manager=manager,
                category=category,
                query=query,
                include_inherited=include_inherited,
            )

        if action == "list_summary":
            return _action_list_summary(
                manager=manager,
                category=category,
                query=query,
                include_inherited=include_inherited,
            )

        if action == "get":
            return _action_get(
                manager=manager,
                name=_resolve_target_name(profile_name=profile_name, name=name),
            )

        if action == "create":
            return _action_create(
                manager=manager,
                name=_resolve_target_name(profile_name=profile_name, name=name),
                description=description,
                category=category,
                content=content,
                file_match=file_match,
                profiles=profiles,
                tools=tools,
                tags=tags,
                llm_model=llm_model,
                use_knowledge=use_knowledge,
                chat_mode=chat_mode,
                avatar=avatar,
                url=url,
                api_settings=api_settings,
            )

        if action == "update":
            return _action_update(
                manager=manager,
                name=_resolve_target_name(profile_name=profile_name, name=name),
                description=description,
                category=category,
                content=content,
                file_match=file_match,
                profiles=profiles,
                tools=tools,
                tags=tags,
                llm_model=llm_model,
                use_knowledge=use_knowledge,
                chat_mode=chat_mode,
                avatar=avatar,
                url=url,
                api_settings=api_settings,
            )

        return _action_delete(
            manager=manager,
            name=_resolve_target_name(profile_name=profile_name, name=name),
        )

    except ValueError as ex:
        # Validation errors are expected (typos, missing confirmation): report
        # them so the model can correct the call instead of crashing the run.
        logger.warning("profile_management(%s): %s", action, ex)
        return ToolResponse(
            user_response=f"❌ {ex}",
            llm_response=f"profile_management action '{action}' failed: {ex}",
        )
    except Exception as ex:
        logger.exception("profile_management(%s): unexpected error", action)
        return ToolResponse(
            user_response=f"❌ Error: {ex}",
            llm_response=f"profile_management action '{action}' failed: {ex}",
        )


# ---------------------------------------------------------------------------
# Fine-grained tools (one tool per CRUD action)
# ---------------------------------------------------------------------------
#
# ``profile_management`` bundles the five CRUD actions in a single tool, so a
# profile either gets the whole CRUD or none of it: there is no way to allow
# "list the profiles" while withholding "delete a profile".
#
# The runtime grants permissions by TOOL NAME (``Profile.tools`` is matched
# against the ``TOOLS`` registry), so a per-action permission requires a
# per-action tool.
#
# These wrappers expose one tool per action. They never re-implement anything:
# each one forwards to :func:`profile_management` with its action fixed, so
# validation, read-only rules, notifications and response formatting stay in a
# single place. Grant in ``Profile.tools`` only the actions the profile must be
# able to run, e.g.::
#
#     ["list_profiles_summary", "get_profile"]                # choose + read
#     ["list_profiles", "get_profile"]                        # read-only (full)
#     ["list_profiles", "get_profile", "update_profile"]      # edits, no delete
#
# NOTE: neither ``list_profiles`` nor ``list_profiles_summary`` returns the
# profile content; reading the instructions always goes through ``get_profile``.
# ---------------------------------------------------------------------------


def list_profiles(
    category: Optional[str] = None,
    query: Optional[str] = None,
    include_inherited: bool = False,
    **kwargs,
) -> ToolResponse:
    """
    List the project's profiles (read-only), WITHOUT their content.

    The result is the profile **JSON definition** (name, description, category,
    ``file_match``, linked profiles, granted tools, tags, model, flags) plus a
    ``has_content`` marker. The Markdown instructions are never inlined: use
    :func:`get_profile` to read them.

    Args:
        category: Only profiles of this category (``assistant``, ``chat``,
            ``agent``, ``file``, ``project``).
        query: Case-insensitive filter on name, description and tags.
        include_inherited: Also list the read-only profiles inherited from
            parent projects and the built-in set.
        **kwargs: Internal. Injected by the agent runtime: ``settings``.

    Returns:
        ToolResponse with the profiles table (user) and the content-free
        definitions (model).
    """
    return profile_management(
        action="list",
        category=category,
        query=query,
        include_inherited=include_inherited,
        **kwargs,
    )


def list_profiles_summary(
    category: Optional[str] = None,
    query: Optional[str] = None,
    include_inherited: bool = False,
    **kwargs,
) -> ToolResponse:
    """
    List the profiles as a compact summary, made to CHOOSE which ones to use.

    Each entry carries only the selection fields: ``name``, ``category``,
    ``chat_mode``, ``tags``, a truncated ``description``, ``has_content`` (the
    profile has instructions, so it can drive a task) and ``editable`` (it
    belongs to the current project). Instructions are never inlined here.

    Typical flow: call it with the task keywords as ``query``, keep the profiles
    that fit and pass their names in the ``profiles`` argument of
    ``create_task`` / ``project_manager``; read the chosen ones with
    :func:`get_profile`.

    Args:
        category: Only profiles of this category (``assistant``, ``chat``,
            ``agent``, ``file``, ``project``).
        query: Case-insensitive filter on name, description and tags.
        include_inherited: Also list the read-only profiles inherited from
            parent projects and the built-in set.
        **kwargs: Internal. Injected by the agent runtime: ``settings``.

    Returns:
        ToolResponse with the summary table (user) and the compact profiles
        (model).
    """
    return profile_management(
        action="list_summary",
        category=category,
        query=query,
        include_inherited=include_inherited,
        **kwargs,
    )


def get_profile(
    profile_name: Optional[str] = None,
    name: Optional[str] = None,
    **kwargs,
) -> ToolResponse:
    """
    Return the definition (JSON) AND the content (Markdown) of one profile.

    This is the only way to read a profile's instructions: listings
    (:func:`list_profiles`, :func:`list_profiles_summary`) omit the content on
    purpose.

    Args:
        profile_name: Exact profile name.
        name: Alias of ``profile_name``.
        **kwargs: Internal. Injected by the agent runtime: ``settings``.

    Returns:
        ToolResponse with the definition and the instructions.
    """
    return profile_management(
        action="get",
        profile_name=profile_name,
        name=name,
        **kwargs,
    )


def create_profile(
    profile_name: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    content: Optional[str] = None,
    file_match: Optional[str] = None,
    profiles: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    llm_model: Optional[str] = None,
    use_knowledge: Optional[bool] = None,
    chat_mode: Optional[str] = None,
    avatar: Optional[str] = None,
    url: Optional[str] = None,
    api_settings: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> ToolResponse:
    """
    Create a new project profile (definition + content files).

    Args:
        profile_name: Profile name (mention-safe, also the folder name).
        name: Alias of ``profile_name``.
        description: When to use the profile (1-3 sentences).
        category: One of ``assistant``, ``chat``, ``agent``, ``file``,
            ``project`` (default ``assistant``).
        content: Markdown instructions. Required.
        file_match: Optional regex matched against file paths.
        profiles: Optional names of linked profiles.
        tools: Optional tool names granted to the profile.
        tags: Optional discovery tags.
        llm_model: Optional model override.
        use_knowledge: Whether knowledge context is injected.
        chat_mode: Optional chat mode restriction.
        avatar: Optional avatar URL.
        url: Optional documentation URL.
        api_settings: Optional ``{active, model_name, description}``.
        **kwargs: Internal. Injected by the agent runtime: ``settings``.

    Returns:
        ToolResponse describing the created profile.
    """
    return profile_management(
        action="create",
        profile_name=profile_name,
        name=name,
        description=description,
        category=category,
        content=content,
        file_match=file_match,
        profiles=profiles,
        tools=tools,
        tags=tags,
        llm_model=llm_model,
        use_knowledge=use_knowledge,
        chat_mode=chat_mode,
        avatar=avatar,
        url=url,
        api_settings=api_settings,
        **kwargs,
    )


def update_profile(
    profile_name: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    content: Optional[str] = None,
    file_match: Optional[str] = None,
    profiles: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    llm_model: Optional[str] = None,
    use_knowledge: Optional[bool] = None,
    chat_mode: Optional[str] = None,
    avatar: Optional[str] = None,
    url: Optional[str] = None,
    api_settings: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> ToolResponse:
    """
    Update an existing project profile, merging only the provided fields.

    Args:
        profile_name: Exact name of the profile to update.
        name: Alias of ``profile_name``.
        description: New description.
        category: New category.
        content: New Markdown instructions (replaces the whole content file).
        file_match: New ``file_match`` regex (``""`` clears it).
        profiles: New linked profile names (replaces the list).
        tools: New tool names (replaces the list).
        tags: New tags (replaces the list).
        llm_model: New model override (``""`` inherits the project model).
        use_knowledge: New knowledge flag.
        chat_mode: New chat mode restriction.
        avatar: New avatar URL.
        url: New documentation URL.
        api_settings: New ``{active, model_name, description}``.
        **kwargs: Internal. Injected by the agent runtime: ``settings``.

    Returns:
        ToolResponse describing the updated profile.
    """
    return profile_management(
        action="update",
        profile_name=profile_name,
        name=name,
        description=description,
        category=category,
        content=content,
        file_match=file_match,
        profiles=profiles,
        tools=tools,
        tags=tags,
        llm_model=llm_model,
        use_knowledge=use_knowledge,
        chat_mode=chat_mode,
        avatar=avatar,
        url=url,
        api_settings=api_settings,
        **kwargs,
    )


def delete_profile(
    profile_name: Optional[str] = None,
    name: Optional[str] = None,
    **kwargs,
) -> ToolResponse:
    """
    Delete a project profile (its folder with both files).

    Inherited and built-in profiles cannot be deleted: only profiles owned by
    the active project can.

    Args:
        profile_name: Exact name of the profile to delete.
        name: Alias of ``profile_name``.
        **kwargs: Internal. Injected by the agent runtime: ``settings``.

    Returns:
        ToolResponse confirming the deletion and the dangling links, if any.
    """
    return profile_management(
        action="delete",
        profile_name=profile_name,
        name=name,
        **kwargs,
    )


# Tool JSON definition
PROFILE_MANAGEMENT_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "profile_management",
        "description": (
            "Create, read, update and delete codx-junior profiles (CRUD). "
            "A profile is stored as two files in the project's .codx/profiles/<Name>/ "
            "folder: <Name>.profile (JSON definition) and <Name>.md (Markdown "
            "instructions); both are always written together. "
            "Actions: 'list' (optionally filtered by category/query; returns the profile "
            "JSON WITHOUT its content), 'list_summary' (compact summary to choose which "
            "profiles to use, e.g. to assign them to a task), 'get' (definition + "
            "content), 'create' (fails if "
            "the name exists, requires content), 'update' (merges only the provided "
            "fields) and 'delete'. "
            "Writes always target the current project: profiles inherited from parent "
            "projects or built-in profiles can be read but not modified. "
            "Use the returned paths to confirm where the profile was saved. "
            "NOTE: this tool bundles every action, so granting it grants the whole CRUD. "
            "To allow some actions and deny others, grant the fine-grained tools instead "
            "(list_profiles, list_profiles_summary, get_profile, create_profile, "
            "update_profile, delete_profile)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": VALID_ACTIONS,
                    "description": (
                        "CRUD operation:\n"
                        "  - 'list': list project profiles, definitions only (read)\n"
                        "  - 'list_summary': compact summary to pick profiles, e.g. for a "
                        "task (read)\n"
                        "  - 'get': read one profile's definition and content (read)\n"
                        "  - 'create': create a new profile (fails if it exists)\n"
                        "  - 'update': merge changes into an existing project profile\n"
                        "  - 'delete': remove a project profile folder"
                    )
                },
                "profile_name": {
                    "type": "string",
                    "description": (
                        "Target profile name. Required for get/update/delete and for "
                        "create unless 'name' is given. Must be mention-safe (letters, "
                        "digits, '_', '-', '.'), because it is also the folder name and "
                        "the @mention."
                    )
                },
                "name": {
                    "type": "string",
                    "description": (
                        "Profile name field (alias of profile_name for create/update). "
                        "Must match profile_name when both are provided."
                    )
                },
                "description": {
                    "type": "string",
                    "description": (
                        "When to use the profile, in 1-3 sentences. Shown in the profile "
                        "card and in the @mention picker."
                    )
                },
                "category": {
                    "type": "string",
                    "enum": PROFILE_CATEGORIES,
                    "description": (
                        "Profile category: 'assistant' (persona/role), 'chat' "
                        "(conversational), 'agent' (multi-step executor), 'file' "
                        "(convention enforcer) or 'project' (project-scoped). "
                        "Defaults to 'assistant'."
                    )
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Markdown instructions of the profile (the .md file): identity, "
                        "method, output format and guardrails. Required on create; on "
                        "update it replaces the whole content file. It is never returned "
                        "by 'list' / 'list_summary' (use 'get' to read it)."
                    )
                },
                "file_match": {
                    "type": "string",
                    "description": (
                        "Optional regex matched against file paths to auto-attach the "
                        "profile (e.g. '\\\\.vue$'). Empty string disables it. Keep it "
                        "narrow: a broad pattern applies the profile to every chat."
                    )
                },
                "profiles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Names of the profiles to link. Their instructions are injected "
                        "when this profile runs. Every name must already exist."
                    )
                },
                "tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Names of the tools granted to the profile (e.g. "
                        "'project_read_file', 'profile_management'). Every name must "
                        "exist in the tool registry."
                    )
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Free-form discovery tags (lowercase, kebab-case)."
                },
                "llm_model": {
                    "type": "string",
                    "description": (
                        "Model override for this profile. Empty string inherits the "
                        "project/default model."
                    )
                },
                "use_knowledge": {
                    "type": "boolean",
                    "description": (
                        "Whether project knowledge (RAG) context is injected. Defaults "
                        "to true."
                    )
                },
                "chat_mode": {
                    "type": "string",
                    "description": (
                        "Optional chat mode restriction for the profile (e.g. 'task')."
                    )
                },
                "avatar": {
                    "type": "string",
                    "description": "Optional avatar URL for the profile card."
                },
                "url": {
                    "type": "string",
                    "description": "Optional documentation/homepage URL."
                },
                "api_settings": {
                    "type": "object",
                    "description": (
                        "Expose the profile through the LLM API: "
                        "{active: bool, model_name: string|null, description: "
                        "string|null}."
                    ),
                    "properties": {
                        "active": {
                            "type": "boolean",
                            "description": "Profile is visible through the API"
                        },
                        "model_name": {
                            "type": "string",
                            "description": "Model name exposed by the API"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description exposed by the API"
                        }
                    }
                },
                "query": {
                    "type": "string",
                    "description": (
                        "For 'list' / 'list_summary': case-insensitive filter matched "
                        "against the name, the description and the tags."
                    )
                },
                "include_inherited": {
                    "type": "boolean",
                    "description": (
                        "For 'list' / 'list_summary': include the read-only profiles "
                        "inherited from parent projects and the built-in set "
                        "(default: false)."
                    )
                }
            },
            "required": ["action"]
        }
    }
}

# Fine-grained tool definitions (one tool per action, so permissions can be
# granted per action: the runtime filters tools by NAME).
PROFILE_LIST_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "list_profiles",
        "description": (
            "List the project's profiles (read-only) returning the profile JSON WITHOUT "
            "its content. Each entry carries name, description, category, file_match, "
            "linked profiles, granted tools, tags, model, flags and 'has_content' "
            "(whether the profile has Markdown instructions). The instructions "
            "themselves are never inlined here: to read them use get_profile. Set "
            "include_inherited=true to also list the read-only profiles inherited from "
            "parent projects and the built-in set. "
            "When the goal is only to CHOOSE profiles (e.g. to assign them to a task), "
            "prefer list_profiles_summary: same filters, far less output."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": PROFILE_CATEGORIES,
                    "description": (
                        "Only list profiles of this category: 'assistant', 'chat', "
                        "'agent', 'file' or 'project'."
                    )
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Case-insensitive filter matched against the name, the "
                        "description and the tags."
                    )
                },
                "include_inherited": {
                    "type": "boolean",
                    "description": (
                        "Include the read-only profiles inherited from parent projects "
                        "and the built-in set (default: false)."
                    )
                }
            },
            "required": []
        }
    }
}

PROFILE_LIST_SUMMARY_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "list_profiles_summary",
        "description": (
            "List the project's profiles as a COMPACT summary, made to CHOOSE which "
            "profiles to use (read-only): typically to pick the profiles to assign to a "
            "task. Each entry carries only the selection fields: name, category, "
            "chat_mode, tags, a truncated description and two flags — 'has_content' "
            "(the profile has Markdown instructions, so it can drive a task) and "
            "'editable' (it belongs to the current project). "
            "Instructions and full definitions are NOT included: use list_profiles for "
            "the definitions and get_profile to read the instructions of the profiles "
            "you keep. "
            "Typical flow: call this with the task keywords as 'query', keep the "
            "profiles that fit, then pass their names in the 'profiles' argument of "
            "create_task or project_manager (action='create_task' / "
            "action='request_changes')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": PROFILE_CATEGORIES,
                    "description": (
                        "Only list profiles of this category: 'assistant', 'chat', "
                        "'agent', 'file' or 'project'."
                    )
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Case-insensitive filter matched against the name, the "
                        "description and the tags. Pass the task keywords to narrow the "
                        "candidates (e.g. 'test', 'backend', 'documentation')."
                    )
                },
                "include_inherited": {
                    "type": "boolean",
                    "description": (
                        "Include the read-only profiles inherited from parent projects "
                        "and the built-in set (default: false). They can be assigned to "
                        "a task but not modified."
                    )
                }
            },
            "required": []
        }
    }
}

PROFILE_GET_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "get_profile",
        "description": (
            "Read one profile (read-only): its JSON definition (category, file_match, "
            "linked profiles, granted tools, tags, model...) AND its Markdown "
            "instructions (content). This is the only way to read a profile's content, "
            "because list_profiles and list_profiles_summary omit it. Inherited and "
            "built-in profiles can be "
            "read this way but are read-only for writes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "profile_name": {
                    "type": "string",
                    "description": (
                        "Exact name of the profile to read (e.g. 'TeamManager')."
                    )
                },
                "name": {
                    "type": "string",
                    "description": "Alias of profile_name."
                }
            },
            "required": ["profile_name"]
        }
    }
}

PROFILE_CREATE_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "create_profile",
        "description": (
            "Create a new project profile. Two files are written together in "
            ".codx/profiles/<Name>/: <Name>.profile (JSON definition) and <Name>.md "
            "(Markdown instructions). Fails if a profile with that name already exists "
            "in the project, a parent project or the built-in set."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "profile_name": {
                    "type": "string",
                    "description": (
                        "Profile name. Must be mention-safe (letters, digits, '_', '-', "
                        "'.'), because it is also the folder name and the @mention."
                    )
                },
                "name": {
                    "type": "string",
                    "description": (
                        "Alias of profile_name. Must match profile_name when both are "
                        "provided."
                    )
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Markdown instructions of the profile (the .md file): identity, "
                        "method, output format and guardrails. Required."
                    )
                },
                "description": {
                    "type": "string",
                    "description": (
                        "When to use the profile, in 1-3 sentences. Shown in the profile "
                        "card and in the @mention picker."
                    )
                },
                "category": {
                    "type": "string",
                    "enum": PROFILE_CATEGORIES,
                    "description": (
                        "Profile category: 'assistant' (persona/role), 'chat' "
                        "(conversational), 'agent' (multi-step executor), 'file' "
                        "(convention enforcer) or 'project' (project-scoped). "
                        "Defaults to 'assistant'."
                    )
                },
                "file_match": {
                    "type": "string",
                    "description": (
                        "Optional regex matched against file paths to auto-attach the "
                        "profile (e.g. '\\\\.vue$'). Empty string disables it. Keep it "
                        "narrow: a broad pattern applies the profile to every chat."
                    )
                },
                "profiles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Names of the profiles to link. Their instructions are injected "
                        "when this profile runs. Every name must already exist."
                    )
                },
                "tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Names of the tools granted to the profile (e.g. "
                        "'project_read_file', 'list_profiles'). Every name must exist in "
                        "the tool registry."
                    )
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Free-form discovery tags (lowercase, kebab-case)."
                },
                "llm_model": {
                    "type": "string",
                    "description": (
                        "Model override for this profile. Empty string inherits the "
                        "project/default model."
                    )
                },
                "use_knowledge": {
                    "type": "boolean",
                    "description": (
                        "Whether project knowledge (RAG) context is injected. Defaults "
                        "to true."
                    )
                },
                "chat_mode": {
                    "type": "string",
                    "description": (
                        "Optional chat mode restriction for the profile (e.g. 'task')."
                    )
                },
                "avatar": {
                    "type": "string",
                    "description": "Optional avatar URL for the profile card."
                },
                "url": {
                    "type": "string",
                    "description": "Optional documentation/homepage URL."
                },
                "api_settings": {
                    "type": "object",
                    "description": (
                        "Expose the profile through the LLM API: "
                        "{active: bool, model_name: string|null, description: "
                        "string|null}."
                    ),
                    "properties": {
                        "active": {
                            "type": "boolean",
                            "description": "Profile is visible through the API"
                        },
                        "model_name": {
                            "type": "string",
                            "description": "Model name exposed by the API"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description exposed by the API"
                        }
                    }
                }
            },
            "required": ["profile_name", "content"]
        }
    }
}

PROFILE_UPDATE_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "update_profile",
        "description": (
            "Update an existing project profile. Only the provided fields are "
            "changed: omitted fields keep their current value, so a partial update "
            "never wipes the rest of the definition or the Markdown content. "
            "Inherited and built-in profiles are read-only: create a project profile "
            "with the same name to override them."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "profile_name": {
                    "type": "string",
                    "description": "Exact name of the profile to update."
                },
                "name": {
                    "type": "string",
                    "description": (
                        "Alias of profile_name. Must match profile_name when both are "
                        "provided."
                    )
                },
                "description": {
                    "type": "string",
                    "description": (
                        "New description: when to use the profile, in 1-3 sentences."
                    )
                },
                "category": {
                    "type": "string",
                    "enum": PROFILE_CATEGORIES,
                    "description": (
                        "New category: 'assistant', 'chat', 'agent', 'file' or 'project'."
                    )
                },
                "content": {
                    "type": "string",
                    "description": (
                        "New Markdown instructions. Replaces the WHOLE content file, so "
                        "always send the complete text."
                    )
                },
                "file_match": {
                    "type": "string",
                    "description": (
                        "New regex matched against file paths. Empty string clears it."
                    )
                },
                "profiles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "New linked profile names. REPLACES the current list."
                    )
                },
                "tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "New tool names granted to the profile. REPLACES the current "
                        "list. Every name must exist in the tool registry."
                    )
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New tags. REPLACES the current list."
                },
                "llm_model": {
                    "type": "string",
                    "description": (
                        "New model override. Empty string inherits the project/default "
                        "model."
                    )
                },
                "use_knowledge": {
                    "type": "boolean",
                    "description": "New knowledge (RAG) flag."
                },
                "chat_mode": {
                    "type": "string",
                    "description": "New chat mode restriction (e.g. 'task')."
                },
                "avatar": {
                    "type": "string",
                    "description": "New avatar URL."
                },
                "url": {
                    "type": "string",
                    "description": "New documentation/homepage URL."
                },
                "api_settings": {
                    "type": "object",
                    "description": (
                        "New API exposure settings: "
                        "{active: bool, model_name: string|null, description: "
                        "string|null}."
                    ),
                    "properties": {
                        "active": {
                            "type": "boolean",
                            "description": "Profile is visible through the API"
                        },
                        "model_name": {
                            "type": "string",
                            "description": "Model name exposed by the API"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description exposed by the API"
                        }
                    }
                }
            },
            "required": ["profile_name"]
        }
    }
}

PROFILE_DELETE_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "delete_profile",
        "description": (
            "Delete a project profile: removes its folder with both files "
            "(.codx/profiles/<Name>/). Inherited and built-in profiles cannot be "
            "deleted from this project. The response lists the profiles that still "
            "link to the deleted one, because those links become dangling."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "profile_name": {
                    "type": "string",
                    "description": "Exact name of the profile to delete."
                },
                "name": {
                    "type": "string",
                    "description": "Alias of profile_name."
                }
            },
            "required": ["profile_name"]
        }
    }
}

# Made with ❤️ by codx-junior