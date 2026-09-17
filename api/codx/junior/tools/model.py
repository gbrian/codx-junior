"""
Data models for tools module.

This module contains data classes and models used by tools in the codx-junior API.

Made with ❤️ by codx-junior
"""

import logging
from typing import Optional, List
from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger(__name__)


class ToolResponse:
    """
    Dual-return response for tools that produce both user-facing output
    and LLM-context feedback.

    This allows tools like code_block_generator to generate formatted output
    visible to the user while simultaneously providing feedback to the LLM
    for continued processing.

    Attributes:
        user_response: Formatted content displayed to the user.
        llm_response: Lightweight feedback for the LLM context.
    """

    def __init__(self, user_response: str, llm_response: str) -> None:
        """
        Initialize a dual-return tool response.

        Args:
            user_response: Content visible to the user in the chat interface.
            llm_response: Feedback/status message for the LLM context.
        """
        self.user_response: str = user_response
        self.llm_response: str = llm_response

    def __str__(self) -> str:
        """Return the LLM feedback (for backward compatibility)."""
        return self.llm_response


class ToolSettings(BaseModel):
    """
    Configuration settings for tool execution and visibility.
    
    Controls how a tool behaves in the agent runtime, including async handling,
    parameter injection, response structure, and scope visibility.
    
    Attributes:
        is_async: Whether the tool is async-capable (default: False).
        project_settings: Inject CODXJuniorSettings parameter (default: False).
        session: Inject session parameter (default: False).
        scope: Tool visibility scope: 'global' (always available) or 'chat' 
               (optional per conversation). Default: 'chat'.
        dual_response: Tool returns ToolResponse with user_response and 
                      llm_response (default: False).
    """
    
    is_async: bool = Field(
        default=False,
        alias="async",
        description="If True, the tool is async and must be awaited"
    )
    project_settings: bool = Field(
        default=False,
        description="If True, inject CODXJuniorSettings as 'settings' parameter"
    )
    session: bool = Field(
        default=False,
        description="If True, inject current session as 'session' parameter"
    )
    scope: str = Field(
        default="chat",
        description="Tool scope: 'global' (always available) or 'chat' (optional)"
    )
    dual_response: bool = Field(
        default=False,
        description="If True, tool returns ToolResponse with user_response and llm_response"
    )
    