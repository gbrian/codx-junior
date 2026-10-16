"""
Planning manager.

Centralises every dataset-wide task computation so the UI never aggregates
paginated rows on the client:

    * filtering     (boards, assignees, priorities, statuses, search, range...)
    * derived flags (overdue / due_today / days_until_due / unassigned / stalled)
    * sorting       (priority -> due_date -> sort_index, server-side)
    * aggregation   (metrics, board progress, priority/status counts)
    * attention queue (severity ordered)
    * activity feed (event sourced, option C)

The unit of work is a *task*, which is the task-shaped projection of a
persisted ``Chat`` (chats and tasks are the same entity).

Flowchart:
```mermaid
flowchart TD
    Q[PlanningQuery] --> F[filter_tasks]
    F --> F1[range / boards / assignees / priorities / statuses / search]
    F --> F2[derived flags + attention_reason]
    F1 --> A[aggregate over ALL filtered tasks]
    F2 --> A
    A --> M[metrics / board_progress / group_counts]
    A --> AT[attention queue severity-ordered]
    ES[(planning/events.jsonl)] --> AC[activity feed]
```
"""

import json
import logging
import os
import uuid

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from codx.junior.chat_manager import ChatManager, _parse_timestamp
from codx.junior.db import Chat
from codx.junior.model.planning import (
    ActivityEvent,
    AttentionItem,
    BoardProgressItem,
    PlanningDashboardResponse,
    PlanningGroupCount,
    PlanningMetrics,
    PlanningQuery,
    PlanningReorderRequest,
    PlanningTask,
    PlanningTaskQueryResponse,
    PlanningTaskUpdate,
)
from codx.junior.project.project_discover import find_project_by_id

logger = logging.getLogger(__name__)

# ── Canonical orderings ────────────────────────────────────────────────────────
PRIORITY_ORDER = ["high", "medium", "low"]
PRIORITY_LABELS = {"high": "High", "medium": "Medium", "low": "Low"}

STATUS_ORDER = ["todo", "doing", "onhold", "done", "rejected"]
STATUS_LABELS = {
    "todo": "To do",
    "doing": "Doing",
    "onhold": "On hold",
    "done": "Done",
    "rejected": "Rejected",
}

DONE_STATUSES = {"done"}
CLOSED_STATUSES = {"done", "rejected"}
ACTIVE_STATUSES = {"todo", "doing"}
ON_HOLD_STATUSES = {"onhold"}

DEFAULT_PRIORITY = "low"
DEFAULT_STATUS = "todo"

# A "doing" task not touched for this many days is surfaced as stalled.
STALLED_AFTER_DAYS = 21

ATTENTION_LIMIT = 50
ACTIVITY_LIMIT = 30

# Field -> emitted activity action, and action -> UI tone.
ACTION_BY_FIELD = {
    "priority": "priority_changed",
    "due_date": "due_date_changed",
    "status": "moved",
    "progress": "progress_changed",
    "assignees": "assigned",
    "sort_index": "reordered",
}
TONE_BY_ACTION = {
    "completed": "success",
    "priority_changed": "warning",
    "created": "primary",
    "moved": "info",
    "assigned": "info",
    "due_date_changed": "warning",
    "progress_changed": "info",
    "reordered": "info",
}


class PlanningConflictError(Exception):
    """Raised when an optimistic-concurrency check fails."""


# ── Small helpers ──────────────────────────────────────────────────────────────
def _now_iso() -> str:
    """Return the current local time as an ISO-8601 string."""
    return datetime.now().isoformat()


def _normalize_priority(value: Optional[str]) -> str:
    value = (value or "").strip().lower()
    return value if value in PRIORITY_ORDER else DEFAULT_PRIORITY


def _normalize_status(value: Optional[str]) -> str:
    value = (value or "").strip().lower()
    return value if value in STATUS_ORDER else DEFAULT_STATUS


def _parse_date(value: Optional[str]) -> Optional[date]:
    """Parse a date/datetime string into a ``date``, or ``None`` when invalid."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            logger.debug("Unparseable planning date: '%s'", value)
            return None


def _stringify(value: Any) -> Optional[str]:
    """Render a scalar/list field value for the activity feed."""
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(v) for v in value)
    return str(value)


class PlanningEventStore:
    """
    Append-only JSONL store for planning activity events.

    Lives under ``<codx_path>/planning/events.jsonl``. Every write endpoint
    records one line per changed field so the dashboard activity feed has a
    real actor / field / from->to trail instead of a value fabricated from the
    task's participant list.
    """

    def __init__(self, codx_path: str):
        self.folder = f"{codx_path}/planning"
        self.file_path = f"{self.folder}/events.jsonl"
        os.makedirs(self.folder, exist_ok=True)

    def append(self, event: ActivityEvent) -> None:
        """Append a single event (best-effort; never raises on IO errors)."""
        try:
            with open(self.file_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event.model_dump()) + "\n")
        except OSError as ex:
            logger.error("PlanningEventStore.append failed: %s", ex)

    def append_many(self, events: List[ActivityEvent]) -> None:
        """Append a batch of events."""
        for event in events:
            self.append(event)

    def read(self) -> List[ActivityEvent]:
        """Read all persisted events; malformed lines are skipped."""
        if not os.path.isfile(self.file_path):
            return []
        events: List[ActivityEvent] = []
        try:
            with open(self.file_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(ActivityEvent(**json.loads(line)))
                    except Exception as ex:  # noqa: BLE001 - defensive parse
                        logger.debug("Skipping malformed planning event: %s", ex)
        except OSError as ex:
            logger.error("PlanningEventStore.read failed: %s", ex)
        return events


class PlanningManager:
    """
    Server-side planning computations over the full task dataset.

    :param chat_manager: Manager used to load/persist chats for the active project.
    :param settings: Active project settings (used for the event store path).
    :param user: Optional authenticated user, stored for reference.
    """

    def __init__(self, chat_manager: ChatManager, settings, user=None):
        self.chat_manager = chat_manager
        self.settings = settings
        self.user = user
        self.event_store = PlanningEventStore(settings.codx_path)

    # -------------------------------------------------------------------------
    # Loading
    # -------------------------------------------------------------------------
    def _managers(self, project_ids: Optional[List[str]]) -> List[ChatManager]:
        """Resolve the set of ChatManagers to read tasks from."""
        if project_ids is None:
            return [self.chat_manager]
        managers: List[ChatManager] = []
        for project_id in project_ids:
            project = find_project_by_id(project_id)
            if project:
                managers.append(ChatManager(settings=project))
        return managers

    def _load_chats(self, query: PlanningQuery) -> List[Chat]:
        """Load chats across the scoped projects."""
        chats: List[Chat] = []
        for manager in self._managers(query.project_ids):
            try:
                chats.extend(manager.list_chats())
            except (OSError, ValueError) as ex:
                logger.warning("planning: failed to load chats: %s", ex)
        return chats

    # -------------------------------------------------------------------------
    # Projection + derived flags
    # -------------------------------------------------------------------------
    @staticmethod
    def _has_planning_signal(chat: Chat) -> bool:
        return bool(
            (chat.status or "").strip()
            or (chat.priority or "").strip()
            or (chat.due_date or "").strip()
            or (chat.assignees or [])
        )

    def _is_task(self, chat: Chat, query: PlanningQuery) -> bool:
        """Determine whether a chat should appear as a planning task."""
        if chat.is_template and not query.include_templates:
            return False
        # Plain conversations are only treated as tasks when they carry some
        # planning metadata (status / priority / due_date / assignees).
        if (chat.mode or "chat") == "chat" and not self._has_planning_signal(chat):
            return False
        return True

    @staticmethod
    def _to_task(chat: Chat) -> PlanningTask:
        """Build the task projection with server-computed derived flags."""
        today = date.today()
        status = _normalize_status(chat.status)
        priority = _normalize_priority(chat.priority)
        assignees = list(chat.assignees or [])
        unassigned = not assignees

        due = _parse_date(chat.due_date)
        days_until_due = (due - today).days if due else None

        overdue = bool(due and days_until_due < 0 and status not in CLOSED_STATUSES)
        due_today = bool(due and days_until_due == 0 and status not in CLOSED_STATUSES)

        updated_ts = _parse_timestamp(chat.updated_at)
        stalled = (
            status == "doing"
            and updated_ts != datetime.min
            and (datetime.now() - updated_ts).days >= STALLED_AFTER_DAYS
        )

        reason = None
        if overdue:
            reason = "overdue"
        elif due_today:
            reason = "due_today"
        elif unassigned and priority == "high":
            reason = "unassigned_high"
        elif stalled:
            reason = "stalled"

        return PlanningTask(
            id=chat.id or "",
            name=chat.name or "",
            description=chat.description,
            board=chat.board,
            column=chat.column,
            status=status,
            priority=priority,
            due_date=chat.due_date,
            progress=int(chat.progress or 0),
            assignees=assignees,
            users=list(chat.users or []),
            sort_index=chat.sort_index,
            project_id=chat.project_id,
            owner_project_id=chat.owner_project_id,
            mode=chat.mode or "task",
            created_at=str(chat.created_at or ""),
            updated_at=str(chat.updated_at or ""),
            overdue=overdue,
            due_today=due_today,
            days_until_due=days_until_due,
            unassigned=unassigned,
            attention_reason=reason,
        )

    # -------------------------------------------------------------------------
    # Filtering
    # -------------------------------------------------------------------------
    @staticmethod
    def _matches_search(task: PlanningTask, search: str) -> bool:
        needle = search.lower().strip()
        haystack = " ".join(
            [task.name or "", task.description or "", task.column or "", task.board or ""]
        ).lower()
        return needle in haystack

    @staticmethod
    def _apply_range(chat: Chat, query: PlanningQuery) -> bool:
        rng = query.range
        if not rng or (not rng.from_ and not rng.to):
            return True

        field = rng.field or "updated_at"
        start = _parse_date(rng.from_)
        end = _parse_date(rng.to)

        if field == "due_date":
            value = _parse_date(chat.due_date)
        else:
            # updated_at / created_at (default)
            value = _parse_timestamp(getattr(chat, field, None)).date()

        if not value:
            return False
        if start and value < start:
            return False
        if end and value > end:
            return False
        return True

    def filter_tasks(self, query: PlanningQuery) -> List[PlanningTask]:
        """Return every task matching *query* (no pagination applied)."""
        tasks: List[PlanningTask] = []
        for chat in self._load_chats(query):
            if not self._is_task(chat, query):
                continue
            if not self._apply_range(chat, query):
                continue

            task = self._to_task(chat)

            if not query.include_done and task.status in DONE_STATUSES:
                continue
            if query.boards and (task.board or "") not in query.boards:
                continue
            if query.priorities and task.priority not in query.priorities:
                continue
            if query.statuses and task.status not in query.statuses:
                continue
            if query.assignees and not (set(task.assignees) & set(query.assignees)):
                continue
            if query.search and not self._matches_search(task, query.search):
                continue
            if query.attention_only and not task.attention_reason:
                continue

            tasks.append(task)
        return tasks

    # -------------------------------------------------------------------------
    # Sorting
    # -------------------------------------------------------------------------
    @staticmethod
    def _priority_rank(priority: str) -> int:
        try:
            return PRIORITY_ORDER.index(priority)
        except ValueError:
            return len(PRIORITY_ORDER)

    def _sort_tasks(self, tasks: List[PlanningTask], sort) -> List[PlanningTask]:
        """Sort *tasks* in place according to *sort* (server-side)."""
        field = sort.field or "priority"
        reverse = (sort.dir or "asc").lower() == "desc"

        if field == "priority":
            def priority_key(task: PlanningTask):
                due = _parse_date(task.due_date)
                due_ord = due.toordinal() if due else 10 ** 9
                sort_index = task.sort_index if task.sort_index is not None else 10 ** 9
                return (self._priority_rank(task.priority), due_ord, sort_index)

            tasks.sort(key=priority_key, reverse=reverse)
        elif field == "due_date":
            def due_key(task: PlanningTask):
                due = _parse_date(task.due_date)
                return (0, due.toordinal()) if due else (1, 0)

            tasks.sort(key=due_key, reverse=reverse)
        elif field == "updated_at":
            tasks.sort(key=lambda t: _parse_timestamp(t.updated_at), reverse=reverse)
        elif field == "sort_index":
            tasks.sort(
                key=lambda t: t.sort_index if t.sort_index is not None else 10 ** 9,
                reverse=reverse,
            )
        else:
            tasks.sort(key=lambda t: self._priority_rank(t.priority), reverse=reverse)

        return tasks

    # -------------------------------------------------------------------------
    # Grouping
    # -------------------------------------------------------------------------
    @staticmethod
    def _group_key(task: PlanningTask, group_by: str) -> Tuple[str, str]:
        if group_by == "status":
            return task.status, STATUS_LABELS.get(task.status, task.status)
        if group_by == "board":
            board = task.board or "—"
            return board, board
        return task.priority, PRIORITY_LABELS.get(task.priority, task.priority)

    def build_group_counts(
        self, tasks: List[PlanningTask], group_by: Optional[str]
    ) -> List[PlanningGroupCount]:
        """True per-group counts over the full filtered dataset."""
        if not group_by:
            return []

        counts: Dict[str, int] = {}
        labels: Dict[str, str] = {}
        for task in tasks:
            key, label = self._group_key(task, group_by)
            counts[key] = counts.get(key, 0) + 1
            labels[key] = label

        order = {"priority": PRIORITY_ORDER, "status": STATUS_ORDER}.get(group_by)
        keys = list(counts.keys())
        if order:
            keys.sort(key=lambda k: order.index(k) if k in order else len(order))
        else:
            keys.sort()

        return [
            PlanningGroupCount(key=k, label=labels[k], total=counts[k])
            for k in keys
        ]

    # -------------------------------------------------------------------------
    # Applied filters (echoed back to the client)
    # -------------------------------------------------------------------------
    @staticmethod
    def _applied_filters(query: PlanningQuery) -> Dict[str, Any]:
        applied: Dict[str, Any] = {}
        if query.boards:
            applied["boards"] = query.boards
        if query.assignees:
            applied["assignees"] = query.assignees
        if query.priorities:
            applied["priorities"] = query.priorities
        if query.statuses:
            applied["statuses"] = query.statuses
        if query.search:
            applied["search"] = query.search
        if query.attention_only:
            applied["attention_only"] = True
        if not query.include_done:
            applied["include_done"] = False
        if query.include_templates:
            applied["include_templates"] = True
        if query.project_ids:
            applied["project_ids"] = query.project_ids
        if query.range and (query.range.from_ or query.range.to):
            applied["range"] = {
                "field": query.range.field,
                "from": query.range.from_,
                "to": query.range.to,
            }
        return applied

    # -------------------------------------------------------------------------
    # Query endpoint
    # -------------------------------------------------------------------------
    def query_tasks(self, query: PlanningQuery) -> PlanningTaskQueryResponse:
        """Paginated task rows + true group counts (dataset-wide)."""
        tasks = self.filter_tasks(query)
        total = len(tasks)
        group_counts = self.build_group_counts(tasks, query.group_by)

        self._sort_tasks(tasks, query.sort)

        page_size = max(1, min(100, query.page_size))
        total_pages = (total + page_size - 1) // page_size if total else 0
        page = min(max(1, query.page), total_pages) if total_pages else 1

        start = (page - 1) * page_size

        logger.info(
            "planning.query_tasks: total=%d page=%d/%d group_by=%s",
            total,
            page,
            total_pages,
            query.group_by,
        )

        return PlanningTaskQueryResponse(
            tasks=tasks[start:start + page_size],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
            group_counts=group_counts,
            applied_filters=self._applied_filters(query),
            generated_at=_now_iso(),
        )

    # -------------------------------------------------------------------------
    # Dashboard aggregation
    # -------------------------------------------------------------------------
    @staticmethod
    def _build_metrics(tasks: List[PlanningTask]) -> PlanningMetrics:
        by_priority: Dict[str, int] = {p: 0 for p in PRIORITY_ORDER}
        by_status: Dict[str, int] = {s: 0 for s in STATUS_ORDER}

        done = active = on_hold = rejected = overdue = due_today = unassigned = 0
        for task in tasks:
            by_priority[task.priority] = by_priority.get(task.priority, 0) + 1
            by_status[task.status] = by_status.get(task.status, 0) + 1

            if task.status in DONE_STATUSES:
                done += 1
            if task.status in ACTIVE_STATUSES:
                active += 1
            if task.status in ON_HOLD_STATUSES:
                on_hold += 1
            if task.status == "rejected":
                rejected += 1
            if task.overdue:
                overdue += 1
            if task.due_today:
                due_today += 1
            if task.unassigned:
                unassigned += 1

        total = len(tasks)
        completion = round((done / total) * 100) if total else 0

        return PlanningMetrics(
            total=total,
            done=done,
            active=active,
            on_hold=on_hold,
            rejected=rejected,
            overdue=overdue,
            due_today=due_today,
            unassigned=unassigned,
            completion=completion,
            by_priority=by_priority,
            by_status=by_status,
        )

    @staticmethod
    def _build_board_progress(tasks: List[PlanningTask]) -> List[BoardProgressItem]:
        buckets: Dict[str, Dict[str, int]] = {}
        for task in tasks:
            board = task.board or "—"
            bucket = buckets.setdefault(
                board,
                {
                    "total": 0,
                    "done": 0,
                    "doing": 0,
                    "todo": 0,
                    "on_hold": 0,
                    "overdue": 0,
                    "unassigned": 0,
                },
            )
            bucket["total"] += 1
            if task.status in DONE_STATUSES:
                bucket["done"] += 1
            elif task.status == "doing":
                bucket["doing"] += 1
            elif task.status == "onhold":
                bucket["on_hold"] += 1
            elif task.status == "todo":
                bucket["todo"] += 1
            if task.overdue:
                bucket["overdue"] += 1
            if task.unassigned:
                bucket["unassigned"] += 1

        items: List[BoardProgressItem] = []
        for board, bucket in buckets.items():
            percentage = (
                round((bucket["done"] / bucket["total"]) * 100) if bucket["total"] else 0
            )
            items.append(
                BoardProgressItem(board=board, percentage=percentage, **bucket)
            )
        items.sort(key=lambda item: item.board.lower())
        return items

    @staticmethod
    def _severity(task: PlanningTask, reason: str) -> int:
        if reason == "overdue":
            return 300 + min(99, abs(task.days_until_due or 0))
        if reason == "due_today":
            return 200
        if reason == "unassigned_high":
            return 100
        return 50  # stalled

    def _build_attention(self, tasks: List[PlanningTask]) -> List[AttentionItem]:
        items: List[AttentionItem] = []
        for task in tasks:
            if not task.attention_reason:
                continue
            items.append(
                AttentionItem(
                    task=task,
                    reason=task.attention_reason,
                    severity=self._severity(task, task.attention_reason),
                )
            )
        items.sort(key=lambda item: item.severity, reverse=True)
        return items[:ATTENTION_LIMIT]

    # -------------------------------------------------------------------------
    # Activity feed
    # -------------------------------------------------------------------------
    def _read_activity(self, task_ids: set, limit: int = ACTIVITY_LIMIT) -> List[ActivityEvent]:
        events = [
            event
            for event in self.event_store.read()
            if not task_ids or event.target_task_id in task_ids
        ]
        events.sort(key=lambda e: _parse_timestamp(e.timestamp), reverse=True)
        return events[:limit]

    def read_activity(
        self, query: Optional[PlanningQuery] = None, limit: int = ACTIVITY_LIMIT
    ) -> List[ActivityEvent]:
        """Standalone activity feed scoped to the current filter."""
        query = query or PlanningQuery()
        tasks = self.filter_tasks(query)
        return self._read_activity({task.id for task in tasks}, limit=limit)

    def build_dashboard(self, query: PlanningQuery) -> PlanningDashboardResponse:
        """All aggregates for the follow-up view (pagination is ignored)."""
        tasks = self.filter_tasks(query)
        metrics = self._build_metrics(tasks)

        return PlanningDashboardResponse(
            metrics=metrics,
            board_progress=self._build_board_progress(tasks),
            attention=self._build_attention(tasks),
            activity=self._read_activity({task.id for task in tasks}),
            priority_counts=metrics.by_priority,
            generated_at=_now_iso(),
        )

    # -------------------------------------------------------------------------
    # Writes
    # -------------------------------------------------------------------------
    def _emit_update_events(
        self,
        chat: Chat,
        changed_fields: Dict[str, Tuple[Any, Any]],
        actor: str,
        actor_type: str,
    ) -> List[ActivityEvent]:
        events: List[ActivityEvent] = []
        now = _now_iso()
        for field, (old, new) in changed_fields.items():
            action = ACTION_BY_FIELD.get(field, f"{field}_changed")
            if field == "status" and new in DONE_STATUSES:
                action = "completed"
            events.append(
                ActivityEvent(
                    id=str(uuid.uuid4()),
                    actor=actor or "system",
                    actor_type=actor_type or "user",
                    action=action,
                    target_task_id=chat.id or "",
                    target_task_name=chat.name or "",
                    board=chat.board,
                    field=field,
                    from_value=_stringify(old),
                    to_value=_stringify(new),
                    timestamp=now,
                    tone=TONE_BY_ACTION.get(action, "info"),
                )
            )
        self.event_store.append_many(events)
        return events

    def update_task(
        self,
        task_id: str,
        update: PlanningTaskUpdate,
        actor: str = "system",
        actor_type: str = "user",
    ) -> Tuple[PlanningTask, List[ActivityEvent]]:
        """Apply a partial task update and emit an activity event per change."""
        chat = self.chat_manager.find_by_id(chat_id=task_id)
        if not chat:
            raise ValueError(f"Task not found: {task_id}")

        if update.expected_updated_at and str(chat.updated_at) != update.expected_updated_at:
            raise PlanningConflictError(
                f"Task '{task_id}' was modified by someone else; reload and retry."
            )

        changed_fields: Dict[str, Tuple[Any, Any]] = {}
        data = update.model_dump(exclude_unset=True, exclude={"expected_updated_at"})
        for field, value in data.items():
            if value is None:
                continue
            old = getattr(chat, field, None)
            if old != value:
                changed_fields[field] = (old, value)
                setattr(chat, field, value)

        saved = chat
        if changed_fields:
            saved = self.chat_manager.save_chat(chat=chat, chat_only=True)

        events = self._emit_update_events(saved, changed_fields, actor, actor_type)
        logger.info(
            "planning.update_task: task=%s fields=%s actor=%s",
            task_id,
            list(changed_fields.keys()),
            actor,
        )
        return self._to_task(saved), events

    def reorder_tasks(
        self,
        request: PlanningReorderRequest,
        actor: str = "system",
        actor_type: str = "user",
    ) -> Tuple[int, List[ActivityEvent]]:
        """Persist a manual ordering (server assigns sort_index = position)."""
        events: List[ActivityEvent] = []
        updated = 0
        now = _now_iso()

        for position, task_id in enumerate(request.ordered_ids):
            chat = self.chat_manager.find_by_id(chat_id=task_id)
            if not chat:
                continue
            old = chat.sort_index
            if old == position:
                continue
            chat.sort_index = position
            self.chat_manager.save_chat(chat=chat, chat_only=True)
            updated += 1
            events.append(
                ActivityEvent(
                    id=str(uuid.uuid4()),
                    actor=actor or "system",
                    actor_type=actor_type or "user",
                    action="reordered",
                    target_task_id=chat.id or "",
                    target_task_name=chat.name or "",
                    board=request.board or chat.board,
                    field="sort_index",
                    from_value=_stringify(old),
                    to_value=str(position),
                    timestamp=now,
                    tone="info",
                )
            )

        self.event_store.append_many(events)
        logger.info(
            "planning.reorder_tasks: board=%s updated=%d", request.board, updated
        )
        return updated, events


# Made with ❤️ by codx-junior