"""
Profile learning tool for codx-junior.

A profile learns **per project**, and what it learns is kept in two places:

* **Rules** — short, always-relevant instructions stored as ``## <title>``
  blocks in ``<profiles>/<Name>/enrich.md``. They are composed into the profile
  content, so they reach every chat prompt. Addressed by title: writing the same
  title again replaces the instruction (never duplicated), ``forget`` removes it.
* **Knowledge files** — reference material under
  ``<profiles>/<Name>/knowledge/**`` (guidelines, conventions, examples, docs).
  Indexed in a ``KnowledgeDB`` per knowledge folder
  (:mod:`codx.junior.profiles.profile_knowledge`) and retrieved on demand.

Both are resolved through the project inheritance chain
(:class:`~codx.junior.profiles.profile_manager.ProfileManager`): the base
profile first, then every parent project down to the current one. Only the
current project's resources are writable.

The tool is meant to be used **proactively**: a profile is expected to store
what it learns as the work happens, without waiting to be asked, and to choose
the cheaper store (rule vs file) depending on the size and lifetime of the
content.

Permissions:

* reading (``overview``, ``search``, ``read``) is available to any user working
  on the project;
* writing (``remember``, ``forget``, ``write_file``, ``delete_file``,
  ``promote``) requires a **codx-junior admin**, a **project admin** or a
  **project knowledge admin** (``knowledge_admin``), see
  :meth:`UserSecurityManager.can_manage_profile_knowledge`.

The tool is NOT part of the profile definition: the agent
(:class:`codx.junior.ai.smol.smol_agent.SmolAgent`) decides whether to inject it
into the request. The check is repeated here, so a tool call can never bypass
it.

The read-only variant (``profile_knowledge_search``) lives in
:mod:`codx.junior.tools.profile_knowledge_tools` and delegates to the ``search``
action of this tool.

Made with ❤️ by codx-junior
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Set

from codx.junior.model.model import CodxUser
from codx.junior.profiles.profile_knowledge import ProfileKnowledge
from codx.junior.profiles.profile_manager import (
    MAX_RULE_CHARS,
    ProfileManager,
)
from codx.junior.security.user_management import UserSecurityManager
from codx.junior.settings import CODXJuniorSettings
from .model import ToolResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

ACTION_OVERVIEW = "overview"
ACTION_SEARCH = "search"
ACTION_READ = "read"
ACTION_REMEMBER = "remember"
ACTION_FORGET = "forget"
ACTION_WRITE_FILE = "write_file"
ACTION_DELETE_FILE = "delete_file"
ACTION_PROMOTE = "promote"

# Read-only actions: available to every project user.
READ_ACTIONS = [ACTION_OVERVIEW, ACTION_SEARCH, ACTION_READ]

# Actions that modify what the profile knows: knowledge administration required.
WRITE_ACTIONS = [
    ACTION_REMEMBER,
    ACTION_FORGET,
    ACTION_WRITE_FILE,
    ACTION_DELETE_FILE,
    ACTION_PROMOTE,
]

VALID_ACTIONS = READ_ACTIONS + WRITE_ACTIONS

# Promotion directions: decide between "always in the prompt" (rule) and
# "indexed, retrieved on demand" (knowledge file).
DIRECTION_RULE_TO_FILE = "rule_to_file"
DIRECTION_FILE_TO_RULE = "file_to_rule"
DIRECTIONS = [DIRECTION_RULE_TO_FILE, DIRECTION_FILE_TO_RULE]

# Number of matches returned to the model by default.
DEFAULT_LIMIT = 8

# A result chunk is injected into the model context: keep it bounded.
MAX_RESULT_CHARS = 1500

# Arguments are validated here too (cost/abuse guard, independent of the tool).
MAX_QUERY_CHARS = 500
MAX_FILE_NAME_CHARS = 500
MAX_FILE_ARG_CHARS = 200000

# Profiles inspected when no profile name is given (token/cost guard).
MAX_PROFILES_SCANNED = 10

# Characters of a rule shown by the `overview` action.
OVERVIEW_RULE_PREVIEW_CHARS = 160

# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------


def _current_user(
    settings: Optional[CODXJuniorSettings] = None,
    session: Any = None
) -> Optional[CodxUser]:
    """
    Resolve the user executing the tool.

    Tools get ``session`` injected (``ToolSettings.session``) or, when they only
    receive ``settings``, the active session attached to them.

    Args:
        settings: Project settings.
        session: Active session, when injected.

    Returns:
        The ``CodxUser`` behind the call, or None when unknown.
    """
    user = getattr(session, "user", None)
    if user:
        return user
    active_session = getattr(settings, "_active_session", None)
    return getattr(active_session, "user", None)


def _require_knowledge_permission(
    settings: Optional[CODXJuniorSettings],
    user: Optional[CodxUser]
) -> None:
    """
    Ensure the user can modify what the profiles learn in the project.

    The rule lives in :meth:`UserSecurityManager.can_manage_profile_knowledge`
    so the agent (which decides whether to offer this tool) and the tool itself
    always agree: codx-junior admins, project admins and project knowledge
    admins (``knowledge_admin``) are allowed.

    Args:
        settings: Project settings.
        user: User executing the tool.

    Raises:
        PermissionError: When the user has no knowledge administration rights.
    """
    if not user or not getattr(user, "username", ""):
        raise PermissionError(
            "Learning requires an authenticated user with profile knowledge "
            "administration rights."
        )

    try:
        allowed = UserSecurityManager().can_manage_profile_knowledge(
            user=user, settings=settings
        )
    except Exception as ex:
        logger.warning(
            "Could not resolve profile knowledge permission for '%s': %s",
            user.username,
            ex,
        )
        allowed = False

    if allowed:
        return

    raise PermissionError(
        f"User '{user.username}' cannot change what profiles learn in project "
        f"'{(settings.project_name if settings else '')}'. Only a project admin, "
        "a project knowledge admin or a codx-junior admin can do it."
    )


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


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
    if project_path and path and path.startswith(project_path):
        return os.path.relpath(path, project_path)
    return path


def _validate_text(value: Optional[str], label: str, max_chars: int) -> str:
    """
    Validate a free-text argument.

    Args:
        value: Raw argument value.
        label: Argument name used in the error message.
        max_chars: Maximum accepted length.

    Returns:
        The stripped value.

    Raises:
        ValueError: When the value is empty or too long.
    """
    text = (value or "").strip()
    if not text:
        raise ValueError(f"{label} is required")
    if len(text) > max_chars:
        raise ValueError(
            f"{label} has {len(text)} characters; the maximum is {max_chars}."
        )
    return text


def _excerpt(content: str) -> str:
    """
    Truncate a document chunk to the maximum excerpt size.

    Args:
        content: Chunk content.

    Returns:
        Excerpt (with an ellipsis when truncated).
    """
    content = (content or "").strip()
    if len(content) <= MAX_RESULT_CHARS:
        return content
    return content[:MAX_RESULT_CHARS].rstrip() + "\n..."


def _score(result: Dict[str, Any]) -> float:
    """
    Safely read the relevance score of a search result.

    Args:
        result: Result dict.

    Returns:
        Score as float, 0 when it cannot be converted.
    """
    try:
        return float(result.get("score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _knowledge_table(
    entries: List[Dict[str, Any]],
    settings: CODXJuniorSettings
) -> str:
    """
    Render the knowledge file list as a Markdown table.

    Args:
        entries: Entries returned by ``ProfileManager.list_profile_knowledge``.
        settings: Project settings (for relative paths).

    Returns:
        Markdown table (or a "no knowledge" note).
    """
    if not entries:
        return "> No knowledge files yet."

    lines = [
        f"> {len(entries)} knowledge file(s)",
        "",
        "**File** | **Source** | **Size** | **Path**",
        "---|---|---|---",
    ]
    for entry in entries:
        lines.append(
            f"`{entry['file']}` | {entry['source']} | {entry['size']} B | "
            f"`{_relative_to_project(settings, entry['path'])}`"
        )
    return "\n".join(lines)


def _first_line(text: str, max_chars: int = OVERVIEW_RULE_PREVIEW_CHARS) -> str:
    """
    Return the first meaningful line of a text block.

    Args:
        text: Block content.
        max_chars: Maximum length of the returned line.

    Returns:
        Single-line preview.
    """
    for line in (text or "").splitlines():
        candidate = " ".join(line.split())
        if candidate:
            return candidate[:max_chars]
    return ""


# ---------------------------------------------------------------------------
# Profile resolution
# ---------------------------------------------------------------------------


def _profiles_with_learning(
    settings: CODXJuniorSettings,
    manager: ProfileManager
) -> List[str]:
    """
    List the profiles that have learned something in this project.

    Union of the profiles with a knowledge folder (base profile and every
    project level) and the profiles with rules learned by this project.

    Args:
        settings: Project settings.
        manager: Project ProfileManager.

    Returns:
        Sorted profile names, capped to :data:`MAX_PROFILES_SCANNED`.
    """
    names: Set[str] = set(
        ProfileKnowledge(settings=settings).profile_names_with_knowledge()
    )
    for profile in manager.list_profiles():
        if not profile or not profile.name:
            continue
        if manager.profile_rules(profile.name, include_inherited=False):
            names.add(profile.name)
    return sorted(names)[:MAX_PROFILES_SCANNED]


# ---------------------------------------------------------------------------
# Search (semantic index with filesystem fallback)
# ---------------------------------------------------------------------------


def _semantic_search(
    settings: CODXJuniorSettings,
    profiles: List[str],
    query: str,
    limit: int
) -> List[Dict[str, Any]]:
    """
    Search the profile knowledge using the semantic index.

    Each knowledge folder has its own ``KnowledgeDB`` (see
    :class:`~codx.junior.profiles.profile_knowledge.ProfileKnowledge`), which is
    indexed lazily on every call.

    Args:
        settings: Project settings.
        profiles: Profiles to search.
        query: Natural-language query.
        limit: Maximum number of results.

    Returns:
        Normalized results: ``profile``, ``level``, ``file``, ``path``,
        ``score`` and ``excerpt``.
    """
    knowledge = ProfileKnowledge(settings=settings)
    results = knowledge.search(query=query, profile_names=profiles, limit=limit)
    return [
        {
            "profile": result.get("profile", ""),
            "level": result.get("knowledge_source", ""),
            "file": result.get("file", ""),
            "path": result.get("source", ""),
            "score": _score(result),
            "excerpt": result.get("content", ""),
        }
        for result in results
    ]


def _term_search(
    manager: ProfileManager,
    profiles: List[str],
    query: str,
    limit: int
) -> List[Dict[str, Any]]:
    """
    Search the profile knowledge with a plain case-insensitive term match.

    Fallback used when the semantic index is unavailable (no embeddings model,
    index error, ...), so the profile can still find what it wrote.

    Args:
        manager: Project ProfileManager.
        profiles: Profiles to search.
        query: Search terms.
        limit: Maximum number of results.

    Returns:
        Normalized results (see :func:`_semantic_search`), unranked (0.0).
    """
    results: List[Dict[str, Any]] = []
    for profile_name in profiles:
        for entry in manager.search_profile_knowledge(
            profile_name=profile_name, query=query, limit=limit
        ):
            results.append({
                "profile": profile_name,
                "level": entry.get("source", ""),
                "file": entry.get("file", ""),
                "path": entry.get("path", ""),
                "score": 0.0,
                "excerpt": entry.get("excerpt", ""),
            })
    return results[:limit]


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def _action_overview(
    manager: ProfileManager,
    settings: CODXJuniorSettings,
    profile_name: str
) -> ToolResponse:
    """
    Summarize what a profile has learned for this project.

    Args:
        manager: Project ProfileManager.
        settings: Project settings.
        profile_name: Profile to inspect (empty to list profiles with material).

    Returns:
        ToolResponse with the overview (user) and the structured state (model).
    """
    if not profile_name:
        names = _profiles_with_learning(settings=settings, manager=manager)
        if not names:
            return ToolResponse(
                user_response="> No profile has learned anything in this project yet.",
                llm_response=json.dumps(
                    {
                        "profiles": [],
                        "next": (
                            "Nothing stored yet. Use action='remember' for a short "
                            "durable rule or action='write_file' for reference "
                            "material."
                        ),
                    },
                    indent=2,
                ),
            )
        return ToolResponse(
            user_response="\n".join([
                f"### Profiles with learned material ({len(names)})",
                "",
                *[f"- `{name}`" for name in names],
            ]),
            llm_response=json.dumps(
                {
                    "profiles": names,
                    "next": (
                        "Call action='overview' with one of these 'profile_name' "
                        "values to inspect it."
                    ),
                },
                indent=2,
            ),
        )

    overview = manager.profile_knowledge_overview(profile_name)
    rules = overview["rules"]
    limits = overview["limits"]

    lines = [f"### Profile knowledge: `{profile_name}`", ""]
    if rules:
        lines.append(
            f"**Learned rules** — {overview['rules_count']} rule(s), "
            f"{overview['rules_chars']} chars (limit {limits['max_rule_chars']} "
            "chars/rule; these are injected in EVERY chat)"
        )
        for rule in rules:
            scope = "editable" if rule["editable"] else f"inherited: {rule['source']}"
            lines.append(
                f"- **{rule['title']}** ({len(rule['content'])} chars, {scope}) — "
                f"{_first_line(rule['content'])}"
            )
    else:
        lines.append("> No learned rules yet.")
    lines.append("")
    lines.append(_knowledge_table(overview["knowledge_files"], settings))
    lines.append("")
    lines.append(
        f"Rules file: `{_relative_to_project(settings, overview['rules_file'])}`"
    )
    lines.append(
        f"Knowledge folder: "
        f"`{_relative_to_project(settings, overview['knowledge_folder'])}/`"
    )
    lines.append(
        "\n> Use `read` (with `title` or `file_name`) to see the full content, "
        "`remember`/`forget` for rules, `write_file`/`delete_file` for files and "
        "`promote` to move content between the two."
    )

    llm_response = json.dumps(
        {
            "profile": profile_name,
            "rules": [
                {
                    "title": rule["title"],
                    "chars": len(rule["content"]),
                    "source": rule["source"],
                    "editable": rule["editable"],
                    "preview": _first_line(rule["content"]),
                }
                for rule in rules
            ],
            "knowledge_files": [
                {
                    "file": entry["file"],
                    "source": entry["source"],
                    "size": entry["size"],
                    "path": entry["path"],
                }
                for entry in overview["knowledge_files"]
            ],
            "rules_file": overview["rules_file"],
            "knowledge_folder": overview["knowledge_folder"],
            "limits": limits,
        },
        indent=2,
    )
    return ToolResponse(user_response="\n".join(lines), llm_response=llm_response)


def _action_search(
    manager: ProfileManager,
    settings: CODXJuniorSettings,
    profiles: List[str],
    query: str,
    limit: int
) -> ToolResponse:
    """
    Search what the profiles have learned (knowledge matches).

    Args:
        manager: Project ProfileManager.
        settings: Project settings.
        profiles: Profiles to search.
        query: Search terms or natural-language question.
        limit: Maximum number of knowledge matches.

    Returns:
        ToolResponse with the excerpts (user) and the matches (model).
    """
    try:
        results = _semantic_search(
            settings=settings, profiles=profiles, query=query, limit=limit
        )
    except Exception as ex:
        logger.warning(
            "profile_learning: semantic search unavailable (%s); falling back to "
            "term search",
            ex,
        )
        results = _term_search(
            manager=manager, profiles=profiles, query=query, limit=limit
        )

    profiles_label = ", ".join(profiles)

    if not results:
        return ToolResponse(
            user_response=(
                f"✓ No profile knowledge matching `{query}` in {profiles_label}"
            ),
            llm_response=json.dumps(
                {
                    "profiles": profiles,
                    "query": query,
                    "count": 0,
                    "results": [],
                    "next": (
                        "Nothing matched. Do not invent knowledge: if the "
                        "information is durable, learn it now with "
                        "action='remember' (short rule) or action='write_file' "
                        "(reference material)."
                    ),
                },
                indent=2,
            ),
        )

    user_lines = [f"### Profile knowledge: {profiles_label}", f"> Query: `{query}`", ""]
    for result in results:
        user_lines.extend([
            f"**`{result['file'] or result['path']}`** — profile "
            f"`{result['profile']}` — {result['level']} — "
            f"score {_score(result):.4f}",
            f"`{_relative_to_project(settings, result['path'])}`",
            "",
            "```markdown",
            _excerpt(result["excerpt"]),
            "```",
            "",
        ])

    llm_response = json.dumps(
        {
            "profiles": profiles,
            "query": query,
            "count": len(results),
            "results": [
                {
                    "profile": result["profile"],
                    "level": result["level"],
                    "file": result["file"],
                    "path": result["path"],
                    "score": _score(result),
                    "content": _excerpt(result["excerpt"]),
                }
                for result in results
            ],
        },
        indent=2,
    )

    logger.info(
        "profile_learning: search '%s' in %s returned %d result(s)",
        query,
        profiles_label,
        len(results),
    )
    return ToolResponse(user_response="\n".join(user_lines), llm_response=llm_response)


def _action_read(
    manager: ProfileManager,
    settings: CODXJuniorSettings,
    profile_name: str,
    title: Optional[str],
    file_name: Optional[str]
) -> ToolResponse:
    """
    Read a learned rule (by ``title``) or a knowledge file (by ``file_name``).

    Args:
        manager: Project ProfileManager.
        settings: Project settings.
        profile_name: Profile name.
        title: Rule title.
        file_name: Knowledge file path relative to the knowledge folder.

    Returns:
        ToolResponse with the content.

    Raises:
        ValueError: When neither argument is given or the resource is missing.
    """
    if title:
        rule = manager.find_profile_rule(profile_name=profile_name, title=title)
        if not rule:
            raise ValueError(
                f"Rule '{title}' not found for profile '{profile_name}'."
            )
        scope = "editable" if rule["editable"] else "inherited (read-only)"
        user_response = "\n".join([
            f"### Rule `{rule['title']}` — profile `{profile_name}`",
            f"> Level: **{rule['source']}** — {scope} — "
            f"`{_relative_to_project(settings, rule['path'])}`",
            "",
            "```markdown",
            rule["content"],
            "```",
        ])
        return ToolResponse(
            user_response=user_response,
            llm_response=json.dumps(
                {
                    "profile": profile_name,
                    "rule": rule["title"],
                    "source": rule["source"],
                    "path": rule["path"],
                    "editable": rule["editable"],
                    "content": rule["content"],
                },
                indent=2,
            ),
        )

    if not file_name:
        raise ValueError(
            "read requires 'title' (learned rule) or 'file_name' (knowledge file)"
        )

    content = manager.read_profile_knowledge(
        profile_name=profile_name, file_name=file_name
    )
    entry = manager._resolve_knowledge_file(profile_name, file_name) or {}

    user_response = "\n".join([
        f"### `{file_name}` — profile `{profile_name}`",
        f"> Level: **{entry.get('source', 'unknown')}** — "
        f"`{_relative_to_project(settings, entry.get('path', file_name))}`",
        "",
        "```markdown",
        content,
        "```",
    ])
    return ToolResponse(
        user_response=user_response,
        llm_response=json.dumps(
            {
                "profile": profile_name,
                "file": file_name,
                "source": entry.get("source", ""),
                "path": entry.get("path", ""),
                "content": content,
            },
            indent=2,
        ),
    )


def _action_remember(
    manager: ProfileManager,
    settings: CODXJuniorSettings,
    profile_name: str,
    title: Optional[str],
    content: Optional[str]
) -> ToolResponse:
    """
    Learn a RULE: create or replace a short instruction for this project.

    Args:
        manager: Project ProfileManager.
        settings: Project settings.
        profile_name: Profile to teach.
        title: Rule title (identifier).
        content: Instruction markdown.

    Returns:
        ToolResponse describing where the rule was stored.
    """
    text = _validate_text(content, "content", MAX_RULE_CHARS)
    rule_title = (title or "").strip() or _first_line(text, 60)
    result = manager.upsert_profile_rule(
        profile_name=profile_name, title=rule_title, text=text
    )

    user_response = "\n".join([
        f"### Rule {'created' if result['created'] else 'updated'} for "
        f"`{profile_name}`",
        "",
        f"- Title: **{result['title']}**",
        f"- Stored in: `{_relative_to_project(settings, result['path'])}`",
        f"- Rules now: {result['rules']} (each one is injected in every chat)",
        f"- Applies to: project **{settings.project_name}** and its children "
        "while they do not define the profile themselves",
        "",
        "```markdown",
        text,
        "```",
    ])
    return ToolResponse(
        user_response=user_response,
        llm_response=json.dumps(
            {
                "action": ACTION_REMEMBER,
                "profile": profile_name,
                "title": result["title"],
                "created": result["created"],
                "rules": result["rules"],
                "path": _relative_to_project(settings, result["path"]),
                "scope": settings.project_name,
            },
            indent=2,
        ),
    )


def _action_forget(
    manager: ProfileManager,
    settings: CODXJuniorSettings,
    profile_name: str,
    title: Optional[str]
) -> ToolResponse:
    """
    Forget a RULE learned by this project.

    Args:
        manager: Project ProfileManager.
        settings: Project settings.
        profile_name: Profile name.
        title: Rule title.

    Returns:
        ToolResponse confirming the removal.
    """
    rule_title = _validate_text(title, "title", MAX_QUERY_CHARS)
    path = manager.delete_profile_rule(profile_name=profile_name, title=rule_title)

    user_response = "\n".join([
        f"### Rule forgotten by `{profile_name}`",
        "",
        f"- Title: **{rule_title}**",
        f"- File: `{_relative_to_project(settings, path)}`",
        "",
        "> Inherited rules (parent projects, base profile) are read-only.",
    ])
    return ToolResponse(
        user_response=user_response,
        llm_response=json.dumps(
            {
                "action": ACTION_FORGET,
                "profile": profile_name,
                "title": rule_title,
                "path": _relative_to_project(settings, path),
            },
            indent=2,
        ),
    )


def _action_write_file(
    manager: ProfileManager,
    settings: CODXJuniorSettings,
    profile_name: str,
    file_name: Optional[str],
    content: Optional[str],
    overwrite: bool
) -> ToolResponse:
    """
    Learn reference material: create or update a knowledge file.

    Args:
        manager: Project ProfileManager.
        settings: Project settings.
        profile_name: Profile to teach.
        file_name: Path relative to the knowledge folder.
        content: File body.
        overwrite: Replace the file when it exists.

    Returns:
        ToolResponse describing the written file.
    """
    text = _validate_text(content, "content", MAX_FILE_ARG_CHARS)
    relative_path = _validate_text(file_name, "file_name", MAX_FILE_NAME_CHARS)
    path = manager.save_profile_knowledge(
        profile_name=profile_name,
        file_name=relative_path,
        content=text,
        overwrite=bool(overwrite),
    )

    user_response = "\n".join([
        f"### Knowledge saved for `{profile_name}`",
        "",
        f"- File: `{_relative_to_project(settings, path)}`",
        f"- Project: **{settings.project_name}**",
        f"- Size: {len(text)} chars (indexed, retrieved on demand)",
        "- Searchable with `profile_learning` (`action='search'`) from now on.",
    ])
    return ToolResponse(
        user_response=user_response,
        llm_response=json.dumps(
            {
                "action": ACTION_WRITE_FILE,
                "profile": profile_name,
                "file": os.path.relpath(
                    path, manager.profile_knowledge_path(profile_name)
                ),
                "path": _relative_to_project(settings, path),
                "chars": len(text),
                "scope": settings.project_name,
            },
            indent=2,
        ),
    )


def _action_delete_file(
    manager: ProfileManager,
    settings: CODXJuniorSettings,
    profile_name: str,
    file_name: Optional[str]
) -> ToolResponse:
    """
    Delete a knowledge file owned by this project.

    Args:
        manager: Project ProfileManager.
        settings: Project settings.
        profile_name: Profile name.
        file_name: Path relative to the knowledge folder.

    Returns:
        ToolResponse confirming the deletion.
    """
    relative_path = _validate_text(file_name, "file_name", MAX_FILE_NAME_CHARS)
    path = manager.delete_profile_knowledge(
        profile_name=profile_name, file_name=relative_path
    )

    user_response = "\n".join([
        f"### Knowledge deleted from `{profile_name}`",
        "",
        f"- File: `{_relative_to_project(settings, path)}`",
        f"- Project: **{settings.project_name}**",
        "",
        "> Base and parent knowledge files are read-only: only this project's "
        "files can be deleted.",
    ])
    return ToolResponse(
        user_response=user_response,
        llm_response=json.dumps(
            {
                "action": ACTION_DELETE_FILE,
                "profile": profile_name,
                "path": _relative_to_project(settings, path),
            },
            indent=2,
        ),
    )


def _action_promote(
    manager: ProfileManager,
    settings: CODXJuniorSettings,
    profile_name: str,
    title: Optional[str],
    file_name: Optional[str],
    direction: Optional[str],
    keep_source: bool
) -> ToolResponse:
    """
    Move content between the two stores (rule ⇄ knowledge file).

    Args:
        manager: Project ProfileManager.
        settings: Project settings.
        profile_name: Profile name.
        title: Rule title (source or target depending on the direction).
        file_name: Knowledge file (source or target depending on the direction).
        direction: ``rule_to_file`` or ``file_to_rule``.
        keep_source: Keep the source after copying.

    Returns:
        ToolResponse describing the promotion.

    Raises:
        ValueError: On a missing/unknown direction or arguments.
    """
    direction = (direction or "").strip().lower()
    if direction not in DIRECTIONS:
        raise ValueError(
            f"promote requires 'direction': {', '.join(DIRECTIONS)}"
        )

    if direction == DIRECTION_RULE_TO_FILE:
        if not title:
            raise ValueError("promote rule_to_file requires 'title'")
        result = manager.promote_profile_rule_to_knowledge(
            profile_name=profile_name,
            title=title,
            file_name=file_name,
            delete_rule=not keep_source,
        )
        user_response = "\n".join([
            f"### Rule promoted to knowledge: `{profile_name}`",
            "",
            f"- Rule: **{result['title']}**",
            f"- File: `{_relative_to_project(settings, result['path'])}`",
            f"- Rule removed: {result['rule_deleted']}",
            "",
            "> It is now indexed and retrieved only when relevant, so it no "
            "longer costs prompt tokens on every chat.",
        ])
    else:
        if not file_name:
            raise ValueError("promote file_to_rule requires 'file_name'")
        result = manager.profile_knowledge_promote_to_rule(
            profile_name=profile_name,
            file_name=file_name,
            title=title,
            delete_file=not keep_source,
        )
        user_response = "\n".join([
            f"### Knowledge promoted to rule: `{profile_name}`",
            "",
            f"- Rule: **{result['title']}**",
            f"- Stored in: `{_relative_to_project(settings, result['path'])}`",
            f"- File removed: {result['file_deleted']}",
            "",
            "> It is now injected in every chat where the profile is active: "
            "keep rules short and imperative.",
        ])

    return ToolResponse(
        user_response=user_response,
        llm_response=json.dumps({"action": ACTION_PROMOTE, **result}, indent=2),
    )


# ---------------------------------------------------------------------------
# Tool entry point
# ---------------------------------------------------------------------------


def profile_learning(
    action: str,
    profile_name: Optional[str] = None,
    query: Optional[str] = None,
    file_name: Optional[str] = None,
    content: Optional[str] = None,
    title: Optional[str] = None,
    direction: Optional[str] = None,
    overwrite: bool = False,
    keep_source: bool = False,
    limit: int = DEFAULT_LIMIT,
    session: Any = None,
    **kwargs
) -> ToolResponse:
    """
    Read, search and update what a profile has learned for this project.

    Actions:
        - ``overview``: rules + knowledge files + writable locations and limits.
        - ``search``: semantic search over the knowledge of one (or all) profile.
        - ``read``: read a rule (``title``) or a knowledge file (``file_name``).
        - ``remember``: create/replace a short RULE (``title`` + ``content``).
        - ``forget``: remove a rule (``title``).
        - ``write_file``: create/update a knowledge file (``file_name`` + ``content``).
        - ``delete_file``: remove a knowledge file (``file_name``).
        - ``promote``: move a rule to a file or a file to a rule (``direction``).

    Args:
        action: One of :data:`VALID_ACTIONS`.
        profile_name: Profile that learns or is consulted. Optional for
            ``overview`` (listing) and ``search`` (all profiles with knowledge).
        query: Search terms for ``search``.
        file_name: Knowledge file path relative to the profile knowledge folder.
        content: Rule text (``remember``) or file body (``write_file``).
        title: Rule title, used as its identifier.
        direction: ``rule_to_file`` or ``file_to_rule`` (``promote``).
        overwrite: Replace an existing knowledge file.
        keep_source: Keep the source when promoting.
        limit: Maximum number of search results (1-50).
        session: Injected by the agent runtime (``ToolSettings.session``).
        **kwargs: Injected by the agent runtime: ``settings``.

    Returns:
        ToolResponse: ``user_response`` for the chat, ``llm_response`` with the
        machine-readable result for the model.

    Raises:
        Exception: If the project settings are missing.

    Example:
        >>> profile_learning("search", profile_name="software_developer",
        ...                  query="angular signals")
        >>> profile_learning("remember", profile_name="software_developer",
        ...                  title="Angular conventions",
        ...                  content="Always use standalone components.")
        >>> profile_learning("write_file", profile_name="software_developer",
        ...                  file_name="guidelines/state.md",
        ...                  content="# State management\\n...")
        >>> profile_learning("promote", profile_name="software_developer",
        ...                  direction="rule_to_file", title="Angular conventions")
    """
    settings: CODXJuniorSettings = kwargs.get("settings")
    if not settings:
        raise Exception("Invalid project settings")
    if session is None:
        session = getattr(settings, "_active_session", None)

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

    manager = ProfileManager(settings=settings)
    profile_name = (profile_name or "").strip()

    try:
        if action in WRITE_ACTIONS:
            _require_knowledge_permission(
                settings=settings, user=_current_user(settings=settings, session=session)
            )

        if profile_name and not manager.profile_exists(profile_name):
            raise ValueError(
                f"Unknown profile '{profile_name}': it does not exist in this "
                "project, in a parent project or in the base profiles."
            )

        if action == ACTION_OVERVIEW:
            return _action_overview(
                manager=manager,
                settings=settings,
                profile_name=profile_name,
            )

        if action == ACTION_SEARCH:
            query = _validate_text(query, "query", MAX_QUERY_CHARS)
            profiles = [profile_name] if profile_name \
                else _profiles_with_learning(settings=settings, manager=manager)
            if not profiles:
                return ToolResponse(
                    user_response="> No profile knowledge found in this project.",
                    llm_response=json.dumps(
                        {
                            "profiles": [],
                            "query": query,
                            "count": 0,
                            "next": (
                                "No profile has a knowledge folder in this project "
                                "or its parents. Use action='write_file' (requires "
                                "project admin, project knowledge admin or "
                                "codx-junior admin) to create the first one."
                            ),
                        },
                        indent=2,
                    ),
                )
            return _action_search(
                manager=manager,
                settings=settings,
                profiles=profiles,
                query=query,
                limit=limit,
            )

        if not profile_name:
            raise ValueError(
                f"profile_name is required for '{action}': it is the profile that "
                "learns or forgets."
            )

        if action == ACTION_READ:
            return _action_read(
                manager=manager,
                settings=settings,
                profile_name=profile_name,
                title=title,
                file_name=file_name,
            )

        if action == ACTION_REMEMBER:
            return _action_remember(
                manager=manager,
                settings=settings,
                profile_name=profile_name,
                title=title,
                content=content,
            )

        if action == ACTION_FORGET:
            return _action_forget(
                manager=manager,
                settings=settings,
                profile_name=profile_name,
                title=title,
            )

        if action == ACTION_WRITE_FILE:
            return _action_write_file(
                manager=manager,
                settings=settings,
                profile_name=profile_name,
                file_name=file_name,
                content=content,
                overwrite=overwrite,
            )

        if action == ACTION_DELETE_FILE:
            return _action_delete_file(
                manager=manager,
                settings=settings,
                profile_name=profile_name,
                file_name=file_name,
            )

        return _action_promote(
            manager=manager,
            settings=settings,
            profile_name=profile_name,
            title=title,
            file_name=file_name,
            direction=direction,
            keep_source=keep_source,
        )

    except PermissionError as ex:
        logger.warning("profile_learning(%s): %s", action, ex)
        return ToolResponse(
            user_response=f"🔒 {ex}",
            llm_response=(
                f"profile_learning action '{action}' denied: {ex} Do not retry: "
                "keep working and mention it to the user, or ask for knowledge "
                "administration rights on the project."
            ),
        )
    except ValueError as ex:
        logger.warning("profile_learning(%s): %s", action, ex)
        return ToolResponse(
            user_response=f"❌ {ex}",
            llm_response=f"profile_learning action '{action}' failed: {ex}",
        )
    except Exception as ex:
        logger.exception("profile_learning(%s): unexpected error", action)
        return ToolResponse(
            user_response=f"❌ Error: {ex}",
            llm_response=f"profile_learning action '{action}' failed: {ex}",
        )


# ---------------------------------------------------------------------------
# Tool JSON definition
# ---------------------------------------------------------------------------

PROFILE_LEARNING_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "profile_learning",
        "description": (
            "Your long-term memory for THIS project: read, search and update what "
            "this profile has learned. "
            "\n\nBE PROACTIVE — do not wait to be asked. Whenever you learn "
            "something durable about how this project must be worked on (a "
            "convention, an architecture decision, a user preference, a gotcha, a "
            "command, an external reference), store it immediately with this tool "
            "and mention in one line what you stored. Never store secrets, tokens, "
            "credentials or transient state. Ignore one-off details: if it will not "
            "change a future chat, do not store it."
            "\n\nTWO STORES — choose the cheaper one:"
            "\n- RULES ('remember'): short instructions (max ~200 words), always "
            "relevant. They are injected into EVERY chat, so they cost prompt "
            "tokens: use them for conventions and hard requirements only, and "
            "update them by title instead of adding near-duplicates ('forget' "
            "removes them)."
            "\n- KNOWLEDGE FILES ('write_file'): anything long (examples, tables, "
            "code, docs, meeting notes). They are indexed and retrieved only when "
            "relevant."
            "\nIf a rule grew too long, 'promote' it to a file; if a file is really "
            "a short durable instruction, 'promote' it to a rule."
            "\n\nUse 'search' before answering anything that depends on "
            "project-specific conventions ('our guidelines', 'what we agreed', "
            "'how do we do X here'), and 'overview' when unsure what is already "
            "stored. Reading is open to every project user; writing requires "
            "project admin, project knowledge admin or codx-junior admin rights."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": VALID_ACTIONS,
                    "description": (
                        "Operation:\n"
                        "  - 'overview': what is stored (rules, files, locations, limits)\n"
                        "  - 'search': semantic search over the stored knowledge\n"
                        "  - 'read': read a rule ('title') or a file ('file_name')\n"
                        "  - 'remember': create/replace a short RULE (admin)\n"
                        "  - 'forget': remove a rule (admin)\n"
                        "  - 'write_file': create/update a knowledge FILE (admin)\n"
                        "  - 'delete_file': remove a knowledge file (admin)\n"
                        "  - 'promote': move a rule to a file or a file to a rule (admin)"
                    )
                },
                "profile_name": {
                    "type": "string",
                    "description": (
                        "Profile that learns or is consulted (the profile running "
                        "this chat, e.g. 'software_developer'). Optional for "
                        "'overview' and 'search' (searches every profile)."
                    )
                },
                "query": {
                    "type": "string",
                    "description": (
                        "For 'search': topic, question or keywords to look for."
                    )
                },
                "file_name": {
                    "type": "string",
                    "description": (
                        "Knowledge file path relative to the profile knowledge "
                        "folder (e.g. 'guidelines/state.md'). '.md' is added when "
                        "no extension is given. Text extensions only."
                    )
                },
                "content": {
                    "type": "string",
                    "description": (
                        "For 'remember': the rule itself — concise, imperative, "
                        f"Markdown, at most {MAX_RULE_CHARS} characters. "
                        "For 'write_file': the full file body."
                    )
                },
                "title": {
                    "type": "string",
                    "description": (
                        "For 'remember' and 'forget': the rule identifier "
                        "(e.g. 'Angular conventions'). Writing an existing title "
                        "replaces that rule instead of adding a duplicate."
                    )
                },
                "direction": {
                    "type": "string",
                    "enum": DIRECTIONS,
                    "description": (
                        "For 'promote': 'rule_to_file' (rule too long for the "
                        "prompt) or 'file_to_rule' (file is really a short durable "
                        "instruction)."
                    )
                },
                "overwrite": {
                    "type": "boolean",
                    "description": (
                        "For 'write_file': replace the file when it already exists "
                        "(read it first). Defaults to false."
                    ),
                    "default": False
                },
                "keep_source": {
                    "type": "boolean",
                    "description": (
                        "For 'promote': keep the original rule/file after copying "
                        "it. Defaults to false (a promotion is a move)."
                    ),
                    "default": False
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        f"For 'search': maximum number of matches (default "
                        f"{DEFAULT_LIMIT}, max 50)."
                    ),
                    "default": DEFAULT_LIMIT
                }
            },
            "required": ["action"]
        }
    }
}

# Made with ❤️ by codx-junior