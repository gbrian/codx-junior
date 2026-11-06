"""
Execution of isolated worker turns.

This module is the bridge between the orchestration service and the existing
chat engine. It runs **one chat turn per worker card**:

    worker card (a normal Chat, own messages)
        -> ChatEngine.chat_with_project  (one or more SmolAgent tool rounds)
        -> final answer + cost
        -> StepResult (structured contract)

Because every step is a different ``Chat``, the worker starts with a fresh
context: it sees only its own contract, not the supervisor conversation and not
the other steps. That is the context-isolation property that lets a run handle
complex work without exhausting a single context window.

The module imports the heavy AI stack lazily and accepts an injectable
``runner`` so the orchestration service can be tested offline.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Optional

from . import constants as C
from .models import RunState, StepResult, parse_step_result
from .prompts import STEP_SYSTEM_PROMPT, SUPERVISOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class StepTimeout(RuntimeError):
    """The worker turn exceeded the per-step timeout."""


# SmolAgent appends this notice when it stops to respect Chat.estimation_cost.
# A worker that hit its cap must not be reported as a completed step even if it
# wrote a partial "done" answer before stopping.
BUDGET_STOP_MARKER = "Execution was stopped to keep the chat within budget"


class StepExecutor:
    """
    Runs chat turns for the supervisor and for the worker cards.

    Args:
        settings: Project settings.
        chat_manager: ``ChatManager`` used to persist the cards.
        event_manager: Optional event manager forwarded to ``ChatEngine``.
        user: Optional ``CodxUser`` used for API keys/analytics.
        runner: Optional async callable ``(chat, system) -> Chat`` replacing the
            real ``ChatEngine`` call (tests).
    """

    def __init__(
        self,
        settings: Any,
        chat_manager: Any,
        event_manager: Any = None,
        user: Any = None,
        runner: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.settings = settings
        self.chat_manager = chat_manager
        self.event_manager = event_manager
        self.user = user
        self._runner = runner

    # -- low level --------------------------------------------------------

    def _cost_of(self, chat: Any) -> float:
        """Return the accumulated cost of *chat*."""
        try:
            return float(getattr(chat, "cost", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _last_assistant_message(chat: Any) -> Any:
        """Return the last non-hidden assistant message of *chat*, if any."""
        for message in reversed(getattr(chat, "messages", []) or []):
            if getattr(message, "role", "") == "assistant":
                return message
        return None

    @staticmethod
    def _message_error(chat: Any) -> str:
        """Return the error/cancellation recorded on the last response message."""
        message = StepExecutor._last_assistant_message(chat)
        if message is None:
            return ""
        error = str(getattr(message, "error", "") or "").strip()
        meta = getattr(message, "meta_data", None) or {}
        if not error and meta.get("cancelled_at"):
            error = "The worker turn was cancelled."
        return error

    async def _call_engine(self, chat: Any, system: Optional[str]) -> Any:
        """
        Execute one real chat turn.

        The import is local so the orchestration service can be imported without
        the AI dependency stack (tests, tooling).
        """
        from codx.junior.chat.chat_engine import ChatEngine

        engine = ChatEngine(
            settings=self.settings,
            event_manager=self.event_manager,
            user=self.user,
        )
        await engine.chat_with_project(chat=chat, system=system)
        return chat

    async def run_chat(
        self,
        chat: Any,
        *,
        system: Optional[str] = None,
        timeout: Optional[float] = None,
        parent_token: Any = None,
    ) -> Any:
        """
        Run one chat turn with cancellation propagation and a hard timeout.

        Args:
            chat: The chat/card to process (mutated by the engine).
            system: Optional extra system prompt.
            timeout: Maximum seconds. ``None`` uses no extra timeout (the chat
                engine's own cancellation and budget still apply).
            parent_token: Optional parent ``CancellationToken``. When it is
                cancelled, the child token is cancelled too.

        Returns:
            The processed chat.

        Raises:
            StepTimeout: When the turn exceeds *timeout*.
        """
        from codx.junior.ai.cancellation import CANCELLATION_REGISTRY

        watchdog: Optional[asyncio.Task] = None

        async def _watch_parent() -> None:
            try:
                await parent_token.wait_for_cancellation()
            except asyncio.CancelledError:
                return
            logger.info(
                "Orchestration: parent cancellation propagated to chat '%s'",
                getattr(chat, "id", ""),
            )
            CANCELLATION_REGISTRY.cancel(str(getattr(chat, "id", "")))

        if parent_token is not None:
            watchdog = asyncio.create_task(_watch_parent())

        runner = self._runner
        try:
            coroutine = (
                runner(chat, system)
                if runner is not None
                else self._call_engine(chat, system)
            )
            if timeout and timeout > 0:
                await asyncio.wait_for(coroutine, timeout=float(timeout))
            else:
                await coroutine
        except asyncio.TimeoutError as ex:
            # Stop the child turn deterministically; the event bridge keeps the
            # partial answer, so nothing is lost.
            CANCELLATION_REGISTRY.cancel(str(getattr(chat, "id", "")))
            raise StepTimeout(
                f"Worker turn exceeded {int(timeout or 0)}s"
            ) from ex
        finally:
            if watchdog is not None:
                watchdog.cancel()
            # Persist the final state of the card (the engine already persists
            # incrementally; this guarantees the last message/cost is on disk).
            try:
                self.chat_manager.save_chat(chat=chat)
            except Exception as ex:  # pragma: no cover - defensive
                logger.warning(
                    "Orchestration: could not persist chat '%s' after the turn: %s",
                    getattr(chat, "id", ""),
                    ex,
                )
        return chat

    # -- public API -------------------------------------------------------

    async def execute_step(
        self,
        run: RunState,
        step: Any,
        chat: Any,
        *,
        parent_token: Any = None,
        timeout: Optional[float] = None,
    ) -> StepResult:
        """
        Execute one plan step and return its structured result.

        Args:
            run: Owning run (for context/budget metadata).
            step: The step (not mutated here).
            chat: The worker card, already containing the step contract.
            parent_token: Optional parent cancellation token.
            timeout: Optional timeout override.
        """
        started = time.monotonic()
        cost_before = self._cost_of(chat)
        error = ""
        try:
            await self.run_chat(
                chat,
                system=STEP_SYSTEM_PROMPT,
                timeout=timeout or run.config.step_timeout_seconds,
                parent_token=parent_token,
            )
        except StepTimeout as ex:
            error = str(ex)
        except asyncio.CancelledError:
            raise
        except Exception as ex:  # never lose the step because of a runtime error
            logger.exception(
                "Orchestration: worker turn failed for run '%s' step '%s': %s",
                run.run_id,
                step.id,
                ex,
            )
            error = str(ex)

        duration = time.monotonic() - started
        cost = max(0.0, self._cost_of(chat) - cost_before)
        message = self._last_assistant_message(chat)
        content = str(getattr(message, "content", "") or "") if message else ""
        error = error or self._message_error(chat)
        result = parse_step_result(
            content,
            error=error or None,
            cost_cxjcoins=cost,
            duration_seconds=duration,
        )
        result = self._downgrade_on_budget(result, content)
        logger.info(
            "Orchestration: step '%s' finished status=%s cost=%.6f duration=%.1fs",
            step.id,
            result.status,
            result.cost_cxjcoins,
            result.duration_seconds,
        )
        return result

    @staticmethod
    def _downgrade_on_budget(result: StepResult, content: str) -> StepResult:
        """Mark a step blocked when the worker stopped because of its budget."""
        if result.status not in C.SUCCESSFUL_STEP_STATUSES and result.status != C.STEP_STATUS_DONE:
            return result
        if BUDGET_STOP_MARKER in (content or ""):
            result.status = C.STEP_STATUS_BLOCKED
            result.error = (
                "The worker reached its step budget before completing the work"
            )
        return result

    async def execute_delegate(
        self,
        chat: Any,
        *,
        parent_token: Any = None,
        timeout: Optional[float] = None,
    ) -> StepResult:
        """
        Execute a one-off delegated subagent card (``delegate`` tool).

        Args:
            chat: The delegated chat, containing the delegate contract.
            parent_token: Optional parent cancellation token.
            timeout: Optional timeout (defaults to the step timeout).
        """
        started = time.monotonic()
        cost_before = self._cost_of(chat)
        error = ""
        try:
            await self.run_chat(
                chat,
                system=STEP_SYSTEM_PROMPT,
                timeout=timeout or C.DEFAULT_STEP_TIMEOUT_SECONDS,
                parent_token=parent_token,
            )
        except StepTimeout as ex:
            error = str(ex)
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            logger.exception(
                "Orchestration: delegated task failed for chat '%s': %s",
                getattr(chat, "id", ""),
                ex,
            )
            error = str(ex)

        duration = time.monotonic() - started
        cost = max(0.0, self._cost_of(chat) - cost_before)
        message = self._last_assistant_message(chat)
        content = str(getattr(message, "content", "") or "") if message else ""
        error = error or self._message_error(chat)
        result = parse_step_result(
            content,
            error=error or None,
            cost_cxjcoins=cost,
            duration_seconds=duration,
        )
        return self._downgrade_on_budget(result, content)

    async def run_supervisor(
        self,
        main_chat: Any,
        *,
        timeout: Optional[float] = None,
        parent_token: Any = None,
    ) -> Any:
        """
        Run one supervisor turn on the main task.

        The supervisor's plan/decision is applied by the ``orchestrator`` tool
        (which writes the run store); this method only executes the turn.
        """
        return await self.run_chat(
            main_chat,
            system=SUPERVISOR_SYSTEM_PROMPT,
            timeout=timeout,
            parent_token=parent_token,
        )

# Made with ❤️ by codx-junior
