"""
Create task tool for creating new task chats.

This tool allows LLM models to create new task chats with all their
information. Tasks are only created through the LLM tools
(``create_task`` / ``project_manager(action="create_task")``) and the API
(``POST /api/chats/tasks``); all of them use
:class:`codx.junior.task_manager.TaskManager` as the single creation core.

Every field is taken from the tool arguments: nothing is inherited from the
chat that triggered the tool (profiles, files, tags or message content).

Made with ❤️ by codx-junior
"""

import json
import logging
from typing import TYPE_CHECKING, Optional, List

from codx.junior.task_manager import TaskManager
from .model import ToolResponse

if TYPE_CHECKING:
    from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)


# Tool JSON definition to be imported in __init__.py
CREATE_TASK_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "create_task",
        "description": (
            "Create a new task (chat) providing ALL of its information. "
            "'name' and 'description' are mandatory: the task is stored exactly as "
            "given, there is no AI step that expands or splits it afterwards. "
            "Nothing is inherited from the current chat (profiles, files, tags), so "
            "send every value the task needs. Returns the created task."
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
                    "description": "Kanban board ID (defaults to 'kanban')"
                },
                "column": {
                    "type": "string",
                    "description": "Kanban column ID (defaults to 'tasks')"
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
    settings: Optional["CODXJuniorSettings"] = None,
) -> ToolResponse:
    """
    Create a new task (chat) with all the information provided.

    The task is created and saved, but not processed: use ``process_task`` to
    start working on it. ``parent_id`` is resolved from the chat that triggered
    the tool (when it exists) so the task stays linked, but no content, profile
    or file is inherited from it.

    Args:
        name: Task name/title (required)
        description: Complete task description (required)
        content: Initial user instruction; defaults to ``description``
        files: List of file paths related to this task
        profiles: List of profiles/roles for this task (parameter only)
        tags: Tags for categorizing the task
        board: Kanban board ID (defaults to ``kanban``)
        column: Kanban column ID (defaults to ``tasks``)
        settings: CODXJuniorSettings instance (injected by SmolAgent)

    Returns:
        ToolResponse with:
            - user_response: Human-readable task creation confirmation
            - llm_response: JSON with task_id and metadata

    Raises:
        ValueError: If ``name`` or ``description`` is missing
        RuntimeError: If the active session is missing or creation fails

    Example:
        >>> create_task(
        ...     name="Fix login timeout",
        ...     description="## Context\nLogin times out after 30s...\n## Done\n- test",
        ...     profiles=["backend"],
        ...     files=["api/auth/login.py"],
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

        task_manager = TaskManager(
            settings=settings,
            chat_manager=session.get_chat_manager(),
            event_manager=getattr(session, "event_manager", None),
        )

        saved_task = task_manager.create_task(
            name=name,
            description=description,
            content=content or None,
            board=board or None,
            column=column or None,
            profiles=profiles,
            files=files,
            tags=tags,
            parent_chat=current_chat,
            user=_resolve_username(session),
        )

        # Build response
        user_message = (
            f"✅ Task created: **{saved_task.name}**\n"
            f"Task ID: `{saved_task.id}`"
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
            "profiles": saved_task.profiles,
            "status": "created"
        })

        return ToolResponse(
            user_response=user_message,
            llm_response=task_response,
        )

    except Exception as ex:
        logger.exception("create_task: error creating task: %s", ex)
        raise RuntimeError(f"Failed to create task: {ex}") from ex

# Made with ❤️ by codx-junior