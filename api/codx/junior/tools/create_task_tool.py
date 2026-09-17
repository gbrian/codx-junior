"""
Create task tool for creating new task chats.

This tool allows LLM models or API clients to create new task chats
with optional content and metadata.

Made with ❤️ by codx-junior
"""

import logging
import uuid
from typing import TYPE_CHECKING, Optional, List

from .model import ToolResponse

if TYPE_CHECKING:
    from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)


# Tool JSON definition to be imported in __init__.py
CREATE_TASK_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "create_task",
        "description": "Create a new task (chat) with optional content and metadata. Returns the task ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Task name/title (required)"
                },
                "content": {
                    "type": "string",
                    "description": "Task description and instructions"
                },
                "description": {
                    "type": "string",
                    "description": "Extended task description"
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths related to this task"
                },
                "profiles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of profiles/roles associated with this task"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorizing the task"
                },
                "board": {
                    "type": "string",
                    "description": "Kanban board ID"
                },
                "column": {
                    "type": "string",
                    "description": "Kanban column ID"
                }
            },
            "required": ["name"]
        }
    }
}


def create_task(
    name: str,
    content: str = "",
    description: str = "",
    files: Optional[List[str]] = None,
    profiles: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    board: str = "",
    column: str = "",
    settings: Optional["CODXJuniorSettings"] = None,
) -> ToolResponse:
    """
    Create a new task (chat) with metadata.

    This tool creates a new task chat without processing it. The task is saved
    to the database and can be processed later using process_task tool.
    
    The parent_id is automatically set by the tools engine based on the current
    chat context (if exists).

    Args:
        name: Task name/title (required)
        content: Task description and instructions
        description: Extended task description
        files: List of file paths related to this task
        profiles: List of profiles/roles for this task
        tags: Tags for categorizing the task
        board: Kanban board ID
        column: Kanban column ID
        settings: CODXJuniorSettings instance (injected by SmolAgent)

    Returns:
        ToolResponse with:
            - user_response: Human-readable task creation confirmation
            - llm_response: JSON with task_id and metadata

    Raises:
        ValueError: If required parameters are missing
        RuntimeError: If task creation fails

    Made with ❤️ by codx-junior
    """
    if not settings:
        error_msg = "create_task requires settings parameter"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not name or not name.strip():
        error_msg = "create_task requires 'name' parameter"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        from codx.junior.db import Chat, Message
        
        # Get the active session
        session = getattr(settings, "_active_session", None)
        if not session:
            raise RuntimeError(
                "create_task: no active session in settings. "
                "The SmolAgent runtime must inject session context."
            )

        # Get current chat for project context (and automatic parent_id)
        current_chat = getattr(session, "_current_chat", None)
        
        # Determine the message content (prefer description over content)
        message_content = "\n".join([description or "", content or ""])
        
        # Create new task chat
        task = Chat(
            name=name,
            description=description,
            parent_id=current_chat.id if current_chat else None,
            files=files or [],
            profiles=profiles or [],
            tags=tags or [],
            board=board,
            column=column,
            project_id=current_chat.project_id if current_chat else None,
            owner_project_id=current_chat.owner_project_id if current_chat else None,
            mode="task",
        )

        task.messages.append(
            Message(
                role="user",
                content=message_content,
                profiles=profiles or [],
                files=files or [],
            )
        )

        # Save the task
        chat_manager = session.get_chat_manager()
        saved_task = chat_manager.save_chat(task)
        
        logger.info(
            "create_task: task created with ID '%s' (parent_id=%s)",
            saved_task.id,
            saved_task.parent_id,
        )

        # Emit event
        session.event_manager.chat_event(
            chat=saved_task,
            message=f"Task '{saved_task.name}' created",
            event_type="created",
        )

        # Build response
        user_message = (
            f"✅ Task created: **{saved_task.name}**\n"
            f"Task ID: `{saved_task.id}`"
        )
        if saved_task.parent_id:
            user_message += f"\nLinked to parent: `{saved_task.parent_id}`"
        user_message += "\n\nUse `process_task` to start working on this task."

        import json
        task_response = json.dumps({
            "task_id": saved_task.id,
            "name": saved_task.name,
            "parent_id": saved_task.parent_id,
            "status": "created"
        })

        return ToolResponse(
            user_response=user_message,
            llm_response=task_response,
        )

    except Exception as ex:
        logger.exception("create_task: error creating task: %s", ex)
        raise RuntimeError(f"Failed to create task: {ex}") from ex