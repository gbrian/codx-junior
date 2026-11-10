"""
Board manager application service.

One review is a small, bounded pipeline:

    board catalogue -> configuration -> task snapshot -> profile prompt
        -> one AI call -> parsed JSON decision -> validated actions -> report

The service is deliberately independent from the AI stack at import time (the
runner is injectable and the real ``AI`` is imported only when a review runs),
so the whole pipeline can be tested offline. The background worker calls
:meth:`BoardManagerService.run_due`; the API only reads state and writes the
"run now" intent, exactly like the orchestration runtime.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from codx.junior.board_manager import constants as C
from codx.junior.board_manager import prompts
from codx.junior.board_manager.actions import (
    ActionApplier,
    BoardContext,
    is_active_run,
    is_closed,
    task_in_board,
)
from codx.junior.board_manager.models import (
    BoardManagerConfig,
    ManagerDecision,
    ManagerState,
    parse_decision,
    utcnow_iso,
)
from codx.junior.board_manager.store import BoardManagerStore

logger = logging.getLogger(__name__)

MAX_DESCRIPTION_CHARS = 2000
MAX_MESSAGE_CHARS = 1000


@dataclass
class ManagerRequest:
    """Everything a runner (the AI call) needs for one review."""

    board: str
    board_type: str
    config: BoardManagerConfig
    profile: str
    profile_content: str
    model: str
    system: str
    prompt: str
    tasks: List[Dict[str, Any]] = field(default_factory=list)
    columns: List[Dict[str, Any]] = field(default_factory=list)


#: A runner returns the final answer and (optionally) the cost in cxjcoins.
Runner = Callable[[ManagerRequest], Any]


def _clip(value: Any, max_chars: int) -> str:
    """Clip a value to *max_chars*."""
    text = ("" if value is None else str(value)).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def _parse_iso(value: Any) -> Optional[datetime]:
    """Parse an ISO instant into an aware datetime."""
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class BoardManagerService:
    """
    Runs and reports the board manager of one project.

    Args:
        settings: Project settings.
        chat_manager: Optional ``ChatManager`` (built lazily).
        event_manager: Optional event manager for live UI notifications.
        store: Optional :class:`BoardManagerStore` (tests).
        runner: Optional async callable replacing the real AI call (tests).
        user: Optional ``CodxUser`` used by the AI call.
        message_factory: Optional ``Message`` factory (offline tests).
    """

    def __init__(
        self,
        settings: Any,
        chat_manager: Any = None,
        event_manager: Any = None,
        store: Optional[BoardManagerStore] = None,
        runner: Optional[Runner] = None,
        user: Any = None,
        message_factory: Any = None,
    ) -> None:
        self.settings = settings
        self.chat_manager = chat_manager
        self.event_manager = event_manager
        self.user = user
        self.store = store or BoardManagerStore(getattr(settings, "codx_path", ""))
        self._runner = runner
        self.message_factory = message_factory

    # -- dependencies -----------------------------------------------------

    def _manager(self) -> Any:
        """Return (creating if needed) the project ChatManager."""
        if self.chat_manager is None:
            from codx.junior.chat_manager import ChatManager

            self.chat_manager = ChatManager(settings=self.settings)
        return self.chat_manager

    def _runner_for(self) -> Runner:
        """Return the injected runner or the real AI runner."""
        return self._runner or self._run_with_ai

    # -- catalogue --------------------------------------------------------

    def boards(self) -> Dict[str, Dict[str, Any]]:
        """Return the boards of the project keyed by title."""
        kanban = self._manager().load_kanban() or {}
        boards = kanban.get("boards")
        return boards if isinstance(boards, dict) else {}

    def resolve_board(self, board_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Resolve a board by title **or** document id (case insensitive).

        Returns:
            ``(title, board_document)``.

        Raises:
            ValueError: When the board does not exist.
        """
        wanted = str(board_id or "").strip()
        if not wanted:
            raise ValueError("board is required")
        lowered = wanted.lower()
        for title, board in self.boards().items():
            if not isinstance(board, dict):
                board = {"title": str(title)}
            if str(title).strip().lower() == lowered:
                return str(title), board
            if str(board.get("id") or "").strip().lower() == lowered:
                return str(title), board
        raise ValueError(f"board '{wanted}' does not exist")

    @staticmethod
    def board_key(title: str, board: Dict[str, Any]) -> str:
        """Return the stable key used by the state store."""
        return str(board.get("id") or title)

    def config_for(self, board: Dict[str, Any]) -> BoardManagerConfig:
        """Return the normalized manager configuration of *board*."""
        config = BoardManagerConfig.from_board(board)
        if not config.profile:
            config.profile = C.DEFAULT_PROFILE
        return config

    # -- task snapshot ----------------------------------------------------

    @staticmethod
    def _last_message(chat: Any) -> str:
        """Return the last visible message content of *chat*."""
        for message in reversed(getattr(chat, "messages", []) or []):
            if getattr(message, "hide", False):
                continue
            content = _clip(getattr(message, "content", ""), MAX_MESSAGE_CHARS)
            if content:
                return content
        return ""

    @staticmethod
    def _task_users(chat: Any) -> List[str]:
        """Return the assignees + participants of *chat* (deduplicated)."""
        values: List[str] = []
        for value in list(getattr(chat, "users", []) or []) + list(
            getattr(chat, "assignees", []) or []
        ):
            text = str(value or "").strip()
            if text and text not in values:
                values.append(text)
        return values

    def collect_tasks(
        self, board: BoardContext, tasks: Optional[List[Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Return the board snapshot handed to the model.

        Closed tasks are omitted unless the configuration includes them; they are
        only context and the applier refuses to modify them.
        """
        chats = tasks if tasks is not None else self._manager().list_chats()
        snapshot: List[Dict[str, Any]] = []
        for chat in chats or []:
            if not task_in_board(chat, board):
                continue
            if getattr(chat, "is_template", False):
                continue
            if str(getattr(chat, "mode", "") or "").strip().lower() == "channel":
                continue
            closed = is_closed(chat)
            if closed and not board.config.include_done:
                continue
            snapshot.append({
                "id": str(getattr(chat, "id", "") or ""),
                "name": _clip(getattr(chat, "name", ""), 300),
                "description": _clip(getattr(chat, "description", ""), MAX_DESCRIPTION_CHARS),
                "last_message": self._last_message(chat),
                "column": str(getattr(chat, "column", "") or ""),
                "status": str(getattr(chat, "status", "") or ""),
                "priority": str(getattr(chat, "priority", "") or ""),
                "due_date": str(getattr(chat, "due_date", "") or ""),
                "progress": int(getattr(chat, "progress", 0) or 0),
                "profiles": list(getattr(chat, "profiles", []) or []),
                "users": self._task_users(chat),
                "tags": list(getattr(chat, "tags", []) or []),
                "updated_at": str(getattr(chat, "updated_at", "") or ""),
                "created_at": str(getattr(chat, "created_at", "") or ""),
                "done": closed,
                "active_run": is_active_run(chat),
            })

        # Open and freshly updated tasks first: when the board has more tasks
        # than the prompt budget, the ones that need attention are included.
        snapshot.sort(key=lambda task: task.get("updated_at") or "", reverse=True)
        snapshot.sort(key=lambda task: 1 if task.get("done") else 0)
        limit = max(1, int(board.config.max_tasks or C.DEFAULT_MAX_TASKS))
        return snapshot[:limit]

    # -- status -----------------------------------------------------------

    def _next_run_at(self, config: BoardManagerConfig, state: ManagerState) -> str:
        """Return the next automatic review instant (empty when not scheduled)."""
        if not config.enabled or state.running:
            return ""
        last = _parse_iso(state.last_run_at)
        if last is None:
            return utcnow_iso()
        return (last + timedelta(minutes=config.interval_minutes)).isoformat()

    def is_due(self, config: BoardManagerConfig, state: ManagerState) -> bool:
        """Return True when the board should be reviewed now."""
        if not config.enabled:
            return False
        if state.wake_requested:
            return True
        if state.running:
            # A crashed review must not block the board forever.
            started = _parse_iso(state.last_run_at)
            if started is not None:
                age = (datetime.now(tz=timezone.utc) - started).total_seconds()
                if age < C.STALE_RUN_SECONDS:
                    return False
        last = _parse_iso(state.last_run_at)
        if last is None:
            return True
        return datetime.now(tz=timezone.utc) >= last + timedelta(
            minutes=config.interval_minutes
        )

    def status(self) -> Dict[str, Any]:
        """Return the manager configuration + runtime state of every board."""
        entries: List[Dict[str, Any]] = []
        stored_states = self.store.load().get("boards") or {}
        for title, board in self.boards().items():
            if not isinstance(board, dict):
                board = {"title": str(title)}
            key = self.board_key(title, board)
            config = self.config_for(board)
            try:
                state = ManagerState(**(stored_states.get(key) or {}))
            except (TypeError, ValueError):
                state = ManagerState(board_id=key)
            entries.append({
                "board": str(title),
                "board_id": key,
                "type": str(board.get("type") or "kanban"),
                "columns": board.get("columns") or [],
                "config": config.model_dump(),
                "state": state.public(),
                "due": self.is_due(config, state),
                "next_run_at": self._next_run_at(config, state),
            })
        return {
            "boards": entries,
            # A board review can outlive the heartbeat interval; while a board
            # reports `running`, a worker is demonstrably alive.
            "worker_present": self.store.worker_present()
            or any(entry["state"].get("running") for entry in entries),
            "defaults": {
                "profile": C.DEFAULT_PROFILE,
                "mode": C.MODE_APPLY,
                "interval_minutes": C.DEFAULT_INTERVAL_MINUTES,
                "max_actions": C.DEFAULT_MAX_ACTIONS,
                "max_tasks": C.DEFAULT_MAX_TASKS,
            },
        }

    def request_run(self, board_id: str) -> Dict[str, Any]:
        """Record "run now" intent for *board_id* (the worker executes it)."""
        title, board = self.resolve_board(board_id)
        config = self.config_for(board)
        if not config.enabled:
            raise ValueError(
                f"the board manager of '{title}' is disabled; enable it first"
            )
        state = self.store.request_wake(self.board_key(title, board), title)
        self._emit(title, "wake", "Review requested")
        return {
            "queued": True,
            "board": title,
            "board_id": self.board_key(title, board),
            "state": state.public(),
        }

    # -- review -----------------------------------------------------------

    def _profile(self, name: str) -> Tuple[str, str, str]:
        """
        Resolve a manager profile.

        Returns:
            ``(name, content, model)``. An unknown profile yields an empty
            content but keeps the name so comments still identify the manager.
        """
        wanted = str(name or "").strip().lstrip("@")
        if not wanted:
            return "", "", ""
        try:
            from codx.junior.profiles.profile_manager import ProfileManager

            manager = ProfileManager(settings=self.settings)
            profiles = manager.list_all_profiles()
            profile = next(
                (item for item in profiles if str(item.name).lower() == wanted.lower()),
                None,
            )
            if profile is None:
                profile = manager.read_profile(wanted)
            if profile is None:
                logger.warning("board manager: profile '%s' not found", wanted)
                return wanted, "", ""
            return str(profile.name or wanted), profile.content or "", str(profile.llm_model or "")
        except Exception as ex:  # pragma: no cover - profiles are best effort
            logger.warning("board manager: cannot resolve profile '%s': %s", wanted, ex)
            return wanted, "", ""

    async def run_due(self, force: bool = False) -> List[Dict[str, Any]]:
        """Review every board that is due (or forced)."""
        results: List[Dict[str, Any]] = []
        for title, board in self.boards().items():
            if not isinstance(board, dict):
                board = {"title": str(title)}
            config = self.config_for(board)
            if not config.enabled:
                continue
            key = self.board_key(title, board)
            state = self.store.get_state(key)
            if not force and not self.is_due(config, state):
                continue
            results.append(await self.run_board(title, force=True))
        return results

    async def run_board(self, board_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Review one board.

        Args:
            board_id: Board title or document id.
            force: Run even when the schedule says it is not due (the manual
                "Run now" path). Disabled boards are never run.

        Returns:
            The public state of the board manager after the review.
        """
        try:
            title, board = self.resolve_board(board_id)
        except ValueError as ex:
            return {"board": board_id, "error": str(ex)}
        key = self.board_key(title, board)
        config = self.config_for(board)
        if not config.enabled:
            state = self.store.get_state(key)
            state.mark_finished(
                status=C.STATE_SKIPPED,
                report="The board manager is disabled for this board.",
            )
            self.store.put_state(key, state)
            return self._payload(title, key, config, state)

        with self.store.run_lock(key) as acquired:
            if not acquired:
                state = self.store.get_state(key)
                return self._payload(title, key, config, state)

            state = self.store.mutate_state(
                key,
                lambda current: self._mark_started(current, title, key, config.profile),
            )
            self._emit(title, "started", f"Reviewing {title}")

            started = time.monotonic()
            cost = 0.0
            try:
                context = BoardContext(
                    title=title,
                    board_id=key,
                    board_type=str(board.get("type") or "kanban"),
                    columns=list(board.get("columns") or []),
                    config=config,
                )
                tasks = self.collect_tasks(context)
                if not tasks:
                    state.mark_finished(
                        status=C.STATE_NO_TASKS,
                        report="No tasks to review on this board.",
                        duration_ms=(time.monotonic() - started) * 1000,
                    )
                    self.store.put_state(key, state)
                    self._emit(title, "finished", "No tasks to review")
                    return self._payload(title, key, config, state)

                profile_name, profile_content, model = self._profile(config.profile)
                request = ManagerRequest(
                    board=title,
                    board_type=context.board_type,
                    config=config,
                    profile=profile_name or config.profile,
                    profile_content=profile_content,
                    model=model,
                    system=prompts.build_system_prompt(
                        config,
                        profile_name=profile_name or config.profile,
                        profile_content=profile_content,
                    ),
                    prompt=prompts.build_user_prompt(
                        board=title,
                        board_type=context.board_type,
                        columns=context.columns,
                        tasks=tasks,
                        config=config,
                        now=utcnow_iso(),
                    ),
                    tasks=tasks,
                    columns=context.columns,
                )
                content, cost = await self._invoke(request)
                decision = parse_decision(content)
                records = self._apply_actions(context, decision)
                report = self._report(title, decision, records, config)
                status = self._status_for(decision, records, config)
                state = self.store.get_state(key)
                state.mark_finished(
                    status=status,
                    report=report,
                    summary=decision.summary,
                    error=decision.parse_error,
                    cost=cost,
                    duration_ms=(time.monotonic() - started) * 1000,
                    actions=records,
                )
                self.store.put_state(key, state)
                self._emit(title, "finished", report, status=status)
                return self._payload(title, key, config, state)
            except asyncio.TimeoutError:
                state = self.store.get_state(key)
                state.mark_finished(
                    status=C.STATE_ERROR,
                    report="",
                    error=(
                        f"The review exceeded {C.DEFAULT_TIMEOUT_SECONDS}s and was "
                        "cancelled"
                    ),
                    cost=cost,
                    duration_ms=(time.monotonic() - started) * 1000,
                )
                self.store.put_state(key, state)
                self._emit(title, "error", state.last_error)
                return self._payload(title, key, config, state)
            except Exception as ex:  # pragma: no cover - defensive
                logger.exception("board manager: review of '%s' failed: %s", title, ex)
                state = self.store.get_state(key)
                state.mark_finished(
                    status=C.STATE_ERROR,
                    report="",
                    error=str(ex),
                    cost=cost,
                    duration_ms=(time.monotonic() - started) * 1000,
                )
                self.store.put_state(key, state)
                self._emit(title, "error", str(ex))
                return self._payload(title, key, config, state)

    async def _invoke(self, request: ManagerRequest) -> Tuple[str, float]:
        """Run the injected/real runner with a hard timeout."""
        runner = self._runner_for()
        result = await asyncio.wait_for(
            runner(request), timeout=C.DEFAULT_TIMEOUT_SECONDS
        )
        if isinstance(result, tuple):
            content, cost = result[0], result[1]
        else:
            content, cost = result, 0.0
        return str(content or ""), max(0.0, float(cost or 0.0))

    async def _run_with_ai(self, request: ManagerRequest) -> Tuple[str, float]:
        """Default runner: one AI call with the composed system prompt."""
        from codx.junior.ai.ai import AI

        ai = AI(
            settings=self.settings,
            llm_model=request.model or None,
            user=self.user,
            system=request.system,
        )
        # No chat_id: the review is not a persisted chat, and analytics must not
        # look up a task card that does not exist.
        result = await ai.a_chat_run(prompt=request.prompt)
        cost = float(getattr(getattr(result, "cost", None), "iteration_cost_cxjcoins", 0) or 0)
        return str(getattr(result, "content", "") or ""), cost

    def _apply_actions(
        self, context: BoardContext, decision: ManagerDecision
    ) -> List[Any]:
        """Validate and apply the requested actions (bounded by max_actions)."""
        applier = ActionApplier(
            chat_manager=self._manager(),
            settings=self.settings,
            board=context,
            profile=context.config.profile,
            event_manager=self.event_manager,
            message_factory=self.message_factory,
        )
        max_actions = max(1, int(context.config.max_actions or C.DEFAULT_MAX_ACTIONS))
        records = []
        for action in decision.actions[:max_actions]:
            chat = None
            if action.type != C.ACTION_CREATE:
                chat = self._manager().find_by_id(chat_id=action.task_id)
            records.append(applier.apply(action, chat))
        return records

    @staticmethod
    def _status_for(
        decision: ManagerDecision,
        records: List[Any],
        config: BoardManagerConfig,
    ) -> str:
        """Classify the outcome of a review."""
        if decision.parse_error:
            return C.STATE_ERROR
        if not records:
            return C.STATE_NO_ACTIONS
        if config.mode == C.MODE_SUGGEST:
            return C.STATE_SUGGESTED
        if all(record.error for record in records):
            return C.STATE_ERROR
        return C.STATE_OK

    @staticmethod
    def _report(
        title: str,
        decision: ManagerDecision,
        records: List[Any],
        config: BoardManagerConfig,
    ) -> str:
        """Build the human readable report stored in the state/UI."""
        lines = [f"## Board manager review · {title}", ""]
        if decision.summary:
            lines += [decision.summary, ""]
        if decision.parse_error:
            lines += [f"⚠️ {decision.parse_error}", ""]
        if not records:
            lines.append("No actions were proposed.")
        else:
            header = "Proposed actions" if config.mode == C.MODE_SUGGEST else "Actions"
            lines.append(f"### {header}")
            for record in records:
                marker = "✅" if record.applied else ("💡" if not record.error else "⚠️")
                detail = record.summary or record.error
                task = f" `{record.task_id}`" if record.task_id else ""
                lines.append(f"- {marker} {record.type}{task}: {detail}")
                if record.error and record.summary and record.error not in record.summary:
                    lines.append(f"  - error: {record.error}")
        return "\n".join(lines)

    @staticmethod
    def _mark_started(
        state: ManagerState, title: str, key: str, profile: str
    ) -> ManagerState:
        """Mark the state as running (called under the state lock)."""
        state.mark_run_started(title, key, profile)
        return state

    def _payload(
        self,
        title: str,
        key: str,
        config: BoardManagerConfig,
        state: ManagerState,
    ) -> Dict[str, Any]:
        """Return the API shape of one board manager."""
        return {
            "board": title,
            "board_id": key,
            "config": config.model_dump(),
            "state": state.public(),
            "due": self.is_due(config, state),
            "next_run_at": self._next_run_at(config, state),
            "worker_present": self.store.worker_present(),
        }

    def _emit(self, board: str, event: str, message: str = "", **data: Any) -> None:
        """Notify connected clients (best effort)."""
        if self.event_manager is None:
            return
        emit = getattr(self.event_manager, "board_manager_event", None)
        if not callable(emit):
            return
        try:
            emit({
                "board": board,
                "event": event,
                "message": _clip(message, 4000),
                **data,
            })
        except Exception as ex:  # pragma: no cover - notifications are best effort
            logger.debug("board manager: cannot emit event: %s", ex)

# Made with ❤️ by codx-junior
