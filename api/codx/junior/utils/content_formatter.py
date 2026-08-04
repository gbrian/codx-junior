"""
Content Formatter Module

Provides shared utilities for formatting documents and chat messages into
structured context blocks. Used across ChatEngine and ChatEngineActions
to ensure consistent content extraction and formatting.

Made with ❤️ by codx-junior
"""

import logging
from typing import List, Optional

from langchain_core.documents import Document

from codx.junior.globals import LANGUAGE_PARSER_MAPPING
from codx.junior.db import Message

logger = logging.getLogger(__name__)


def format_document_to_context(doc: Document) -> str:
    """
    Format a Document object into a structured context block.

    Extracts language from metadata, resolves it against known parsers,
    and wraps content in a markdown code fence with file path annotation.

    Args:
        doc: A LangChain Document with page_content and metadata.

    Returns:
        Formatted context string with ### FILE CONTEXT header and code fence.

    Example:
        ```
        ### FILE CONTEXT
        File path is 'src/main.py', use same file path in your response.

        ```python src/main.py
        def hello():
            print("world")
        ```
        ```
    """
    content = doc.page_content
    source = doc.metadata['source']
    language = doc.metadata.get('language')
    extension = source.split(".")[-1] if "." in source else ""

    language = language or extension
    language = LANGUAGE_PARSER_MAPPING.get(language, language)

    return "\n".join([
        "### FILE CONTEXT",
        f"File path is '{source}', use same file path in your response.",
        "",
        f"```{language} {source}",
        content,
        "```",
        ""
    ])


def format_message_to_context(
    message: Message,
    include_role: bool = True,
    include_metadata: bool = False
) -> str:
    """
    Format a single chat Message into a context block.

    Follows the same structural pattern as format_document_to_context
    for consistency. Messages are wrapped with role and content delimiters.

    Args:
        message: The chat Message to format.
        include_role: Whether to include the message role in the header.
        include_metadata: Whether to include message metadata (files, profiles, etc).

    Returns:
        Formatted message context string.

    Example:
        ```
        ### MESSAGE CONTEXT
        Role: user

        <message>
        User query content here
        </message>
        ```
    """
    lines = ["### MESSAGE CONTEXT"]

    if include_role:
        lines.append(f"Role: {message.role}")

    lines.append("")
    lines.append(f"<message>")
    lines.append(message.content)
    lines.append("</message>")

    if include_metadata:
        metadata_parts = []
        if message.files:
            metadata_parts.append(f"Files: {', '.join(message.files)}")
        if message.profiles:
            metadata_parts.append(f"Profiles: {', '.join(message.profiles)}")
        if metadata_parts:
            lines.append("")
            lines.extend(metadata_parts)

    lines.append("")
    return "\n".join(lines)


def format_chat_messages_to_context(
    messages: List[Message],
    exclude_hidden: bool = True,
    exclude_improvements: bool = True
) -> str:
    """
    Format a list of chat messages into a consolidated context block.

    Filters messages based on visibility flags and concatenates them
    using a consistent format. This is the primary method used by
    ChatEngineActions.generate_tasks() to extract full chat content
    instead of relying on summarization.

    Args:
        messages: List of Message objects from a chat.
        exclude_hidden: If True, skip messages with hide=True.
        exclude_improvements: If True, skip messages with improvement=True.

    Returns:
        Formatted concatenated context string for all visible messages.

    Example:
        ```
        ### CHAT CONTEXT
        Total messages: 3

        ### MESSAGE CONTEXT
        Role: user
        ...

        ### MESSAGE CONTEXT
        Role: assistant
        ...
        ```
    """
    # Filter messages based on visibility flags
    visible_messages = [
        m for m in messages
        if (not exclude_hidden or not m.hide)
        and (not exclude_improvements or not m.improvement)
    ]

    if not visible_messages:
        return "### CHAT CONTEXT\nNo visible messages in chat.\n"

    lines = [
        "### CHAT CONTEXT",
        f"Total messages: {len(visible_messages)}",
        ""
    ]

    # Append each visible message
    for message in visible_messages:
        msg_context = format_message_to_context(
            message=message,
            include_role=True,
            include_metadata=False
        )
        lines.append(msg_context)

    return "\n".join(lines)


def format_chat_content_for_task_generation(
    chat_messages: List[Message],
    parent_content: str = "",
    last_message_content: str = ""
) -> str:
    """
    Format chat content specifically for task generation.

    Combines parent context, full chat messages, and the latest user
    request in a structured format that preserves all necessary context
    for accurate task decomposition.

    Used by ChatEngineActions.generate_tasks() to build the content
    that is sent to the AI for task splitting.

    Args:
        chat_messages: Messages from the current chat.
        parent_content: Concatenated content from parent chats (if any).
        last_message_content: The latest user message content.

    Returns:
        Formatted content string ready for task generation AI prompt.

    Example:
        ```
        <parent_context>
        ... parent messages ...
        </parent_context>

        <chat_history>
        ### CHAT CONTEXT
        ...
        </chat_history>

        <main_task>
        ... latest user message ...
        </main_task>
        ```
    """
    lines = []

    if parent_content:
        lines.append("<parent_context>")
        lines.append(parent_content.strip())
        lines.append("</parent_context>")
        lines.append("")

    lines.append("<chat_history>")
    lines.append(format_chat_messages_to_context(
        messages=chat_messages,
        exclude_hidden=True,
        exclude_improvements=True
    ).strip())
    lines.append("</chat_history>")
    lines.append("")

    if last_message_content:
        lines.append("<main_task>")
        lines.append(last_message_content.strip())
        lines.append("</main_task>")

    return "\n".join(lines)