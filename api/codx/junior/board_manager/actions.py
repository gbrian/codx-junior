"""
Application of board-manager actions.

Every action is validated against the real board before it touches a task:

* the task must belong to the board being reviewed,
* the destination column/status must exist on that board,
* closed tasks, templates, channels and active orchestration cards are never
  modified (the service already filters them, this module re-checks),
* ``suggest`` mode records the action without applying it.

The module delegates persistence to the regular ``ChatManager`` /
``TaskManager``, so the board, planning and sprint read models keep working and
status history is recorded as for any human edit.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from codx.junior.board_manager import constants as C
from codx.junior.board_manager.models import ActionRecord, BoardManagerConfig, ManagerAction

logger = logging.getLogger(__name__)

PRIORITIES = ("high", "medium", "low")
MAX_COMMENT_CHARS = 4000

#: Marker stored in the comment metadata so the UI can identify manager notes.
MANAGER_META_KEY = "board_manager"


@dataclass
class BoardContext:
    """One board being reviewed."""

    title: str
    board_id: str
    board_type: str
    columns: List[Dict[str, Any]] = field(default_factory=list)
    config: BoardManagerConfig = field(default_factory=BoardManagerConfig)

    @property
    def is_sprint(self) -> bool:
        """Return True when the board groups tasks by status (sprint)."""
        return str(self.board_type or "").strip().lower() == "sprint"


def _same(value: Any, other: Any) -> bool:
    """Case-insensitive comparison of two optional labels."""
    return str(value or "").strip().lower() == str(other or "").strip().lower()


def find_column(
    columns: List[Dict[str, Any]], value: str
) -> Optional[Dict[str, Any]]:
    """
    Resolve a column by title **or** status (case insensitive).

    ``value`` may be the column label a human sees or the status a sprint column
    groups, so both are accepted.
    """
    wanted = str(value or "").strip().lower()
    if not wanted:
        return None
    for column in columns or []:
        if not isinstance(column, dict):
            column = {"title": str(column)}
        if _same(column.get("title"), wanted) or _same(column.get("status"), wanted):
            return column
    return None


def column_status(column: Dict[str, Any]) -> str:
    """Return the status a column writes on its tasks."""
    return str(column.get("status") or column.get("title") or "").strip()


def task_in_board(chat: Any, board: BoardContext) -> bool:
    """
    Return True when *chat* belongs to *board*.

    A kanban card carries ``chat.board``. A sprint is a view over statuses:
    membership is ``chat.sprints`` and the task may live on another kanban
    board.
    """
    if board.is_sprint:
        return any(_same(sprint, board.title) for sprint in (getattr(chat, "sprints", []) or []))
    return _same(getattr(chat, "board", ""), board.title)


def is_active_run(chat: Any) -> bool:
    """Return True when the card is owned by an in-flight orchestration run."""
    return bool(getattr(chat, "run_id", None)) and str(
        getattr(chat, "run_status", "") or ""
    ).strip().lower() in C.ACTIVE_RUN_STATUSES


def is_closed(chat: Any) -> bool:
    """Return True when the task status is one of the closed statuses."""
    return str(getattr(chat, "status", "") or "").strip().lower() in C.DONE_STATUSES


def _valid_date(value: str) -> bool:
    """Return True for an ISO ``YYYY-MM-DD`` date."""
    try:
        date.fromisoformat(str(value or ""))
        return True
    except (TypeError, ValueError):
        return False


@dataclass
class _Proposal:
    """Human readable summary of one action before/after applying it."""

    summary: str
    changed: bool


class ActionApplier:
    """
    Applies the actions of one review.

    Args:
        chat_manager: Project ``ChatManager``.
        settings: Project settings (used by ``create_task``).
        board: The board being reviewed.
        profile: Manager profile name (stamped on comments/tasks).
        event_manager: Optional event manager for live UI notifications.
        message_factory: Optional ``Message`` factory (offline tests).
    """

    def __init__(
        self,
        chat_manager: Any,
        settings: Any,
        board: BoardContext,
        profile: str,
        event_manager: Any = None,
        message_factory: Any = None,
    ) -> None:
        self.chat_manager = chat_manager
        self.settings = settings
        self.board = board
        self.profile = str(profile or "").strip()
        self.event_manager = event_manager
        self.message_factory = message_factory

    def _message(self, **kwargs: Any) -> Any:
        """Create a ``Message`` (injectable for offline tests)."""
        if self.message_factory is not None:
            return self.message_factory(**kwargs)
        from codx.junior.db import Message

        return Message(**kwargs)

    # -- public -----------------------------------------------------------

    def apply(self, action: ManagerAction, chat: Any) -> ActionRecord:
        """
        Apply *action* to *chat* (or create a task).

        Args:
            action: Parsed action.
            chat: Target task, or None for ``create_task``.

        Returns:
            The audit record. Errors are reported in ``record.error`` instead of
            raising, so one bad action never loses the rest of the review.
        """
        record = ActionRecord(
            type=action.type,
            task_id=action.task_id,
            task_name=str(getattr(chat, "name", "") or action.name or ""),
            proposed=action.model_dump(),
        )
        try:
            if action.type not in C.ACTION_TYPES:
                record.error = f"Unknown action type '{action.type}'"
                return record
            if self.board.config.mode == C.MODE_SUGGEST:
                record.summary = self._suggest(action, chat)
                record.applied = False
                return record
            handler = {
                C.ACTION_MOVE: self._move,
                C.ACTION_CLOSE: self._close,
                C.ACTION_COMMENT: self._comment,
                C.ACTION_UPDATE: self._update,
                C.ACTION_CREATE: self._create,
            }[action.type]
            proposal = handler(action, chat)
            record.summary = proposal.summary
            record.applied = bool(proposal.changed)
            return record
        except ValueError as ex:
            record.error = str(ex)
            record.summary = str(ex)
            logger.info("board manager: action rejected (%s): %s", action.type, ex)
            return record
        except Exception as ex:  # pragma: no cover - defensive
            logger.exception("board manager: action failed (%s): %s", action.type, ex)
            record.error = str(ex)
            record.summary = f"Unexpected error: {ex}"
            return record

    # -- action handlers --------------------------------------------------

    def _require_task(
        self, action: ManagerAction, chat: Any, *, allow_closed: bool = False
    ) -> Any:
        """Validate that an action has an actionable target task."""
        if chat is None:
            raise ValueError(f"task '{action.task_id}' not found")
        if not task_in_board(chat, self.board):
            raise ValueError(
                f"task '{action.task_id}' does not belong to board '{self.board.title}'"
            )
        if getattr(chat, "is_template", False):
            raise ValueError("templates are not tasks")
        if str(getattr(chat, "mode", "") or "").strip().lower() == "channel":
            raise ValueError("channel chats are not tasks")
        if is_active_run(chat):
            raise ValueError(
                "task belongs to an active orchestration run and is managed by its worker"
            )
        if not allow_closed and is_closed(chat):
            raise ValueError("closed tasks are never modified by the board manager")
        return chat

    def _move(self, action: ManagerAction, chat: Any) -> _Proposal:
        """Move a kanban card to a column, or a sprint card to a status."""
        chat = self._require_task(action, chat)
        target = action.column or action.status
        if not target:
            raise ValueError("move_task requires 'column' (or 'status' on a sprint)")
        column = find_column(self.board.columns, target)
        if column is None:
            raise ValueError(
                f"unknown column '{target}' on board '{self.board.title}'"
            )

        if self.board.is_sprint:
            value = column_status(column)
            current = str(getattr(chat, "status", "") or "")
            if _same(current, value):
                return _Proposal(f"Already in {column.get('title')}", changed=False)
            self.chat_manager.update_chat_metadata(chat, {"status": value})
            return _Proposal(f"Moved to {column.get('title')}", changed=True)

        value = str(column.get("title") or "").strip()
        current = str(getattr(chat, "column", "") or "").strip()
        if _same(current, value):
            return _Proposal(f"Already in {value}", changed=False)
        self.chat_manager.update_chat_metadata(chat, {"column": value})
        return _Proposal(f"Moved to {value}", changed=True)

    def _close(self, action: ManagerAction, chat: Any) -> _Proposal:
        """Close a card: status done, progress 100 and the Done column when any."""
        chat = self._require_task(action, chat, allow_closed=True)
        if is_closed(chat):
            return _Proposal("Already closed", changed=False)

        metadata: Dict[str, Any] = {"status": "done", "progress": 100}
        done_column = None
        for column in self.board.columns or []:
            label = f"{column.get('title') or ''} {column.get('status') or ''}".lower()
            # Match whole words so "Undone" or "Not done yet" cannot be mistaken
            # for the board's Done column.
            if re.search(r"\b(done|closed|completed)\b", label):
                done_column = column
                break
        if done_column is not None:
            if self.board.is_sprint:
                metadata["status"] = column_status(done_column) or "done"
            else:
                metadata["column"] = str(done_column.get("title") or "").strip()

        self.chat_manager.update_chat_metadata(chat, metadata)
        target = (
            f" in {done_column.get('title')}"
            if done_column is not None and not self.board.is_sprint
            else ""
        )
        return _Proposal(f"Closed{target} (status done, progress 100%)", changed=True)

    def _comment(self, action: ManagerAction, chat: Any) -> _Proposal:
        """Add a manager comment (assistant message) to the task."""
        chat = self._require_task(action, chat)
        comment = str(action.comment or "").strip()
        if not comment:
            raise ValueError("comment requires 'comment' text")
        if len(comment) > MAX_COMMENT_CHARS:
            comment = comment[:MAX_COMMENT_CHARS].rstrip() + "…"

        # Never duplicate a comment the manager already left recently: a model
        # that repeats itself must not spam the task.
        recent = [
            str(getattr(message, "content", "") or "").strip()
            for message in (getattr(chat, "messages", []) or [])[-10:]
        ]
        if any(comment in content for content in recent if content):
            return _Proposal("Comment already present", changed=False)

        message = self._message(
            role="assistant",
            content=comment,
            profiles=[self.profile] if self.profile else [],
            user=self.profile or "board-manager",
            meta_data={MANAGER_META_KEY: {"profile": self.profile}},
        )
        saved = self.chat_manager.add_message(chat, message)
        self._emit_chat(saved, f"Board manager commented on '{getattr(chat, 'name', '')}'")
        if self.event_manager is not None and hasattr(self.event_manager, "message_event"):
            try:
                self.event_manager.message_event(chat=saved, message=message)
            except Exception:  # pragma: no cover - notifications are best effort
                pass
        return _Proposal("Comment added", changed=True)

    def _update(self, action: ManagerAction, chat: Any) -> _Proposal:
        """Update the editable metadata of a task."""
        chat = self._require_task(action, chat)
        metadata: Dict[str, Any] = {}
        changes: List[str] = []

        priority = str(action.priority or "").strip().lower()
        if priority:
            if priority not in PRIORITIES:
                raise ValueError(
                    f"invalid priority '{priority}' (valid: {', '.join(PRIORITIES)})"
                )
            metadata["priority"] = priority
            changes.append(f"priority={priority}")

        due_date = str(action.due_date or "").strip()
        if due_date:
            if not _valid_date(due_date):
                raise ValueError(f"invalid due_date '{due_date}' (expected YYYY-MM-DD)")
            metadata["due_date"] = due_date
            changes.append(f"due={due_date}")

        if action.progress is not None:
            progress = max(0, min(100, int(action.progress)))
            metadata["progress"] = progress
            changes.append(f"progress={progress}%")

        if action.assignees:
            metadata["assignees"] = list(action.assignees)
            changes.append(f"assignees={', '.join(action.assignees)}")

        if action.tags:
            metadata["tags"] = list(action.tags)
            changes.append(f"tags={', '.join(action.tags)}")

        if not metadata:
            raise ValueError(
                "update_task requires at least one of priority, due_date, "
                "progress, assignees or tags"
            )

        self.chat_manager.update_chat_metadata(chat, metadata)
        return _Proposal("Updated " + ", ".join(changes), changed=True)

    def _create(self, action: ManagerAction, chat: Any) -> _Proposal:
        """Create a follow-up task found during the review."""
        from codx.junior.task_manager import TaskManager

        if self.board.is_sprint:
            raise ValueError(
                "create_task is only supported on kanban boards: create the task "
                "on a kanban board and add it to the sprint afterwards"
            )

        name = str(action.name or "").strip()
        description = str(action.description or "").strip()
        if not name:
            raise ValueError("create_task requires 'name'")
        if not description:
            raise ValueError("create_task requires 'description'")

        target = action.column or action.status
        columns = self.board.columns or []
        column = find_column(columns, target) if target else None
        if target and column is None:
            raise ValueError(
                f"unknown column '{target}' on board '{self.board.title}'"
            )
        if column is None and columns:
            column = columns[0]

        priority = str(action.priority or "").strip().lower()
        kwargs: Dict[str, Any] = {
            "name": name,
            "description": description,
            "board": self.board.title,
            "profiles": [self.profile] if self.profile else [],
            "priority": priority if priority in PRIORITIES else None,
            "assignees": list(action.assignees),
            "tags": list(action.tags),
            "user": self.profile or "board-manager",
        }
        if column is not None:
            kwargs["column"] = str(column.get("title") or "").strip()

        manager = TaskManager(
            settings=self.settings,
            chat_manager=self.chat_manager,
            event_manager=self.event_manager,
        )
        created = manager.create_task(**kwargs)
        return _Proposal(
            f"Created task '{getattr(created, 'name', name)}' ({getattr(created, 'id', '')})",
            changed=True,
        )

    # -- helpers ----------------------------------------------------------

    def _suggest(self, action: ManagerAction, chat: Any) -> str:
        """Render the human readable suggestion of an action in suggest mode."""
        target = str(getattr(chat, "name", "") or action.name or action.task_id)
        if action.type == C.ACTION_MOVE:
            return f"Suggest moving '{target}' to {action.column or action.status}"
        if action.type == C.ACTION_CLOSE:
            return f"Suggest closing '{target}'"
        if action.type == C.ACTION_COMMENT:
            return f"Suggest commenting on '{target}'"
        if action.type == C.ACTION_UPDATE:
            return f"Suggest updating '{target}'"
        if action.type == C.ACTION_CREATE:
            return f"Suggest creating '{action.name}'"
        return f"Suggest {action.type} on '{target}'"

    def _emit_chat(self, chat: Any, message: str) -> None:
        """Notify connected clients that *chat* changed."""
        if self.event_manager is None or not hasattr(self.event_manager, "chat_event"):
            return
        try:
            self.event_manager.chat_event(chat=chat, message=message, event_type="changed")
        except Exception:  # pragma: no cover - notifications are best effort
            pass

# Made with ❤️ by codx-junior
