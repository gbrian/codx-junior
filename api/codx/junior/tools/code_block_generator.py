"""
Code block generator tool for formatting code blocks.

This module provides functionality to format code blocks with language,
file path, and content information into markdown code block format.

Made with ❤️ by codx-junior
"""

import logging
from typing import Union

from .model import ToolResponse

# Configure logging
logger = logging.getLogger(__name__)


def code_block_generator(
    language: str,
    file_path: str,
    content: str
) -> ToolResponse:
    """
    Format a code block with language, file path, and content.

    This function takes code block components and formats them into
    a markdown code block with language and file path information.

    Args:
        language (str): The programming language or code block type
                       (e.g., 'python', 'javascript', 'html', 'markdown')
        file_path (str): The target file path for the code block
        content (str): The actual code or file content

    Returns:
        ToolResponse: A dual-return object containing:
                     - user_content: The formatted markdown code block
                     - llm_feedback: Status message for the LLM

    Example:
        >>> result = code_block_generator(
        ...     language="python",
        ...     file_path="codx/app.py",
        ...     content="print('hello')"
        ... )
        >>> result.user_content
        '```python codx/app.py\\nprint(\'hello\')\\n```'
        >>> result.llm_feedback
        'Code block created successfully'

    Made with ❤️ by codx-junior
    """
    try:
        # Validate inputs
        if not isinstance(language, str) or not language.strip():
            error_msg: str = "Language parameter must be a non-empty string"
            logger.warning(error_msg)
            return ToolResponse(
                user_content="",
                llm_feedback=error_msg
            )

        if not isinstance(file_path, str) or not file_path.strip():
            error_msg = "File path parameter must be a non-empty string"
            logger.warning(error_msg)
            return ToolResponse(
                user_content="",
                llm_feedback=error_msg
            )

        if not isinstance(content, str):
            error_msg = "Content parameter must be a string"
            logger.warning(error_msg)
            return ToolResponse(
                user_content="",
                llm_feedback=error_msg
            )

        logger.debug(
            "Generating code block for file: %s (language: %s)",
            file_path,
            language
        )

        # Format the code block in markdown format
        code_block: str = f"```{language} {file_path}\n{content}\n```"

        logger.debug("Code block generated successfully for: %s", file_path)

        return ToolResponse(
            user_content=code_block,
            llm_feedback="Code block created successfully"
        )

    except Exception as e:
        error_msg = f"Unexpected error generating code block: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ToolResponse(
            user_content="",
            llm_feedback=error_msg
        )

