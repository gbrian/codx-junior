"""
Git tools for version control operations and change history analysis.

This module provides tools for analyzing git history and file versions.
Useful for understanding changes, PR reviews, and rollback analysis.

Made with ❤️ by codx-junior
"""

import logging
from typing import Optional

from codx.junior.engine import CODXJuniorSession
from .model import ToolResponse

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_DEPTH = 0
MAX_DEPTH = 50


def get_file_last_version(
    file_path: str,
    depth: Optional[int] = None,
    **kwargs
) -> ToolResponse:
    """
    Retrieve a previous version of a file from git history.

    Navigate through file history by depth level without needing commit IDs.
    Each depth level represents how many commits back to look:
    - depth=0 (or None): Get the immediate previous version (1 commit back)
    - depth=1: Get version from 2 commits ago
    - depth=2: Get version from 3 commits ago
    - etc.

    Useful for:
    - Understanding what changed between versions
    - PR reviews and change analysis
    - Forensic debugging and rollback analysis
    - Comparing current code against previous implementations

    Args:
        file_path: Relative or absolute path to the file to retrieve.
        depth: How many commits back to navigate (default: 0 = previous version).
               Must be >= 0. If exceeds available history, returns error.
        **kwargs: Additional arguments including:
            - session (CODXJuniorSession): Session with git engine (required).

    Returns:
        ToolResponse: Contains:
            - user_response: Summary of the version retrieved.
            - llm_response: File content with metadata or error message.

    Raises:
        ValueError: If file_path is empty or depth is invalid.
        Exception: If session or git engine is not available.

    Example:
        Get previous version (1 commit back):
        >>> get_file_last_version("src/main.py")
        # Returns ToolResponse with file content from previous commit

        Get version from 2 commits ago:
        >>> get_file_last_version("src/main.py", depth=1)

        Get version from 5 commits ago:
        >>> get_file_last_version("config/settings.py", depth=4)
    """
    session: CODXJuniorSession = kwargs.get("session", None)
    if not session:
        raise Exception("Invalid session - git engine not available")

    if not file_path:
        raise ValueError("file_path must be provided and cannot be empty")

    # Normalize depth
    if depth is None:
        depth = DEFAULT_DEPTH
    depth = max(0, min(int(depth), MAX_DEPTH))

    try:
        # Get git engine and retrieve file version
        git_engine = session.get_git_engine()
        result = git_engine.get_file_version_at_depth(file_path=file_path, depth=depth)

        # Check for errors
        if result.get("error"):
            error_msg = result["error"]
            logger.warning("Error retrieving file version: %s", error_msg)
            return ToolResponse(
                user_response=f"error [{file_path}]\nERROR: {error_msg}",
                llm_response=f"Failed to retrieve file version: {error_msg}",
            )

        # Build file content response
        if not result.get("content"):
            error_msg = "File content is empty or file did not exist at this version"
            logger.warning("Empty content for %s at depth %d", file_path, depth)
            return ToolResponse(
                user_response=f"warning [{file_path}]\n{error_msg}",
                llm_response=f"Retrieved empty file: {file_path} at depth {depth}",
            )

        # Format the file content in a code block
        extension = file_path.split(".")[-1] if "." in file_path else "txt"
        content_block = f"```{extension} {file_path}\n{result['content']}\n```"

        # Build metadata section
        metadata = [
            f"# File Version History: {file_path}",
            f"## Retrieved Version (Depth: {depth})",
            f"- Commit: `{result['short_commit']}` ({result['commit']})",
            f"- Author: {result['author']} <{result['email']}>",
            f"- Date: {result['date']}",
            f"- Message: {result['message']}",
            "",
            "## File Content",
            content_block,
        ]

        llm_response = "\n".join(metadata)

        # Build user summary
        user_response = (
            f"Retrieved version of `{file_path}` | "
            f"Depth: {depth} | "
            f"Commit: {result['short_commit']} | "
            f"Author: {result['author']}"
        )

        logger.info(
            "Retrieved file version: %s (depth=%d, commit=%s)",
            file_path,
            depth,
            result["short_commit"]
        )

        return ToolResponse(user_response=user_response, llm_response=llm_response)

    except ValueError as e:
        error_msg = str(e)
        logger.error("Validation error: %s", error_msg)
        return ToolResponse(
            user_response=f"error [{file_path}]\nERROR: {error_msg}",
            llm_response=f"Failed to retrieve file version: {error_msg}",
        )

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        return ToolResponse(
            user_response=f"error [{file_path}]\nERROR: {error_msg}",
            llm_response=f"Failed to retrieve file version: {error_msg}",
        )

# Made with ❤️ by codx-junior