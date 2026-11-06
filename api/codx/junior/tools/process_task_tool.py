"""
Process task tool for processing existing task chats.

This tool allows invoking AI processing on existing tasks
with optional wait/async behavior.

Made with ❤️ by codx-junior
"""

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Optional

from .model import ToolResponse

if TYPE_CHECKING:
    from codx.junior.settings import CODXJuniorSettings

logger = logging.getLogger(__name__)


# Tool JSON definition to be imported in __init__.py
PROCESS_TASK_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "process_task",
        "description": "Process an existing task (chat) with AI. Optionally wait for completion or execute asynchronously.",
        "parameters": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": "ID of the task chat to process (required)"
                },
                "wait": {
                    "type": "boolean",
                    "description": "If true, wait for task processing to complete. If false, queue asynchronously. Default is true.",
                    "default": True
                }
            },
            "required": ["chat_id"]
        }
    }
}


async def process_task(
    chat_id: str,
    wait: bool = True,
    settings: Optional["CODXJuniorSettings"] = None,
) -> ToolResponse:
    """
    Process an existing task (chat) with AI.

    This tool invokes the AI chat processing pipeline on an existing task,
    generating responses and updating the task with AI-generated content.

    Args:
        chat_id: ID of the task chat to process (required)
        wait: If True, wait for completion. If False, queue asynchronously.
        settings: CODXJuniorSettings instance (passed by SmolAgent)

    Returns:
        ToolResponse with:
            - user_response: Human-readable processing status
            - llm_response: JSON with processing result or async task ID

    Raises:
        ValueError: If required parameters are missing
        RuntimeError: If task processing fails or chat not found

    Made with ❤️ by codx-junior
    """
    if not settings:
        error_msg = "process_task requires settings parameter"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not chat_id or not chat_id.strip():
        error_msg = "process_task requires 'chat_id' parameter"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        # Get the active session
        session = getattr(settings, "_active_session", None)
        if not session:
            raise RuntimeError(
                "process_task: no active session in settings. "
                "The SmolAgent runtime must inject session context."
            )

        # Load the task chat
        chat_manager = session.get_chat_manager()
        task = chat_manager.find_by_id(chat_id=chat_id)
        
        if not task:
            raise RuntimeError(f"process_task: task with ID '{chat_id}' not found")

        logger.info(
            "process_task: starting processing for task '%s' (wait=%s)",
            task.name,
            wait,
        )

        # Prepare async processing function
        async def _process():
            """Async wrapper for task processing."""
            await session.chat_with_project(chat=task)

        if not wait:
            # Queue asynchronously. A dedicated thread (with its own event loop)
            # is used instead of the caller's loop: a tool call belongs to one
            # HTTP/socket request, and a fire-and-forget task on that loop would
            # die with it.
            import threading
            import uuid

            task_id = str(uuid.uuid4())

            def _background() -> None:
                try:
                    asyncio.run(_process())
                except Exception as ex:  # pragma: no cover - background logging
                    logger.exception(
                        "process_task: background processing failed for '%s': %s",
                        chat_id,
                        ex,
                    )

            thread = threading.Thread(target=_background, daemon=True)
            thread.start()
            logger.info(
                "process_task: task queued in background thread with ID '%s'",
                task_id,
            )

            user_message = (
                f"⏳ Task processing queued for '{task.name}'.\n"
                f"Async ID: `{task_id}`\n"
                f"Processing will continue in the background."
            )
            process_response = json.dumps({
                "task_id": task_id,
                "status": "queued",
                "chat_name": task.name,
                "chat_id": chat_id
            })

            return ToolResponse(
                user_response=user_message,
                llm_response=process_response,
            )

        else:
            # Wait for processing to complete. Because this tool is async, the
            # SmolAgent loop awaits it and the caller receives the REAL result
            # (the previous implementation created a task and returned
            # immediately while claiming success).
            await _process()

            last_message = task.messages[-1] if task.messages else None
            error = str(getattr(last_message, "error", "") or "").strip()
            if error:
                raise RuntimeError(f"task processing failed: {error}")

            user_message = (
                f"✅ Task processing completed for '{task.name}'.\n"
                f"Chat ID: `{chat_id}`"
            )

            # Get latest message from processed task
            latest_message = task.messages[-1].content if task.messages else ""
            if len(latest_message) > 200:
                latest_message = latest_message[:200] + "..."

            process_response = json.dumps({
                "task_id": chat_id,
                "status": "completed",
                "chat_name": task.name,
                "messages_count": len(task.messages),
                "latest_response": latest_message
            })

            logger.info(
                "process_task: processing completed for task '%s'",
                task.name,
            )

            return ToolResponse(
                user_response=user_message,
                llm_response=process_response,
            )

    except Exception as ex:
        logger.exception("process_task: error processing task: %s", ex)
        raise RuntimeError(f"Failed to process task: {ex}") from ex