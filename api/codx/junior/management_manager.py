"""
Management manager — cross-project aggregation for the management dashboard.

Unlike :class:`codx.junior.planning_manager.PlanningManager`, which is scoped to
one project, this manager reads the tasks of **every project the user can see**
and produces the payloads the "Team Command Center" screen renders:

    overview()    pulse: metrics, attention, activity, forecast, team, cost
    tasks()       the Work section (filtered + paginated)
    blockers()    the attention queue
    delivery()    forecast + burndown
    team_load()   capacity and workload per assignee
    cost()        AI consumption and budget (from ``Analytics``)
    update_task() write-through to the owning project
    ask()         rule-based answer over the same numbers

Source of truth
---------------
Tasks are chats: a ``Chat`` row carries ``board``, ``column``, ``status``,
``priority``, ``due_date``, ``progress`` and ``assignees``. The board identity
used by this API is ``"<project_id>::<board>"`` because board *titles* are what
a chat stores and they are not unique across projects.

Derived signals
---------------
``Chat`` does not store every field the dashboard needs, so these are derived
(and documented instead of being silently invented):

* ``blocked``       – the task is on hold (``status == "onhold"``). "On hold" is
                      the only human-set "stopped" signal in the data model.
* ``stalled``       – ``doing`` and untouched for ``STALLED_AFTER_DAYS`` days.
* ``load_pct``      – there are no task estimates, so capacity is counted in
                      active tasks: ``CAPACITY_TASKS`` open tasks = 100%.
* ``hours``         – ``active_tasks * HOURS_PER_TASK`` (display only).
* ``target_date``   – the latest due date committed inside the board.
* ``demo_date``     – boards whose tasks declare sprints are treated as sprint
                      boards and demo on their target date.
* ``weekly_budget`` – ``CODX_JUNIOR_MANAGEMENT_WEEKLY_BUDGET`` (cxjcoins), split
                      evenly across the projects.

Flowchart:
```mermaid
flowchart TD
    P[find_all_projects / user projects] --> L[ChatManager.list_chats per project]
    L --> D[_decorate: derived flags per task]
    D --> W[window filter: updated in range OR not closed]
    W --> A[aggregations]
    A --> M[metrics / board_progress / attention]
    A --> F[forecast per board + burndown]
    A --> T[team load per assignee]
    A --> C[cost from Analytics]
```
"""

import logging
import os

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from codx.junior.analytics import Analytics
from codx.junior.chat_manager import ChatManager, _parse_timestamp
from codx.junior.db import Chat
from codx.junior.globals import ANALYTICS_DATA_PATH
from codx.junior.model.management import (
    ManagementActivity,
    ManagementAssistantResponse,
    ManagementAssistantSource,
    ManagementAttentionItem,
    ManagementBlockersResponse,
    ManagementBoardProgress,
    ManagementBudget,
    ManagementBudgetProject,
    ManagementBurndown,
    ManagementBurndownPoint,
    ManagementCost,
    ManagementCostResponse,
    ManagementDashboard,
    ManagementDeliveryResponse,
    ManagementForecast,
    ManagementMetrics,
    ManagementOverview,
    ManagementPerson,
    ManagementProject,
    ManagementTask,
    ManagementTaskQueryRequest,
    ManagementTaskQueryResponse,
    ManagementTaskUpdate,
    ManagementTeamResponse,
)
from codx.junior.planning_manager import PlanningEventStore
from codx.junior.project.project_discover import (
    find_all_projects,
    find_all_user_projects,
)

logger = logging.getLogger(__name__)

# ── Canonical orderings ────────────────────────────────────────────────────────
PRIORITY_ORDER = ["high", "medium", "low"]
STATUS_ORDER = ["todo", "doing", "onhold", "done", "rejected"]
CLOSED_STATUSES = {"done", "rejected"}
ACTIVE_STATUSES = {"todo", "doing"}
BLOCKED_STATUSES = {"onhold"}

STALLED_AFTER_DAYS = 14
ATTENTION_LIMIT = 50
ACTIVITY_LIMIT = 30
BURNDOWN_DAYS = 14

# No estimates exist in the data model: capacity is counted in active tasks.
CAPACITY_TASKS = int(os.getenv("CODX_JUNIOR_MANAGEMENT_CAPACITY_TASKS") or 10)
HOURS_PER_TASK = 4
DEFAULT_WEEKLY_BUDGET = float(os.getenv("CODX_JUNIOR_MANAGEMENT_WEEKLY_BUDGET") or 10000.0)

PROJECT_PALETTE = [
    "#e2419f", "#38bdf8", "#22c55e", "#f59e0b",
    "#a855f7", "#14b8a6", "#f05252", "#6366f1",
]

AGENT_PREFIXES = ("agent", "bot", "ai-")

# Higher = worse. Mirrors the client ordering so both agree without sharing code.
SEVERITY = {
    "blocked": 4.0,
    "overdue": 3.0,
    "due_today": 2.0,
    "unassigned_high": 1.5,
    "stalled": 1.0,
}


# ── Small helpers ──────────────────────────────────────────────────────────────
def _now_iso() -> str:
    """Return the current local time as an ISO-8601 string."""
    return datetime.now().isoformat()


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
            logger.debug("management: unparseable date '%s'", value)
            return None


def _iso(value: Any) -> str:
    """Normalise a stored timestamp to ISO-8601 (``''`` when unset/invalid)."""
    if not value:
        return ""
    parsed = _parse_timestamp(value)
    if parsed == datetime.min:
        return ""
    return parsed.isoformat()


def _resolve_range(from_value: Optional[str], to_value: Optional[str]) -> Tuple[date, date]:
    """Return the inclusive (start, end) window, defaulting to the last 7 days."""
    end = _parse_date(to_value) or date.today()
    start = _parse_date(from_value) or (end - timedelta(days=7))
    if start > end:
        start, end = end, start
    return start, end


def _in_window(updated_at: Any, start: date, end: date) -> bool:
    """True when the timestamp falls inside the inclusive window."""
    parsed = _parse_timestamp(updated_at)
    if parsed == datetime.min:
        return False
    return start <= parsed.date() <= end


def _project_code(name: str) -> str:
    """Short upper-case code used for board titles (``codx-junior`` -> ``COD``)."""
    letters = "".join(ch for ch in (name or "") if ch.isalnum())
    return (letters[:3] or "PRJ").upper()


def _person_type(username: str) -> str:
    """Classify an assignee as an AI agent when its name says so."""
    lowered = (username or "").lower()
    return "agent" if lowered.startswith(AGENT_PREFIXES) else "human"


class ManagementManager:
    """
    Cross-project task aggregation for the management dashboard.

    :param user: Authenticated user. Non-admins only see the projects they have
                 access to, which keeps the aggregation inside their permissions.
    """

    def __init__(self, user=None):
        self.user = user
        self._analytics: Optional[Analytics] = None
        self._projects: Optional[List[Any]] = None

    # -------------------------------------------------------------------------
    # Projects / reference data
    # -------------------------------------------------------------------------
    @property
    def analytics(self) -> Analytics:
        """Lazily created shared analytics reader (real AI consumption)."""
        if self._analytics is None:
            self._analytics = Analytics(analytics_path=ANALYTICS_DATA_PATH)
        return self._analytics

    def _load_projects(self) -> List[Any]:
        """Resolve the projects this user may see (admin sees everything)."""
        if self._projects is not None:
            return self._projects

        try:
            if self.user is not None and getattr(self.user, "role", None) != "admin":
                settings_list = list(find_all_user_projects(self.user))
            else:
                settings_list = list((find_all_projects() or {}).values())
        except Exception as ex:  # noqa: BLE001 - discovery must never break a request
            logger.error("management: project discovery failed: %s", ex)
            settings_list = []

        self._projects = [
            settings for settings in settings_list
            if getattr(settings, "codx_path", None) and getattr(settings, "project_id", None)
        ]
        logger.info("management: scoped to %d project(s)", len(self._projects))
        return self._projects

    def project_dicts(self) -> List[ManagementProject]:
        """Projects the dashboard reports on (id, name, colour, code)."""
        return [
            ManagementProject(
                id=settings.project_id,
                name=getattr(settings, "project_name", None) or settings.project_id,
                color=PROJECT_PALETTE[index % len(PROJECT_PALETTE)],
                code=_project_code(getattr(settings, "project_name", "") or ""),
            )
            for index, settings in enumerate(self._load_projects())
        ]

    def _project_meta(self) -> Dict[str, ManagementProject]:
        return {project.id: project for project in self.project_dicts()}

    # -------------------------------------------------------------------------
    # Loading
    # -------------------------------------------------------------------------
    @staticmethod
    def _is_task(chat: Chat) -> bool:
        """
        Whether a chat should appear as a task.

        Templates are excluded; plain conversations only count when they carry
        some planning metadata (status / priority / due_date / assignees), which
        is the same rule the planning surface uses.
        """
        if chat.is_template:
            return False
        if (chat.mode or "chat") == "chat":
            return bool(
                (chat.status or "").strip()
                or (chat.priority or "").strip()
                or (chat.due_date or "").strip()
                or (chat.assignees or [])
            )
        return True

    @staticmethod
    def _decorate(chat: Chat, project: ManagementProject) -> ManagementTask:
        """Build the task projection with its derived flags."""
        today = date.today()

        status = (chat.status or "").strip().lower()
        if status not in STATUS_ORDER:
            status = "todo"

        priority = (chat.priority or "").strip().lower()
        if priority not in PRIORITY_ORDER:
            priority = "low"

        assignees = [str(assignee) for assignee in (chat.assignees or [])]
        due = _parse_date(chat.due_date)
        days_until_due = (due - today).days if due else None

        overdue = bool(due and days_until_due is not None
                       and days_until_due < 0 and status not in CLOSED_STATUSES)
        due_today = bool(due and days_until_due == 0 and status not in CLOSED_STATUSES)

        updated = _parse_timestamp(chat.updated_at)
        stale_days = (datetime.now() - updated).days if updated != datetime.min else 0
        stalled = (
            status == "doing"
            and updated != datetime.min
            and stale_days >= STALLED_AFTER_DAYS
        )

        blocked = status in BLOCKED_STATUSES
        block_reason = None
        blocked_since = None
        if blocked:
            blocked_since = _iso(chat.updated_at) or None
            block_reason = f"On hold for {stale_days} day{'s' if stale_days != 1 else ''}"

        reason = None
        if blocked:
            reason = "blocked"
        elif overdue:
            reason = "overdue"
        elif due_today:
            reason = "due_today"
        elif not assignees and priority == "high":
            reason = "unassigned_high"
        elif stalled:
            reason = "stalled"

        board = (chat.board or "").strip() or "—"

        return ManagementTask(
            id=chat.id or "",
            name=chat.name or "",
            description=chat.description,
            project_id=project.id,
            project_name=project.name,
            project_color=project.color,
            board=board,
            board_id=f"{project.id}::{board}",
            column=chat.column or chat.column_id or None,
            status=status,
            priority=priority,
            due_date=chat.due_date,
            progress=int(chat.progress or 0),
            assignees=assignees,
            assignee_names=list(assignees),
            assignees_info=[
                {"id": assignee, "name": assignee, "role": "",
                 "type": _person_type(assignee)}
                for assignee in assignees
            ],
            tags=list(chat.tags or []),
            created_at=_iso(chat.created_at),
            updated_at=_iso(chat.updated_at),
            days_until_due=days_until_due,
            overdue=overdue,
            due_today=due_today,
            unassigned=not assignees,
            blocked=blocked,
            block_reason=block_reason,
            blocked_since=blocked_since,
            attention_reason=reason,
        )

    def load_tasks(self) -> List[ManagementTask]:
        """Load and decorate every task of every scoped project."""
        meta = self._project_meta()
        tasks: List[ManagementTask] = []

        for settings in self._load_projects():
            project = meta.get(settings.project_id)
            if not project:
                continue
            try:
                chats = ChatManager(settings=settings).list_chats() or []
            except Exception as ex:  # noqa: BLE001 - one bad project must not win
                logger.warning(
                    "management: failed to list chats for '%s': %s",
                    project.name, ex,
                )
                continue
            for chat in chats:
                if not self._is_task(chat):
                    continue
                tasks.append(self._decorate(chat, project))

        logger.info("management: loaded %d task(s)", len(tasks))
        return tasks

    @staticmethod
    def window_tasks(tasks: List[ManagementTask], start: date, end: date) -> List[ManagementTask]:
        """
        Tasks inside the window: updated in it PLUS every unfinished task.

        A blocker must never disappear because it stopped moving.
        """
        return [
            task for task in tasks
            if _in_window(task.updated_at, start, end) or task.status not in CLOSED_STATUSES
        ]

    # -------------------------------------------------------------------------
    # Aggregations
    # -------------------------------------------------------------------------
    @staticmethod
    def build_metrics(tasks: List[ManagementTask]) -> ManagementMetrics:
        """Headline counters over the given tasks."""
        by_status: Dict[str, int] = {status: 0 for status in STATUS_ORDER}
        by_priority: Dict[str, int] = {priority: 0 for priority in PRIORITY_ORDER}

        done = active = on_hold = overdue = due_today = unassigned = blocked = 0
        for task in tasks:
            by_status[task.status] = by_status.get(task.status, 0) + 1
            by_priority[task.priority] = by_priority.get(task.priority, 0) + 1
            if task.status in CLOSED_STATUSES and task.status == "done":
                done += 1
            if task.status in ACTIVE_STATUSES:
                active += 1
            if task.status in BLOCKED_STATUSES:
                on_hold += 1
            if task.overdue:
                overdue += 1
            if task.due_today:
                due_today += 1
            if task.unassigned and task.status not in CLOSED_STATUSES:
                unassigned += 1
            if task.blocked:
                blocked += 1

        total = len(tasks)
        return ManagementMetrics(
            total=total,
            done=done,
            active=active,
            on_hold=on_hold,
            overdue=overdue,
            due_today=due_today,
            unassigned=unassigned,
            blocked=blocked,
            completion=round((done / total) * 100) if total else 0,
            by_status=by_status,
            by_priority=by_priority,
        )

    @staticmethod
    def build_board_progress(tasks: List[ManagementTask]) -> List[ManagementBoardProgress]:
        """Per-board progress breakdown."""
        buckets: Dict[str, List[ManagementTask]] = {}
        for task in tasks:
            buckets.setdefault(task.board_id or "—", []).append(task)

        items: List[ManagementBoardProgress] = []
        for board_id, rows in buckets.items():
            head = rows[0]
            done = sum(1 for task in rows if task.status == "done")
            total = len(rows)
            items.append(
                ManagementBoardProgress(
                    board_id=board_id,
                    board=head.board or "—",
                    project_id=head.project_id,
                    project_name=head.project_name,
                    type="sprint" if any(task.column == "sprint" for task in rows) else "kanban",
                    total=total,
                    done=done,
                    doing=sum(1 for task in rows if task.status == "doing"),
                    todo=sum(1 for task in rows if task.status == "todo"),
                    on_hold=sum(1 for task in rows if task.status == "onhold"),
                    blocked=sum(1 for task in rows if task.blocked),
                    percentage=round((done / total) * 100) if total else 0,
                    target_date=ManagementManager._max_due(rows),
                )
            )

        items.sort(key=lambda item: ((item.project_name or "").lower(), item.board.lower()))
        return items

    @staticmethod
    def _max_due(tasks: List[ManagementTask]) -> Optional[str]:
        """Latest committed due date among the given tasks."""
        dates = [parsed for parsed in (_parse_date(task.due_date) for task in tasks) if parsed]
        return max(dates).isoformat() if dates else None

    @staticmethod
    def build_attention(tasks: List[ManagementTask]) -> List[ManagementAttentionItem]:
        """Attention queue, most severe first."""
        items = [
            ManagementAttentionItem(
                task=task,
                reason=task.attention_reason,
                severity=SEVERITY.get(task.attention_reason, 0.0),
            )
            for task in tasks
            if task.attention_reason
        ]
        items.sort(
            key=lambda item: (
                item.severity,
                abs(item.task.days_until_due or 0),
            ),
            reverse=True,
        )
        return items[:ATTENTION_LIMIT]

    def build_activity(self, tasks: List[ManagementTask]) -> List[ManagementActivity]:
        """
        Activity feed.

        Prefers the real, event-sourced planning trail
        (``<codx_path>/planning/events.jsonl``) and falls back to a projection of
        the task state when no project has recorded events yet.
        """
        task_ids = {task.id for task in tasks}
        events: List[ManagementActivity] = []
        meta = self._project_meta()

        for settings in self._load_projects():
            file_path = f"{getattr(settings, 'codx_path', '')}/planning/events.jsonl"
            if not os.path.isfile(file_path):
                continue  # do not create the folder as a side effect
            project = meta.get(settings.project_id)
            try:
                for event in PlanningEventStore(settings.codx_path).read():
                    if task_ids and event.target_task_id not in task_ids:
                        continue
                    events.append(
                        ManagementActivity(
                            id=event.id,
                            actor=event.actor,
                            actor_type=event.actor_type,
                            action=event.action,
                            tone=event.tone,
                            task_id=event.target_task_id,
                            task_name=event.target_task_name,
                            board=event.board,
                            project_id=project.id if project else None,
                            project_name=project.name if project else None,
                            field=event.field,
                            from_value=event.from_value,
                            to_value=event.to_value,
                            timestamp=event.timestamp,
                        )
                    )
            except Exception as ex:  # noqa: BLE001 - a corrupt log must not break the page
                logger.warning("management: failed to read planning events: %s", ex)

        if not events:
            events = self._synthesize_activity(tasks)

        events.sort(key=lambda event: _parse_timestamp(event.timestamp), reverse=True)
        return events[:ACTIVITY_LIMIT]

    @staticmethod
    def _synthesize_activity(tasks: List[ManagementTask]) -> List[ManagementActivity]:
        """Project the latest task updates as activity when no event log exists."""
        ordered = sorted(tasks, key=lambda task: _parse_timestamp(task.updated_at), reverse=True)
        feed: List[ManagementActivity] = []
        for task in ordered[:ACTIVITY_LIMIT]:
            action, tone = "updated", "info"
            if task.blocked:
                action, tone = "flagged as blocked", "error"
            elif task.status == "done":
                action, tone = "completed", "success"
            elif task.status == "doing":
                action, tone = "moved to In progress", "primary"
            elif task.status == "onhold":
                action, tone = "put on hold", "warning"
            feed.append(
                ManagementActivity(
                    id=f"{task.id}-{task.updated_at}",
                    actor=(task.assignees[0] if task.assignees else "Unassigned"),
                    actor_type=_person_type(task.assignees[0]) if task.assignees else "user",
                    action=action,
                    tone=tone,
                    task_id=task.id,
                    task_name=task.name,
                    board=task.board,
                    project_id=task.project_id,
                    project_name=task.project_name,
                    timestamp=task.updated_at,
                )
            )
        return feed

    def build_dashboard(self, tasks: List[ManagementTask]) -> ManagementDashboard:
        """Metrics + board progress + attention + activity for the given tasks."""
        metrics = self.build_metrics(tasks)
        return ManagementDashboard(
            metrics=metrics,
            board_progress=self.build_board_progress(tasks),
            attention=self.build_attention(tasks),
            activity=self.build_activity(tasks),
            priority_counts=metrics.by_priority,
            generated_at=_now_iso(),
        )

    # -------------------------------------------------------------------------
    # Delivery
    # -------------------------------------------------------------------------
    def build_forecast(
        self, all_tasks: List[ManagementTask], start: date, end: date
    ) -> List[ManagementForecast]:
        """
        Forecast per board.

        Counts come from ALL tasks of the board; the *velocity* comes from the
        selected window (delivered tasks per week), which is what the ETA is
        based on.
        """
        weeks = max(1.0, ((end - start).days + 1) / 7.0)
        buckets: Dict[str, List[ManagementTask]] = {}
        for task in all_tasks:
            buckets.setdefault(task.board_id or "—", []).append(task)

        forecast: List[ManagementForecast] = []
        for board_id, rows in buckets.items():
            head = rows[0]
            total = len(rows)
            done_rows = [task for task in rows if task.status == "done"]
            remaining = total - len(done_rows)
            done_in_window = sum(
                1 for task in done_rows if _in_window(task.updated_at, start, end)
            )
            velocity = round(max(done_in_window / weeks, 0.2), 1)
            eta_days = int(round((remaining / velocity) * 7)) if remaining else 0
            eta_date = date.today() + timedelta(days=eta_days)

            target = _parse_date(self._max_due(rows))
            blocked = sum(1 for task in rows if task.blocked)
            # Sprint boards (any task declares sprint membership) demo on target.
            is_sprint = any(task.column == "sprint" for task in rows)

            status, confidence = "on_track", "high"
            if blocked:
                status, confidence = "at_risk", "low"
            if target:
                left = (target - date.today()).days
                if eta_date > target:
                    status = "late" if left < 0 else "at_risk"
                    confidence = "low" if left < 0 else "medium"

            forecast.append(
                ManagementForecast(
                    board_id=board_id,
                    board=head.board or "—",
                    project_id=head.project_id,
                    project_name=head.project_name,
                    type="sprint" if is_sprint else "kanban",
                    committed=total,
                    done=len(done_rows),
                    remaining=remaining,
                    velocity=velocity,
                    eta_date=eta_date.isoformat(),
                    eta_days=eta_days,
                    target_date=target.isoformat() if target else None,
                    demo_date=target.isoformat() if (is_sprint and target) else None,
                    percentage=round((len(done_rows) / total) * 100) if total else 0,
                    blocked=blocked,
                    confidence=confidence,
                    status=status,
                )
            )

        forecast.sort(key=lambda item: ((item.project_name or "").lower(), item.board.lower()))
        return forecast

    @staticmethod
    def build_burndown(
        board_id: Optional[str], all_tasks: List[ManagementTask]
    ) -> ManagementBurndown:
        """Burndown of one board over the last ``BURNDOWN_DAYS`` days."""
        candidates = [task for task in all_tasks if task.board_id == board_id] if board_id else []
        if not candidates:
            first_board = all_tasks[0].board_id if all_tasks else None
            candidates = [task for task in all_tasks if task.board_id == first_board]

        if not candidates:
            return ManagementBurndown()

        total = len(candidates)
        points: List[ManagementBurndownPoint] = []
        divisor = max(1, BURNDOWN_DAYS - 1)

        for index in range(BURNDOWN_DAYS):
            day = date.today() - timedelta(days=BURNDOWN_DAYS - 1 - index)
            completed = 0
            for task in candidates:
                if task.status != "done":
                    continue
                parsed = _parse_timestamp(task.updated_at)
                if parsed != datetime.min and parsed.date() <= day:
                    completed += 1
            points.append(
                ManagementBurndownPoint(
                    date=day.isoformat(),
                    ideal=max(0, round(total - (total / divisor) * index)),
                    actual=max(0, total - completed),
                )
            )

        return ManagementBurndown(
            board_id=candidates[0].board_id or "",
            board=candidates[0].board or "",
            total=total,
            points=points,
        )

    # -------------------------------------------------------------------------
    # Team
    # -------------------------------------------------------------------------
    def build_team_load(
        self,
        all_tasks: List[ManagementTask],
        window: List[ManagementTask],
        start: date,
        end: date,
    ) -> List[ManagementPerson]:
        """Capacity and workload per assignee (humans and AI agents)."""
        try:
            usage_by_user = self.analytics.get_usage_by_user(
                start_date=start.isoformat(), end_date=end.isoformat()
            )
        except Exception as ex:  # noqa: BLE001 - analytics is optional
            logger.warning("management: usage by user failed: %s", ex)
            usage_by_user = {}

        identifiers: Dict[str, Dict[str, Any]] = {}
        for task in all_tasks:
            for assignee in task.assignees:
                entry = identifiers.setdefault(
                    assignee,
                    {"project_ids": set(), "last_active": None},
                )
                if task.project_id:
                    entry["project_ids"].add(task.project_id)
                if task.updated_at and (
                    entry["last_active"] is None or task.updated_at > entry["last_active"]
                ):
                    entry["last_active"] = task.updated_at

        people: List[ManagementPerson] = []
        for username, extra in identifiers.items():
            mine = [task for task in window if username in task.assignees]
            active = [task for task in mine if task.status in ACTIVE_STATUSES]
            hours = len(active) * HOURS_PER_TASK
            load = min(100, round((len(active) / CAPACITY_TASKS) * 100)) if CAPACITY_TASKS else 0
            usage = usage_by_user.get(username, {})
            people.append(
                ManagementPerson(
                    id=username,
                    name=username,
                    role="AI agent" if _person_type(username) == "agent" else "Team member",
                    type=_person_type(username),
                    capacity_h=CAPACITY_TASKS * HOURS_PER_TASK,
                    hours=hours,
                    load_pct=load,
                    active=len(active),
                    blocked=sum(1 for task in mine if task.blocked),
                    done=sum(1 for task in mine if task.status == "done"),
                    overdue=sum(1 for task in mine if task.overdue),
                    cost_cxjcoins=round(float(usage.get("total_cxjcoins") or 0), 2),
                    project_ids=sorted(pid for pid in extra["project_ids"] if pid),
                    last_active=extra["last_active"],
                )
            )

        people.sort(key=lambda person: person.load_pct, reverse=True)
        return people

    # -------------------------------------------------------------------------
    # Cost
    # -------------------------------------------------------------------------
    def build_cost(
        self,
        start: date,
        end: date,
        project_id: Optional[str] = None,
        model: Optional[str] = None,
        projects: Optional[List[ManagementProject]] = None,
    ) -> ManagementCost:
        """
        AI consumption payload, read from the real analytics store.

        ``project_id`` is translated to ``project_name`` for the analytics calls
        that only filter by name (daily series and by-model grouping).
        """
        projects = projects if projects is not None else self.project_dicts()
        project_name = next(
            (project.name for project in projects if project.id == project_id), None
        )
        start_s, end_s = start.isoformat(), end.isoformat()

        empty = {
            "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            "calls": 0, "total_duration_seconds": 0.0,
            "total_cxjcoins": 0.0, "tokens_from_provider": False,
        }

        try:
            total = self.analytics.get_total_usage(
                start_date=start_s, end_date=end_s,
                project_id=project_id, project_name=project_name, model=model,
            )
            daily = self.analytics.get_daily_usage(
                start_date=start_s, end_date=end_s,
                project_name=project_name, grouping="day",
            )
            by_model = self.analytics.get_usage_by_model(
                start_date=start_s, end_date=end_s, project_name=project_name,
            )
            by_user = self.analytics.get_usage_by_user(
                start_date=start_s, end_date=end_s, project_id=project_id,
            )
            by_project = self.analytics.get_usage_by_project(
                start_date=start_s, end_date=end_s,
            )
        except Exception as ex:  # noqa: BLE001 - an empty store must render zeros
            logger.warning("management: analytics aggregation failed: %s", ex)
            total, daily, by_model, by_user, by_project = dict(empty), [], {}, {}, {}

        if project_name and by_project:
            by_project = {project_name: by_project[project_name]} if project_name in by_project else {}

        delivered = 0
        try:
            delivered = sum(
                1 for task in self.load_tasks()
                if task.status == "done" and _in_window(task.updated_at, start, end)
                and (not project_id or task.project_id == project_id)
            )
        except Exception as ex:  # noqa: BLE001
            logger.warning("management: delivered task count failed: %s", ex)

        total = dict(total or empty)
        total["delivered_tasks"] = delivered
        total["cost_per_delivered_task"] = (
            round(float(total.get("total_cxjcoins") or 0) / delivered, 2) if delivered else None
        )

        spent = float(total.get("total_cxjcoins") or 0)
        days = max(1, (end - start).days + 1)
        projected = round((spent / days) * 7)
        share = round(DEFAULT_WEEKLY_BUDGET / max(1, len(projects)))

        per_project: List[ManagementBudgetProject] = []
        for project in projects:
            project_spent = 0.0
            if project.name in by_project:
                project_spent = float(by_project[project.name].get("total_cxjcoins") or 0)
            per_project.append(
                ManagementBudgetProject(
                    project_id=project.id,
                    project_name=project.name,
                    color=project.color,
                    budget=share,
                    spent=round(project_spent, 2),
                    pct=round((project_spent / share) * 100) if share else 0,
                )
            )

        return ManagementCost(
            total=total,
            daily=daily,
            by_project=by_project,
            by_model=by_model,
            by_user=by_user,
            budget=ManagementBudget(
                weekly_budget=DEFAULT_WEEKLY_BUDGET,
                spent=round(spent, 2),
                remaining=round(DEFAULT_WEEKLY_BUDGET - projected, 2),
                projected=projected,
                pct=round((projected / DEFAULT_WEEKLY_BUDGET) * 100) if DEFAULT_WEEKLY_BUDGET else 0,
                per_project=per_project,
            ),
            models=sorted(by_model.keys()),
            projects=projects,
            people=self.build_team_load(self.load_tasks(),
                                        self.window_tasks(self.load_tasks(), start, end),
                                        start, end),
            generated_at=_now_iso(),
        )

    # -------------------------------------------------------------------------
    # Section payloads
    # -------------------------------------------------------------------------
    def overview(self, from_value: Optional[str], to_value: Optional[str]) -> ManagementOverview:
        """Everything the Pulse section draws, in one round trip."""
        start, end = _resolve_range(from_value, to_value)
        projects = self.project_dicts()
        all_tasks = self.load_tasks()
        window = self.window_tasks(all_tasks, start, end)

        return ManagementOverview(
            range={"from": start.isoformat(), "to": end.isoformat()},
            projects=projects,
            dashboard=self.build_dashboard(window),
            forecast=self.build_forecast(all_tasks, start, end),
            team_load=self.build_team_load(all_tasks, window, start, end),
            cost=self.build_cost(start, end, projects=projects),
        )

    def blockers(self, from_value: Optional[str], to_value: Optional[str],
                 project_id: Optional[str] = None) -> ManagementBlockersResponse:
        """Attention queue, optionally scoped to one project."""
        start, end = _resolve_range(from_value, to_value)
        window = self.window_tasks(self.load_tasks(), start, end)
        if project_id:
            window = [task for task in window if task.project_id == project_id]
        return ManagementBlockersResponse(
            range={"from": start.isoformat(), "to": end.isoformat()},
            dashboard=self.build_dashboard(window),
            projects=self.project_dicts(),
        )

    def delivery(self, from_value: Optional[str], to_value: Optional[str],
                 board_id: Optional[str] = None) -> ManagementDeliveryResponse:
        """Forecast per board plus the burndown of the selected one."""
        start, end = _resolve_range(from_value, to_value)
        all_tasks = self.load_tasks()
        return ManagementDeliveryResponse(
            range={"from": start.isoformat(), "to": end.isoformat()},
            forecast=self.build_forecast(all_tasks, start, end),
            burndown=self.build_burndown(board_id, all_tasks),
            projects=self.project_dicts(),
        )

    def team_load(self, from_value: Optional[str], to_value: Optional[str]) -> ManagementTeamResponse:
        """Capacity and workload per assignee."""
        start, end = _resolve_range(from_value, to_value)
        all_tasks = self.load_tasks()
        window = self.window_tasks(all_tasks, start, end)
        return ManagementTeamResponse(
            range={"from": start.isoformat(), "to": end.isoformat()},
            team_load=self.build_team_load(all_tasks, window, start, end),
            tasks=window,
            projects=self.project_dicts(),
        )

    def cost(self, from_value: Optional[str], to_value: Optional[str],
             project_id: Optional[str] = None,
             model: Optional[str] = None) -> ManagementCostResponse:
        """AI consumption and budget for the window."""
        start, end = _resolve_range(from_value, to_value)
        projects = self.project_dicts()
        payload = self.build_cost(start, end, project_id=project_id, model=model, projects=projects)
        return ManagementCostResponse(
            range={"from": start.isoformat(), "to": end.isoformat()},
            models=payload.models,
            total=payload.total,
            daily=payload.daily,
            by_project=payload.by_project,
            by_model=payload.by_model,
            by_user=payload.by_user,
            budget=payload.budget,
            projects=payload.projects,
            people=payload.people,
            generated_at=payload.generated_at,
        )

    def tasks(self, request: ManagementTaskQueryRequest) -> ManagementTaskQueryResponse:
        """Filtered, sorted and paginated task rows across every project."""
        start, end = _resolve_range(request.from_, request.to)
        rows = self.window_tasks(self.load_tasks(), start, end)

        if request.project_id:
            rows = [task for task in rows if task.project_id == request.project_id]
        if request.board_id:
            rows = [task for task in rows if task.board_id == request.board_id]
        if request.statuses:
            rows = [task for task in rows if task.status in request.statuses]
        if request.priorities:
            rows = [task for task in rows if task.priority in request.priorities]
        if request.assignees:
            wanted = set(request.assignees)
            rows = [task for task in rows if wanted.intersection(task.assignees)]
        if request.search:
            needle = request.search.lower().strip()
            rows = [
                task for task in rows
                if needle in f"{task.name} {task.description or ''} {task.board or ''} {' '.join(task.tags)}".lower()
            ]

        reverse = (request.sort.dir or "asc").lower() == "desc"
        sort_field = request.sort.field or "priority"
        if sort_field == "priority":
            rows.sort(key=lambda task: PRIORITY_ORDER.index(task.priority), reverse=reverse)
        elif sort_field == "due_date":
            rows.sort(key=lambda task: (_parse_date(task.due_date) or date.max), reverse=reverse)
        elif sort_field == "status":
            rows.sort(key=lambda task: task.status, reverse=reverse)
        elif sort_field == "name":
            rows.sort(key=lambda task: (task.name or "").lower(), reverse=reverse)
        elif sort_field == "project":
            rows.sort(key=lambda task: (task.project_name or "").lower(), reverse=reverse)
        else:  # updated_at
            rows.sort(key=lambda task: _parse_timestamp(task.updated_at), reverse=reverse)

        total = len(rows)
        page_size = max(1, min(100, request.page_size))
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = min(max(1, request.page), total_pages)
        start_index = (page - 1) * page_size

        return ManagementTaskQueryResponse(
            tasks=rows[start_index:start_index + page_size],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
            group_counts=[
                {"key": status, "label": status, "total": sum(1 for task in rows if task.status == status)}
                for status in STATUS_ORDER
            ],
            boards=[
                {"id": board_id, "name": board_id.split("::", 1)[-1]}
                for board_id in sorted({task.board_id for task in rows if task.board_id})
            ],
            projects=self.project_dicts(),
            people=self.build_team_load(self.load_tasks(), rows, start, end),
            generated_at=_now_iso(),
        )

    # -------------------------------------------------------------------------
    # Writes
    # -------------------------------------------------------------------------
    def _find_chat(self, task_id: str) -> Tuple[Optional[Chat], Optional[Any]]:
        """Locate a chat and the project settings that own it."""
        for settings in self._load_projects():
            try:
                chat = ChatManager(settings=settings).find_by_id(chat_id=task_id)
            except Exception as ex:  # noqa: BLE001 - keep looking in other projects
                logger.debug("management: find_by_id failed for %s: %s", task_id, ex)
                continue
            if chat:
                return chat, settings
        return None, None

    def update_task(self, task_id: str, update: ManagementTaskUpdate) -> ManagementTask:
        """
        Apply a partial task update in the project that owns the chat.

        ``blocked`` is translated to a status change because ``Chat`` has no
        blocked field.
        """
        chat, settings = self._find_chat(task_id)
        if not chat:
            raise ValueError(f"Task not found: {task_id}")

        data = update.model_dump(exclude_unset=True)
        blocked = data.pop("blocked", None)
        if blocked is not None:
            if blocked:
                data["status"] = "onhold"
            elif (chat.status or "").strip().lower() == "onhold":
                data["status"] = "doing"

        for field, value in data.items():
            if field == "due_date" and value == "":
                value = None
            elif value is None:
                continue
            if getattr(chat, field, None) != value:
                setattr(chat, field, value)

        if (chat.status or "").strip().lower() == "done":
            chat.progress = 100

        saved = ChatManager(settings=settings).save_chat(chat=chat, chat_only=True)
        logger.info(
            "management.update_task: task=%s project=%s fields=%s",
            task_id,
            getattr(settings, "project_name", "?"),
            list(data.keys()) + (["blocked"] if blocked is not None else []),
        )

        project = self._project_meta().get(settings.project_id) or ManagementProject(
            id=settings.project_id,
            name=getattr(settings, "project_name", settings.project_id),
        )
        return self._decorate(saved or chat, project)

    # -------------------------------------------------------------------------
    # Assistant
    # -------------------------------------------------------------------------
    def ask(self, question: str, from_value: Optional[str],
            to_value: Optional[str]) -> ManagementAssistantResponse:
        """Answer a question from the numbers this manager already computes."""
        start, end = _resolve_range(from_value, to_value)
        text = (question or "").lower()

        all_tasks = self.load_tasks()
        window = self.window_tasks(all_tasks, start, end)
        attention = self.build_attention(window)
        metrics = self.build_metrics(window)

        def label(task: ManagementTask) -> str:
            owner = task.assignees[0] if task.assignees else "unassigned"
            return f"{task.name} — {task.project_name} · {owner}"

        if "block" in text or "stuck" in text or "stopp" in text or "risk" in text:
            blocked = [item for item in attention if item.reason == "blocked"]
            if not blocked:
                return ManagementAssistantResponse(
                    answer=(
                        f"Nothing is on hold in this window. {len(attention)} task(s) still need "
                        "attention (overdue, due today or unowned)."
                    ),
                    sources=[ManagementAssistantSource(section="blockers", label="Blockers")],
                )
            lines = "\n".join(
                f"• {label(item.task)} — {item.task.block_reason} ({item.task.updated_at[:10]})"
                for item in blocked[:5]
            )
            return ManagementAssistantResponse(
                answer=f"{len(blocked)} task(s) are on hold:\n{lines}",
                sources=[
                    ManagementAssistantSource(section="blockers", label="Blockers"),
                    ManagementAssistantSource(section="work", label="Work"),
                ],
            )

        if any(word in text for word in ("cost", "spend", "budget", "token", "model", "consum")):
            cost = self.build_cost(start, end)
            by_project = sorted(
                cost.by_project.items(),
                key=lambda entry: float(entry[1].get("total_cxjcoins") or 0),
                reverse=True,
            )
            top = by_project[0] if by_project else None
            used = cost.total.get("cost_per_delivered_task")
            return ManagementAssistantResponse(
                answer=(
                    f"In this window the platform burned "
                    f"{float(cost.total.get('total_cxjcoins') or 0):.1f} cx over "
                    f"{int(cost.total.get('calls') or 0)} calls "
                    f"({int(cost.total.get('total_tokens') or 0)} tokens).\n"
                    f"• Biggest project: {top[0]} with {float(top[1].get('total_cxjcoins') or 0):.1f} cx\n"
                    if top else "No AI usage recorded in this window.\n"
                ) + (
                    f"• Projected week: {cost.budget.projected:.0f} cx against a "
                    f"{cost.budget.weekly_budget:.0f} cx budget ({cost.budget.pct}%)\n"
                    f"• Cost per delivered task: "
                    f"{f'{used:.2f} cx' if used is not None else 'n/a'}"
                ),
                sources=[ManagementAssistantSource(section="cost", label="Cost & AI")],
            )

        if any(word in text for word in ("who", "team", "load", "capacity", "overload", "busy")):
            people = [person for person in self.build_team_load(all_tasks, window, start, end)
                      if person.type == "human"]
            hot = [person for person in people if person.load_pct >= 85]
            lines = "\n".join(
                f"• {person.name} — {person.load_pct}% load · {person.active} active · "
                f"{person.blocked} blocked"
                for person in people[:4]
            )
            return ManagementAssistantResponse(
                answer=(
                    f"{len(hot)} people are above 85% load.\n{lines}" if hot
                    else f"Nobody is above 85% load.\n{lines}"
                ),
                sources=[ManagementAssistantSource(section="team", label="Team")],
            )

        if any(word in text for word in ("ship", "deliver", "forecast", "when", "eta", "demo")):
            forecast = self.build_forecast(all_tasks, start, end)
            demos = sorted(
                [board for board in forecast if board.demo_date],
                key=lambda board: board.demo_date,
            )
            risk = [board for board in forecast if board.status != "on_track"]
            lines = "\n".join(
                f"• {board.board} — demo {board.demo_date} · {board.done}/{board.committed} done · "
                f"{board.status.replace('_', ' ')}"
                for board in demos
            ) or "• none scheduled"
            return ManagementAssistantResponse(
                answer=(
                    f"Next demos:\n{lines}\n" + (
                        f"{len(risk)} board(s) at risk: "
                        f"{', '.join(board.board for board in risk)}."
                        if risk else "All boards are on track."
                    )
                ),
                sources=[ManagementAssistantSource(section="delivery", label="Delivery")],
            )

        if any(word in text for word in ("overdue", "late", "behind")):
            late = [item for item in attention if item.reason == "overdue"]
            if not late:
                return ManagementAssistantResponse(
                    answer="Nothing is overdue in this window.",
                    sources=[ManagementAssistantSource(section="blockers", label="Blockers")],
                )
            lines = "\n".join(
                f"• {label(item.task)} — {abs(item.task.days_until_due or 0)}d late"
                for item in late[:6]
            )
            return ManagementAssistantResponse(
                answer=f"{len(late)} overdue task(s):\n{lines}",
                sources=[ManagementAssistantSource(section="blockers", label="Blockers")],
            )

        if any(word in text for word in ("done", "finish", "completed", "delivered")):
            done = [task for task in window if task.status == "done"]
            lines = "\n".join(f"• {label(task)}" for task in done[:6]) or "• nothing yet"
            return ManagementAssistantResponse(
                answer=f"{len(done)} task(s) completed in this window:\n{lines}",
                sources=[ManagementAssistantSource(section="work", label="Work")],
            )

        cost = self.build_cost(start, end)
        return ManagementAssistantResponse(
            answer=(
                f"State of play for this window:\n"
                f"• {metrics.active} active, {metrics.blocked} blocked, {metrics.overdue} overdue\n"
                f"• {metrics.done} completed ({metrics.completion}% of everything in scope)\n"
                f"• AI spend {float(cost.total.get('total_cxjcoins') or 0):.1f} cx\n\n"
                "Ask me about blockers, costs, team load, what ships next, or what we finished."
            ),
            sources=[ManagementAssistantSource(section="pulse", label="Pulse")],
        )


# Made with ❤️ by codx-junior