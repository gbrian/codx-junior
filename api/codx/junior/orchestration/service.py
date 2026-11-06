"""
Durable orchestration service: the brain of the board-native run.

Responsibilities
----------------
* **Run lifecycle** — create/attach a run to a main task, pause, resume, stop,
  finish; persist everything through :class:`~.store.RunStore`.
* **Plan management** — upsert the plan produced by the supervisor, validate the
  dependency graph, retry steps (`orchestrator` tool).
* **Advancement** — one ``tick`` per run: refresh budgets, recover interrupted
  workers, run a supervisor round (plan/verify/replan) or dispatch the ready
  steps in parallel, mirror every transition to the board/sprint.
* **Reports** — a delivery report on completion and no-AI reports for budget
  exhaustion, stalls and stops, so a human always gets an artefact.

The service is deliberately independent from the AI stack at import time: the
chat manager, the executor and the board can be injected (tests use fakes), and
the heavy imports happen only when a real worker turn runs.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Sequence

from . import constants as C
from . import prompts
from .board import RunBoard
from .executor import StepExecutor, StepTimeout
from .models import (
    PlanError,
    PlanStep,
    RunConfig,
    RunState,
    StepResult,
    blocked_steps,
    merge_plan,
    next_actions,
    ready_steps,
    result_to_step_status,
    utcnow_iso,
)
from .store import DEFAULT_WORKER_TTL_SECONDS, RunStore

logger = logging.getLogger(__name__)


class OrchestrationService:
    """
    Application service for orchestration runs.

    Args:
        settings: Project settings (``codx_path``, ``project_id``...).
        chat_manager: Optional ``ChatManager`` (built lazily from *settings*).
        event_manager: Optional event manager for socket notifications.
        user: Optional ``CodxUser`` used by the supervisor/worker turns.
        store: Optional :class:`RunStore` (tests).
        board: Optional :class:`RunBoard` (tests).
        executor: Optional :class:`StepExecutor` (tests).
    """

    def __init__(
        self,
        settings: Any,
        chat_manager: Any = None,
        event_manager: Any = None,
        user: Any = None,
        store: Optional[RunStore] = None,
        board: Optional[RunBoard] = None,
        executor: Optional[StepExecutor] = None,
        message_factory: Optional[Any] = None,
    ) -> None:
        self.settings = settings
        self.chat_manager = chat_manager
        self.event_manager = event_manager
        self.user = user
        self.message_factory = message_factory
        self.store = store or RunStore(getattr(settings, "codx_path", ""))
        self.board = board or RunBoard(
            settings=settings,
            chat_manager=chat_manager,
            event_manager=event_manager,
        )
        self.executor = executor or StepExecutor(
            settings=settings,
            chat_manager=chat_manager,
            event_manager=event_manager,
            user=user,
        )

    # -- dependencies -----------------------------------------------------

    def _manager(self) -> Any:
        """Return (creating if needed) the project ChatManager."""
        if self.chat_manager is None:
            from codx.junior.chat_manager import ChatManager

            self.chat_manager = ChatManager(
                settings=self.settings,
                event_manager=self.event_manager,
            )
        return self.chat_manager

    def _message(self, **kwargs: Any) -> Any:
        """Create a ``Message`` (injectable for offline tests)."""
        if self.message_factory is not None:
            return self.message_factory(**kwargs)
        from codx.junior.db import Message

        return Message(**kwargs)

    # -- events / persistence --------------------------------------------

    def _emit(self, run: RunState, event_type: str, message: str = "", **data: Any) -> None:
        """Append the event to the run timeline and notify listeners."""
        run.add_event(event_type, message, **data)
        if self.event_manager is not None:
            emit = getattr(self.event_manager, "orchestration_event", None)
            if callable(emit):
                try:
                    emit({
                        "run_id": run.run_id,
                        "event": event_type,
                        "message": message,
                        "status": run.status,
                        "main_chat_id": run.main_chat_id,
                        "progress": run.progress(),
                        **data,
                    })
                except Exception as ex:  # pragma: no cover - notifications are best effort
                    logger.warning("Orchestration: could not emit event: %s", ex)

    def _save(self, run: RunState) -> RunState:
        """Persist *run* (atomic write)."""
        run.touch()
        return self.store.save(run)

    def _update_main_card_safe(self, run: RunState, **kwargs: Any) -> None:
        """Mirror the run on the main card without ever losing the run state."""
        try:
            self.board.update_main_card(run, **kwargs)
        except Exception as ex:  # pragma: no cover - defensive
            logger.warning(
                "Orchestration: could not update the main card of run '%s': %s",
                run.run_id,
                ex,
            )

    def _append_report(
        self,
        run: RunState,
        content: str,
        main_chat: Optional[Any] = None,
    ) -> None:
        """
        Publish a report message on the main task (idempotent per run).

        ``main_chat`` must be the SAME object the chat engine is holding when the
        report is written from inside a turn (``finish``/``stop`` tool): the
        engine saves that object at the end of the turn, and a report appended to
        a separately loaded object would be overwritten.
        """
        if not content:
            return
        # Keep the report in the durable run document too: the message on the
        # main task is the human-facing copy, but the run store must never lose
        # the report (the main task can be missing, moved or archived).
        run.last_report = content[:40000]
        if run.report_written:
            return
        if main_chat is None or str(getattr(main_chat, "id", "")) != str(run.main_chat_id):
            main_chat = None
            try:
                main_chat = self._manager().find_by_id(run.main_chat_id)
            except Exception as ex:  # pragma: no cover - defensive
                logger.warning("Orchestration: could not load main task for report: %s", ex)
        if main_chat is None:
            logger.warning(
                "Orchestration: main task '%s' not found; report kept in the run store",
                run.main_chat_id,
            )
            run.report_written = True
            return
        # Idempotency beyond the persisted flag: if a previous attempt wrote
        # the report but a crash prevented saving `report_written`, do not add a
        # second copy.
        generation = int(getattr(run, "report_generation", 0) or 0)
        for existing in getattr(main_chat, "messages", []) or []:
            meta = getattr(existing, "meta_data", None) or {}
            if (
                meta.get("orchestration_report")
                and meta.get("run_id") == run.run_id
                and int(meta.get("report_generation", 0) or 0) == generation
            ):
                run.report_written = True
                return
        message = self._message(
            role="assistant",
            content=content,
            task_item="summary",
            meta_data={
                "run_id": run.run_id,
                "run_status": run.status,
                "report_generation": generation,
                "orchestration_report": True,
            },
        )
        try:
            self._manager().add_message(chat=main_chat, message=message)
            run.report_written = True
            self._emit(run, "report", "Delivery report published on the main task")
        except Exception as ex:  # pragma: no cover - defensive
            logger.exception("Orchestration: could not publish run report: %s", ex)

    def _append_supervisor_prompt(self, run: RunState, main_chat: Any, prompt: str) -> None:
        """Append the supervisor round prompt to the main task and persist it."""
        profiles = list(run.config.supervisor_profiles or [])
        current = list(main_chat.profiles or [])
        for name in profiles:
            clean = str(name or "").strip().lstrip("@")
            if clean and clean not in current:
                current.append(clean)
        main_chat.profiles = current
        main_chat.messages.append(
            self._message(role="user", content=prompt, profiles=profiles)
        )
        main_chat.run_id = run.run_id
        main_chat.run_status = run.status
        main_chat.status = "doing"
        if run.config.budget_cxjcoins > 0:
            main_chat.estimation_cost = run.config.budget_cxjcoins
        # Persist BEFORE the AI call so a crash never loses the round prompt.
        self._manager().save_chat(chat=main_chat)

    # -- creation ---------------------------------------------------------

    @staticmethod
    def _default_objective(chat: Any) -> str:
        """Return a sensible objective from the chat (last visible user message)."""
        for message in reversed(getattr(chat, "messages", []) or []):
            if getattr(message, "role", "") == "user" and not getattr(message, "hide", False):
                content = str(getattr(message, "content", "") or "").strip()
                if content:
                    return content[:8000]
        return str(getattr(chat, "description", "") or getattr(chat, "name", "") or "").strip()

    def create_run(
        self,
        *,
        name: str = "",
        objective: str = "",
        config: Optional[RunConfig] = None,
        main_chat: Any = None,
        created_by: str = "",
        start: bool = True,
        persist_main: bool = True,
    ) -> RunState:
        """
        Create a run, optionally attached to an existing main task.

        When *main_chat* is omitted a new main task is created on the run board
        (API path). When it is provided the chat becomes the run dashboard and
        keeps its board/column unless the caller moves it (tool path).

        Args:
            name: Run name (defaults to the main task name).
            objective: What the run must achieve.
            config: Policy/budget/limits.
            main_chat: Optional existing chat to use as the main task.
            created_by: Username recorded for audit.
            start: Start immediately (running) or leave queued.
            persist_main: Persist the main chat now. Keep False when this is
                called from inside a chat turn (the engine saves it at the end).

        Returns:
            The persisted run.
        """
        if main_chat is not None and getattr(main_chat, "run_id", None):
            return self.get(main_chat.run_id)

        if config is None:
            config = RunConfig()
        elif isinstance(config, dict):
            config = RunConfig(**config)
        config = config.normalized()
        if config.budget_cxjcoins <= 0:
            existing_budget = float(getattr(main_chat, "estimation_cost", 0.0) or 0.0)
            if existing_budget > 0:
                config.budget_cxjcoins = existing_budget

        objective = (objective or (self._default_objective(main_chat) if main_chat else "") or name).strip()
        name = (name or getattr(main_chat, "name", "") or "Orchestration run").strip()
        if not objective:
            raise ValueError("An orchestration run requires an objective")

        run = RunState(
            name=name,
            objective=objective,
            config=config,
            status=C.RUN_STATUS_QUEUED,
            pending_supervisor=True,
            created_at=utcnow_iso(),
            updated_at=utcnow_iso(),
        )
        run.config.created_by = created_by or run.config.created_by

        # The catalogue must exist before the main card is created/saved.
        self.board.ensure_run(run)

        if main_chat is not None:
            if not getattr(main_chat, "id", None):
                raise ValueError("The main task must be persisted (it needs an id) before attaching a run")
            if getattr(main_chat, "parent_id", None):
                raise ValueError(
                    "The main task of a run must be a root task (it cannot have a "
                    "parent): the run budget lives on the root cost accumulator. "
                    "Start the run from the root task or create a new one."
                )
            # A run is always a budget root, even for legacy chats whose root_id
            # cache points somewhere else.
            if getattr(main_chat, "root_id", None) != main_chat.id:
                main_chat.root_id = main_chat.id
            run.main_chat_id = str(main_chat.id or "")
            self.board.attach_main(
                run,
                main_chat,
                persist=False,
                move=False,
                status="todo",
                progress=0,
            )
            if run.config.budget_cxjcoins > 0:
                main_chat.estimation_cost = run.config.budget_cxjcoins
            if persist_main:
                self._manager().save_chat(chat=main_chat)
        else:
            main_chat = self.board.create_main_task(
                run,
                profiles=run.config.supervisor_profiles,
                estimation_cost=run.config.budget_cxjcoins or None,
            )
            run.main_chat_id = str(main_chat.id or "")
            self.board.attach_main(
                run,
                main_chat,
                persist=True,
                move=False,
                status="todo",
                progress=0,
            )

        if start:
            run.status = C.RUN_STATUS_RUNNING
            run.started_at = run.started_at or utcnow_iso()
            if main_chat is not None:
                main_chat.run_status = run.status
                main_chat.status = "doing"
                if persist_main:
                    self._manager().save_chat(chat=main_chat)

        self._save(run)
        self._emit(
            run,
            "run_created",
            f"Run '{run.name}' created with board '{run.config.board}' and sprint '{run.config.sprint}'",
            main_chat_id=run.main_chat_id,
        )
        logger.info(
            "Orchestration: run created id='%s' name='%s' main='%s' board='%s' sprint='%s' budget=%s",
            run.run_id,
            run.name,
            run.main_chat_id,
            run.config.board,
            run.config.sprint,
            run.config.budget_cxjcoins,
        )
        return run

    def attach_run(
        self,
        chat: Any,
        *,
        name: str = "",
        objective: str = "",
        config: Optional[RunConfig] = None,
        created_by: str = "",
        start: bool = True,
        persist_main: bool = False,
    ) -> RunState:
        """
        Turn an existing chat into the main task of a run.

        This is the tool path (``orchestrator(action="start")``): the current
        chat is mid-turn, so by default it is NOT persisted here — the chat
        engine saves the chat at the end of the turn, including ``run_id``.
        """
        return self.create_run(
            name=name,
            objective=objective,
            config=config,
            main_chat=chat,
            created_by=created_by,
            start=start,
            persist_main=persist_main,
        )

    # -- read -------------------------------------------------------------

    def get(self, run_id: str) -> RunState:
        """Load one run."""
        return self.store.load(run_id)

    def _summary_payload(self, run: RunState, worker: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Compact run representation used by list endpoints/tools."""
        remaining = run.remaining_budget()
        counts = run.counts()
        counts["total"] = len(run.steps)
        return {
            "run_id": run.run_id,
            "name": run.name,
            "objective": run.objective,
            "status": run.status,
            "main_chat_id": run.main_chat_id,
            "board": run.config.board,
            "sprint": run.config.sprint,
            "progress": run.progress(),
            "counts": counts,
            "spent_cxjcoins": round(float(run.spent_cxjcoins or 0.0), 6),
            "budget_cxjcoins": run.config.budget_cxjcoins,
            "remaining_cxjcoins": round(remaining, 6) if remaining is not None else None,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "stop_reason": run.stop_reason,
            "last_error": run.last_error,
            "rounds": run.rounds,
            "worker": worker or {},
        }

    def list_runs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List readable runs (newest first) with a compact payload."""
        worker = self.worker_status()
        return [self._summary_payload(run, worker) for run in self.store.list_runs(status=status)]

    def summary(self, run_id: str) -> Dict[str, Any]:
        """Return the compact payload of one run (public counterpart of status)."""
        return self._summary_payload(self.get(run_id), self.worker_status())

    def get_chat(self, chat_id: str) -> Optional[Any]:
        """Load a chat by id (main task or card)."""
        if not chat_id:
            return None
        return self._manager().find_by_id(chat_id)

    def assert_actor(self, run: RunState, actor_chat_id: Optional[str]) -> None:
        """Public wrapper around the main-task actor guard."""
        self._assert_actor(run, actor_chat_id)

    def status(self, run_id: str, *, include_events: bool = True) -> Dict[str, Any]:
        """
        Return the detail payload of a run (API/tool).

        The payload includes the plan, the per-step results, the next action
        diagnosis, the board/sprint location and the worker presence.
        """
        run = self.get(run_id)
        self._refresh_spent(run)
        payload = run.model_dump()
        payload["progress"] = run.progress()
        counts = run.counts()
        counts["total"] = len(run.steps)
        payload["counts"] = counts
        payload["budget_cxjcoins"] = run.config.budget_cxjcoins
        payload["spent_cxjcoins"] = round(float(run.spent_cxjcoins or 0.0), 6)
        remaining = run.remaining_budget()
        payload["remaining_cxjcoins"] = round(remaining, 6) if remaining is not None else None
        payload["reserve_cxjcoins"] = round(run.config.resolve_reserve(), 6)
        payload["plan_table"] = prompts.render_plan_table(run)
        payload["next_action"] = next_actions(run)
        payload["worker"] = self.worker_status()
        if not include_events:
            payload["events"] = payload.get("events", [])[-10:]
        return payload

    def worker_status(self) -> Dict[str, Any]:
        """Return the background-worker presence for this project."""
        try:
            ttl = float(os.environ.get(C.ENV_WORKER_TTL, DEFAULT_WORKER_TTL_SECONDS))
        except (TypeError, ValueError):
            ttl = DEFAULT_WORKER_TTL_SECONDS
        return self.store.worker_status(ttl_seconds=ttl)

    # -- plan management --------------------------------------------------

    @staticmethod
    def _assert_actor(run: RunState, actor_chat_id: Optional[str]) -> None:
        """Reject plan/finish changes coming from a chat that is not the main task."""
        if actor_chat_id and run.main_chat_id and str(actor_chat_id) != str(run.main_chat_id):
            raise PlanError(
                "Only the main task of the run can change its plan or finish it"
            )

    def plan(
        self,
        run_id: str,
        steps: Sequence[Any],
        *,
        remove_step_ids: Optional[Sequence[str]] = None,
        actor_chat_id: Optional[str] = None,
    ) -> RunState:
        """
        Upsert steps into the run plan (supervisor tool).

        Existing steps not mentioned are kept; running/terminal steps are never
        reset implicitly. Dependencies are validated (unknown/cycle rejected).
        """
        run = self.get(run_id)
        self._assert_actor(run, actor_chat_id)
        if run.is_terminal():
            raise PlanError(f"Run '{run.name}' is already {run.status}")
        removals = {str(step_id).strip() for step_id in (remove_step_ids or []) if str(step_id).strip()}
        removed_steps = [step for step in run.steps if step.id in removals]
        run.steps = merge_plan(run, steps, remove_step_ids=remove_step_ids)
        for removed in removed_steps:
            self._archive_step_card(run, removed)
        run.pending_supervisor = False
        run.last_error = ""
        self._emit(
            run,
            "plan_updated",
            f"Plan updated: {len(run.steps)} step(s)",
            steps=[step.id for step in run.steps],
        )
        self._save(run)
        return run

    def add_step(self, run_id: str, step: Any, *, actor_chat_id: Optional[str] = None) -> RunState:
        """Add one step to the plan."""
        return self.plan(run_id, [step], actor_chat_id=actor_chat_id)

    def remove_steps(
        self,
        run_id: str,
        step_ids: Sequence[str],
        *,
        actor_chat_id: Optional[str] = None,
    ) -> RunState:
        """Remove steps that have not run/are not complete."""
        return self.plan(
            run_id,
            [],
            remove_step_ids=step_ids,
            actor_chat_id=actor_chat_id,
        )

    def _archive_step_card(self, run: RunState, step: PlanStep) -> None:
        """Keep a removed step's card visible as rejected (never silently hide work)."""
        if not step.chat_id:
            return
        try:
            card = self._manager().find_by_id(step.chat_id)
        except Exception:  # pragma: no cover - defensive
            card = None
        if card is None:
            return
        card.status = "rejected"
        card.column = (run.config.columns or C.DEFAULT_RUN_COLUMNS).get(
            "blocked", "Blocked"
        )
        tags = list(card.tags or [])
        if "run-removed" not in tags:
            tags.append("run-removed")
        card.tags = tags
        try:
            self._manager().save_chat(chat=card, chat_only=True)
        except Exception as ex:  # pragma: no cover - defensive
            logger.warning("Orchestration: could not archive removed step card: %s", ex)
        self._emit(
            run,
            "step_removed",
            f"Step '{step.title}' removed from the plan; its card was marked rejected",
            step_id=step.id,
            chat_id=step.chat_id,
        )

    def retry_step(self, run_id: str, step_id: str, *, actor_chat_id: Optional[str] = None) -> RunState:
        """
        Reset a failed/blocked step so the worker runs it again.

        The card is reused, so the worker sees its previous attempt in the
        conversation and can take a different approach. Attempts reset to 0 to
        give the retry a fresh allowance.
        """
        run = self.get(run_id)
        self._assert_actor(run, actor_chat_id)
        step = run.step_by_id(step_id)
        if step is None:
            raise PlanError(f"Unknown step '{step_id}'")
        if step.status == C.STEP_STATUS_RUNNING:
            raise PlanError(f"Step '{step.title}' is already running")
        if step.status in C.SUCCESSFUL_STEP_STATUSES:
            raise PlanError(f"Step '{step.title}' is already completed")
        step.status = C.STEP_STATUS_PENDING
        step.attempts = 0
        step.result = None
        step.error = ""
        step.finished_at = ""
        step.updated_at = utcnow_iso()
        run.pending_supervisor = False
        self.board.update_step_card(run, step)
        self._emit(run, "step_retried", f"Step '{step.title}' queued for retry", step_id=step.id)
        self._save(run)
        return run

    def finish(
        self,
        run_id: str,
        summary: str,
        *,
        actor_chat_id: Optional[str] = None,
        main_chat: Optional[Any] = None,
    ) -> RunState:
        """
        Mark a run as completed and publish the delivery report.

        Only the main task may finish a run (when ``actor_chat_id`` is given).
        The report is written immediately, so it survives even if the worker is
        not running.
        """
        run = self.get(run_id)
        self._assert_actor(run, actor_chat_id)
        self._refresh_spent(run)
        summary = (summary or "").strip()
        if not summary:
            raise PlanError("finish requires a summary for the delivery report")
        if run.status in C.TERMINAL_RUN_STATUSES and run.status != C.RUN_STATUS_COMPLETED:
            raise PlanError(f"Run '{run.name}' is already {run.status}")
        run.status = C.RUN_STATUS_COMPLETED
        run.stop_reason = summary
        run.finished_at = run.finished_at or utcnow_iso()
        run.pending_supervisor = False
        self._update_main_card_safe(
            run,
            status="done",
            column_phase="done",
            progress=100,
            run_status=run.status,
        )
        self._append_report(
            run,
            prompts.build_delivery_report(run, summary),
            main_chat=main_chat,
        )
        self._emit(run, "run_completed", "Run completed", summary=summary[:2000])
        self._save(run)
        return run

    # -- control ----------------------------------------------------------

    def pause(self, run_id: str, reason: str = "") -> RunState:
        """Pause a run (the in-flight turn, if any, is allowed to finish)."""
        run = self.get(run_id)
        if run.is_terminal():
            return run
        run.status = C.RUN_STATUS_PAUSED
        run.stop_reason = reason or run.stop_reason
        self._update_main_card_safe(run, status="onhold", run_status=run.status)
        self._emit(run, "run_paused", reason or "Run paused")
        self._save(run)
        return run

    def resume(self, run_id: str) -> RunState:
        """Resume a paused/queued/stalled run without reopening it."""
        run = self.get(run_id)
        if run.status not in (C.RUN_STATUS_PAUSED, C.RUN_STATUS_QUEUED, C.RUN_STATUS_STALLED):
            return run
        was_stalled = run.status == C.RUN_STATUS_STALLED
        run.status = C.RUN_STATUS_RUNNING
        run.started_at = run.started_at or utcnow_iso()
        run.finished_at = ""
        run.stagnant_rounds = 0
        run.pending_supervisor = was_stalled or not run.steps
        # A stalled run published a stall report before this resume. That report
        # must not suppress the delivery/budget report of the new attempt: bump
        # the generation (so the idempotency marker of the old report no longer
        # matches) and allow a new report to be written.
        if was_stalled and run.report_written:
            run.report_generation = int(getattr(run, "report_generation", 0) or 0) + 1
            run.report_written = False
        self._update_main_card_safe(run, status="doing", run_status=run.status)
        self._emit(run, "run_resumed", "Run resumed")
        self._save(run)
        return run

    def start(self, run_id: str) -> RunState:
        """
        Start (or restart) a run from the UI/API.

        ``start`` is the single user-facing "go" action:

        * an active run is returned unchanged (idempotent),
        * a paused/queued/stalled run is resumed,
        * a stopped/failed run is reopened and continues from its persisted
          plan (the previous control/report events are kept in the timeline),
        * a completed run is refused (there is nothing left to do),
        * a budget-exhausted run is refused: the budget must be raised first.

        A stopped run is terminal for the worker (see :meth:`stop`); reopening
        is an explicit human decision made through this method.
        """
        run = self.get(run_id)
        if run.status in C.ACTIVE_RUN_STATUSES:
            return run
        if run.status in (C.RUN_STATUS_PAUSED, C.RUN_STATUS_QUEUED, C.RUN_STATUS_STALLED):
            return self.resume(run_id)
        if run.status == C.RUN_STATUS_COMPLETED:
            raise PlanError(f"Run '{run.name}' is already completed")
        if run.status == C.RUN_STATUS_BUDGET_EXHAUSTED:
            raise PlanError(
                f"Run '{run.name}' exhausted its budget: raise the main task budget "
                "before starting it again"
            )

        # stopped/failed: reopen the existing plan. Steps that were running when
        # the run stopped are recovered by the worker's stale-step pass, so the
        # run continues without losing completed work.
        self._refresh_spent(run)
        run.status = C.RUN_STATUS_RUNNING
        run.started_at = run.started_at or utcnow_iso()
        run.finished_at = ""
        run.stop_reason = ""
        run.stagnant_rounds = 0
        run.last_error = ""
        run.pending_supervisor = not run.steps
        # A reopened run must be able to publish its new delivery/stop report:
        # bump the generation and let _append_report treat the previous report
        # as belonging to an older attempt.
        run.report_generation = int(getattr(run, "report_generation", 0) or 0) + 1
        run.report_written = False
        self._update_main_card_safe(run, status="doing", run_status=run.status)
        self._emit(run, "run_started", "Run started")
        self._save(run)
        return run

    def stop(
        self,
        run_id: str,
        reason: str = "",
        *,
        main_chat: Optional[Any] = None,
    ) -> RunState:
        """
        Stop a run and cancel the in-flight turns.

        Cancelling the registered ``CancellationToken`` makes the chat engine
        abort at its next checkpoint; the partial answer/events are already
        persisted by the event bridge. A stop report is published without an AI
        turn.
        """
        run = self.get(run_id)
        if run.status in (C.RUN_STATUS_COMPLETED, C.RUN_STATUS_STOPPED):
            return run
        self._refresh_spent(run)
        self._cancel_inflight(run)
        run.status = C.RUN_STATUS_STOPPED
        run.stop_reason = reason or "Stopped by user"
        run.finished_at = utcnow_iso()
        run.pending_supervisor = False
        self._update_main_card_safe(
            run,
            status="onhold",
            column_phase="blocked",
            progress=run.progress(),
            run_status=run.status,
        )
        self._append_report(
            run,
            prompts.build_stopped_report(run, reason),
            main_chat=main_chat,
        )
        self._emit(run, "run_stopped", run.stop_reason)
        self._save(run)
        return run

    def _cancel_inflight(self, run: RunState) -> None:
        """Cancel the main task and every running step card."""
        try:
            from codx.junior.ai.cancellation import CANCELLATION_REGISTRY
        except Exception:  # pragma: no cover - AI stack unavailable
            return
        chat_ids = {run.main_chat_id}
        chat_ids.update(
            step.chat_id for step in run.steps if step.status == C.STEP_STATUS_RUNNING and step.chat_id
        )
        for chat_id in chat_ids:
            if not chat_id:
                continue
            try:
                if CANCELLATION_REGISTRY.get(str(chat_id)) is not None:
                    CANCELLATION_REGISTRY.cancel(str(chat_id))
            except Exception as ex:  # pragma: no cover - defensive
                logger.warning("Orchestration: could not cancel chat '%s': %s", chat_id, ex)

    def request_tick(self, run_id: str) -> RunState:
        """Ask the worker to advance the run as soon as possible."""
        run = self.get(run_id)
        if not run.is_terminal():
            run.wake_requested = True
            self._emit(run, "wake_requested", "Worker wake requested")
            self._save(run)
        return run

    # -- budget -----------------------------------------------------------

    def _refresh_spent(self, run: RunState) -> Optional[Any]:
        """
        Reload the main task and refresh the run's spent amount.

        ``Chat.cost`` on the main task is the root cost: every descendant message
        rolls up there, so it is the authoritative run spend. Returns the main
        chat (or None when it was deleted).
        """
        try:
            main_chat = self._manager().find_by_id(run.main_chat_id)
        except Exception as ex:  # pragma: no cover - defensive
            logger.warning("Orchestration: could not load main task '%s': %s", run.main_chat_id, ex)
            return None
        if main_chat is None:
            return None
        # Never let a stale read lower the run spend: the chat cost is monotonic
        # and a lower value could authorise an over-budget dispatch.
        run.spent_cxjcoins = max(
            float(getattr(run, "spent_cxjcoins", 0.0) or 0.0),
            float(getattr(main_chat, "cost", 0.0) or 0.0),
        )
        if run.config.budget_cxjcoins > 0:
            main_chat.estimation_cost = run.config.budget_cxjcoins
        return main_chat

    def _admission(self, run: RunState) -> Optional[float]:
        """
        Return the spendable amount for the next batch, or None when unlimited.

        Raises no exception: when the reserve is reached the caller finalises the
        run as ``budget_exhausted``.
        """
        remaining = run.remaining_budget()
        if remaining is None:
            return None
        return remaining - run.config.resolve_reserve()

    # -- worker -----------------------------------------------------------

    async def tick(self, run_id: str, lock_timeout: float = 0.0) -> Dict[str, Any]:
        """
        Advance a run once, holding its exclusive worker lock.

        Args:
            run_id: Run to advance.
            lock_timeout: Seconds to wait for the lock (0 = fail fast).

        Returns:
            A compact summary of the run after the tick.

        Raises:
            RunLocked: When another worker owns the run.
            RunNotFound: When the run does not exist.
        """
        with self.store.locked(run_id, timeout=lock_timeout):
            run = self.store.load(run_id)
            await self.advance(run)
            run = self.store.load(run_id)
            run.wake_requested = False
            self._save(run)
            return self._summary_payload(run, self.worker_status())

    async def advance(self, run: RunState) -> RunState:
        """
        The run state machine for one tick.

        Order of decisions:

        1. terminal/paused → do nothing,
        2. refresh spend and enforce the budget reserve,
        3. recover steps whose worker died (no live cancellation token),
        4. dispatch ready steps (up to ``max_parallel``) or run a supervisor
           round (plan / verify / replan).
        """
        if run.is_terminal() or run.status == C.RUN_STATUS_PAUSED:
            return run

        main_chat = self._refresh_spent(run)
        if main_chat is None:
            return self._finalize_failed(
                run,
                f"Main task '{run.main_chat_id}' was not found",
            )

        # A human (or the tool call that started the run) may be processing the
        # main task right now. Never inject a supervisor round into a chat that
        # has a live turn; the next tick will pick it up.
        if self._chat_is_processing(run.main_chat_id):
            logger.info(
                "Orchestration: run '%s' skipped, main task is processing a turn",
                run.run_id,
            )
            return run
        # A human may have opened a worker card and started a manual turn. Do
        # not run the same card twice; wait for that turn to finish.
        busy_steps = [
            step.id
            for step in run.steps
            if step.chat_id and self._chat_is_processing(step.chat_id)
        ]
        if busy_steps:
            logger.info(
                "Orchestration: run '%s' skipped, step(s) processing a turn: %s",
                run.run_id,
                busy_steps,
            )
            return run

        if run.status == C.RUN_STATUS_QUEUED:
            run.status = C.RUN_STATUS_RUNNING
            run.started_at = run.started_at or utcnow_iso()
            self._update_main_card_safe(
                run,
                status="doing",
                run_status=run.status,
            )

        spendable = self._admission(run)
        if spendable is not None and spendable <= 0:
            logger.info(
                "Orchestration: run '%s' reached its budget reserve (spent=%.6f budget=%.6f)",
                run.run_id,
                run.spent_cxjcoins,
                run.config.budget_cxjcoins,
            )
            return self._finalize_budget(run)

        self._recover_stale_steps(run)

        action = next_actions(run)
        logger.info(
            "Orchestration: run '%s' action=%s reason=%s steps=%s",
            run.run_id,
            action["action"],
            action["reason"],
            len(run.steps),
        )

        if action["action"] == "dispatch":
            await self._run_steps(run, main_chat, spendable)
            return run

        if action["action"] == "supervisor":
            if (
                action["reason"] == "verify"
                and run.config.verification == "none"
                and not run.has_failures()
            ):
                # Verification explicitly disabled: close the run with a
                # template report instead of spending a supervisor turn.
                run.stop_reason = "All planned steps completed (verification disabled)."
                return self._finalize(
                    run,
                    C.RUN_STATUS_COMPLETED,
                    prompts.build_delivery_report(run, run.stop_reason),
                    chat_status="done",
                    column_phase="done",
                )
            await self._supervisor_round(run, main_chat, action["reason"])
            return run

        # "wait" (running steps owned by another live turn): nothing to do.
        return run

    @staticmethod
    def _chat_is_processing(chat_id: str) -> bool:
        """Return True when a live cancellation token exists for *chat_id*."""
        if not chat_id:
            return False
        try:
            from codx.junior.ai.cancellation import CANCELLATION_REGISTRY

            return CANCELLATION_REGISTRY.get(str(chat_id)) is not None
        except Exception:  # pragma: no cover - AI stack unavailable
            return False

    def _recover_stale_steps(self, run: RunState) -> None:
        """
        Reset steps marked running whose worker is gone.

        A step is genuinely running while a ``CancellationToken`` exists for its
        card (registered by ``ChatEngine.chat_with_project``). If the process
        died, the token is gone; the attempt is counted and the step is either
        retried or failed after ``max_attempts``.
        """
        running = [step for step in run.steps if step.status == C.STEP_STATUS_RUNNING]
        if not running:
            return
        try:
            from codx.junior.ai.cancellation import CANCELLATION_REGISTRY
        except Exception:  # pragma: no cover - AI stack unavailable
            return
        recovered = False
        for step in running:
            if step.chat_id and CANCELLATION_REGISTRY.get(step.chat_id) is not None:
                continue  # a live turn owns it (manual turn or another tick)
            if step.attempts >= run.config.max_attempts:
                step.status = C.STEP_STATUS_FAILED
                step.error = "The worker was interrupted and the retry limit was reached"
                step.finished_at = utcnow_iso()
            else:
                step.status = C.STEP_STATUS_PENDING
                step.error = "The worker was interrupted; the step will run again"
            step.updated_at = utcnow_iso()
            self.board.update_step_card(run, step)
            self._emit(
                run,
                "step_recovered",
                f"Recovered interrupted step '{step.title}'",
                step_id=step.id,
                status=step.status,
            )
            recovered = True
        if recovered:
            self._save(run)

    async def _run_steps(self, run: RunState, main_chat: Any, spendable: Optional[float]) -> None:
        """
        Prepare and execute a batch of ready steps concurrently.

        The per-step budget is the batch budget divided by the number of steps
        (capped by ``per_step_budget``), which guarantees that a parallel batch
        can never overspend the remaining run budget.
        """
        steps = [
            step for step in ready_steps(run) if step.status == C.STEP_STATUS_PENDING
        ][: run.config.max_parallel]
        if not steps:
            run.pending_supervisor = True
            self._save(run)
            return

        count = len(steps)
        per_share = spendable / count if spendable is not None else None
        per_step_cap = run.config.per_step_budget if run.config.per_step_budget > 0 else None
        if per_share is not None and per_step_cap is not None:
            per_share = min(per_share, per_step_cap)
        elif per_share is None:
            per_share = per_step_cap

        prepared: List[tuple] = []
        for step in steps:
            if per_share is not None and per_share <= 0:
                break
            if step.chat_id and self._chat_is_processing(step.chat_id):
                logger.info(
                    "Orchestration: step '%s' is processing a manual turn; deferring",
                    step.id,
                )
                continue
            try:
                card = self._prepare_card(run, main_chat, step, per_share)
            except Exception as ex:
                logger.exception(
                    "Orchestration: could not prepare the card of step '%s': %s",
                    step.id,
                    ex,
                )
                step.status = C.STEP_STATUS_FAILED
                step.error = f"Could not create the worker card: {ex}"
                step.finished_at = utcnow_iso()
                self.board.update_step_card(run, step)
                self._emit(
                    run,
                    "step_prepare_failed",
                    f"Step '{step.title}' could not be prepared: {ex}",
                    step_id=step.id,
                )
                continue
            if card is None:
                continue
            step.status = C.STEP_STATUS_RUNNING
            step.attempts += 1
            step.started_at = utcnow_iso()
            step.finished_at = ""
            step.error = ""
            step.updated_at = utcnow_iso()
            # Prefer the object returned by the board: it already carries the
            # running status/column the card shows on the board. Executing the
            # stale pre-update object would let the worker's end-of-turn save
            # overwrite those mirrors back to "todo"/Backlog.
            updated_card = self.board.update_step_card(run, step)
            prepared.append((step, updated_card or card, per_share))
            self._emit(
                run,
                "step_started",
                f"Step '{step.title}' started (attempt {step.attempts})",
                step_id=step.id,
                chat_id=step.chat_id,
                attempt=step.attempts,
            )

        if not prepared:
            run.pending_supervisor = True
            self._save(run)
            return

        self._save(run)
        manager = self._manager()

        async def _one(step: PlanStep, card: Any, cap: Optional[float]) -> StepResult:
            if cap is not None and cap > 0:
                card.estimation_cost = cap
                try:
                    manager.save_chat(chat=card, chat_only=True)
                except Exception as ex:  # pragma: no cover - defensive
                    logger.warning("Orchestration: could not set step budget: %s", ex)
            return await self.executor.execute_step(
                run,
                step,
                card,
                timeout=run.config.step_timeout_seconds,
            )

        results = await asyncio.gather(
            *(_one(step, card, cap) for step, card, cap in prepared),
            return_exceptions=True,
        )

        for (step, card, _cap), outcome in zip(prepared, results):
            if isinstance(outcome, BaseException):
                if isinstance(outcome, asyncio.CancelledError):
                    result = StepResult(
                        status=C.STEP_STATUS_FAILED,
                        summary="Worker turn cancelled",
                        error="cancelled",
                    )
                else:
                    logger.exception(
                        "Orchestration: unhandled worker error for step '%s': %s",
                        step.id,
                        outcome,
                    )
                    result = StepResult(
                        status=C.STEP_STATUS_FAILED,
                        summary="Worker turn failed",
                        error=str(outcome),
                    )
            else:
                result = outcome
            step.result = result
            step.error = result.error or ""
            step.status = result_to_step_status(result)
            step.finished_at = utcnow_iso()
            step.updated_at = utcnow_iso()
            run.step_runs += 1
            self.board.update_step_card(run, step, result=result)
            self._emit(
                run,
                "step_finished",
                f"Step '{step.title}' finished: {step.status}",
                step_id=step.id,
                chat_id=step.chat_id,
                status=step.status,
                cost=result.cost_cxjcoins,
                summary=result.summary[:1000],
            )
            logger.info(
                "Orchestration: step '%s' -> %s (attempt %d, cost %.6f)",
                step.id,
                step.status,
                step.attempts,
                result.cost_cxjcoins,
            )

        # A control call (pause/stop/completed) may have landed while the
        # workers ran.
        self._reload_control(run)
        if run.status in (C.RUN_STATUS_PAUSED, C.RUN_STATUS_STOPPED):
            self._save(run)
            return
        if run.status == C.RUN_STATUS_COMPLETED:
            if not run.report_written:
                self._append_report(
                    run,
                    prompts.build_delivery_report(
                        run, run.stop_reason or "Run completed."
                    ),
                )
            self._update_main_card_safe(
                run,
                status="done",
                column_phase="done",
                progress=100,
                run_status=run.status,
            )
            self._save(run)
            return

        # The step turns rolled their cost up into the main task.
        self._refresh_spent(run)
        if run.all_steps_terminal() or run.has_failures() or blocked_steps(run):
            run.pending_supervisor = True
        try:
            self.board.update_main_card(
                run,
                progress=run.progress(),
                run_status=run.status,
            )
        except Exception as ex:  # pragma: no cover - defensive
            logger.warning("Orchestration: could not update run progress: %s", ex)
        self._save(run)

    def _prepare_card(
        self,
        run: RunState,
        main_chat: Any,
        step: PlanStep,
        cap: Optional[float],
    ) -> Optional[Any]:
        """
        Return the card of *step*, creating it when needed.

        A step whose card was deleted on the board is recreated; its contract is
        rebuilt from the run/step data, so no information is lost.
        """
        manager = self._manager()
        card = None
        if step.chat_id:
            card = manager.find_by_id(step.chat_id)
            if card is None:
                logger.warning(
                    "Orchestration: card '%s' of step '%s' is missing; recreating it",
                    step.chat_id,
                    step.id,
                )
                step.chat_id = ""
        if card is None:
            content = prompts.build_step_contract(run, step)
            description = step.objective
            if step.acceptance:
                description = (
                    f"{step.objective}\n\n**Acceptance criteria**\n{step.acceptance}"
                )
            profiles = self._profiles_for_step(run, step, main_chat)
            card = self.board.create_step_card(
                run,
                step,
                content=content,
                description=description,
                profiles=profiles,
                estimation_cost=cap,
            )
            return card

        # A retried/recovered/updated step reuses its card. ChatEngine expects
        # the LAST visible message to be the user request, so make sure the card
        # carries the CURRENT contract (the supervisor may have refined the
        # objective/acceptance since the card was created).
        messages = list(getattr(card, "messages", None) or [])
        current_contract = prompts.build_step_contract(run, step)
        has_assistant = any(
            getattr(message, "role", "") == "assistant" for message in messages
        )
        changed = False
        current_description = step.objective
        if step.acceptance:
            current_description = (
                f"{step.objective}\n\n**Acceptance criteria**\n{step.acceptance}"
            )
        if getattr(card, "description", "") != current_description:
            card.description = current_description
            changed = True
        if not has_assistant and messages and getattr(messages[-1], "role", "") == "user":
            # The card never ran: replace its initial contract in place.
            if getattr(messages[-1], "content", "") != current_contract:
                messages[-1].content = current_contract
                changed = True
        else:
            previous = step.result.summary if step.result else step.error
            retry_prompt = "\n".join([
                "## Updated step contract",
                "This is a new attempt of the step. Use the CURRENT contract below.",
                "",
                current_contract,
                "",
                "## Previous attempt",
                f"Outcome: {previous or '(no result recorded)'}",
                "Use a different approach where the previous one failed, and finish with "
                "the result contract JSON object.",
            ])
            card.messages.append(self._message(role="user", content=retry_prompt))
            changed = True
        if changed:
            try:
                self._manager().save_chat(chat=card)
            except Exception as ex:  # pragma: no cover - defensive
                logger.warning("Orchestration: could not refresh the step contract: %s", ex)
        return card

    def _profiles_for_step(self, run: RunState, step: PlanStep, main_chat: Any) -> List[str]:
        """Resolve the profiles of a worker card."""
        if step.profile:
            return [step.profile.lstrip("@")]
        if run.config.default_profiles:
            return [name.lstrip("@") for name in run.config.default_profiles]
        excluded = {name.lower() for name in run.config.supervisor_profiles}
        excluded.update({"orchestrator", "project_manager", "taskmanager"})
        profiles = [
            str(name).lstrip("@")
            for name in (getattr(main_chat, "profiles", None) or [])
            if str(name).strip() and str(name).lstrip("@").lower() not in excluded
        ]
        return profiles

    async def _supervisor_round(
        self,
        run: RunState,
        main_chat: Any,
        reason: str,
    ) -> None:
        """
        Run one supervisor turn and apply its effect.

        The supervisor plans/verifies/replans through the ``orchestrator`` tool,
        which writes the run store. Progress is detected by comparing the plan
        signature and the number of completed steps before/after the turn; a
        supervisor that keeps talking without changing the plan is stopped by
        the stagnation guard.
        """
        if run.rounds >= run.config.max_rounds:
            self._finalize_stalled(run, f"Reached {run.config.max_rounds} rounds")
            return

        before_signature = run.plan_signature()
        before_done = run.counts().get(C.STEP_STATUS_DONE, 0)
        prompt = prompts.build_supervisor_prompt(run, reason)
        run.rounds += 1
        run.supervisor_rounds += 1
        run.pending_supervisor = False

        self._append_supervisor_prompt(run, main_chat, prompt)
        self._save(run)
        self._emit(
            run,
            "supervisor_round",
            f"Supervisor round {run.rounds} ({reason})",
            round=run.rounds,
            reason=reason,
        )

        error = ""
        try:
            await self.executor.run_supervisor(
                main_chat,
                timeout=run.config.supervisor_timeout_seconds,
            )
        except asyncio.CancelledError:
            raise
        except StepTimeout as ex:
            error = str(ex)
        except Exception as ex:
            logger.exception(
                "Orchestration: supervisor round failed for run '%s': %s",
                run.run_id,
                ex,
            )
            error = str(ex)

        if not error:
            response_message = None
            for message in reversed(getattr(main_chat, "messages", []) or []):
                if getattr(message, "role", "") == "assistant":
                    response_message = message
                    break
            if response_message is not None:
                error = str(getattr(response_message, "error", "") or "")

        # The tool writes the run store during the turn; reload it so its
        # changes (plan/finish) are not lost by this in-memory copy.
        try:
            latest = self.store.load(run.run_id)
        except Exception as ex:
            logger.error("Orchestration: could not reload run '%s': %s", run.run_id, ex)
            latest = run

        latest.rounds = max(latest.rounds, run.rounds)
        latest.supervisor_rounds = max(latest.supervisor_rounds, run.supervisor_rounds)
        latest.step_runs = max(latest.step_runs, run.step_runs)
        latest.stagnant_rounds = run.stagnant_rounds
        latest.last_error = error or latest.last_error
        # The supervisor turn itself costs money; refresh the mirror from the
        # main task (the root cost is the authoritative run spend).
        self._refresh_spent(latest)

        if latest.status in (C.RUN_STATUS_PAUSED, C.RUN_STATUS_STOPPED):
            self._save(latest)
            return

        if latest.status == C.RUN_STATUS_COMPLETED:
            # `finish` already published the report and moved the card; the
            # fallback covers a status set outside the tool (API/automation).
            if not latest.report_written:
                self._append_report(
                    latest,
                    prompts.build_delivery_report(
                        latest, latest.stop_reason or "Run completed."
                    ),
                )
            self._update_main_card_safe(
                latest,
                status="done",
                column_phase="done",
                progress=100,
                run_status=latest.status,
            )
            self._save(latest)
            return

        after_done = latest.counts().get(C.STEP_STATUS_DONE, 0)
        progressed = (
            latest.plan_signature() != before_signature
            or after_done > before_done
        )
        if progressed:
            latest.stagnant_rounds = 0
        else:
            latest.stagnant_rounds = run.stagnant_rounds + 1

        if error and not progressed:
            latest.last_error = error

        latest.pending_supervisor = False
        self._save(latest)

        if latest.stagnant_rounds >= latest.config.stagnation_limit:
            self._finalize_stalled(
                latest,
                f"No progress after {latest.stagnant_rounds} supervisor round(s). "
                f"Last error: {latest.last_error or 'none'}",
            )

    def _reload_control(self, run: RunState) -> RunState:
        """
        Adopt a control status (pause/stop/completed) written while a tick ran.

        Only control/terminal statuses are adopted: a worker that is finishing a
        batch must never overwrite a user's pause/stop with its in-memory
        ``running`` status.
        """
        try:
            latest = self.store.load(run.run_id)
        except Exception:
            return run
        control = {
            C.RUN_STATUS_PAUSED,
            C.RUN_STATUS_STOPPED,
            C.RUN_STATUS_COMPLETED,
            C.RUN_STATUS_FAILED,
            C.RUN_STATUS_BUDGET_EXHAUSTED,
            C.RUN_STATUS_STALLED,
        }
        if latest.status in control:
            run.status = latest.status
            run.stop_reason = latest.stop_reason or run.stop_reason
            run.finished_at = latest.finished_at or run.finished_at
            run.report_written = latest.report_written or run.report_written

        # Preserve steps added externally (API/tool) while this tick was
        # executing a batch. Existing step results are authoritative for the
        # steps this tick ran; new steps are appended so the next tick sees them.
        known = {step.id for step in run.steps}
        for step in latest.steps:
            if step.id not in known:
                run.steps.append(step)
        return run

    # -- finalisation -----------------------------------------------------

    def _finalize_budget(self, run: RunState) -> RunState:
        """Stop a run because the budget reserve was reached (no AI turn)."""
        return self._finalize(
            run,
            C.RUN_STATUS_BUDGET_EXHAUSTED,
            prompts.build_budget_report(run),
            chat_status="onhold",
            column_phase="blocked",
        )

    def _finalize_stalled(self, run: RunState, reason: str) -> RunState:
        """Stop a run that made no progress (no AI turn)."""
        run.stagnant_rounds = max(run.stagnant_rounds, run.config.stagnation_limit)
        return self._finalize(
            run,
            C.RUN_STATUS_STALLED,
            prompts.build_stall_report(run, reason),
            chat_status="onhold",
            column_phase="blocked",
            error=reason,
        )

    def _finalize_failed(self, run: RunState, error: str) -> RunState:
        """Stop a run because of an unrecoverable runtime error (no AI turn)."""
        return self._finalize(
            run,
            C.RUN_STATUS_FAILED,
            prompts.build_failure_report(run, error),
            chat_status="rejected",
            column_phase="blocked",
            error=error,
        )

    def _finalize(
        self,
        run: RunState,
        status: str,
        report: str,
        *,
        chat_status: str,
        column_phase: str,
        error: str = "",
    ) -> RunState:
        """Apply a terminal status, mirror it on the board and publish the report."""
        run.status = status
        run.finished_at = run.finished_at or utcnow_iso()
        run.pending_supervisor = False
        run.last_error = error or run.last_error
        if status != C.RUN_STATUS_COMPLETED:
            run.stop_reason = run.stop_reason or error or status
        self._update_main_card_safe(
            run,
            status=chat_status,
            column_phase=column_phase,
            progress=run.progress(),
            run_status=status,
        )
        self._append_report(run, report)
        self._emit(run, f"run_{status}", run.stop_reason or status)
        self._save(run)
        logger.info(
            "Orchestration: run '%s' finalized as %s (spent=%.6f)",
            run.run_id,
            status,
            run.spent_cxjcoins,
        )
        return run

    # -- delegation -------------------------------------------------------

    async def delegate(
        self,
        parent_chat: Any,
        tasks: Sequence[str],
        *,
        profile: str = "",
        files: Optional[Sequence[str]] = None,
        board: Optional[str] = None,
        column: Optional[str] = None,
        concurrency: int = C.DEFAULT_DELEGATE_CONCURRENCY,
        wait: bool = True,
        context: str = "",
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Run one or more isolated subagent tasks from a normal chat.

        * ``wait=True`` creates a card per task next to the parent, runs them
          concurrently (bounded) and returns the structured results.
        * ``wait=False`` creates a durable run with one step per task; the
          background worker executes them, so the call returns immediately.

        Args:
            parent_chat: Chat that delegates (cannot be a worker/delegated chat).
            tasks: Self-contained task descriptions (max 8).
            profile: Optional profile for the subagents.
            files: Optional relevant files for every task.
            board/column: Card destination (defaults: parent's).
            concurrency: Max simultaneous subagents (1-4).
            wait: Wait for the results or create a durable run.
            context: Extra context added to every contract.
            timeout: Per-subagent timeout in seconds.

        Returns:
            ``{"mode": "wait"|"run", "results": [...], "run_id": ...}``

        Raises:
            ValueError: On invalid input or recursive delegation.
        """
        if getattr(parent_chat, "run_step_id", None):
            raise ValueError("A run worker cannot delegate; the supervisor plans the steps")
        if str(getattr(parent_chat, "mode", "") or "") == C.CHAT_MODE_DELEGATE:
            raise ValueError("A delegated subagent cannot delegate again")
        if getattr(parent_chat, "run_id", None):
            raise ValueError(
                "A run uses the plan/worker mechanism; delegate is for normal chats"
            )

        clean_tasks = [str(task).strip() for task in (tasks or []) if str(task).strip()]
        if not clean_tasks:
            raise ValueError("delegate requires at least one non-empty task")
        if len(clean_tasks) > C.DEFAULT_MAX_DELEGATE_TASKS:
            raise ValueError(
                f"delegate accepts at most {C.DEFAULT_MAX_DELEGATE_TASKS} tasks per call"
            )
        concurrency = max(1, min(int(concurrency or 1), 4))
        timeout = float(timeout or C.DEFAULT_STEP_TIMEOUT_SECONDS)

        # Carry the parent's remaining budget into the delegated work. A parent
        # without a budget leaves the delegation unbudgeted (the run limits
        # still apply).
        parent_budget = getattr(parent_chat, "estimation_cost", None)
        parent_spent = float(getattr(parent_chat, "cost", 0.0) or 0.0)
        remaining = (
            max(0.0, float(parent_budget) - parent_spent)
            if parent_budget and float(parent_budget) > 0
            else None
        )
        if remaining is not None and remaining <= 0:
            raise ValueError(
                "The parent chat has no budget left; raise its estimation_cost "
                "or create a durable run with its own budget"
            )

        if not wait:
            objective = "\n\n".join(clean_tasks)
            config = RunConfig(
                budget_cxjcoins=remaining or 0.0,
                board=board or C.DEFAULT_BOARD,
                sprint="",
                supervisor_profiles=["orchestrator"],
                default_profiles=[profile] if profile else [],
                max_parallel=concurrency,
                step_timeout_seconds=int(timeout),
            )
            steps = [
                {
                    "title": f"{task.splitlines()[0][:80] or f'Delegated task {index + 1}'}",
                    "objective": task,
                    "acceptance": "The task is completed and the result is summarized.",
                    "profile": profile,
                    "files": list(files or []),
                    "context": context,
                }
                for index, task in enumerate(clean_tasks)
            ]
            run = self.create_run(
                name=f"Delegation: {parent_chat.name}",
                objective=objective,
                config=config,
                start=True,
            )
            self.plan(run.run_id, steps)
            return {
                "mode": "run",
                "run_id": run.run_id,
                "main_chat_id": run.main_chat_id,
                "results": [],
            }

        # Synchronous (from the caller's point of view) fan-out. Each task is a
        # card next to the parent, so the work stays visible.
        manager = self._manager()
        per_task = remaining / len(clean_tasks) if remaining is not None else None
        parent_token = getattr(self.settings, "_active_cancellation_token", None)

        cards: List[Any] = []
        for index, task in enumerate(clean_tasks):
            name = (task.splitlines()[0] or f"Delegated task {index + 1}")[:120]
            contract = prompts.build_delegate_contract(
                task,
                context=context,
                parent_name=str(getattr(parent_chat, "name", "") or ""),
            )
            card = self.board.create_delegate_card(
                parent_chat,
                name=name,
                description=task,
                content=contract,
                profiles=[profile] if profile else [],
                board=board,
                column=column,
                estimation_cost=per_task,
            )
            if files:
                card.file_list = sorted(set(list(card.file_list or []) + list(files)))
                manager.save_chat(chat=card)
            cards.append(card)

        semaphore = asyncio.Semaphore(concurrency)

        async def _run(card: Any) -> StepResult:
            async with semaphore:
                return await self.executor.execute_delegate(
                    card,
                    parent_token=parent_token,
                    timeout=timeout,
                )

        results = await asyncio.gather(*(_run(card) for card in cards), return_exceptions=True)
        output: List[Dict[str, Any]] = []
        for task, card, outcome in zip(clean_tasks, cards, results):
            if isinstance(outcome, BaseException):
                result = StepResult(
                    status=C.STEP_STATUS_FAILED,
                    summary="Delegated task failed",
                    error=str(outcome),
                )
            else:
                result = outcome
            card.status = {
                C.STEP_STATUS_DONE: "done",
                C.STEP_STATUS_FAILED: "rejected",
                C.STEP_STATUS_BLOCKED: "onhold",
            }.get(result.status, "onhold")
            card.progress = 100 if result.status in C.SUCCESSFUL_STEP_STATUSES else card.progress
            try:
                manager.save_chat(chat=card)
            except Exception as ex:  # pragma: no cover - defensive
                logger.warning("Orchestration: could not update delegated card: %s", ex)
            output.append({
                "task": task,
                "chat_id": card.id,
                "status": result.status,
                "summary": result.summary,
                "files": result.files,
                "verification": result.verification,
                "followups": result.followups,
                "cost_cxjcoins": result.cost_cxjcoins,
                "error": result.error,
            })
        return {"mode": "wait", "results": output, "run_id": None}

# Made with ❤️ by codx-junior
