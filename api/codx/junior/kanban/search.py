"""
Project-wide task search for the Kanban section.

Why a dedicated search module
-----------------------------
The board views used to filter only the tasks the client already had in memory,
which is not the whole project: ``GET /api/chats`` defaults to the last 30 days
and the board sidebar only sees one board. Users with many boards and long-lived
tasks lost the ability to find a card by name, description, profile, assignee or
last message.

This module builds a compact snapshot of **every task file of the project**
(``.codx/tasks/**``), scores it against the query and applies the same filters
the board UI offers. It never loads the whole message history: the chat manager
returns chats with their last message, which is enough for discovery and keeps
the search cheap.

The snapshot is cached for :data:`CACHE_TTL_SECONDS` because the UI sends one
request per keystroke. Created / moved boards and columns invalidate it
immediately; a task saved in place becomes visible on the next search after the
short TTL (chat files are not re-read per keystroke).

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

#: How long a snapshot is reused. Short enough that a task saved from another
#: browser tab shows up while the user is still typing.
CACHE_TTL_SECONDS = 5.0

#: Maximum number of matches returned by one call.
MAX_LIMIT = 100
DEFAULT_LIMIT = 40

#: Descriptions feed the prompt/UI only; the full text lives in the task.
MAX_DESCRIPTION_CHARS = 2000
MAX_MESSAGE_CHARS = 1000
MAX_SNIPPET_CHARS = 220

_CACHE_LOCK = threading.Lock()
_CACHE: Dict[str, Tuple[float, float, List[Dict[str, Any]]]] = {}


def _text(value: Any, max_chars: int = 0) -> str:
    """Convert *value* to a stripped string, optionally clipped."""
    text = "" if value is None else str(value).strip()
    if max_chars and len(text) > max_chars:
        return text[:max_chars].rstrip() + "…"
    return text


def _as_list(value: Any) -> List[str]:
    """Normalize a string/iterable into a clean list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    try:
        return [str(item).strip() for item in value if str(item or "").strip()]
    except TypeError:
        return []


def _unique(values: Iterable[Any], limit: int = 200) -> List[str]:
    """Return unique, non-empty strings preserving the first spelling seen."""
    seen = set()
    result: List[str] = []
    for value in values:
        text = _text(value)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def clear_cache() -> None:
    """Drop every cached snapshot (tests and manual invalidation)."""
    with _CACHE_LOCK:
        _CACHE.clear()


def _directory_stamp(tasks_path: str) -> float:
    """
    Return a cheap fingerprint of the tasks tree.

    ``os.path.getmtime`` of the root only changes when a directory entry of the
    root changes (new board / column), not when an existing task file is saved.
    The newest ``mtime`` of the root and the first two directory levels is used
    instead: cheap to compute and enough to invalidate on any task save.
    """
    newest = 0.0
    try:
        newest = os.path.getmtime(tasks_path)
    except OSError:
        return time.time()
    try:
        for name in os.listdir(tasks_path):
            board_path = os.path.join(tasks_path, name)
            if not os.path.isdir(board_path):
                continue
            try:
                newest = max(newest, os.path.getmtime(board_path))
            except OSError:
                continue
            try:
                for column in os.listdir(board_path):
                    column_path = os.path.join(board_path, column)
                    if os.path.isdir(column_path):
                        newest = max(newest, os.path.getmtime(column_path))
            except OSError:
                continue
    except OSError:
        pass
    return newest


def _last_message(chat: Any) -> str:
    """Return the content of the last visible message of *chat*."""
    messages = getattr(chat, "messages", None) or []
    for message in reversed(messages):
        content = _text(getattr(message, "content", ""))
        if content and not getattr(message, "hide", False):
            return content
    return ""


def _task_from_chat(chat: Any) -> Optional[Dict[str, Any]]:
    """
    Build the searchable snapshot of one chat.

    Templates and channel chats are not tasks: templates are blueprints and a
    channel is a conversation container, so neither belongs in a task search.
    """
    chat_id = _text(getattr(chat, "id", ""))
    if not chat_id:
        return None
    if getattr(chat, "is_template", False):
        return None
    if _text(getattr(chat, "mode", "")).lower() == "channel":
        return None

    name = _text(getattr(chat, "name", ""))
    description = _text(getattr(chat, "description", ""), MAX_DESCRIPTION_CHARS)
    last_message = _text(_last_message(chat), MAX_MESSAGE_CHARS)
    board = _text(getattr(chat, "board", ""))
    column = _text(getattr(chat, "column", ""))
    status = _text(getattr(chat, "status", ""))
    sprints = _as_list(getattr(chat, "sprints", []))
    profiles = _as_list(getattr(chat, "profiles", []))
    users = _unique(
        _as_list(getattr(chat, "users", []))
        + _as_list(getattr(chat, "assignees", []))
    )
    tags = _as_list(getattr(chat, "tags", []))
    boards = _unique([board, *sprints]) if (board or sprints) else []

    return {
        "id": chat_id,
        "name": name,
        "description": description,
        "last_message": last_message,
        "board": board,
        "column": column,
        "status": status,
        "priority": _text(getattr(chat, "priority", "")),
        "due_date": _text(getattr(chat, "due_date", "")),
        "progress": int(getattr(chat, "progress", 0) or 0),
        "mode": _text(getattr(chat, "mode", "")),
        "profiles": profiles,
        "users": users,
        "tags": tags,
        "sprints": sprints,
        "boards": boards,
        "owner_project_id": _text(getattr(chat, "owner_project_id", "")),
        "project_id": _text(getattr(chat, "project_id", "")),
        "run_id": _text(getattr(chat, "run_id", "")),
        "run_status": _text(getattr(chat, "run_status", "")),
        "created_at": _text(getattr(chat, "created_at", "")),
        "updated_at": _text(getattr(chat, "updated_at", "")),
        "cost": float(getattr(chat, "cost", 0.0) or 0.0),
    }


def build_index(chat_manager: Any, force: bool = False) -> List[Dict[str, Any]]:
    """
    Return the searchable task snapshots of one project.

    Args:
        chat_manager: A ``ChatManager`` for the project.
        force: Bypass the snapshot cache.

    Returns:
        Task dictionaries, most recently updated first.
    """
    tasks_path = _text(getattr(chat_manager, "chat_path", ""))
    stamp = _directory_stamp(tasks_path)
    now = time.monotonic()

    with _CACHE_LOCK:
        cached = _CACHE.get(tasks_path)
        if cached and not force:
            expires_at, cached_stamp, tasks = cached
            if expires_at > now and cached_stamp == stamp:
                return tasks

    chats = chat_manager.list_chats()
    tasks = [task for task in (_task_from_chat(chat) for chat in chats or []) if task]
    tasks.sort(key=lambda task: task.get("updated_at") or "", reverse=True)

    with _CACHE_LOCK:
        _CACHE[tasks_path] = (now + CACHE_TTL_SECONDS, stamp, tasks)
    logger.debug("kanban search: indexed %d task(s) from '%s'", len(tasks), tasks_path)
    return tasks


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

#: Field weights: the name is what a user types first, metadata next, messages
#: last (they are the most expensive to match and the least precise).
FIELD_WEIGHTS = (
    ("name", 8.0),
    ("description", 3.0),
    ("board", 2.5),
    ("column", 2.0),
    ("status", 2.0),
    ("priority", 1.0),
    ("profiles", 2.5),
    ("users", 2.0),
    ("tags", 1.5),
    ("last_message", 1.2),
)


def _haystack(task: Dict[str, Any]) -> str:
    """Return every searchable value of *task* as one lowercase string."""
    parts: List[str] = [
        task.get("name") or "",
        task.get("description") or "",
        task.get("board") or "",
        task.get("column") or "",
        task.get("status") or "",
        task.get("priority") or "",
        task.get("last_message") or "",
    ]
    for key in ("profiles", "users", "tags", "sprints"):
        parts.extend(task.get(key) or [])
    return " ".join(parts).lower()


def _terms(query: str) -> List[str]:
    """Split a query into lowercase terms (AND semantics)."""
    return [term for term in str(query or "").lower().split() if term]


def _score(task: Dict[str, Any], terms: Sequence[str], query: str) -> Optional[float]:
    """
    Score *task* against *terms*, or return None when it does not match.

    Every term must appear somewhere (AND semantics) so "login timeout" does
    not return every card mentioning either word. ``FIELD_WEIGHTS`` decides how
    much each place is worth.
    """
    haystack = _haystack(task)
    if any(term not in haystack for term in terms):
        return None

    score = 0.0
    for field, weight in FIELD_WEIGHTS:
        values = task.get(field)
        if isinstance(values, list):
            text = " ".join(str(value or "") for value in values).lower()
        else:
            text = str(values or "").lower()
        if not text:
            continue
        for term in terms:
            if term in text:
                score += weight
                # A term at the very start of the most important field wins.
                if field == "name" and text.startswith(term):
                    score += weight
        if field == "name" and text.strip() == query:
            # Exact title match: the strongest signal when several cards share
            # a word ("Deploy" over "Deploy pipeline notes").
            score += weight
    if query and query in haystack:
        score += 6.0
    # Boost open tasks: a closed task is usually not what "find" should show
    # first when both match the same query.
    if (task.get("status") or "").lower() not in {"done", "rejected"}:
        score += 0.5
    return score


def _snippet(task: Dict[str, Any], terms: Sequence[str]) -> str:
    """Return a short excerpt around the first term found in text fields."""
    candidates = [
        task.get("description") or "",
        task.get("last_message") or "",
        task.get("name") or "",
    ]
    for text in candidates:
        if not text:
            continue
        lowered = text.lower()
        position = -1
        for term in terms:
            position = lowered.find(term)
            if position >= 0:
                break
        if position < 0:
            continue
        start = max(0, position - 60)
        end = min(len(text), position + MAX_SNIPPET_CHARS - 60)
        prefix = "…" if start else ""
        suffix = "…" if end < len(text) else ""
        return f"{prefix}{text[start:end].strip()}{suffix}"
    return _text(task.get("description") or task.get("last_message") or "", MAX_SNIPPET_CHARS)


def _matches_filter(task: Dict[str, Any], key: str, wanted: str) -> bool:
    """Apply one case-insensitive filter, with board/sprint awareness."""
    if not wanted:
        return True
    lowered = wanted.strip().lower()
    if key == "board":
        return any(str(board).strip().lower() == lowered for board in task.get("boards") or [])
    if key == "profile":
        return any(str(profile).strip().lower() == lowered for profile in task.get("profiles") or [])
    if key == "assignee":
        return any(str(user).strip().lower() == lowered for user in task.get("users") or [])
    return str(task.get(key) or "").strip().lower() == lowered


def _public_result(task: Dict[str, Any], score: float, terms: Sequence[str]) -> Dict[str, Any]:
    """Return the API shape of a matched task (no full message history)."""
    return {
        "id": task["id"],
        "name": task.get("name") or "",
        "description": _text(task.get("description") or "", 600),
        "snippet": _snippet(task, terms),
        "board": task.get("board") or "",
        "column": task.get("column") or "",
        "status": task.get("status") or "",
        "priority": task.get("priority") or "",
        "due_date": task.get("due_date") or "",
        "progress": task.get("progress") or 0,
        "mode": task.get("mode") or "",
        "profiles": task.get("profiles") or [],
        "users": task.get("users") or [],
        "tags": task.get("tags") or [],
        "sprints": task.get("sprints") or [],
        "boards": task.get("boards") or [],
        "owner_project_id": task.get("owner_project_id") or "",
        "project_id": task.get("project_id") or "",
        "run_id": task.get("run_id") or "",
        "run_status": task.get("run_status") or "",
        "created_at": task.get("created_at") or "",
        "updated_at": task.get("updated_at") or "",
        "score": round(score, 3),
    }


def _facets(tasks: Sequence[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Build the values offered by the filter dropdowns."""
    return {
        "boards": _unique(
            board
            for task in tasks
            for board in (task.get("boards") or [])
        ),
        "columns": _unique(task.get("column") for task in tasks),
        "statuses": _unique(task.get("status") for task in tasks),
        "priorities": _unique(task.get("priority") for task in tasks),
        "profiles": _unique(
            profile for task in tasks for profile in (task.get("profiles") or [])
        ),
        "assignees": _unique(
            user for task in tasks for user in (task.get("users") or [])
        ),
    }


def search_tasks(
    chat_manager: Any,
    query: str = "",
    *,
    board: str = "",
    column: str = "",
    status: str = "",
    priority: str = "",
    profile: str = "",
    assignee: str = "",
    include_done: bool = True,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Search every task of the project.

    Args:
        chat_manager: Project ``ChatManager``.
        query: Free text. Every whitespace-separated term must match.
        board: Board or sprint title filter (case insensitive).
        column: Kanban column title filter.
        status: Task status filter.
        priority: ``high`` / ``medium`` / ``low``.
        profile: Profile name carried by the task.
        assignee: User / assignee name carried by the task.
        include_done: When False, tasks whose status is ``done`` are hidden.
        limit: Page size (clamped to :data:`MAX_LIMIT`).
        offset: Matches to skip (pagination).

    Returns:
        ``{"query", "total", "offset", "limit", "results", "facets"}``.
    """
    tasks = build_index(chat_manager)
    terms = _terms(query)
    normalized_query = " ".join(terms)

    filtered: List[Tuple[float, Dict[str, Any]]] = []
    for task in tasks:
        if not include_done and str(task.get("status") or "").lower() == "done":
            continue
        if not _matches_filter(task, "board", board):
            continue
        if not _matches_filter(task, "column", column):
            continue
        if not _matches_filter(task, "status", status):
            continue
        if not _matches_filter(task, "priority", priority):
            continue
        if not _matches_filter(task, "profile", profile):
            continue
        if not _matches_filter(task, "assignee", assignee):
            continue
        if terms:
            score = _score(task, terms, normalized_query)
            if score is None:
                continue
        else:
            score = 0.0
        filtered.append((score, task))

    # Stable two-pass sort: most recently updated first, then by score. Cards
    # with the same score therefore keep the recency order, and a strong name
    # match beats a weak match on a newer message.
    filtered.sort(key=lambda item: item[1].get("updated_at") or "", reverse=True)
    filtered.sort(key=lambda item: item[0], reverse=True)

    total = len(filtered)
    safe_limit = max(1, min(int(limit or DEFAULT_LIMIT), MAX_LIMIT))
    safe_offset = max(0, int(offset or 0))
    page = filtered[safe_offset:safe_offset + safe_limit]

    return {
        "query": query,
        "total": total,
        "offset": safe_offset,
        "limit": safe_limit,
        "results": [
            _public_result(task, score, terms) for score, task in page
        ],
        "facets": _facets(tasks),
    }
