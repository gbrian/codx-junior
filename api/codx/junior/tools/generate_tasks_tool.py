"""
Generate tasks tool for invoking task splitting from within conversations.

This tool allows LLM models to request generation of sub-tasks from the
current chat context. It bridges the SmolAgent execution environment with
the task generation pipeline.

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


def generate_tasks_tool(
    instructions: str = "",
    settings: Optional["CODXJuniorSettings"] = None,
) -> ToolResponse:
    """
    Generate sub-tasks from the current chat using AI.

    This tool invokes the task generation pipeline, which analyzes the current
    chat context and creates a list of actionable sub-tasks. Each sub-task
    is created as a child chat connected to the parent via parent_id.

    Args:
        instructions: Optional additional instructions for task generation
                     to guide the AI in creating sub-tasks.
        settings: CODXJuniorSettings instance (passed by SmolAgent).

    Returns:
        ToolResponse with:
            - user_response: Human-readable summary of generated tasks
            - llm_response: JSON task list for model context

    Raises:
        ValueError: If settings is not provided or session is unavailable.
        RuntimeError: If task generation fails.

    Made with ❤️ by codx-junior
    """
    if not settings:
        error_msg = "generate_tasks_tool requires settings parameter"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        # Access the session from settings (assumes settings has a reference)
        # The caller (SmolAgent context) must inject the session reference
        from codx.junior.engine.session import CODXJuniorSession
        
        # Get the active session - this is contextual to the request
        session = getattr(settings, "_active_session", None)
        if not session:
            raise RuntimeError(
                "generate_tasks_tool: no active session in settings. "
                "The SmolAgent runtime must inject session context."
            )

        # Get the current chat from the session context
        chat_manager = session.get_chat_manager()
        current_chat = getattr(session, "_current_chat", None)
        
        if not current_chat:
            raise RuntimeError(
                "generate_tasks_tool: no current chat in session context"
            )

        logger.info(
            "generate_tasks_tool: starting task generation for chat '%s'",
            current_chat.name,
        )

        # Invoke the async task generation pipeline
        # Run in a new event loop if necessary
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        async def _generate():
            """Async wrapper for task generation."""
            await session.chat_engine_actions.generate_tasks(
                chat=current_chat,
                instructions=instructions,
            )

        if loop:
            # Already in async context - create a task
            task = loop.create_task(_generate())
            # Note: caller must await this or handle it via context
            logger.debug("generate_tasks_tool: task created asynchronously")
        else:
            # Fallback for sync context (shouldn't happen in SmolAgent)
            asyncio.run(_generate())

        # Build response with task summary
        task_count = len(current_chat.messages)
        user_message = (
            f"✅ Task generation initiated for '{current_chat.name}'. "
            f"Sub-tasks are being created and will appear in the project board."
        )

        # Extract task list from the latest AI response if available
        task_list = "Tasks are being generated and will be available shortly."
        for msg in reversed(current_chat.messages):
            if msg.task_item == "status":
                task_list = msg.content
                break

        logger.info(
            "generate_tasks_tool: task generation completed for chat '%s'",
            current_chat.name,
        )

        return ToolResponse(
            user_response=user_message,
            llm_response=task_list,
        )

    except Exception as ex:
        logger.exception("generate_tasks_tool: error during task generation: %s", ex)
        raise RuntimeError(f"Task generation failed: {ex}") from ex