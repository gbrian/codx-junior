"""
Data models for tools module.

This module contains data classes and models used by tools in the codx-junior API.

Made with ❤️ by codx-junior
"""

import logging
from typing import Optional

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
