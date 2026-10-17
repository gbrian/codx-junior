"""
Engine contract for the chat organization decision process.

A *decision engine* takes a chat plus the project's destination catalogue
(:class:`codx.junior.organizer.models.OrganizationContext`) and returns where
the chat should live — or ``None`` / an abstained decision when it cannot tell.

Engines are chained (see :class:`codx.junior.organizer.service.ChatOrganizer`):
the first one that returns a confident decision wins, the next one is used as
fallback. Implementations must therefore be *safe to fail* and never raise.

```mermaid
classDiagram
    class ChatOrganizationEngine {
        <<abstract>>
        +str name
        +available() bool
        +organize(chat, context) Optional~ChatOrganization~
    }
    ChatOrganizationEngine <|-- StructuredOrganizationEngine
    ChatOrganizationEngine <|-- LLMOrganizationEngine
```
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from codx.junior.db import Chat
from codx.junior.organizer.models import ChatOrganization, OrganizationContext

logger = logging.getLogger(__name__)

# How much of a chat is used as "state" by a decision engine.
STATE_MAX_MESSAGES = 4
STATE_MAX_CHARS_PER_MESSAGE = 2000
STATE_MAX_FILES = 10


def build_chat_state(
    chat: Chat,
    max_messages: int = STATE_MAX_MESSAGES,
    max_chars: int = STATE_MAX_CHARS_PER_MESSAGE,
) -> str:
    """
    Build the textual state a decision engine reasons about.

    Only the chat identity plus the last few *visible* messages are included:
    hidden messages (tool noise, streamed drafts, summaries) carry no routing
    signal and would only add noise.

    :param chat: The chat to describe.
    :param max_messages: How many trailing visible messages to include.
    :param max_chars: Per-message character budget.
    :return: A compact, human readable description of the chat.
    """
    lines: List[str] = []
    if chat.name:
        lines.append(f"Name: {chat.name}")
    if chat.description:
        lines.append(f"Description: {chat.description}")
    if chat.mode:
        lines.append(f"Mode: {chat.mode}")
    if chat.file_list:
        lines.append("Files: " + ", ".join(chat.file_list[:STATE_MAX_FILES]))

    visible = [m for m in (chat.messages or []) if not m.hide]
    for message in visible[-max_messages:]:
        content = (message.content or "").strip()
        if content:
            lines.append(f"{message.role or 'user'}: {content[:max_chars]}")
    return "\n".join(lines)


class ChatOrganizationEngine(ABC):
    """
    A pluggable chat organization decision engine.

    Subclasses declare a unique ``name`` (recorded on the decision for
    traceability) and implement :meth:`organize`.
    """

    name: str = "base"

    def available(self) -> bool:
        """
        Return ``False`` when the engine cannot run.

        Used to skip engines whose optional dependency (a local model, a
        remote endpoint, ...) is not present in this deployment.
        """
        return True

    @abstractmethod
    def organize(
        self, chat: Chat, context: OrganizationContext
    ) -> Optional[ChatOrganization]:
        """
        Decide where *chat* belongs.

        :param chat: The chat to organize.
        :param context: The project's board/column catalogue.
        :return: A decision, or ``None`` when the engine has no match
            (the caller then tries the next engine).
        """
        raise NotImplementedError


# Made with ❤️ by codx-junior