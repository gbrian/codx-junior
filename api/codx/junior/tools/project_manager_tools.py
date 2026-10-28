"""
Project manager tools for codx-junior.

These tools let a profile (AI role) act as a **project manager** over the
project's kanban tasks (each task is a :class:`~codx.junior.db.Chat` stored in
``.codx/tasks/<board>/<column>/``). They cover the day-to-day workflow:

    - ``create_task``     : create a new task chat associated to a kanban
                            board + column and one or more sprints.
    - ``get_task``        : review a task (status, board/column, sprints and
                            the visible conversation).
    - ``list_tasks``      : list/filter tasks (board, column, sprint, status,
                            free-text).
    - ``list_boards``     : discover the kanban boards, their columns, the
                            sprint boards and the valid task states (so names
                            are known before creating or moving a task).
    - ``update_task``     : change the task status and/or move it between
                            boards, columns and sprints (and edit priority,
                            due date, progress, assignees and tags).
    - ``request_changes`` : add a comment **and** process the task through
                            :class:`~codx.junior.chat.chat_engine.ChatEngine`
                            (``session.chat_with_project``).
    - ``request_help``    : add a comment **without** triggering the engine
                            (ask the user for help / leave a note).

Design notes:
    - **One tool, several actions.** Keeping the workflow unified (like
      ``team_management``/``profile_management``) avoids spending prompt tokens
      on a schema per action and keeps the mental model small.
    - **Nothing duplicated.** Tasks are plain chats: this module never
      re-implements persistence, it delegates to
      :class:`~codx.junior.chat_manager.ChatManager`
      (``save_chat`` / ``update_chat_metadata`` / ``find_by_id`` / ``list_chats``).
      ``update_chat_metadata`` keeps messages intact and records a
      ``ChatStatusEvent`` on every real status transition, so task-performance
      metrics keep working.
    - **Processing is explicit.** Only ``request_changes`` runs the engine;
      ``request_help`` only writes a comment. A background run preserves the
      coroutine reference so it is not garbage-collected.
    - **Strict destination validation.** A task can NEVER be stored on a board,
      a column, a sprint or a state that does not exist: those values are
      validated against the project catalogue (``tasks/kanban.json`` and the
      states owned by :mod:`codx.junior.planning_manager`) and an invalid value
      is rejected with an error that lists the available options and asks to
      create the missing one first. The catalogue spelling is also enforced, so
      ``bugs`` resolves to the existing ``Bugs`` board instead of creating a
      phantom ``.codx/tasks/bugs`` folder.

Made with ❤️ by codx-junior
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from codx.junior.db import Chat, Message
from .model import ToolResponse

logger = logging.getLogger(__name__)

# Actions exposed by the tool (canonical names).
VALID_ACTIONS = [
    "list_boards",
    "list_tasks",
    "get_task",
    "create_task",
    "update_task",
    "request_changes",
    "request_help",
]

# Tolerant aliases so a slightly different verb never crashes the run.
ACTION_ALIASES = {
    "boards": "list_boards",
    "list": "list_tasks",
    "tasks": "list_tasks",
    "get": "get_task",
    "read": "get_task",
    "create": "create_task",
    "new": "create_task",
    "update": "update_task",
    "status": "update_task",
    "move": "update_task",
    "process": "request_changes",
    "changes": "request_changes",
    "comment": "request_help",
    "help": "request_help",
    "ask": "request_help",
}

DEFAULT_BOARD = "kanban"
DEFAULT_COLUMN = "tasks"
DEFAULT_MODE = "task"

# Comment defaults per action: a change request is a user prompt (the engine
# processes the last visible user message), while a help request is a note from
# the assistant that must NOT be re-processed as a prompt.
REQUEST_CHANGES_ROLE = "user"
REQUEST_HELP_ROLE = "assistant"

MAX_MESSAGES_PREVIEW = 8
MAX_PREVIEW_CHARS = 300
MAX_RESULT_CHARS = 800
DEFAULT_LIST_LIMIT = 50

# Keep-alive for fire-and-forget processing tasks (avoids GC cancelling them).
_BACKGROUND_TASKS: set = set()


# ---------------------------------------------------------------------------
# Context resolution helpers
# ---------------------------------------------------------------------------


def _resolve_settings(**kwargs):
    """
    Return the project settings from the injected ``settings`` or ``session``.

    Args:
        **kwargs: Tool keyword arguments; ``settings``/``session`` are injected
            by the agent runtime.

    Returns:
        The ``CODXJuniorSettings`` instance, or None.
    """
    settings = kwargs.get("settings")
    if settings is not None:
        return settings
    session = kwargs.get("session")
    return getattr(session, "settings", None) if session is not None else None


def _resolve_chat_manager(**kwargs):
    """
    Build the :class:`ChatManager` for the current execution context.

    Resolution order:
        1. The manager of the active project session
           (``settings._active_session``).
        2. The manager of the injected ``session``.
        3. A manager built from the injected project ``settings``.

    Args:
        **kwargs: Tool keyword arguments.

    Returns:
        A ready :class:`ChatManager`.

    Raises:
        ValueError: When neither a session nor settings are available.
    """
    settings = _resolve_settings(**kwargs)
    active_session = getattr(settings, "_active_session", None) if settings else None

    for candidate in (active_session, kwargs.get("session")):
        if candidate is not None and hasattr(candidate, "get_chat_manager"):
            try:
                return candidate.get_chat_manager()
            except TypeError:
                # Some managers require an explicit project id: fall back.
                continue

    if settings is not None:
        from codx.junior.chat_manager import ChatManager

        return ChatManager(settings=settings)

    raise ValueError(
        "project_manager requires a project session or project settings "
        "(none were injected by the runtime)"
    )


def _resolve_processing_session(**kwargs):
    """
    Return a session able to run ``chat_with_project``.

    A *fresh* engine is created per ``chat_with_project`` call by
    :class:`ChatEngineActions`, so using the active project session is
    preferred over an injected engine instance (avoids re-entering the engine
    that is currently producing this very response).

    Args:
        **kwargs: Tool keyword arguments.

    Returns:
        A session exposing ``chat_with_project``.

    Raises:
        ValueError: When no session/settings are available.
    """
    settings = _resolve_settings(**kwargs)
    active_session = getattr(settings, "_active_session", None) if settings else None

    if active_session is not None and hasattr(active_session, "chat_with_project"):
        return active_session

    session = kwargs.get("session")
    if session is not None and hasattr(session, "chat_with_project"):
        return session

    if settings is not None:
        from codx.junior.engine import CODXJuniorSession

        return CODXJuniorSession(settings=settings)

    raise ValueError(
        "project_manager could not resolve a session to process the task"
    )


def _resolve_event_manager(**kwargs):
    """
    Return the event manager used to notify the UI (best effort).

    Args:
        **kwargs: Tool keyword arguments.

    Returns:
        The event manager, or None.
    """
    settings = _resolve_settings(**kwargs)
    active_session = getattr(settings, "_active_session", None) if settings else None
    for candidate in (active_session, kwargs.get("session")):
        event_manager = getattr(candidate, "event_manager", None) if candidate else None
        if event_manager is not None:
            return event_manager
    return None


def _current_chat(**kwargs):
    """
    Return the chat that triggered the current tool execution, if any.

    The runtime stamps the running chat on the session
    (``session._current_chat``); it is used to inherit ``parent_id`` and the
    project scope when creating a task.

    Args:
        **kwargs: Tool keyword arguments.

    Returns:
        The current Chat, or None.
    """
    session = kwargs.get("session")
    chat = getattr(session, "_current_chat", None) if session is not None else None
    if chat is not None:
        return chat
    settings = _resolve_settings(**kwargs)
    active_session = getattr(settings, "_active_session", None) if settings else None
    return getattr(active_session, "_current_chat", None) if active_session else None


def _username(**kwargs) -> Optional[str]:
    """
    Return the username of the current execution context, if available.

    Args:
        **kwargs: Tool keyword arguments.

    Returns:
        The username string, or None.
    """
    settings = _resolve_settings(**kwargs)
    active_session = getattr(settings, "_active_session", None) if settings else None
    for candidate in (kwargs.get("session"), active_session):
        user = getattr(candidate, "user", None) if candidate else None
        username = getattr(user, "username", None) if user else None
        if username:
            return username
    return None


def _emit(event_manager, chat: Chat, message: str, event_type: Optional[str] = None) -> None:
    """
    Emit a chat event, never letting a notification failure break the action.

    Args:
        event_manager: Event manager (may be None).
        chat: Chat the event refers to.
        message: Human-readable message.
        event_type: Optional event type (``created``, ``changed``...).
    """
    if event_manager is None:
        return
    try:
        if event_type:
            event_manager.chat_event(chat=chat, message=message, event_type=event_type)
        else:
            event_manager.chat_event(chat=chat, message=message)
    except Exception as ex:
        logger.warning("project_manager: could not emit chat event: %s", ex)


# ---------------------------------------------------------------------------
# Normalization / formatting helpers
# ---------------------------------------------------------------------------


def _to_list(value: Any) -> List[str]:
    """
    Normalize a string, iterable or None into a clean list of strings.

    Args:
        value: A string, a list/tuple/set or None.

    Returns:
        List of non-empty, stripped strings.
    """
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    try:
        return [str(item).strip() for item in value if item and str(item).strip()]
    except TypeError:
        return []


def _normalize_sprints(current: Optional[List[str]], replace: Any, add: Any) -> List[str]:
    """
    Compute the sprint list after applying a replace and/or add operation.

    Args:
        current: Existing sprints (used when ``replace`` is None).
        replace: Full replacement list (``None`` keeps ``current``).
        add: Sprints to append (``None``/empty adds nothing).

    Returns:
        The resulting sprint list without duplicates.
    """
    if replace is not None:
        result = _to_list(replace)
    else:
        result = _to_list(current)
    for sprint in _to_list(add):
        if sprint not in result:
            result.append(sprint)
    return result


def _short_id(chat: Chat) -> str:
    """Return the first 8 characters of the chat id (or an empty string)."""
    return (chat.id or "")[:8]


def _json(data: Any) -> str:
    """Serialize ``data`` to a stable, indented JSON string."""
    return json.dumps(data, indent=2, default=str)


def _task_dict(chat: Chat, include_messages: bool = False) -> Dict[str, Any]:
    """
    Build a portable, JSON-ready view of a task (chat).

    Args:
        chat: The task chat.
        include_messages: When True, include the visible message list.

    Returns:
        Dict describing the task.
    """
    data: Dict[str, Any] = {
        "id": chat.id,
        "name": chat.name,
        "status": chat.status,
        "mode": chat.mode,
        "board": chat.board,
        "column": chat.column,
        "sprints": list(chat.sprints or []),
        "priority": chat.priority,
        "due_date": chat.due_date,
        "progress": chat.progress,
        "assignees": list(chat.assignees or []),
        "profiles": list(chat.profiles or []),
        "tags": list(chat.tags or []),
        "parent_id": chat.parent_id,
        "project_id": chat.project_id,
        "owner_project_id": chat.owner_project_id,
        "created_at": chat.created_at,
        "updated_at": chat.updated_at,
        "description": chat.description,
        "message_count": len(chat.messages or []),
    }
    if include_messages:
        data["messages"] = [
            {"role": msg.role, "content": msg.content, "hidden": msg.hide}
            for msg in (chat.messages or [])
            if not msg.hide
        ]
    return data


def _task_summary(chat: Chat) -> str:
    """
    Render a compact Markdown summary of a task.

    Args:
        chat: The task chat.

    Returns:
        Markdown summary.
    """
    sprints = ", ".join(f"`{s}`" for s in (chat.sprints or [])) or "none"
    assignees = ", ".join(chat.assignees or []) or "none"
    lines = [
        f"### Task `{chat.name or '(unnamed)'}`",
        f"- ID: `{chat.id}`",
        f"- Status: `{chat.status or '-'}` | Mode: `{chat.mode}`",
        f"- Board: `{chat.board}` | Column: `{chat.column}`",
        f"- Sprints: {sprints}",
        f"- Priority: `{chat.priority or '-'}` | Progress: {chat.progress or 0}% | "
        f"Due: `{chat.due_date or '-'}`",
        f"- Assignees: {assignees}",
        f"- Updated: {chat.updated_at}",
    ]
    if chat.description:
        lines.append(f"- Description: {chat.description}")
    return "\n".join(lines)


def _messages_markdown(chat: Chat, limit: int = MAX_MESSAGES_PREVIEW) -> str:
    """
    Render the tail of the visible conversation as a Markdown list.

    Args:
        chat: The task chat.
        limit: Maximum number of messages to show.

    Returns:
        Markdown list (or a note when there is nothing to show).
    """
    visible = [msg for msg in (chat.messages or []) if not msg.hide]
    if not visible:
        return "> No visible messages."
    tail = visible[-limit:]
    lines = [f"> Last {len(tail)} of {len(visible)} visible message(s)"]
    for msg in tail:
        content = (msg.content or "").strip().replace("\n", " ")
        if len(content) > MAX_PREVIEW_CHARS:
            content = content[:MAX_PREVIEW_CHARS] + "..."
        lines.append(f"- **{msg.role}**: {content}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Kanban / sprint / state catalogue
# ---------------------------------------------------------------------------


def _load_kanban(chat_manager) -> Dict[str, Any]:
    """
    Load the project's kanban definition, tolerating any failure.

    Args:
        chat_manager: The project ChatManager.

    Returns:
        The kanban dict, or an empty dict when it cannot be loaded.
    """
    try:
        kanban = chat_manager.load_kanban()
        return kanban if isinstance(kanban, dict) else {}
    except Exception as ex:
        logger.warning("project_manager: could not load kanban: %s", ex)
        return {}


def _boards_info(kanban: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract a normalized list of boards from a kanban definition.

    Handles the ``boards`` collection being either a dict (name -> board) or a
    list of board objects, and columns being either a dict or a list. It never
    raises: an unexpected shape yields an empty columns list.

    Args:
        kanban: The kanban dict returned by ``load_kanban``.

    Returns:
        List of ``{"name", "type", "is_sprint", "columns"}`` dicts.
    """
    boards = kanban.get("boards") if isinstance(kanban, dict) else None
    info: List[Dict[str, Any]] = []

    if isinstance(boards, dict):
        items = boards.items()
    elif isinstance(boards, list):
        items = [
            (
                board.get("title") or board.get("name") or board.get("id") or "",
                board,
            )
            for board in boards
            if isinstance(board, dict)
        ]
    else:
        items = []

    for name, board in items:
        board = board if isinstance(board, dict) else {}
        columns = board.get("columns")
        if isinstance(columns, dict):
            column_names = list(columns.keys())
        elif isinstance(columns, list):
            column_names = [
                col if isinstance(col, str)
                else (col.get("title") or col.get("name") or col.get("id"))
                for col in columns
                if col
            ]
        else:
            column_names = []

        board_type = str(board.get("type") or "").lower()
        is_sprint = board_type == "sprint" or bool(board.get("sprint"))
        info.append(
            {
                "name": str(name),
                "type": board_type or ("sprint" if is_sprint else "kanban"),
                "is_sprint": is_sprint,
                "columns": [c for c in column_names if c],
            }
        )
    return info


def _task_states() -> List[str]:
    """
    Return the canonical task states (the ``Chat.status`` values).

    The states are owned by :mod:`codx.junior.planning_manager` and imported
    lazily: duplicating the list here would let the tool and the planning views
    drift apart, and a state that the UI cannot render is not a valid state.

    Returns:
        Canonical state names, in workflow order.
    """
    from codx.junior.planning_manager import STATUS_ORDER

    return list(STATUS_ORDER)


def _board_catalogue(kanban: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Index the kanban boards by their normalized (lowercase) name.

    A board name is also the folder name under ``.codx/tasks``, so lookups must
    be case-insensitive: ``bugs`` and ``Bugs`` are the same board.

    Args:
        kanban: The kanban dict.

    Returns:
        Mapping of ``board name lowercased`` to its board info.
    """
    return {board["name"].strip().lower(): board for board in _boards_info(kanban)}


def _board_names(boards: List[Dict[str, Any]]) -> str:
    """Render the known board names for error messages."""
    return ", ".join(board["name"] for board in boards) or "none"


def _match_board(
    by_name: Dict[str, Dict[str, Any]], board: Optional[str]
) -> Optional[Dict[str, Any]]:
    """
    Return the board info for *board* (case-insensitive).

    Args:
        by_name: Board catalogue (see :func:`_board_catalogue`).
        board: Board name to resolve.

    Returns:
        The board info, or None when the board does not exist.
    """
    if not board:
        return None
    return by_name.get(board.strip().lower())


def _match_column(
    board_info: Optional[Dict[str, Any]], column: Optional[str]
) -> Optional[str]:
    """
    Return the column title as spelled on *board_info*.

    Args:
        board_info: The board the column must belong to.
        column: Column name to resolve.

    Returns:
        The catalogue spelling of the column, or None when it does not exist.
    """
    if not column or not board_info:
        return None
    wanted = column.strip().lower()
    return next(
        (
            title for title in board_info.get("columns") or []
            if title.strip().lower() == wanted
        ),
        None,
    )


def _match_state(status: Optional[str]) -> Optional[str]:
    """
    Return the canonical state for *status* (case-insensitive).

    Args:
        status: State name to resolve.

    Returns:
        The canonical state, or None when it is not a valid state.
    """
    wanted = (status or "").strip().lower()
    if not wanted:
        return None
    return next(
        (state for state in _task_states() if state.lower() == wanted),
        None,
    )


def _validate_task_location(
    kanban: Dict[str, Any],
    board: Optional[str] = None,
    column: Optional[str] = None,
    sprints: Optional[List[str]] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate a task destination and return its canonical spelling.

    A task must never be stored on a board, column, sprint or state that does
    not exist: such a task would be invisible on the board it claims to belong
    to and would create phantom folders under ``.codx/tasks``. Every provided
    value is therefore validated against the project catalogue
    (``tasks/kanban.json`` plus the states exposed by
    :func:`_task_states`) and the resulting :class:`ValueError` lists every
    problem together with the available options, asking to create the missing
    board/column/sprint/state first.

    Values that are ``None`` are not validated: they are not being changed.

    flowchart TD
        A[board] --> B{exists in kanban.json?}
        B -->|no| E[problem: unknown board]
        B -->|yes| C{column exists on that board?}
        C -->|no| E2[problem: unknown column]
        C -->|yes| F{state is canonical?}
        F -->|no| E3[problem: unknown state]
        F -->|yes| G{every sprint is a known board?}
        G -->|no| E4[problem: unknown sprint]
        G -->|yes| OK[canonical board / column / sprints / status]
        E --> RAISE[ValueError listing the problems]
        E2 --> RAISE
        E3 --> RAISE
        E4 --> RAISE

    Args:
        kanban: The project kanban definition (``ChatManager.load_kanban``).
        board: Target board name (``None`` = not being changed).
        column: Target column name (``None`` = not being changed).
        sprints: Target sprint list (``None`` = not being changed).
        status: Target task state (``None`` = not being changed).

    Returns:
        Dict with the canonical ``board``, ``column``, ``sprints`` and
        ``status`` (values that were not provided stay ``None``).

    Raises:
        ValueError: When any provided value does not exist. The message lists
            every problem, the available options and invites to create the
            missing board, column, sprint or state first.
    """
    problems: List[str] = []
    canonical: Dict[str, Any] = {
        "board": board,
        "column": column,
        "sprints": list(sprints) if sprints is not None else None,
        "status": status,
    }

    # -- state: closed set owned by the planning module ---------------------
    if status is not None and status.strip():
        matched_state = _match_state(status=status)
        if matched_state:
            canonical["status"] = matched_state
        else:
            problems.append(
                f"state '{status}' does not exist "
                f"(valid states: {', '.join(_task_states())})"
            )

    # -- board / column / sprint: catalogue from tasks/kanban.json ----------
    boards = _boards_info(kanban)
    if not boards:
        # A project without a kanban has no catalogue to validate against; the
        # call keeps working with the given names (states were checked above).
        if board or column or sprints:
            logger.warning(
                "project_manager: no boards in kanban.json, cannot validate "
                "board/column/sprints (board=%s column=%s sprints=%s)",
                board, column, sprints,
            )
    else:
        by_name = _board_catalogue(kanban=kanban)

        board_info = None
        if board:
            board_info = _match_board(by_name=by_name, board=board)
            if board_info:
                canonical["board"] = board_info["name"]
            else:
                problems.append(
                    f"board '{board}' does not exist "
                    f"(available boards: {_board_names(boards)})"
                )

        # The column is only validated against a resolved board: reporting both
        # "unknown board" and "unknown column" for the same call would be noise.
        if board_info is not None and column:
            matched_column = _match_column(board_info=board_info, column=column)
            if matched_column:
                canonical["column"] = matched_column
            elif not (board_info.get("columns") or []):
                problems.append(
                    f"board '{board_info['name']}' has no columns defined; "
                    "create the column first"
                )
            else:
                problems.append(
                    f"column '{column}' does not exist on board "
                    f"'{board_info['name']}' (available columns: "
                    f"{', '.join(board_info.get('columns') or [])})"
                )

        if sprints:
            resolved_sprints: List[str] = []
            for sprint in sprints:
                sprint_info = _match_board(by_name=by_name, board=sprint)
                if sprint_info:
                    resolved_sprints.append(sprint_info["name"])
                else:
                    problems.append(
                        f"sprint '{sprint}' does not exist "
                        f"(available boards: {_board_names(boards)})"
                    )
            canonical["sprints"] = resolved_sprints

    if problems:
        raise ValueError(
            "Invalid task destination:\n"
            + "\n".join(f"  - {problem}" for problem in problems)
            + "\nCreate the missing board, column, sprint or state first, then "
            "try again (action='list_boards' shows the current catalogue)."
        )

    return canonical


# ---------------------------------------------------------------------------
# Chat loading
# ---------------------------------------------------------------------------


def _find_task(chat_manager, chat_id: str) -> Optional[Chat]:
    """
    Load a task (chat) by id.

    Args:
        chat_manager: The project ChatManager.
        chat_id: Task/chat id.

    Returns:
        The full Chat (with messages), or None.
    """
    if not chat_id:
        return None
    return chat_manager.find_by_id(chat_id=chat_id)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def _action_list_boards(chat_manager) -> ToolResponse:
    """
    List the project's kanban boards, their columns, the sprint boards and the
    valid task states.

    Reporting the states here (and not only the boards) lets the model know
    what exists before trying to create or move a task, so an invalid value is
    avoided instead of rejected.

    Args:
        chat_manager: The project ChatManager.

    Returns:
        ToolResponse with a Markdown table (user) and JSON (model).
    """
    kanban = _load_kanban(chat_manager)
    boards = _boards_info(kanban)
    states = _task_states()

    if not boards:
        return ToolResponse(
            user_response=(
                "✓ No kanban boards defined yet. "
                f"Tasks will default to board '{DEFAULT_BOARD}' / "
                f"column '{DEFAULT_COLUMN}'.\n"
                f"- Valid states: {', '.join(states)}"
            ),
            llm_response=_json(
                {
                    "boards": [],
                    "states": states,
                    "default_board": DEFAULT_BOARD,
                    "default_column": DEFAULT_COLUMN,
                }
            ),
        )

    lines = [
        f"> {len(boards)} board(s)",
        "",
        "**Board** | **Type** | **Sprint** | **Columns**",
        "---|---|---|---",
    ]
    for board in boards:
        lines.append(
            f"`{board['name']}` | {board['type']} | "
            f"{'yes' if board['is_sprint'] else 'no'} | "
            f"{', '.join(board['columns']) or '-'}"
        )
    lines.extend(["", f"**Valid task states:** {', '.join(states)}"])

    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=_json({"boards": boards, "states": states}),
    )


def _action_list_tasks(
    chat_manager,
    board: Optional[str] = None,
    column: Optional[str] = None,
    sprint: Optional[str] = None,
    status: Optional[str] = None,
    query: Optional[str] = None,
    limit: Optional[int] = None,
) -> ToolResponse:
    """
    List the project's tasks with optional filters.

    Filters are not validated on purpose: filtering by a board/column/state that
    does not exist simply returns no tasks, which is a harmless way to discover
    that the destination is missing.

    Args:
        chat_manager: The project ChatManager.
        board: Only tasks on this board.
        column: Only tasks on this column.
        sprint: Only tasks associated to this sprint.
        status: Only tasks with this status (case-insensitive).
        query: Case-insensitive substring matched against name and description.
        limit: Maximum number of tasks returned.

    Returns:
        ToolResponse with a Markdown table (user) and JSON (model).
    """
    chats = chat_manager.list_chats()

    if board:
        chats = [c for c in chats if (c.board or "").lower() == board.lower()]
    if column:
        chats = [c for c in chats if (c.column or "").lower() == column.lower()]
    if sprint:
        chats = [c for c in chats if sprint in (c.sprints or [])]
    if status:
        chats = [c for c in chats if (c.status or "").lower() == status.lower()]
    if query:
        needle = query.strip().lower()
        chats = [
            c for c in chats
            if needle in (c.name or "").lower()
            or needle in (c.description or "").lower()
        ]

    chats = sorted(chats, key=lambda c: str(c.updated_at or ""), reverse=True)
    total = len(chats)
    if limit and limit > 0:
        chats = chats[:limit]

    if not chats:
        return ToolResponse(
            user_response="✓ No tasks match the given filters.",
            llm_response=_json({"count": 0, "tasks": []}),
        )

    lines = [
        f"> {len(chats)} of {total} task(s)",
        "",
        "**ID** | **Name** | **Status** | **Board/Column** | **Sprints** | **Updated**",
        "---|---|---|---|---|---",
    ]
    for chat in chats:
        sprints = ", ".join(chat.sprints or []) or "-"
        name = (chat.name or "(unnamed)").replace("|", "/")
        lines.append(
            f"`{_short_id(chat)}` | {name} | {chat.status or '-'} | "
            f"{chat.board}/{chat.column} | {sprints} | {chat.updated_at}"
        )

    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=_json({"count": len(chats), "total": total, "tasks": [
            _task_dict(chat) for chat in chats
        ]}),
    )


def _action_get_task(chat_manager, chat_id: str) -> ToolResponse:
    """
    Read a single task: status, location, sprints and visible messages.

    Args:
        chat_manager: The project ChatManager.
        chat_id: Task/chat id.

    Returns:
        ToolResponse with the task summary and messages.
    """
    chat = _find_task(chat_manager, chat_id)
    if chat is None:
        return ToolResponse(
            user_response=f"❌ Task `{chat_id}` not found",
            llm_response=(
                f"Task '{chat_id}' not found. Use action='list_tasks' to find "
                "the available tasks."
            ),
        )

    user_response = "\n".join([
        _task_summary(chat),
        "",
        "**Conversation**",
        _messages_markdown(chat),
    ])
    return ToolResponse(
        user_response=user_response,
        llm_response=_json(_task_dict(chat, include_messages=True)),
    )


def _action_create_task(
    chat_manager,
    event_manager,
    current_chat: Optional[Chat],
    settings,
    name: str,
    content: Optional[str],
    description: Optional[str],
    board: Optional[str],
    column: Optional[str],
    sprints: Any,
    sprint: Optional[str],
    status: Optional[str],
    priority: Optional[str],
    due_date: Optional[str],
    progress: Optional[int],
    assignees: Any,
    profiles: Any,
    files: Any,
    tags: Any,
    parent_id: Optional[str],
    username: Optional[str],
) -> ToolResponse:
    """
    Create a new task chat associated to a board, column and sprint(s).

    The destination is validated BEFORE the chat is created: a task can only be
    created on an existing board, in an existing column of that board, with
    existing sprints and a valid state. Names are canonicalised to the
    catalogue spelling so the task is stored in the right folder.

    Args:
        chat_manager: The project ChatManager.
        event_manager: Event manager used to notify the UI (may be None).
        current_chat: The chat that triggered the tool (for parent/project).
        settings: Project settings (for project scope).
        name: Task name (required).
        content: Initial user instruction (defaults to description/name).
        description: Task description.
        board: Kanban board (defaults to ``kanban``; must exist).
        column: Kanban column (defaults to ``tasks``; must exist on the board).
        sprints: Sprint list to associate (each must be a known board).
        sprint: Single sprint to associate (merged with ``sprints``).
        status: Initial state (must be a valid state).
        priority: Task priority.
        due_date: Due date (ISO ``YYYY-MM-DD``).
        progress: Completion percentage (0-100).
        assignees: Usernames assigned.
        profiles: Profiles/roles for the task.
        files: Files related to the task.
        tags: Tags for categorizing the task.
        parent_id: Parent chat id (defaults to the current chat).
        username: Author username.

    Returns:
        ToolResponse describing the created task.

    Raises:
        ValueError: When ``name`` is empty or the destination (board, column,
            sprint or state) does not exist.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required to create a task")

    # Validate (and canonicalise) the destination BEFORE creating the chat: a
    # task must never land on a board/column/sprint/state that does not exist.
    location = _validate_task_location(
        kanban=_load_kanban(chat_manager),
        board=(board or DEFAULT_BOARD).strip(),
        column=(column or DEFAULT_COLUMN).strip(),
        sprints=_normalize_sprints(None, sprints, sprint),
        status=status,
    )
    board = location["board"]
    column = location["column"]
    task_sprints = location["sprints"] or []
    status = location["status"]

    project_id = (
        getattr(current_chat, "project_id", None) if current_chat else None
    ) or getattr(settings, "project_id", None)
    owner_project_id = (
        getattr(current_chat, "owner_project_id", None) if current_chat else None
    ) or getattr(settings, "project_id", None)

    task = Chat(
        name=name,
        description=description or "",
        parent_id=parent_id or (current_chat.id if current_chat else None),
        board=board,
        column=column,
        sprints=task_sprints,
        status=status or "",
        priority=priority,
        due_date=due_date,
        progress=int(progress or 0),
        assignees=_to_list(assignees),
        profiles=_to_list(profiles),
        tags=_to_list(tags),
        file_list=_to_list(files),
        project_id=project_id,
        owner_project_id=owner_project_id,
        mode=DEFAULT_MODE,
    )

    message_content = content or description or name
    task.messages.append(
        Message(
            role="user",
            content=message_content,
            profiles=_to_list(profiles),
            files=_to_list(files),
            user=username,
        )
    )

    saved_task = chat_manager.save_chat(chat=task)
    _emit(
        event_manager=event_manager,
        chat=saved_task,
        message=f"Task '{saved_task.name}' created",
        event_type="created",
    )

    user_lines = [
        f"✅ Task created: **{saved_task.name}**",
        f"- ID: `{saved_task.id}`",
        f"- Board/Column: `{saved_task.board}` / `{saved_task.column}`",
        f"- Sprints: {', '.join(f'`{s}`' for s in task_sprints) or 'none'}",
        f"- Status: `{saved_task.status or '-'}`",
        "\nUse action='request_changes' to process this task through the engine.",
    ]

    logger.info(
        "project_manager: created task '%s' (board=%s column=%s sprints=%s)",
        saved_task.id, board, column, task_sprints,
    )
    return ToolResponse(
        user_response="\n".join(user_lines),
        llm_response=_json({"status": "created", "task": _task_dict(saved_task)}),
    )


def _action_update_task(
    chat_manager,
    event_manager,
    chat_id: str,
    board: Optional[str],
    column: Optional[str],
    sprints: Any,
    sprint: Optional[str],
    status: Optional[str],
    priority: Optional[str],
    due_date: Optional[str],
    progress: Optional[int],
    assignees: Any,
    tags: Any,
) -> ToolResponse:
    """
    Update a task's status and/or move it between boards, columns and sprints.

    Metadata-only changes are delegated to
    :meth:`ChatManager.update_chat_metadata`, which keeps the messages intact
    and records a ``ChatStatusEvent`` whenever the status actually changes.

    The destination is validated BEFORE the chat is modified. Only the values
    being changed are validated, but a move validates the resulting location:
    when the board changes the current column is checked against the NEW board,
    so a task can never end up in a column that only exists on the previous
    board.

    Args:
        chat_manager: The project ChatManager.
        event_manager: Event manager used to notify the UI (may be None).
        chat_id: Task/chat id.
        board: New board (must exist).
        column: New column (must exist on the resulting board).
        sprints: Full replacement sprint list (each must be a known board).
        sprint: Single sprint to append (used when ``sprints`` is None).
        status: New state (must be a valid state).
        priority: New priority.
        due_date: New due date.
        progress: New completion percentage.
        assignees: New assignee list (replaces).
        tags: New tag list (replaces).

    Returns:
        ToolResponse describing the updated task.

    Raises:
        ValueError: When the task does not exist, nothing is provided, or the
            target destination (board, column, sprint or state) does not exist.
    """
    chat = _find_task(chat_manager, chat_id)
    if chat is None:
        raise ValueError(f"task '{chat_id}' not found")

    sprints_changed = sprints is not None or sprint is not None
    new_sprints = _normalize_sprints(chat.sprints, sprints, sprint)

    # Validate (and canonicalise) the destination BEFORE touching the chat.
    # Changing only the column still validates the board it lives on.
    target_board = (
        board.strip() if board is not None
        else (chat.board if column is not None else None)
    )
    location = _validate_task_location(
        kanban=_load_kanban(chat_manager),
        board=target_board,
        column=(
            column.strip() if column is not None
            else (chat.column if board is not None else None)
        ),
        sprints=new_sprints if sprints_changed else None,
        status=status,
    )
    if board is not None:
        board = location["board"]
    if column is not None:
        column = location["column"]
    if sprints_changed:
        new_sprints = location["sprints"] or []
    if status is not None:
        status = location["status"]

    metadata: Dict[str, Any] = {}
    if status is not None:
        metadata["status"] = status
    if board is not None:
        metadata["board"] = board.strip()
    if column is not None:
        metadata["column"] = column.strip()
    if priority is not None:
        metadata["priority"] = priority
    if due_date is not None:
        metadata["due_date"] = due_date
    if progress is not None:
        metadata["progress"] = max(0, min(100, int(progress)))
    if assignees is not None:
        metadata["assignees"] = _to_list(assignees)
    if tags is not None:
        metadata["tags"] = _to_list(tags)

    if sprints_changed and new_sprints != list(chat.sprints or []):
        metadata["sprints"] = new_sprints

    if not metadata:
        raise ValueError(
            "Nothing to update: provide at least one of status, board, column, "
            "sprints, sprint, priority, due_date, progress, assignees or tags"
        )

    updated = chat_manager.update_chat_metadata(chat=chat, metadata=metadata)
    _emit(
        event_manager=event_manager,
        chat=updated,
        message=f"Task '{updated.name}' updated: {', '.join(sorted(metadata))}",
        event_type="changed",
    )

    user_lines = [
        _task_summary(updated),
        "",
        f"- Changed fields: {', '.join(sorted(metadata))}",
    ]

    logger.info(
        "project_manager: updated task '%s' (fields=%s)",
        updated.id, ", ".join(sorted(metadata)),
    )
    return ToolResponse(
        user_response="\n".join(user_lines),
        llm_response=_json(
            {"status": "updated", "changed_fields": sorted(metadata),
             "task": _task_dict(updated)}
        ),
    )


def _append_comment(
    chat_manager,
    chat: Chat,
    content: str,
    role: str,
    profiles: Any,
    files: Any,
    username: Optional[str],
) -> Message:
    """
    Append a comment (message) to a task and persist it.

    Args:
        chat_manager: The project ChatManager.
        chat: The task chat (mutated in place).
        content: Comment content.
        role: Message role ('user', 'assistant').
        profiles: Profiles to stamp on the message.
        files: Files to stamp on the message.
        username: Author username.

    Returns:
        The persisted message.
    """
    message = Message(
        role=role,
        content=content,
        profiles=_to_list(profiles),
        files=_to_list(files),
        user=username,
    )
    chat.messages.append(message)
    chat_manager.save_chat(chat=chat)
    return message


def _latest_assistant_content(chat: Chat) -> str:
    """
    Return a short preview of the last visible assistant message.

    Args:
        chat: The task chat.

    Returns:
        The (truncated) assistant content, or an empty string.
    """
    for message in reversed(chat.messages or []):
        if message.hide or message.role != "assistant":
            continue
        content = (message.content or "").strip()
        if len(content) > MAX_RESULT_CHARS:
            content = content[:MAX_RESULT_CHARS] + "..."
        return content
    return ""


async def _action_request_changes(
    processing_session,
    chat_manager,
    event_manager,
    chat_id: str,
    comment: str,
    role: Optional[str],
    profiles: Any,
    files: Any,
    username: Optional[str],
    disable_knowledge: bool,
    wait: bool,
) -> ToolResponse:
    """
    Add a comment to a task and process it through the ChatEngine.

    The comment is stored as the task's latest user message, then
    ``session.chat_with_project`` runs the engine so the task is actually
    processed. With ``wait=False`` the engine runs in the background (the
    coroutine is kept alive until it finishes).

    Args:
        processing_session: A session exposing ``chat_with_project``.
        chat_manager: The project ChatManager.
        event_manager: Event manager used to notify the UI (may be None).
        chat_id: Task/chat id.
        comment: The change request (required).
        role: Comment role (defaults to ``user``).
        profiles: Profiles to stamp on the comment.
        files: Files to stamp on the comment.
        username: Author username.
        disable_knowledge: Skip knowledge retrieval when processing.
        wait: Wait for processing to finish (default True).

    Returns:
        ToolResponse describing the request and, when waited, the response.

    Raises:
        ValueError: When the task does not exist or the comment is empty.
    """
    comment = (comment or "").strip()
    if not comment:
        raise ValueError("comment is required to request changes")

    chat = _find_task(chat_manager, chat_id)
    if chat is None:
        raise ValueError(f"task '{chat_id}' not found")

    _append_comment(
        chat_manager=chat_manager,
        chat=chat,
        content=comment,
        role=role or REQUEST_CHANGES_ROLE,
        profiles=profiles,
        files=files,
        username=username,
    )
    _emit(
        event_manager=event_manager,
        chat=chat,
        message=f"Changes requested on task '{chat.name}'",
        event_type="changed",
    )

    async def _run() -> None:
        """Run the engine and persist the resulting chat."""
        try:
            await processing_session.chat_with_project(
                chat=chat, disable_knowledge=disable_knowledge
            )
        finally:
            try:
                chat_manager.save_chat(chat=chat)
            except Exception as ex:
                logger.warning(
                    "project_manager: could not persist processed task '%s': %s",
                    chat.id, ex,
                )

    if wait:
        await _run()
        result_preview = _latest_assistant_content(chat)
        user_lines = [
            f"✅ Changes requested on task **{chat.name}** and processed.",
            f"- ID: `{chat.id}`",
            f"- Status: `{chat.status or '-'}`",
            f"- Messages: {len(chat.messages)}",
        ]
        if result_preview:
            user_lines.extend(["", "**Latest response**", result_preview])
        return ToolResponse(
            user_response="\n".join(user_lines),
            llm_response=_json(
                {"status": "processed", "task_id": chat.id,
                 "response": result_preview, "task": _task_dict(chat)}
            ),
        )

    task = asyncio.ensure_future(_run())
    _BACKGROUND_TASKS.add(task)

    def _done(future: "asyncio.Future") -> None:
        _BACKGROUND_TASKS.discard(future)
        if future.cancelled():
            return
        error = future.exception()
        if error is not None:
            logger.exception("project_manager: background processing error: %s", error)

    task.add_done_callback(_done)

    logger.info(
        "project_manager: queued background processing for task '%s'", chat.id
    )
    return ToolResponse(
        user_response=(
            f"⏳ Changes requested on task **{chat.name}**; processing started "
            "in the background."
        ),
        llm_response=_json({"status": "queued", "task_id": chat.id}),
    )


def _action_request_help(
    chat_manager,
    event_manager,
    chat_id: str,
    comment: str,
    role: Optional[str],
    profiles: Any,
    files: Any,
    username: Optional[str],
) -> ToolResponse:
    """
    Add a comment to a task WITHOUT triggering the engine (ask for help).

    Args:
        chat_manager: The project ChatManager.
        event_manager: Event manager used to notify the UI (may be None).
        chat_id: Task/chat id.
        comment: The help request / note (required).
        role: Comment role (defaults to ``assistant``).
        profiles: Profiles to stamp on the comment.
        files: Files to stamp on the comment.
        username: Author username.

    Returns:
        ToolResponse confirming the comment was recorded.

    Raises:
        ValueError: When the task does not exist or the comment is empty.
    """
    comment = (comment or "").strip()
    if not comment:
        raise ValueError("comment is required to request help")

    chat = _find_task(chat_manager, chat_id)
    if chat is None:
        raise ValueError(f"task '{chat_id}' not found")

    message = _append_comment(
        chat_manager=chat_manager,
        chat=chat,
        content=comment,
        role=role or REQUEST_HELP_ROLE,
        profiles=profiles,
        files=files,
        username=username,
    )
    _emit(
        event_manager=event_manager,
        chat=chat,
        message=f"Help requested on task '{chat.name}' (no processing)",
        event_type="changed",
    )

    logger.info(
        "project_manager: help comment added to task '%s' (message=%s)",
        chat.id, message.doc_id,
    )
    return ToolResponse(
        user_response=(
            f"📝 Comment added to task **{chat.name}**.\n"
            f"- ID: `{chat.id}`\n"
            "- No processing was triggered: the request waits for a user."
        ),
        llm_response=_json(
            {"status": "comment_added", "task_id": chat.id,
             "message_id": message.doc_id, "processed": False}
        ),
    )


# ---------------------------------------------------------------------------
# Tool entry point
# ---------------------------------------------------------------------------


async def project_manager(
    action: str,
    chat_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    content: Optional[str] = None,
    board: Optional[str] = None,
    column: Optional[str] = None,
    sprints: Optional[List[str]] = None,
    sprint: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None,
    progress: Optional[int] = None,
    assignees: Optional[List[str]] = None,
    profiles: Optional[List[str]] = None,
    files: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    parent_id: Optional[str] = None,
    comment: Optional[str] = None,
    role: Optional[str] = None,
    wait: bool = True,
    disable_knowledge: bool = False,
    query: Optional[str] = None,
    limit: Optional[int] = None,
    **kwargs,
) -> ToolResponse:
    """
    Unified project-manager tool over the project's kanban tasks (chats).

    A *task* is a :class:`~codx.junior.db.Chat` stored in
    ``.codx/tasks/<board>/<column>/`` and associated to one or more sprints
    (``Chat.sprints``). This tool lets a profile create tasks, review them,
    move them between statuses/boards/columns/sprints, and drive their
    processing.

    Actions:
        - ``list_boards``: boards, their columns, the sprint boards and the
          valid task states.
        - ``list_tasks``: list/filter tasks (board, column, sprint, status,
          ``query``).
        - ``get_task``: read one task (status, location, sprints, messages).
        - ``create_task``: create a task chat associated to board/column/sprint.
        - ``update_task``: change status / move between boards, columns and
          sprints (also priority, due date, progress, assignees, tags).
        - ``request_changes``: add a comment **and** process the task through
          the ChatEngine (``wait=False`` runs it in the background).
        - ``request_help``: add a comment with **no** processing (ask the user).

    Args:
        action: One of :data:`VALID_ACTIONS` (common aliases accepted).
        chat_id: Target task id (get/update/request actions).
        name: Task name (required on ``create_task``).
        description: Task description.
        content: Initial user instruction (defaults to description/name).
        board: Kanban board (defaults to ``kanban``; must exist).
        column: Kanban column (defaults to ``tasks``; must exist on the board).
        sprints: Full sprint list (create: associates; update: replaces).
        sprint: Single sprint (create/update: appended to the sprint list).
        status: Task state (one of :func:`_task_states`).
        priority: Task priority ('high' | 'medium' | 'low').
        due_date: Due date (ISO ``YYYY-MM-DD``).
        progress: Completion percentage (0-100).
        assignees: Assigned usernames (replaces on update).
        profiles: Profiles/roles for the task/comment.
        files: Files related to the task/comment.
        tags: Tags (replaces on update).
        parent_id: Parent chat id when creating (defaults to current chat).
        comment: Comment text for request_changes / request_help (required).
        role: Comment role override (``user``/``assistant``).
        wait: For request_changes, wait for processing (default True).
        disable_knowledge: For request_changes, skip knowledge retrieval.
        query: For list_tasks, case-insensitive filter on name/description.
        limit: For list_tasks, maximum number of tasks returned.
        **kwargs: Internal. Injected by the agent runtime:
            ``settings`` and/or ``session``.

    Returns:
        ToolResponse: ``user_response`` for the chat, ``llm_response`` (JSON)
        for the model.

    Raises:
        ValueError: If required parameters are missing for the chosen action,
            or the target board/column/sprint/state does not exist.

    Example:
        >>> await project_manager("list_boards")
        # Shows boards, columns, sprint boards and valid states
        >>> await project_manager("create_task", name="Fix login timeout",
        ...                       board="kanban", column="tasks")
        # Creates the task and returns its id
        >>> await project_manager("create_task", name="Fix login timeout",
        ...                       board="kanban", column="tasks",
        ...                       sprint="Sprint 12")
        # ❌ Invalid board 'kanban': available boards: Bugs, Engine...
        #    Create the missing board, column, sprint or state first
        >>> await project_manager("update_task", chat_id="<id>",
        ...                       status="doing", sprint="Sprint 13")
        # Moves the task and updates its state
        >>> await project_manager("request_changes", chat_id="<id>",
        ...                       comment="Please add the failing test.")
        # Adds the comment and processes the task
        >>> await project_manager("request_help", chat_id="<id>",
        ...                       comment="Which branch should I target?")
        # Adds a comment without processing
    """
    raw_action = (action or "").strip().lower()
    resolved_action = ACTION_ALIASES.get(raw_action, raw_action)

    if resolved_action not in VALID_ACTIONS:
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

    try:
        chat_manager = _resolve_chat_manager(**kwargs)
        event_manager = _resolve_event_manager(**kwargs)

        if resolved_action == "list_boards":
            return _action_list_boards(chat_manager=chat_manager)

        if resolved_action == "list_tasks":
            return _action_list_tasks(
                chat_manager=chat_manager,
                board=board,
                column=column,
                sprint=sprint or (sprints[0] if sprints else None),
                status=status,
                query=query,
                limit=limit if limit is not None else DEFAULT_LIST_LIMIT,
            )

        if resolved_action == "get_task":
            if not chat_id:
                raise ValueError("chat_id is required for action='get_task'")
            return _action_get_task(chat_manager=chat_manager, chat_id=chat_id)

        if resolved_action == "create_task":
            return _action_create_task(
                chat_manager=chat_manager,
                event_manager=event_manager,
                current_chat=_current_chat(**kwargs),
                settings=_resolve_settings(**kwargs),
                name=name,
                content=content,
                description=description,
                board=board,
                column=column,
                sprints=sprints,
                sprint=sprint,
                status=status,
                priority=priority,
                due_date=due_date,
                progress=progress,
                assignees=assignees,
                profiles=profiles,
                files=files,
                tags=tags,
                parent_id=parent_id,
                username=_username(**kwargs),
            )

        if resolved_action == "update_task":
            if not chat_id:
                raise ValueError("chat_id is required for action='update_task'")
            return _action_update_task(
                chat_manager=chat_manager,
                event_manager=event_manager,
                chat_id=chat_id,
                board=board,
                column=column,
                sprints=sprints,
                sprint=sprint,
                status=status,
                priority=priority,
                due_date=due_date,
                progress=progress,
                assignees=assignees,
                tags=tags,
            )

        if resolved_action == "request_changes":
            if not chat_id:
                raise ValueError("chat_id is required for action='request_changes'")
            return await _action_request_changes(
                processing_session=_resolve_processing_session(**kwargs),
                chat_manager=chat_manager,
                event_manager=event_manager,
                chat_id=chat_id,
                comment=comment,
                role=role,
                profiles=profiles,
                files=files,
                username=_username(**kwargs),
                disable_knowledge=disable_knowledge,
                wait=wait,
            )

        # request_help
        if not chat_id:
            raise ValueError("chat_id is required for action='request_help'")
        return _action_request_help(
            chat_manager=chat_manager,
            event_manager=event_manager,
            chat_id=chat_id,
            comment=comment,
            role=role,
            profiles=profiles,
            files=files,
            username=_username(**kwargs),
        )

    except ValueError as ex:
        # Expected validation errors (including an invalid destination): report
        # them so the model can create the missing board/column/sprint/state or
        # correct the call instead of crashing the run.
        logger.warning("project_manager(%s): %s", resolved_action, ex)
        return ToolResponse(
            user_response=f"❌ {ex}",
            llm_response=f"project_manager action '{resolved_action}' failed: {ex}",
        )
    except Exception as ex:
        logger.exception("project_manager(%s): unexpected error", resolved_action)
        return ToolResponse(
            user_response=f"❌ Error: {ex}",
            llm_response=f"project_manager action '{resolved_action}' failed: {ex}",
        )


# Tool JSON definition
PROJECT_MANAGER_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "project_manager",
        "description": (
            "Manage the project's kanban tasks (each task is a chat stored in "
            ".codx/tasks/<board>/<column>/ and associated to one or more sprints). "
            "Actions: "
            "'list_boards' (boards, columns, sprint boards and valid states), "
            "'list_tasks' (list/filter tasks), "
            "'get_task' (read a task: status, board/column, sprints and messages), "
            "'create_task' (create a task chat associated to board + column + sprint), "
            "'update_task' (change status and/or move between boards, columns and "
            "sprints; also priority, due date, progress, assignees, tags), "
            "'request_changes' (add a comment AND process the task through the AI "
            "engine) and "
            "'request_help' (add a comment WITHOUT processing, to ask the user for help). "
            "Every destination is validated: a task can NEVER be created or moved to a "
            "board, column, sprint or state that does not exist. Invalid values are "
            "rejected with an error listing the available options, so create the "
            "missing board, column, sprint or state first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": VALID_ACTIONS,
                    "description": (
                        "Operation:\n"
                        "  - 'list_boards': list kanban boards, columns, sprint boards and states\n"
                        "  - 'list_tasks': list/filter tasks (read)\n"
                        "  - 'get_task': read one task with its conversation (read)\n"
                        "  - 'create_task': create a new task chat\n"
                        "  - 'update_task': change status / move between boards, columns, sprints\n"
                        "  - 'request_changes': add a comment and process the task (runs the engine)\n"
                        "  - 'request_help': add a comment without processing (ask the user)"
                    )
                },
                "chat_id": {
                    "type": "string",
                    "description": (
                        "Target task id. Required for get_task, update_task, "
                        "request_changes and request_help."
                    )
                },
                "name": {
                    "type": "string",
                    "description": "Task name/title. Required for action='create_task'."
                },
                "description": {
                    "type": "string",
                    "description": "Task description (what needs to be done)."
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Initial user instruction/message for the new task. "
                        "Defaults to the description (or the name) when omitted."
                    )
                },
                "board": {
                    "type": "string",
                    "description": (
                        f"Kanban board name. Defaults to '{DEFAULT_BOARD}'. Must be an "
                        "existing board of the project (see action='list_boards'): an "
                        "unknown board is rejected and must be created first. On update, "
                        "moves the task to another board."
                    )
                },
                "column": {
                    "type": "string",
                    "description": (
                        f"Kanban column name. Defaults to '{DEFAULT_COLUMN}'. Must be a "
                        "column of the target board: an unknown column is rejected and "
                        "must be created first. On update, moves the task to another column."
                    )
                },
                "sprints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Sprint identifiers to associate (a sprint is a board of the "
                        "project). Each one must exist: unknown sprints are rejected and "
                        "must be created first. On create it sets the list; on update it "
                        "REPLACES the list."
                    )
                },
                "sprint": {
                    "type": "string",
                    "description": (
                        "Single sprint identifier to append to the task's sprint list "
                        "(create and update). Must be an existing sprint/board."
                    )
                },
                "status": {
                    "type": "string",
                    "enum": ["todo", "doing", "onhold", "done", "rejected"],
                    "description": (
                        "Task state. Only the project's canonical states are accepted "
                        "('todo', 'doing', 'onhold', 'done', 'rejected'); any other value "
                        "is rejected. Used on create and update."
                    )
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Task priority."
                },
                "due_date": {
                    "type": "string",
                    "description": "Task due date in ISO format (YYYY-MM-DD)."
                },
                "progress": {
                    "type": "integer",
                    "description": "Task completion percentage (0-100)."
                },
                "assignees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Usernames assigned to the task. On update it REPLACES the list."
                    )
                },
                "profiles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Profiles/roles for the task or the comment."
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files related to the task or the comment."
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorizing the task (replaces on update)."
                },
                "parent_id": {
                    "type": "string",
                    "description": (
                        "Parent chat id when creating a task. Defaults to the chat "
                        "that triggered this tool, when present."
                    )
                },
                "comment": {
                    "type": "string",
                    "description": (
                        "Comment text. Required for request_changes (the change "
                        "request to process) and request_help (the note to the user)."
                    )
                },
                "role": {
                    "type": "string",
                    "enum": ["user", "assistant"],
                    "description": (
                        "Comment role override. Defaults to 'user' for "
                        "request_changes and 'assistant' for request_help."
                    )
                },
                "wait": {
                    "type": "boolean",
                    "description": (
                        "For request_changes: wait for the engine to finish "
                        "(default true). Set false to process in the background."
                    ),
                    "default": True
                },
                "disable_knowledge": {
                    "type": "boolean",
                    "description": (
                        "For request_changes: skip knowledge (RAG) retrieval while "
                        "processing."
                    ),
                    "default": False
                },
                "query": {
                    "type": "string",
                    "description": (
                        "For list_tasks: case-insensitive filter matched against the "
                        "task name and description."
                    )
                },
                "limit": {
                    "type": "integer",
                    "description": "For list_tasks: maximum number of tasks to return."
                }
            },
            "required": ["action"]
        }
    }
}

# Made with ❤️ by codx-junior