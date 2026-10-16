"""
Planning domain models.

Shared request/response models for the ``/api/planning/*`` surface. They are
consumed by:

    * ``POST  /api/planning/tasks/query``    -> PlanningTaskQueryResponse
    * ``POST  /api/planning/dashboard``       -> PlanningDashboardResponse
    * ``GET   /api/planning/activity``        -> List[ActivityEvent]
    * ``PATCH /api/planning/tasks/{task_id}`` -> PlanningTaskUpdateResponse
    * ``POST  /api/planning/tasks/reorder``   -> PlanningReorderResponse

All dataset-wide aggregation, filtering and sorting is performed by
:class:`codx.junior.planning_manager.PlanningManager`, so the numbers the UI
renders are always computed over the *entire* filtered dataset instead of a
single loaded page.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanningRange(BaseModel):
    """
    Date window applied to a configurable field.

    ``from`` is a reserved Python keyword, so the attribute is named ``from_``
    while the JSON alias stays ``from`` for clients (and the JS
    ``PlanningQuery`` model). ``populate_by_name`` keeps ``from_`` accepted too.
    """
    model_config = ConfigDict(populate_by_name=True)

    field: str = Field(
        default="updated_at",
        description="Which date the range applies to: updated_at | due_date | created_at",
    )
    from_: Optional[str] = Field(
        default=None, alias="from", description="Inclusive YYYY-MM-DD"
    )
    to: Optional[str] = Field(
        default=None, description="Inclusive YYYY-MM-DD"
    )


class PlanningSort(BaseModel):
    """Sort configuration applied server-side before pagination."""
    field: str = Field(
        default="priority",
        description="sort_index | priority | due_date | updated_at",
    )
    dir: str = Field(default="asc", description="asc | desc")


class PlanningQuery(BaseModel):
    """Shared request for the planning list and the follow-up dashboard."""
    range: Optional[PlanningRange] = Field(default=None)
    boards: Optional[List[str]] = Field(default=None)
    assignees: Optional[List[str]] = Field(default=None)
    priorities: Optional[List[str]] = Field(default=None)
    statuses: Optional[List[str]] = Field(default=None)
    search: Optional[str] = Field(default=None)
    attention_only: bool = Field(default=False)
    include_done: bool = Field(default=True)
    include_templates: bool = Field(default=False)
    project_ids: Optional[List[str]] = Field(default=None)
    group_by: Optional[str] = Field(
        default="priority", description="priority | status | board | None"
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    sort: PlanningSort = Field(default_factory=PlanningSort)


class PlanningTask(BaseModel):
    """A single task row with server-computed derived flags."""
    id: str
    name: str = ""
    description: Optional[str] = None
    board: Optional[str] = None
    column: Optional[str] = None
    status: str = "todo"
    priority: str = "low"
    due_date: Optional[str] = None
    progress: int = 0
    assignees: List[str] = Field(default_factory=list)
    users: List[str] = Field(default_factory=list)
    sort_index: Optional[int] = None
    project_id: Optional[str] = None
    owner_project_id: Optional[str] = None
    mode: str = "task"
    created_at: str = ""
    updated_at: str = ""

    # ── Server-computed derived flags (single source of truth for dates) ──
    overdue: bool = False
    due_today: bool = False
    days_until_due: Optional[int] = None
    unassigned: bool = False
    attention_reason: Optional[str] = Field(
        default=None,
        description="overdue | due_today | unassigned_high | stalled | None",
    )


class PlanningGroupCount(BaseModel):
    """True count of tasks per group (priority/status/board)."""
    key: str
    label: str
    total: int
    loaded_window: Optional[int] = None


class PlanningTaskQueryResponse(BaseModel):
    """Paginated task rows plus dataset-wide counts."""
    tasks: List[PlanningTask]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    group_counts: List[PlanningGroupCount]
    applied_filters: Dict[str, Any]
    generated_at: str


class PlanningMetrics(BaseModel):
    """Dashboard headline metrics computed over the whole filtered dataset."""
    total: int
    done: int
    active: int
    on_hold: int
    rejected: int
    overdue: int
    due_today: int
    unassigned: int
    completion: int
    by_priority: Dict[str, int]
    by_status: Dict[str, int]


class BoardProgressItem(BaseModel):
    """Per-board progress breakdown."""
    board: str
    total: int
    done: int
    doing: int
    todo: int
    on_hold: int
    overdue: int
    unassigned: int
    percentage: int


class AttentionItem(BaseModel):
    """A task that needs attention, ordered by server-computed severity."""
    task: PlanningTask
    reason: str
    severity: int


class ActivityEvent(BaseModel):
    """A single, event-sourced task change."""
    id: str
    actor: str
    actor_type: str = "user"
    action: str
    target_task_id: str
    target_task_name: str = ""
    board: Optional[str] = None
    field: Optional[str] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    timestamp: str = ""
    tone: str = "info"


class PlanningDashboardResponse(BaseModel):
    """Everything the follow-up view renders, from a single request."""
    metrics: PlanningMetrics
    board_progress: List[BoardProgressItem]
    attention: List[AttentionItem]
    activity: List[ActivityEvent]
    priority_counts: Dict[str, int]
    generated_at: str


class PlanningTaskUpdate(BaseModel):
    """Partial update for a single task."""
    priority: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    assignees: Optional[List[str]] = None
    sort_index: Optional[int] = None
    expected_updated_at: Optional[str] = Field(
        default=None,
        description="Optimistic concurrency: reject if the stored updated_at differs",
    )


class PlanningReorderRequest(BaseModel):
    """Bulk manual reordering request."""
    board: Optional[str] = None
    priority: Optional[str] = None
    ordered_ids: List[str] = Field(
        description="New order; server assigns sort_index = position"
    )


class PlanningTaskUpdateResponse(BaseModel):
    """Result of PATCH /planning/tasks/{task_id}."""
    task: PlanningTask
    activity_event: Optional[ActivityEvent] = None


class PlanningReorderResponse(BaseModel):
    """Result of POST /planning/tasks/reorder."""
    updated: int
    activity_events: List[ActivityEvent] = Field(default_factory=list)


# Made with ❤️ by codx-junior