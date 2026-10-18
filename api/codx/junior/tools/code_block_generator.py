"""
Code block generator tool.

Use this tool to deliver file content changes (create, update or delete) for a
project. It is the supported way to hand a file change over to the user:
instead of writing the file content inside a plain markdown code fence, call
this tool once per file with the full resulting content.

Why use it:

    * the change is clearly attached to a file path and a change type;
    * the user can review and apply it directly from the chat;
    * full file content is accepted as-is, including markdown and code fences.

Made with ❤️ by codx-junior
"""

import base64
import logging
from typing import Union

from .model import ToolResponse

# Configure logging
logger = logging.getLogger(__name__)

# Envelope sentinels, each one must be placed on its own line
CODX_FILE_SENTINEL = "@@ CODX_FILE @@"
CODX_CONTENT_SENTINEL = "@@ CODX_CONTENT @@"
CODX_END_SENTINEL = "@@ CODX_END @@"

# A content line equal to any of these would break the envelope
CODX_SENTINELS = (
    CODX_FILE_SENTINEL,
    CODX_CONTENT_SENTINEL,
    CODX_END_SENTINEL,
)

# Supported envelope header values
CHANGE_TYPES = ("new", "update", "delete")
ENCODINGS = ("text", "base64")
DEFAULT_CHANGE_TYPE = "update"
DEFAULT_ENCODING = "text"


def _error_response(message: str) -> ToolResponse:
    """
    Log a validation error and build the matching ToolResponse.

    Args:
        message (str): Human readable error description.

    Returns:
        ToolResponse: Empty user_response and the error as llm_response.

    Made with ❤️ by codx-junior
    """
    logger.warning(message)
    return ToolResponse(
        user_response="",
        llm_response=message
    )


def _contains_sentinel_line(content: str) -> bool:
    """
    Check whether any line of the content equals an envelope sentinel.

    Lines are stripped before comparing, so a sentinel surrounded by blanks
    (which a lenient parser may accept) is also considered a collision.

    Args:
        content (str): The file content to inspect.

    Returns:
        bool: True when the payload cannot be sent as plain text.

    Made with ❤️ by codx-junior
    """
    for line in content.split("\n"):
        if line.strip() in CODX_SENTINELS:
            return True
    return False


def code_block_generator(
    language: str,
    file_path: str,
    content: str,
    change_type: str = DEFAULT_CHANGE_TYPE,
    encoding: str = DEFAULT_ENCODING
) -> ToolResponse:
    """
    Deliver a file content change for the user to review and apply.

    Use this tool every time a file must be created, rewritten or deleted.
    Do not paste the file content inside a plain markdown code fence: this tool
    is what turns the content into an actionable change for the given file.

    Call it once per file and send the full resulting content, not a diff.
    Content is emitted verbatim, so markdown and code fences are allowed.

    Args:
        language (str): The programming language or file type
                       (e.g., 'python', 'javascript', 'html', 'markdown').
                       Must be a single line.
        file_path (str): The project-relative path of the file.
                        Must be a single line.
        content (str): The full file content, written verbatim (not a diff).
        change_type (str): 'new' to create the file, 'update' to rewrite an
                          existing one or 'delete' to remove it. Defaults to
                          'update'. For 'delete' the content is ignored.
        encoding (str): Payload encoding, 'text' or 'base64'. Defaults to
                       'text'; base64 is applied automatically when plain text
                       would break the block.

    Returns:
        ToolResponse: A dual-return object containing:
                     - user_response: The formatted file change
                     - llm_response: Status message for the LLM

    Example:
        >>> result = code_block_generator(
        ...     language="python",
        ...     file_path="codx/app.py",
        ...     content="print('hello')"
        ... )
        >>> print(result.user_response)
        @@ CODX_FILE @@
        path: codx/app.py
        language: python
        change_type: update
        encoding: text
        @@ CODX_CONTENT @@
        print('hello')
        @@ CODX_END @@
        >>> result.llm_response
        "File envelope created: update 'codx/app.py' (language: python, encoding: text)"

    Made with ❤️ by codx-junior
    """
    try:
        # Validate inputs
        if not isinstance(language, str) or not language.strip():
            return _error_response("Language parameter must be a non-empty string")

        if "\n" in language:
            return _error_response("Language parameter must be a single line")

        if not isinstance(file_path, str) or not file_path.strip():
            return _error_response("File path parameter must be a non-empty string")

        if "\n" in file_path:
            return _error_response("File path parameter must be a single line")

        if not isinstance(content, str):
            return _error_response("Content parameter must be a string")

        # Normalize and validate the envelope header values
        change_type = (change_type or DEFAULT_CHANGE_TYPE).strip().lower()
        if change_type not in CHANGE_TYPES:
            return _error_response(
                "Change type must be one of %s, got: '%s'" % (
                    ", ".join(CHANGE_TYPES),
                    change_type
                )
            )

        encoding = (encoding or DEFAULT_ENCODING).strip().lower()
        if encoding not in ENCODINGS:
            return _error_response(
                "Encoding must be one of %s, got: '%s'" % (
                    ", ".join(ENCODINGS),
                    encoding
                )
            )

        logger.debug(
            "Generating file envelope for: %s (language: %s, change_type: %s)",
            file_path,
            language,
            change_type
        )

        # A delete change carries no content
        if change_type == "delete":
            content = ""
            encoding = "text"

        # Keep the envelope parseable: sentinel lines force base64 encoding
        if encoding == "text" and _contains_sentinel_line(content):
            logger.warning(
                "Content for '%s' contains an envelope sentinel line, "
                "switching to base64 encoding",
                file_path
            )
            encoding = "base64"

        if encoding == "base64":
            payload = base64.b64encode(content.encode("utf-8")).decode("ascii")
        else:
            payload = content

        # Build the CODX file envelope
        envelope = "\n".join([
            CODX_FILE_SENTINEL,
            f"path: {file_path}",
            f"language: {language}",
            f"change_type: {change_type}",
            f"encoding: {encoding}",
            CODX_CONTENT_SENTINEL,
            payload,
            CODX_END_SENTINEL,
        ])

        logger.debug("File envelope generated successfully for: %s", file_path)

        return ToolResponse(
            user_response=envelope,
            llm_response=(
                f"File envelope created: {change_type} '{file_path}' "
                f"(language: {language}, encoding: {encoding})"
            )
        )

    except Exception as e:
        error_msg = f"Unexpected error generating file envelope: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return ToolResponse(
            user_response="",
            llm_response=error_msg
        )