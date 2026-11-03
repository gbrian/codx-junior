"""
Create task tool for creating new task chats.

This tool allows LLM models to create new task chats with all their
information. Tasks are only created through the LLM tools
(``create_task`` / ``project_manager(action="create_task")``) and the API
(``POST /api/chats/tasks``); all of them use
:class:`codx.junior.task_manager.TaskManager` as the single creation core.

Every field is taken from the tool arguments: nothing is inherited from the
chat that triggered the tool (profiles, files, tags or message content).

The whole task information is accepted (``board``/``column``, ``sprints``,
``status``, ``priority``, ``due_date``, ``progress``, ``assignees``,
``parent_id``) and the destination is validated against the project catalogue
before anything is written: a task can never land on a board, column, sprint or
state that does not exist. Boards, sprints and columns are created with the
``project_manager`` tool (actions ``create_board`` / ``create_sprint`` /
``create_column``).

Made with ❤️ by codx-junior
"""

import json
import logging
from typing import TYPE_CHECKING, Optional, List

from codx.junior.task_manager import TaskManager
from .model import ToolResponse
from .project_manager_tools import validate_task_destination

if TYPE_CHECKING:
    from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)

# Default destination, matching ChatManager/TaskManager defaults.
DEFAULT_BOARD = "kanban"
DEFAULT_COLUMN = "tasks"


def _merge_sprints(
    sprints: Optional[List[str]], sprint: Optional[str]
) -> Optional[List[str]]:
    """
    Merge the plural and singular sprint arguments.

    Args:
        sprints: Full sprint list (``None`` = not provided).
        sprint: Single sprint to append (``None`` = not provided).

    Returns:
        The merged list, or ``None`` when neither argument was provided (so the
        destination validation knows the sprint list is not being changed).
    """
    if sprints is None and sprint is None:
        return None
    merged: List[str] = []
    for name in list(sprints or []) + ([sprint] if sprint else []):
        clean = (name or "").strip()
        if clean and clean not in merged:
            merged.append(clean)
    return merged


# Tool JSON definition to be imported in __init__.py
CREATE_TASK_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "create_task",
        "description": (
            "Create a new task (chat) providing ALL of its information. "
            "'name' and 'description' are mandatory: the task is stored exactly as "
            "given, there is no AI step that expands or splits it afterwards. "
            "Also accepts the kanban destination (board, column), the sprint "
            "membership (sprints/sprint), the planning fields (status, priority, "
            "due_date, progress, assignees) and the parent chat. "
            "Nothing is inherited from the current chat (profiles, files, tags), so "
            "send every value the task needs. The destination must exist in the "
            "project catalogue: create the missing board, sprint or column first "
            "with project_manager (create_board / create_sprint / create_column). "
            "Returns the created task."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Task name/title (required)"
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Complete task description: context, what to do and any "
                        "acceptance criteria (required)."
                    )
                },
                "content": {
                    "type": "string",
                    "description": (
                        "Initial user instruction for the task. Defaults to the "
                        "description when omitted."
                    )
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths related to this task"
                },
                "profiles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Profiles/roles for this task. Taken ONLY from this argument: "
                        "profiles are never inherited from the current chat."
                    )
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorizing the task"
                },
                "board": {
                    "type": "string",
                    "description": (
                        f"Kanban board name (defaults to '{DEFAULT_BOARD}'). Must be an "
                        "existing board: an unknown board is rejected and must be "
                        "created first with project_manager action='create_board'."
                    )
                },
                "column": {
                    "type": "string",
                    "description": (
                        f"Kanban column name (defaults to '{DEFAULT_COLUMN}'). Must "
                        "exist on the target board: create it first with "
                        "project_manager action='create_column'."
                    )
                },
                "sprints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Sprints this task belongs to (a sprint is a board of the "
                        "project whose type is 'sprint'). Each one must exist: create "
                        "it first with project_manager action='create_sprint'."
                    )
                },
                "sprint": {
                    "type": "string",
                    "description": "Single sprint to associate (merged with 'sprints')."
                },
                "status": {
                    "type": "string",
                    "enum": ["todo", "doing", "onhold", "done", "rejected"],
                    "description": "Initial task state (defaults to the project default)."
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
                    "description": "Usernames assigned to this task."
                },
                "parent_id": {
                    "type": "string",
                    "description": (
                        "Parent chat id, to link the task to the conversation it "
                        "comes from. Defaults to the chat that triggered this tool."
                    )
                }
            },
            "required": ["name", "description"]
        }
    }
}


def _resolve_username(session) -> Optional[str]:
    """
    Return the username of the session running the tool, when available.

    Args:
        session: The active project session (may be None).

    Returns:
        The username or None.
    """
    user = getattr(session, "user", None) if session is not None else None
    return getattr(user, "username", None) if user else None


def create_task(
    name: str,
    description: str,
    content: str = "",
    files: Optional[List[str]] = None,
    profiles: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    board: str = "",
    column: str = "",
    sprints: Optional[List[str]] = None,
    sprint: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None,
    progress: Optional[int] = None,
    assignees: Optional[List[str]] = None,
    parent_id: Optional[str] = None,
    settings: Optional["CODXJuniorSettings"] = None,
) -> ToolResponse:
    """
    Create a new task (chat) with all the information provided.

    The task is created and saved, but not processed: use ``process_task`` to
    start working on it. ``parent_id`` defaults to the chat that triggered the
    tool (when it exists) so the task stays linked, but no content, profile or
    file is inherited from it.

    The destination (board, column, sprints and state) is validated against the
    project catalogue before the task is created, so the tool either creates the
    task on a real board/column or fails with the list of available options
    instead of creating a phantom ``.codx/tasks/<board>`` folder.

    Args:
        name: Task name/title (required)
        description: Complete task description (required)
        content: Initial user instruction; defaults to ``description``
        files: List of file paths related to this task
        profiles: List of profiles/roles for this task (parameter only)
        tags: Tags for categorizing the task
        board: Kanban board name (defaults to ``kanban``; must exist)
        column: Kanban column name (defaults to ``tasks``; must exist on the board)
        sprints: Sprints the task belongs to (each must be an existing board)
        sprint: Single sprint to associate (merged with ``sprints``)
        status: Initial task state (one of the canonical states)
        priority: Task priority (``high`` / ``medium`` / ``low``)
        due_date: Due date in ISO format (``YYYY-MM-DD``)
        progress: Completion percentage (0-100)
        assignees: Usernames assigned to the task
        parent_id: Parent chat id (defaults to the chat that triggered the tool)
        settings: CODXJuniorSettings instance (injected by SmolAgent)

    Returns:
        ToolResponse with:
            - user_response: Human-readable task creation confirmation
            - llm_response: JSON with task_id and metadata

    Raises:
        ValueError: If ``name``, ``description`` or the destination is missing
            or invalid (unknown board, column, sprint or state)
        RuntimeError: If the active session is missing or creation fails

    Example:
        >>> create_task(
        ...     name="Fix login timeout",
        ...     description="## Context\nLogin times out after 30s...\n## Done\n- test",
        ...     profiles=["backend"],
        ...     files=["api/auth/login.py"],
        ...     board="Bugs",
        ...     column="Backlog",
        ...     sprint="Sprint 12",
        ...     priority="high",
        ...     due_date="2024-05-31",
        ... )
    """
    if not settings:
        error_msg = "create_task requires settings parameter"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not name or not name.strip():
        error_msg = "create_task requires 'name' parameter"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not description or not description.strip():
        error_msg = (
            "create_task requires 'description' parameter: tasks are created with "
            "all their information (there is no AI sub-task generation anymore)"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        # Get the active session
        session = getattr(settings, "_active_session", None)
        if not session:
            raise RuntimeError(
                "create_task: no active session in settings. "
                "The SmolAgent runtime must inject session context."
            )

        # The current chat only provides the linkage (parent_id) and the
        # project scope: its profiles/files are NEVER copied to the task.
        current_chat = getattr(session, "_current_chat", None)
        chat_manager = session.get_chat_manager()

        # Validate (and canonicalise) the destination BEFORE creating the chat:
        # a task must never land on a board/column/sprint/state that does not
        # exist. Missing destinations are created with the `project_manager`
        # tool, which owns the board/sprint/column catalogue.
        location = validate_task_destination(
            chat_manager=chat_manager,
            board=(board or DEFAULT_BOARD).strip(),
            column=(column or DEFAULT_COLUMN).strip(),
            sprints=_merge_sprints(sprints, sprint),
            status=status,
        )

        task_manager = TaskManager(
            settings=settings,
            chat_manager=chat_manager,
            event_manager=getattr(session, "event_manager", None),
        )

        saved_task = task_manager.create_task(
            name=name,
            description=description,
            content=content or None,
            board=location["board"],
            column=location["column"],
            sprints=location["sprints"],
            status=location["status"],
            priority=priority,
            due_date=due_date,
            progress=progress,
            assignees=assignees,
            profiles=profiles,
            files=files,
            tags=tags,
            parent_id=parent_id,
            parent_chat=current_chat,
            user=_resolve_username(session),
        )

        # Build response
        user_message = (
            f"✅ Task created: **{saved_task.name}**\n"
            f"Task ID: `{saved_task.id}`\n"
            f"Board/Column: `{saved_task.board}` / `{saved_task.column}`\n"
            f"Sprints: {', '.join(saved_task.sprints or []) or 'none'}\n"
            f"Status: `{saved_task.status or '-'}`"
        )
        if saved_task.parent_id:
            user_message += f"\nLinked to parent: `{saved_task.parent_id}`"
        user_message += "\n\nUse `process_task` to start working on this task."

        task_response = json.dumps({
            "task_id": saved_task.id,
            "name": saved_task.name,
            "parent_id": saved_task.parent_id,
            "board": saved_task.board,
            "column": saved_task.column,
            "sprints": list(saved_task.sprints or []),
            "status": saved_task.status,
            "priority": saved_task.priority,
            "due_date": saved_task.due_date,
            "progress": saved_task.progress,
            "assignees": list(saved_task.assignees or []),
            "profiles": saved_task.profiles,
            "status": "created"
        })

        return ToolResponse(
            user_response=user_message,
            llm_response=task_response,
        )

    except ValueError as ex:
        # Invalid destination or missing data: report the validation message as
        # is so the model can create the missing board/sprint/column.
        logger.warning("create_task: invalid task: %s", ex)
        raise
    except Exception as ex:
        logger.exception("create_task: error creating task: %s", ex)
        raise RuntimeError(f"Failed to create task: {ex}") from ex

# Made with ❤️ by codx-junior