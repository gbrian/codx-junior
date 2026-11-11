"""
Board and sprint materialization of an orchestration run.

The whole point of this module is **visibility**: an orchestration run never
lives in an invisible queue. Every plan step becomes a normal task card on a
kanban board, and every card is also a member of the run's sprint, so the same
work can be followed:

* on the run board — columns describe the orchestration phases
  (Backlog → In progress → Done / Blocked),
* on the run sprint — columns describe the task status
  (To do → Doing → Done), exactly like any other sprint in codx-junior.

Cards are created through :class:`~codx.junior.task_manager.TaskManager` (the
canonical task factory) and updated through the regular ``ChatManager``, so the
existing board, planning and management read models keep working unchanged.

The module uses lazy imports for the heavy codx modules, which keeps it
importable from tests and from the orchestration models layer.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Dict, List, Optional, Tuple

from . import constants as C
from .models import RunState

logger = logging.getLogger(__name__)


def _column_titles(board: Dict[str, Any]) -> List[str]:
    """Return the column titles of a catalogue board (dict or string entries)."""
    titles: List[str] = []
    for entry in board.get("columns") or []:
        if isinstance(entry, dict):
            title = str(entry.get("title") or "").strip()
        else:
            title = str(entry or "").strip()
        if title and title not in titles:
            titles.append(title)
    return titles


def _find_title(boards: Dict[str, Any], wanted: str) -> Optional[str]:
    """Find an existing catalogue key matching *wanted* case-insensitively."""
    target = (wanted or "").strip().lower()
    if not target:
        return None
    for title in boards:
        if str(title).strip().lower() == target:
            return str(title)
    return None


class RunBoard:
    """
    Creates and updates the boards, sprints and cards of a run.

    Args:
        settings: Project settings (``codx_path``, ``project_id``...).
        chat_manager: Optional ``ChatManager`` (built from *settings* when omitted).
        task_manager: Optional ``TaskManager`` (built from *settings* when omitted).
        event_manager: Optional event manager (forwarded to TaskManager).
    """

    def __init__(
        self,
        settings: Any,
        chat_manager: Optional[Any] = None,
        task_manager: Optional[Any] = None,
        event_manager: Optional[Any] = None,
    ) -> None:
        self.settings = settings
        self.chat_manager = chat_manager
        self.task_manager = task_manager
        self.event_manager = event_manager

    # -- lazy dependencies ------------------------------------------------

    def _manager(self) -> Any:
        """Return (creating if needed) the ChatManager."""
        if self.chat_manager is None:
            from codx.junior.chat_manager import ChatManager

            self.chat_manager = ChatManager(
                settings=self.settings,
                event_manager=self.event_manager,
            )
        return self.chat_manager

    def _tasks(self) -> Any:
        """Return (creating if needed) the TaskManager."""
        if self.task_manager is None:
            from codx.junior.task_manager import TaskManager

            self.task_manager = TaskManager(
                settings=self.settings,
                chat_manager=self._manager(),
                event_manager=self.event_manager,
            )
        return self.task_manager

    # -- catalogue --------------------------------------------------------

    def ensure_destinations(
        self,
        board_name: str,
        sprint_name: str,
        columns: Dict[str, str],
    ) -> Tuple[str, str]:
        """
        Make sure the run board and sprint exist with the required columns.

        Existing boards are never replaced: missing columns are appended, and the
        rest of the catalogue is preserved byte-for-byte in semantics (the v2
        store diffs and writes one file per board).

        Args:
            board_name: Desired board title (created when missing).
            sprint_name: Desired sprint title (created when missing).
            columns: Mapping ``phase -> column title``.

        Returns:
            ``(board_title, sprint_title)`` as stored in the catalogue.
        """
        manager = self._manager()
        kanban = manager.load_kanban() or {}
        boards = kanban.get("boards")
        if not isinstance(boards, dict):
            if boards is not None:
                logger.warning(
                    "Orchestration: unexpected kanban boards type %s", type(boards)
                )
            boards = {}
            kanban["boards"] = boards

        wanted_board = (board_name or C.DEFAULT_BOARD).strip() or C.DEFAULT_BOARD
        board_title = _find_title(boards, wanted_board) or wanted_board
        board = boards.get(board_title)
        if not isinstance(board, dict):
            board = {"title": board_title, "type": "kanban", "columns": []}
            boards[board_title] = board
        board.setdefault("title", board_title)
        board.setdefault("type", "kanban")
        board.setdefault("columns", [])
        self._ensure_columns(board, list(columns.values()))

        wanted_sprint = (sprint_name or "").strip()
        sprint_title = ""
        if wanted_sprint:
            sprint_title = _find_title(boards, wanted_sprint) or wanted_sprint
            if sprint_title.strip().lower() == board_title.strip().lower():
                # A board and its sprint cannot be the same catalogue entry.
                sprint_title = f"{sprint_title} (sprint)"
            sprint = boards.get(sprint_title)
            if not isinstance(sprint, dict):
                sprint = {"title": sprint_title, "type": "sprint", "columns": []}
                boards[sprint_title] = sprint
            sprint.setdefault("title", sprint_title)
            # A sprint is a board whose type is sprint. If the name collides
            # with a regular kanban board, keep its configuration but make it a
            # sprint so the run cards grouped by status are visible.
            existing_type = str(sprint.get("type") or "").strip().lower()
            if existing_type and existing_type != "sprint":
                logger.warning(
                    "Orchestration: board '%s' has type '%s'; using it as the run "
                    "sprint and switching its type to sprint",
                    sprint_title,
                    existing_type,
                )
            sprint["type"] = "sprint"
            sprint.setdefault("columns", [])
            self._ensure_columns(sprint, list(C.SPRINT_COLUMN_TITLES))

        manager.save_kanban(kanban)
        logger.info(
            "Orchestration: destinations ready board='%s' sprint='%s'",
            board_title,
            sprint_title,
        )
        return board_title, sprint_title

    @staticmethod
    def _ensure_columns(board: Dict[str, Any], titles: List[str]) -> None:
        """Append the missing column titles to *board* (preserving order/colors)."""
        existing = {title.lower() for title in _column_titles(board)}
        columns = board.get("columns")
        if not isinstance(columns, list):
            columns = []
            board["columns"] = columns
        for title in titles:
            clean = str(title or "").strip()
            if not clean or clean.lower() in existing:
                continue
            columns.append({"title": clean})
            existing.add(clean.lower())

    def ensure_run(self, run: RunState) -> RunState:
        """
        Ensure the catalogue of *run* and store the resolved titles on the config.

        Args:
            run: Run to prepare (mutated).

        Returns:
            The same run, with ``config.board``/``config.sprint`` resolved.
        """
        sprint_name = run.config.sprint or f"Run: {run.name}".strip()
        board_title, sprint_title = self.ensure_destinations(
            board_name=run.config.board or C.DEFAULT_BOARD,
            sprint_name=sprint_name,
            columns=run.config.columns or C.DEFAULT_RUN_COLUMNS,
        )
        run.config.board = board_title
        run.config.sprint = sprint_title
        return run

    # -- card helpers -----------------------------------------------------

    def _column_for(self, run: RunState, step_status: str) -> str:
        """Resolve the board column title for a step status."""
        phase = C.STEP_BOARD_PHASE.get(step_status, "backlog")
        return (run.config.columns or C.DEFAULT_RUN_COLUMNS).get(phase, phase)

    def _supported_task_kwargs(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Keep only the keyword arguments the loaded ``create_task`` accepts.

        The API process can run an older build than the source tree (uvicorn
        without ``--reload``, an installed copy of the package, a container that
        was not rebuilt). The newest plan kwargs (``estimation_cost``,
        ``run_id``, ``run_step_id``) then do not exist yet, and a blind call
        raises ``TypeError`` *before* any worker starts: every ready step is
        marked failed, the dependent steps stay blocked, and the run sits at
        0 % until it burns its whole timeout.

        Dropping the unsupported keys keeps the run alive. The missing features
        degrade gracefully (the card is still tagged ``run:<id>``) and the stale
        runtime is reported, so the cause is visible instead of looking like a
        blocked task.

        Args:
            payload: Keyword arguments for ``TaskManager.create_task``.

        Returns:
            The subset of *payload* supported by the running callable.
        """
        try:
            parameters = inspect.signature(self._tasks().create_task).parameters
        except (AttributeError, TypeError, ValueError):  # pragma: no cover - defensive
            return payload
        if any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in parameters.values()
        ):
            return payload
        unsupported = sorted(name for name in payload if name not in parameters)
        if unsupported:
            logger.warning(
                "Orchestration: the running TaskManager.create_task() does not accept "
                "%s; creating the card without them. The API is running older code "
                "than %s: restart it to enable per-step budget and run back-references.",
                ", ".join(unsupported),
                __file__,
            )
        return {name: value for name, value in payload.items() if name in parameters}

    def create_step_card(
        self,
        run: RunState,
        step,
        *,
        content: str,
        description: str,
        profiles: Optional[List[str]] = None,
        estimation_cost: Optional[float] = None,
    ) -> Any:
        """
        Create the kanban card (a child task chat) of one plan step.

        The card is linked to the main task and stamped with ``run_id`` /
        ``run_step_id`` so it can be found from the board, the run API and the
        planning views. The card's first message is the self-contained worker
        contract, because workers never inherit the supervisor conversation.

        Args:
            run: Owning run.
            step: Step to materialize.
            content: First user message (worker contract).
            description: Card description (short objective + acceptance).
            profiles: Profiles for the worker.
            estimation_cost: Per-step budget cap (cxjcoins).

        Returns:
            The saved ``Chat`` card.
        """
        board = run.config.board or C.DEFAULT_BOARD
        column = self._column_for(run, step.status)
        chat_status = C.STEP_CHAT_STATUS.get(step.status, "todo")
        main_chat = None
        if run.main_chat_id:
            try:
                main_chat = self._manager().find_by_id(run.main_chat_id)
            except Exception:  # pragma: no cover - defensive
                main_chat = None
        tags = [
            "orchestration",
            f"run:{run.run_id}",
            f"step:{step.id}",
        ]
        payload = {
            "name": step.title,
            "description": description,
            "content": content,
            "board": board,
            "column": column,
            "sprints": [run.config.sprint] if run.config.sprint else None,
            "status": chat_status,
            "priority": step.priority,
            "profiles": profiles or ([step.profile] if step.profile else []),
            "files": step.files,
            "tags": tags,
            "parent_id": run.main_chat_id or None,
            "parent_chat": main_chat,
            "mode": step.mode or run.config.step_mode or "chat",
            "estimation_cost": estimation_cost,
            "run_id": run.run_id,
            "run_step_id": step.id,
            "ignore_parent_knowledge": True,
            "ignore_parent_files": True,
        }
        task = self._tasks().create_task(**self._supported_task_kwargs(payload))
        step.chat_id = task.id
        step.board = task.board or board
        step.column = task.column or column
        step.chat_status = task.status or chat_status
        step.updated_at = task.updated_at
        logger.info(
            "Orchestration: card created run='%s' step='%s' chat='%s' board='%s' column='%s'",
            run.run_id,
            step.id,
            task.id,
            step.board,
            step.column,
        )
        return task

    def update_step_card(
        self,
        run: RunState,
        step,
        *,
        result: Optional[Any] = None,
        persist: bool = True,
    ) -> Optional[Any]:
        """
        Mirror the step status onto its card.

        Args:
            run: Owning run.
            step: Step whose status/result changed.
            result: Optional :class:`StepResult` (unused for the card fields but
                kept for callers that want to append a note later).
            persist: Persist the card (False for dry runs/tests).

        Returns:
            The updated chat, or None when the card no longer exists.
        """
        if not step.chat_id:
            return None
        manager = self._manager()
        card = manager.find_by_id(chat_id=step.chat_id)
        if card is None:
            logger.warning(
                "Orchestration: card '%s' of step '%s' was deleted; it will be recreated on retry",
                step.chat_id,
                step.id,
            )
            step.chat_id = ""
            step.board = ""
            step.column = ""
            step.chat_status = ""
            return None

        column = self._column_for(run, step.status)
        chat_status = C.STEP_CHAT_STATUS.get(step.status, "todo")
        card.column = column
        card.status = chat_status
        card.progress = {
            C.STEP_STATUS_PENDING: 0,
            C.STEP_STATUS_RUNNING: 50,
            C.STEP_STATUS_DONE: 100,
            C.STEP_STATUS_SKIPPED: 100,
            C.STEP_STATUS_FAILED: 100,
            C.STEP_STATUS_BLOCKED: 100,
        }.get(step.status, card.progress or 0)
        card.run_id = run.run_id
        card.run_step_id = step.id
        if run.config.sprint and run.config.sprint not in (card.sprints or []):
            card.sprints = list(card.sprints or []) + [run.config.sprint]
        if persist:
            manager.save_chat(chat=card, chat_only=True)
        step.board = card.board or step.board
        step.column = card.column
        step.chat_status = card.status
        return card

    def create_main_task(
        self,
        run: RunState,
        *,
        profiles: Optional[List[str]] = None,
        estimation_cost: Optional[float] = None,
    ) -> Any:
        """
        Create the main task (the human dashboard) of a run.

        The main task is a normal task card: it owns the objective, the budget
        (``estimation_cost``), the supervisor profile and the run back-reference.
        Its root is itself (runs are budget roots), so it is created without a
        parent.
        """
        board = run.config.board or C.DEFAULT_BOARD
        column = (
            (run.config.columns or C.DEFAULT_RUN_COLUMNS).get("running")
            or "In progress"
        )
        tags = ["orchestration", "run", f"run:{run.run_id}"]
        task = self._tasks().create_task(
            name=run.name or "Orchestration run",
            description=run.objective or run.name or "Orchestration run",
            content=run.objective or run.name or "Orchestration run",
            board=board,
            column=column,
            sprints=[run.config.sprint] if run.config.sprint else None,
            status="todo",
            priority="high",
            profiles=profiles or run.config.supervisor_profiles,
            tags=tags,
            mode=C.CHAT_MODE_ORCHESTRATE,
            estimation_cost=estimation_cost,
            run_id=run.run_id,
        )
        logger.info(
            "Orchestration: main task created run='%s' chat='%s' board='%s' column='%s'",
            run.run_id,
            task.id,
            task.board,
            task.column,
        )
        return task

    def create_delegate_card(
        self,
        parent_chat: Any,
        *,
        name: str,
        description: str,
        content: str,
        profiles: Optional[List[str]] = None,
        board: Optional[str] = None,
        column: Optional[str] = None,
        estimation_cost: Optional[float] = None,
        priority: Optional[str] = None,
    ) -> Any:
        """
        Create a one-off delegated subagent card under *parent_chat*.

        Delegated cards stay next to the parent on the board/sprint, so a user
        watching the project sees the subagent work exactly like any other task.
        They are created with ``ignore_parent_knowledge`` / ``ignore_parent_files``
        so the subagent gets an isolated context.
        """
        tags = ["delegation", f"delegated-from:{getattr(parent_chat, 'id', '')}"]
        task = self._tasks().create_task(
            name=name,
            description=description,
            content=content,
            board=board or getattr(parent_chat, "board", None) or C.DEFAULT_BOARD,
            column=column or getattr(parent_chat, "column", None) or "tasks",
            sprints=list(getattr(parent_chat, "sprints", None) or []),
            status="doing",
            priority=priority,
            profiles=profiles or [],
            parent_chat=parent_chat,
            tags=tags,
            mode=C.CHAT_MODE_DELEGATE,
            estimation_cost=estimation_cost,
            ignore_parent_knowledge=True,
            ignore_parent_files=True,
        )
        logger.info(
            "Orchestration: delegated card created parent='%s' chat='%s' board='%s' column='%s'",
            getattr(parent_chat, "id", ""),
            task.id,
            task.board,
            task.column,
        )
        return task

    def attach_main(
        self,
        run: RunState,
        main_chat: Any,
        *,
        persist: bool = False,
        move: bool = False,
        status: Optional[str] = None,
        progress: Optional[int] = None,
    ) -> Any:
        """
        Stamp the run fields on the main task and (optionally) move it.

        The main task is the human-facing dashboard of the run; it is NOT
        required to live on the run board. By default it keeps its board and is
        only added to the run sprint, so attaching a run to an existing task
        never surprises the user. ``move=True`` (API-created runs) places it on
        the run board.

        Args:
            run: Owning run.
            main_chat: Main task chat (mutated).
            persist: Save the chat now. Keep False when called from inside a
                chat turn (the engine will persist it at the end).
            move: Move the main task to the run board/column.
            status: Optional ``Chat.status`` mirror.
            progress: Optional progress percentage.

        Returns:
            The same chat.
        """
        main_chat.run_id = run.run_id
        main_chat.run_status = run.status
        # The supervisor profile carries the planning rules and the control
        # tools for a promoted chat. Append it without dropping the profiles the
        # user already selected.
        profiles = list(main_chat.profiles or [])
        for name in run.config.supervisor_profiles or []:
            clean = str(name or "").strip().lstrip("@")
            if clean and clean not in profiles:
                profiles.append(clean)
        main_chat.profiles = profiles
        if status is not None:
            main_chat.status = status
        if progress is not None:
            main_chat.progress = progress
        if run.config.sprint and run.config.sprint not in (main_chat.sprints or []):
            main_chat.sprints = list(main_chat.sprints or []) + [run.config.sprint]
        if move:
            main_chat.board = run.config.board or C.DEFAULT_BOARD
            main_chat.column = (
                (run.config.columns or C.DEFAULT_RUN_COLUMNS).get("running")
                or "In progress"
            )
        tags = list(main_chat.tags or [])
        for tag in ("orchestration", f"run:{run.run_id}"):
            if tag not in tags:
                tags.append(tag)
        main_chat.tags = tags
        if persist:
            self._manager().save_chat(chat=main_chat)
        return main_chat

    def update_main_card(
        self,
        run: RunState,
        *,
        status: Optional[str] = None,
        column_phase: Optional[str] = None,
        progress: Optional[int] = None,
        run_status: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Update the main task card from outside a chat turn (worker/API).

        Uses ``chat_only=True`` so the conversation messages are preserved.
        """
        if not run.main_chat_id:
            return None
        manager = self._manager()
        main_chat = manager.find_by_id(chat_id=run.main_chat_id)
        if main_chat is None:
            return None
        if status is not None:
            main_chat.status = status
        if run_status is not None:
            main_chat.run_status = run_status
        main_chat.run_id = run.run_id
        if column_phase:
            column = (run.config.columns or C.DEFAULT_RUN_COLUMNS).get(
                column_phase, column_phase
            )
            main_chat.column = column
        if progress is not None:
            main_chat.progress = max(0, min(100, int(progress)))
        if run.config.sprint and run.config.sprint not in (main_chat.sprints or []):
            main_chat.sprints = list(main_chat.sprints or []) + [run.config.sprint]
        manager.save_chat(chat=main_chat, chat_only=True)
        return main_chat

# Made with ❤️ by codx-junior
