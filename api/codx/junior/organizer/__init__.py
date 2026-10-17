"""
Chat organization decision process.

Decides where a chat lives (board + column) using a chain of pluggable
decision engines. Names are intentionally generic: the concrete decider behind
an engine (a local typed model, an LLM prompt, a rule set, ...) can be swapped
without renaming files, classes or the public API.

```mermaid
flowchart LR
    A[ChatOrganizer] --> B[ChatOrganizationEngine chain]
    B --> C[StructuredOrganizationEngine]
    C -- unavailable / abstain --> D[LLMOrganizationEngine]
    C --> E[ChatOrganization]
    D --> E
    E --> F[ChatManager.update_chat_metadata]
```

Quick usage::

    from codx.junior.organizer import ChatOrganizer

    organizer = ChatOrganizer(settings=session.settings,
                              chat_manager=session.get_chat_manager())
    organizer.organize_if_needed(chat)   # fills board/column/priority
"""

from codx.junior.organizer.base import ChatOrganizationEngine, build_chat_state
from codx.junior.organizer.catalogue import build_context, build_context_from_kanban
from codx.junior.organizer.engines import (
    LLMOrganizationEngine,
    StructuredOrganizationEngine,
    build_default_engines,
)
from codx.junior.organizer.models import (
    DEFAULT_BOARD,
    DEFAULT_COLUMN,
    PRIORITIES,
    REVIEW_COLUMN,
    BoardColumn,
    BoardInfo,
    ChatOrganization,
    OrganizationContext,
)
from codx.junior.organizer.prompts import build_organization_prompt
from codx.junior.organizer.service import ChatOrganizer

__all__ = [
    # service
    "ChatOrganizer",
    # engine contract
    "ChatOrganizationEngine",
    "build_chat_state",
    # engines
    "StructuredOrganizationEngine",
    "LLMOrganizationEngine",
    "build_default_engines",
    # catalogue
    "OrganizationContext",
    "BoardInfo",
    "BoardColumn",
    "build_context",
    "build_context_from_kanban",
    # decision
    "ChatOrganization",
    "build_organization_prompt",
    # constants
    "DEFAULT_BOARD",
    "DEFAULT_COLUMN",
    "REVIEW_COLUMN",
    "PRIORITIES",
]

# Made with ❤️ by codx-junior