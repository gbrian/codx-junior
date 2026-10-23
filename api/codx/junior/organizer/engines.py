"""
Decision engine implementations for the chat organization process.

Two engines ship by default:

* :class:`StructuredOrganizationEngine` — a local, typed decider. It answers a
  closed-set question ("which board?" / "which column?") and returns a
  calibrated probability plus an explicit ``abstain`` flag. The underlying
  runtime is an *optional* dependency: when it is not installed the engine
  simply reports ``available() == False`` and is skipped.

* :class:`LLMOrganizationEngine` — the fallback, identical in spirit to the
  current behaviour (ask the configured LLM for a JSON board/column and parse
  it). It is the safety net when the typed decider abstains or is unavailable,
  so a chat is never left unorganized.

Both engines normalise their answer against the project catalogue, so they can
only ever return a board/column that actually exists.

Every decision is also recorded to the analytics store (best-effort) so the
decision process — including the typed model's answers, calibrated
probabilities and abstentions — can be audited afterwards. See
:mod:`codx.junior.analytics`.

```mermaid
flowchart TD
    A[chat + context] --> B[StructuredOrganizationEngine]
    B --> C{available?}
    C -- no --> D
    C -- yes --> E{confident decision?}
    E -- no (abstain) --> D
    E -- yes --> F[ChatOrganization engine=structured]
    D[LLMOrganizationEngine] --> G{available?}
    G -- no --> H[None]
    G -- yes --> I[ChatOrganization engine=llm]
    F --> J[(analytics: decision event)]
    I --> J
```
"""

import logging
import time
from typing import Any, Dict, List, Optional

from codx.junior.db import Chat
from codx.junior.organizer.base import ChatOrganizationEngine, build_chat_state
from codx.junior.organizer.models import (
    PRIORITIES,
    ChatOrganization,
    OrganizationContext,
)
from codx.junior.organizer.prompts import build_organization_prompt
from codx.junior.utils.utils import extract_json_blocks

logger = logging.getLogger(__name__)

# Default model name for the local typed engine (smallest/fastest variant).
STRUCTURED_DEFAULT_MODEL = "0.8b"

# Analytics decision type recorded for every chat organization decision.
DECISION_TYPE_CHAT_ORGANIZATION = "chat_organization"


def _identity(chat: Chat, settings=None) -> Dict[str, Any]:
    """
    Extract the user/project identifiers used when recording decision analytics.

    All lookups are defensive (``getattr`` with defaults) so a chat or settings
    object that does not expose an attribute simply yields an empty value.
    """
    return {
        "username": getattr(chat, "username", "") or "",
        "project_name": getattr(settings, "project_name", "") or "",
        "project_id": getattr(settings, "project_id", "") or "",
    }


def _record_decision(analytics, chat: Chat, settings=None, **kwargs) -> None:
    """
    Persist a decision analytics event, never raising into the chat flow.

    Analytics is a best-effort side channel: a missing recorder or a storage
    failure must never change where a chat ends up.
    """
    if analytics is None:
        return
    try:
        analytics.record_decision(
            chat_id=getattr(chat, "id", None),
            **_identity(chat, settings),
            **kwargs,
        )
    except Exception as ex:  # analytics must never break organization
        logger.warning("Could not record decision analytics: %s", ex)


class StructuredOrganizationEngine(ChatOrganizationEngine):
    """
    Local, typed decision engine.

    It answers closed-set ``choice`` questions derived from the project
    catalogue and returns the selected board/column together with a
    calibrated probability. When the runtime reports it cannot stand behind
    its answer (``abstain``) the engine returns ``None`` so the organizer can
    fall back to the LLM engine.

    The class is named generically on purpose: the concrete decider behind it
    can be replaced (another local model, another typed service, ...) without
    renaming files, classes or the public API.
    """

    name = "structured"

    def __init__(
        self,
        model: str = STRUCTURED_DEFAULT_MODEL,
        analytics=None,
        settings=None,
    ) -> None:
        """
        :param model: Model variant requested from the underlying runtime.
        :param analytics: Optional decision analytics recorder (best-effort).
        :param settings: Optional project settings, used for analytics identity.
        """
        self._model_name = model
        self._runtime = None
        self._analytics = analytics
        self._settings = settings

    def available(self) -> bool:
        """True when the optional local runtime can be imported."""
        try:
            import vegaml  # noqa: F401  (optional dependency, imported lazily)
        except ImportError:
            logger.debug("Structured engine unavailable: runtime not installed")
            return False
        return True

    def _get_runtime(self):
        """Lazily load (and cache) the underlying local runtime."""
        if self._runtime is None:
            import vegaml

            self._runtime = vegaml.load(self._model_name)
            logger.info("Structured engine runtime loaded (model=%s)", self._model_name)
        return self._runtime

    @staticmethod
    def _board_description(context: OrganizationContext, board_name: str) -> str:
        """Human readable criteria for a board (description, else its columns)."""
        board = next((b for b in context.boards if b.name == board_name), None)
        if board and board.description:
            return board.description
        if board and board.column_titles():
            return f"board with columns: {', '.join(board.column_titles())}"
        return board_name

    def _question_sheet(self, context: OrganizationContext) -> Dict[str, dict]:
        """Build the typed questions from the project catalogue."""
        boards = context.board_names()
        columns = context.all_columns() or [context.default_column]
        return {
            "board": {
                "type": "choice",
                "instructions": "Which board should this chat live on?",
                "criteria": {
                    name: self._board_description(context, name) for name in boards
                },
            },
            "column": {
                "type": "choice",
                "instructions": "Which column should this chat live in?",
                "criteria": {name: name for name in columns},
            },
            "priority": {
                "type": "choice",
                "instructions": "How urgent is this task?",
                "criteria": {
                    "high": "blocking or time critical",
                    "medium": "should be done soon",
                    "low": "can wait, no urgency",
                },
            },
        }

    @staticmethod
    def _confidence(answer: dict) -> Optional[float]:
        """Extract the calibrated probability of the chosen answer, if any."""
        choice = (answer or {}).get("choice")
        probs = (answer or {}).get("probs")
        if isinstance(probs, dict) and choice in probs:
            try:
                return float(probs[choice])
            except (TypeError, ValueError):
                return None
        return None

    def organize(
        self, chat: Chat, context: OrganizationContext
    ) -> Optional[ChatOrganization]:
        """
        Decide the chat destination with the local typed runtime.

        :return: A decision, or ``None`` when the engine is unavailable, the
            catalogue is empty, or the runtime abstains (LLM fallback applies).
        """
        if not context.is_complete() or not self.available():
            return None

        state = build_chat_state(chat)
        start = time.monotonic()
        try:
            output = self._get_runtime().decide(state, self._question_sheet(context))
        except Exception as ex:  # a failed decision must never break the chat
            logger.warning("Structured engine failed for chat '%s': %s", chat.id, ex)
            _record_decision(
                self._analytics,
                chat,
                self._settings,
                decision_type=DECISION_TYPE_CHAT_ORGANIZATION,
                engine=self.name,
                model=self._model_name,
                state=state,
                success=False,
                error=str(ex),
                duration_seconds=time.monotonic() - start,
                reason="structured decision failed",
            )
            return None
        duration = time.monotonic() - start

        answers = (output or {}).get("answers") or {}

        board_answer = answers.get("board") or {}

        # Record the raw decision (answers, calibrated probabilities, abstention)
        # before validating it, so the model output is always auditable.
        _record_decision(
            self._analytics,
            chat,
            self._settings,
            decision_type=DECISION_TYPE_CHAT_ORGANIZATION,
            engine=self.name,
            model=self._model_name,
            state=state,
            questions=list(answers.keys()),
            choices={
                key: (value or {}).get("choice")
                for key, value in answers.items()
                if isinstance(value, dict)
            },
            probs={
                key: ((value or {}).get("probs") or {})
                for key, value in answers.items()
                if isinstance(value, dict)
            },
            choice=board_answer.get("choice"),
            confidence=self._confidence(board_answer),
            abstained=bool(board_answer.get("abstain")),
            success=bool(answers),
            duration_seconds=duration,
            reason="typed (closed-set) decision",
            details=output if isinstance(output, dict) else {},
        )

        if board_answer.get("abstain"):
            logger.info(
                "Structured engine abstained for chat '%s'; falling back to LLM", chat.id
            )
            return None
        board = context.canonical_board(board_answer.get("choice"))
        if not board:
            logger.info(
                "Structured engine returned unknown board '%s' for chat '%s'",
                board_answer.get("choice"),
                chat.id,
            )
            return None

        column_answer = answers.get("column") or {}
        column = None
        if not column_answer.get("abstain"):
            column = context.canonical_column(board, column_answer.get("choice"))
        if not column:
            column = context.first_column(board) or context.default_column

        priority_answer = answers.get("priority") or {}
        priority = priority_answer.get("choice")
        priority = priority if priority in PRIORITIES else None

        return ChatOrganization(
            board=board,
            column=column,
            priority=priority,
            engine=self.name,
            confidence=self._confidence(board_answer),
            reason="typed (closed-set) decision",
        )


class LLMOrganizationEngine(ChatOrganizationEngine):
    """
    Fallback decision engine backed by the project's configured LLM.

    This keeps the behaviour that exists today (ask the LLM for JSON and parse
    it) but validates the answer against the catalogue before returning it.
    """

    name = "llm"

    def __init__(
        self,
        settings=None,
        ai=None,
        llm_model: Optional[str] = None,
        analytics=None,
    ) -> None:
        """
        :param settings: Project settings, used to build the AI client lazily.
        :param ai: Optional pre-built AI instance (skips lazy construction).
        :param llm_model: Optional model override for the AI client.
        :param analytics: Optional decision analytics recorder (best-effort).
        """
        self.settings = settings
        self._ai = ai
        self._llm_model = llm_model
        self._analytics = analytics

    def available(self) -> bool:
        """True when an AI client is available (provided or constructible)."""
        return self._ai is not None or self.settings is not None

    def _get_ai(self):
        """Lazily build the AI client so importing this module stays cheap."""
        if self._ai is None:
            from codx.junior.ai import AI
            from codx.junior.model.model import CodxUser

            self._ai = AI(
                settings=self.settings,
                llm_model=self._llm_model,
                user=CodxUser(username=__name__),
            )
        return self._ai

    def organize(
        self, chat: Chat, context: OrganizationContext
    ) -> Optional[ChatOrganization]:
        """
        Ask the LLM where the chat belongs and validate the answer.

        :return: A decision, or ``None`` when the LLM is unavailable, the
            catalogue is empty, or no valid JSON answer was produced.
        """
        if not context.is_complete() or not self.available():
            return None

        state = build_chat_state(chat)
        prompt = build_organization_prompt(state=state, context=context)
        start = time.monotonic()
        try:
            messages = self._get_ai().chat(prompt=prompt)
            content = messages[-1].content
        except Exception as ex:  # never break the chat on an AI failure
            logger.warning("LLM engine failed for chat '%s': %s", chat.id, ex)
            _record_decision(
                self._analytics,
                chat,
                self.settings,
                decision_type=DECISION_TYPE_CHAT_ORGANIZATION,
                engine=self.name,
                model=self._llm_model or "",
                state=state,
                success=False,
                error=str(ex),
                duration_seconds=time.monotonic() - start,
                reason="llm decision failed",
            )
            return None
        duration = time.monotonic() - start

        # The model is asked for a single JSON block; ignore anything that does
        # not carry a "board" key (e.g. an echoed catalogue).
        payload = next(
            (
                block
                for block in extract_json_blocks(content)
                if isinstance(block, dict) and block.get("board")
            ),
            None,
        )
        if not payload:
            logger.warning(
                "LLM engine produced no usable JSON for chat '%s': %s", chat.id, content
            )
            _record_decision(
                self._analytics,
                chat,
                self.settings,
                decision_type=DECISION_TYPE_CHAT_ORGANIZATION,
                engine=self.name,
                model=self._llm_model or "",
                state=state,
                success=False,
                error="no usable JSON in LLM response",
                duration_seconds=duration,
                reason="llm decision unparseable",
                details={"content": content},
            )
            return None

        _record_decision(
            self._analytics,
            chat,
            self.settings,
            decision_type=DECISION_TYPE_CHAT_ORGANIZATION,
            engine=self.name,
            model=self._llm_model or "",
            state=state,
            choice=payload.get("board"),
            success=True,
            duration_seconds=duration,
            reason="llm fallback decision",
            details=payload,
        )

        board = context.canonical_board(payload.get("board"))
        if not board:
            logger.warning(
                "LLM engine returned unknown board '%s' for chat '%s'",
                payload.get("board"),
                chat.id,
            )
            return None

        column = context.canonical_column(board, payload.get("column"))
        if not column:
            column = context.first_column(board) or context.default_column

        priority = payload.get("priority")
        priority = priority if priority in PRIORITIES else None

        return ChatOrganization(
            board=board,
            column=column,
            priority=priority,
            engine=self.name,
            confidence=None,
            reason="llm fallback decision",
        )


def _default_analytics():
    """
    Best-effort construction of the decision analytics recorder.

    Returns ``None`` when analytics cannot be initialised (e.g. the storage
    path is not writable) so the organizer keeps working without logging.
    """
    try:
        from codx.junior.analytics.analytics import Analytics

        return Analytics()
    except Exception as ex:  # pragma: no cover - environment dependent
        logger.warning("Decision analytics unavailable: %s", ex)
        return None


def build_default_engines(
    settings=None,
    ai=None,
    llm_model: Optional[str] = None,
    analytics=None,
) -> List[ChatOrganizationEngine]:
    """
    Build the ordered default engine chain.

    Order matters: the first engine returning a confident decision wins. The
    local typed engine goes first (cheap, deterministic, calibrated, abstains
    when unsure) and the LLM engine is the fallback — so an "I don't know" from
    the typed engine degrades to today's behaviour instead of leaving the chat
    unorganized.

    :param settings: Project settings used to build the fallback AI client.
    :param ai: Optional pre-built AI instance for the fallback engine.
    :param llm_model: Optional model override for the fallback engine.
    :param analytics: Optional decision analytics recorder shared by the chain.
        When omitted, a default recorder is built (best-effort).
    :return: List of engines, highest priority first.
    """
    if analytics is None:
        analytics = _default_analytics()
    return [
        StructuredOrganizationEngine(analytics=analytics, settings=settings),
        LLMOrganizationEngine(
            settings=settings, ai=ai, llm_model=llm_model, analytics=analytics
        ),
    ]


# Made with ❤️ by codx-junior