"""
Chat organization service.

:class:`ChatOrganizer` runs the decision engines in order and (optionally)
persists the winning decision through the existing
``ChatManager.update_chat_metadata`` API — the same call the
``POST /api/chats/metadata`` endpoint uses, so no new persistence path is
introduced.

```mermaid
flowchart TD
    A[chat] --> B[build OrganizationContext from kanban.json]
    B --> C{context complete?}
    C -- no --> Z[None: keep defaults]
    C -- yes --> D[next engine]
    D --> E{engine available?}
    E -- no --> D
    E -- yes --> F[engine.organize]
    F --> G{confident decision?}
    G -- no / abstain --> D
    G -- yes --> H[ChatOrganization]
    H --> I[ChatManager.update_chat_metadata board/column/priority]
```
"""

import logging
from typing import List, Optional

from codx.junior.db import Chat
from codx.junior.organizer.base import ChatOrganizationEngine
from codx.junior.organizer.catalogue import build_context
from codx.junior.organizer.engines import build_default_engines
from codx.junior.organizer.models import ChatOrganization, OrganizationContext

logger = logging.getLogger(__name__)


class ChatOrganizer:
    """
    Decides — and optionally applies — where a chat lives (board + column).

    Engines are tried in order; the first confident decision wins and the
    fallback engine (the LLM, as today) is used when the preferred engine is
    unavailable or abstains.
    """

    def __init__(
        self,
        settings,
        chat_manager=None,
        engines: Optional[List[ChatOrganizationEngine]] = None,
        ai=None,
        llm_model: Optional[str] = None,
        analytics=None,
    ) -> None:
        """
        :param settings: Project settings.
        :param chat_manager: Optional ``ChatManager`` (built lazily otherwise).
        :param engines: Optional explicit engine chain (overrides the defaults).
        :param ai: Optional pre-built AI instance for the fallback engine.
        :param llm_model: Optional model override for the fallback engine.
        :param analytics: Optional decision analytics recorder shared by the
            default engine chain (best-effort).
        """
        self.settings = settings
        self._chat_manager = chat_manager
        self._engines = engines
        self._ai = ai
        self._llm_model = llm_model
        self._analytics = analytics

    # -- lazy collaborators -------------------------------------------------

    @property
    def chat_manager(self):
        """The project's ``ChatManager`` (built on first use)."""
        if self._chat_manager is None:
            from codx.junior.chat_manager import ChatManager

            self._chat_manager = ChatManager(settings=self.settings)
        return self._chat_manager

    @property
    def engines(self) -> List[ChatOrganizationEngine]:
        """The ordered engine chain (built on first use)."""
        if self._engines is None:
            self._engines = build_default_engines(
                settings=self.settings,
                ai=self._ai,
                llm_model=self._llm_model,
                analytics=self._analytics,
            )
        return self._engines

    # -- catalogue ----------------------------------------------------------

    def build_context(self) -> OrganizationContext:
        """Return the project's board/column catalogue."""
        return build_context(self.chat_manager)

    # -- decision process ---------------------------------------------------

    def organize(
        self, chat: Chat, context: Optional[OrganizationContext] = None
    ) -> Optional[ChatOrganization]:
        """
        Ask each engine in order where *chat* belongs.

        :param chat: The chat to organize.
        :param context: Optional pre-built catalogue (avoids re-reading kanban
            when organizing several chats in a row).
        :return: The first confident decision, or ``None`` when no engine could
            decide (the caller should then leave the chat's defaults untouched).
        """
        context = context or self.build_context()
        if not context.is_complete():
            logger.info(
                "Skipping chat organization for '%s': no boards/columns configured",
                chat.id,
            )
            return None

        for engine in self.engines:
            try:
                if not engine.available():
                    logger.debug("Engine '%s' is not available", engine.name)
                    continue
                decision = engine.organize(chat, context)
            except Exception as ex:  # a failing engine must not stop the chain
                logger.exception("Engine '%s' failed for chat '%s': %s", engine.name, chat.id, ex)
                continue

            if decision and not decision.abstained:
                logger.info(
                    "Chat '%s' organized by engine '%s': board='%s' column='%s' "
                    "priority='%s' confidence=%s",
                    chat.id,
                    decision.engine,
                    decision.board,
                    decision.column,
                    decision.priority,
                    decision.confidence,
                )
                return decision
            logger.debug(
                "Engine '%s' produced no decision for chat '%s'", engine.name, chat.id
            )

        logger.info("No engine could organize chat '%s'", chat.id)
        return None

    # -- persistence --------------------------------------------------------

    def apply(
        self,
        chat: Chat,
        decision: Optional[ChatOrganization] = None,
        context: Optional[OrganizationContext] = None,
    ) -> Optional[ChatOrganization]:
        """
        Decide (when needed) and persist the destination on the chat.

        Uses ``ChatManager.update_chat_metadata`` so only metadata fields are
        written and the chat's messages are preserved.

        :param chat: The chat to update (mutated in place and persisted).
        :param decision: Optional decision to apply (a new one is computed when
            omitted).
        :param context: Optional pre-built catalogue for the decision.
        :return: The applied decision, or ``None`` when nothing was decided.
        """
        if decision is None:
            decision = self.organize(chat, context=context)
        if not decision:
            return None

        self.chat_manager.update_chat_metadata(chat, decision.as_metadata())
        logger.info(
            "Applied organization to chat '%s': board='%s' column='%s'",
            chat.id,
            decision.board,
            decision.column,
        )
        return decision

    # -- hooks --------------------------------------------------------------

    @staticmethod
    def needs_organization(chat: Chat) -> bool:
        """
        True when the chat has no destination yet.

        A board/column already set (by the user, the UI or another subsystem)
        always wins: organization only fills the gaps and never moves a chat
        that a human placed.
        """
        return not (chat.board or "").strip() or not (chat.column or "").strip()

    def organize_if_needed(
        self, chat: Chat, context: Optional[OrganizationContext] = None
    ) -> Optional[ChatOrganization]:
        """
        Organize and persist only when the chat still lacks a destination.

        This is the intended hook for new chats (``Chat.auto_initialize``) and
        for flows that currently copy the parent's board/column onto sub-tasks.

        :param chat: The chat to organize.
        :param context: Optional pre-built catalogue.
        :return: The applied decision, or ``None`` when nothing was needed/decided.
        """
        if not self.needs_organization(chat):
            logger.debug("Chat '%s' already has a destination; skipping", chat.id)
            return None
        return self.apply(chat, context=context)


# Made with ❤️ by codx-junior