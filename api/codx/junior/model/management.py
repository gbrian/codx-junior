"""
Management dashboard domain models.

Shared request/response models for the ``/api/management/*`` surface, consumed
by the client "Team Command Center" screen (management view across every
project):

    * ``GET   /api/management/overview``     -> ManagementOverview
    * ``POST  /api/management/tasks/query``  -> ManagementTaskQueryResponse
    * ``GET   /api/management/blockers``     -> ManagementBlockersResponse
    * ``GET   /api/management/delivery``     -> ManagementDeliveryResponse
    * ``GET   /api/management/team-load``    -> ManagementTeamResponse
    * ``GET   /api/management/cost``         -> ManagementCostResponse
    * ``PATCH /api/management/tasks/{id}``   -> ManagementTaskUpdateResponse
    * ``POST  /api/management/assistant``    -> ManagementAssistantResponse

Every aggregation is computed server-side by
:class:`codx.junior.management_manager.ManagementManager` over the *whole*
filtered dataset, so the numbers the UI renders are never a client-side
reduction over a single page.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Reference data ─────────────────────────────────────────────────────────────


class ManagementProject(BaseModel):
    """A project the dashboard reports on."""

    id: str = Field(description="Project id")
    name: str = Field(default="", description="Project display name")
    color: str = Field(default="#e2419f", description="Stable colour used by the UI")
    code: Optional[str] = Field(default=None, description="Short code (max 3 chars)")


class ManagementPerson(BaseModel):
    """
    A team member: a human (a task assignee) or an AI agent.

    ``Chat`` has no estimate or capacity field, so capacity is measured in
    *active tasks*: see ``CAPACITY_TASKS`` in the management manager.
    """

    id: str = Field(description="Username / assignee id")
    name: str = Field(default="", description="Display name")
    role: str = Field(default="Team member")
    type: str = Field(default="human", description="human | agent")
    capacity_h: Optional[int] = Field(default=None, description="Capacity in hours")
    hours: int = Field(default=0, description="Allocated hours (tasks x HOURS_PER_TASK)")
    load_pct: int = Field(default=0, description="Load percentage (0-100+)")
    active: int = Field(default=0, description="Open tasks in the window")
    blocked: int = Field(default=0, description="On-hold tasks in the window")
    done: int = Field(default=0, description="Completed tasks in the window")
    overdue: int = Field(default=0, description="Overdue tasks in the window")
    cost_cxjcoins: float = Field(default=0.0, description="AI cost attributed to the user")
    project_ids: List[str] = Field(default_factory=list)
    last_active: Optional[str] = Field(default=None, description="Last task update (ISO)")


# ── Tasks ──────────────────────────────────────────────────────────────────────


class ManagementTask(BaseModel):
    """
    A task row with the derived flags the dashboard renders.

    Derived flags are computed once on the server so the client never has to
    re-derive "is this late" from a date string.
    """

    id: str
    name: str = Field(default="")
    description: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    project_color: Optional[str] = None
    board: Optional[str] = Field(default=None, description="Board title")
    board_id: Optional[str] = Field(
        default=None, description="Stable board identity: '<project_id>::<board>'"
    )
    column: Optional[str] = None
    status: str = Field(default="todo")
    priority: str = Field(default="low")
    due_date: Optional[str] = None
    progress: int = Field(default=0)
    assignees: List[str] = Field(default_factory=list)
    assignee_names: List[str] = Field(default_factory=list)
    assignees_info: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_at: str = Field(default="")
    updated_at: str = Field(default="")

    # ── Server-computed derived flags ─────────────────────────────────────
    days_until_due: Optional[int] = None
    overdue: bool = False
    due_today: bool = False
    unassigned: bool = False
    blocked: bool = Field(
        default=False,
        description="Task is on hold (Chat has no explicit blocked flag)",
    )
    block_reason: Optional[str] = None
    blocked_since: Optional[str] = None
    attention_reason: Optional[str] = Field(
        default=None,
        description="blocked | overdue | due_today | unassigned_high | stalled | None",
    )


class ManagementMetrics(BaseModel):
    """Headline counters computed over the whole filtered dataset."""

    total: int = 0
    done: int = 0
    active: int = 0
    on_hold: int = 0
    overdue: int = 0
    due_today: int = 0
    unassigned: int = 0
    blocked: int = 0
    completion: int = 0
    by_status: Dict[str, int] = Field(default_factory=dict)
    by_priority: Dict[str, int] = Field(default_factory=dict)


class ManagementBoardProgress(BaseModel):
    """Per-board progress breakdown."""

    board_id: str
    board: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    type: str = Field(default="kanban", description="kanban | sprint")
    total: int = 0
    done: int = 0
    doing: int = 0
    todo: int = 0
    on_hold: int = 0
    blocked: int = 0
    percentage: int = 0
    target_date: Optional[str] = None
    demo_date: Optional[str] = None


class ManagementAttentionItem(BaseModel):
    """A task that needs attention, ordered by server-computed severity."""

    task: ManagementTask
    reason: str
    severity: float = 0.0


class ManagementActivity(BaseModel):
    """A single task change, taken from the planning event store."""

    id: str
    actor: str = Field(default="system")
    actor_type: str = Field(default="user")
    action: str = Field(default="updated")
    tone: str = Field(default="info")
    task_id: str = Field(default="")
    task_name: str = Field(default="")
    board: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    field: Optional[str] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    timestamp: str = Field(default="")


class ManagementDashboard(BaseModel):
    """Everything the Pulse and Blockers sections render, in one payload."""

    metrics: ManagementMetrics
    board_progress: List[ManagementBoardProgress] = Field(default_factory=list)
    attention: List[ManagementAttentionItem] = Field(default_factory=list)
    activity: List[ManagementActivity] = Field(default_factory=list)
    priority_counts: Dict[str, int] = Field(default_factory=dict)
    generated_at: str = Field(default="")


# ── Delivery ───────────────────────────────────────────────────────────────────


class ManagementForecast(BaseModel):
    """Delivery forecast for one board."""

    board_id: str
    board: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    type: str = Field(default="kanban")
    committed: int = 0
    done: int = 0
    remaining: int = 0
    velocity: float = Field(default=0.0, description="Delivered tasks per week")
    eta_date: Optional[str] = None
    eta_days: int = 0
    target_date: Optional[str] = None
    demo_date: Optional[str] = None
    percentage: int = 0
    blocked: int = 0
    confidence: str = Field(default="high", description="high | medium | low")
    status: str = Field(default="on_track", description="on_track | at_risk | late")


class ManagementBurndownPoint(BaseModel):
    """One burndown sample."""

    date: str
    ideal: int = 0
    actual: int = Field(default=0, description="Remaining tasks at end of day")


class ManagementBurndown(BaseModel):
    """Burndown series for one board (last 14 days)."""

    board_id: str = Field(default="")
    board: str = Field(default="")
    total: int = 0
    points: List[ManagementBurndownPoint] = Field(default_factory=list)


# ── Work section ───────────────────────────────────────────────────────────────


class ManagementSort(BaseModel):
    """Sort configuration applied server-side, before pagination."""

    field: str = Field(
        default="priority",
        description="priority | due_date | status | name | project | updated_at",
    )
    dir: str = Field(default="asc", description="asc | desc")


class ManagementTaskQueryRequest(BaseModel):
    """
    Body of ``POST /api/management/tasks/query``.

    ``from`` is a reserved keyword, so the attribute is ``from_`` while the JSON
    alias stays ``from`` for clients.
    """

    model_config = ConfigDict(populate_by_name=True)

    from_: Optional[str] = Field(default=None, alias="from", description="Inclusive YYYY-MM-DD")
    to: Optional[str] = Field(default=None, description="Inclusive YYYY-MM-DD")
    project_id: Optional[str] = None
    board_id: Optional[str] = None
    statuses: List[str] = Field(default_factory=list)
    priorities: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)
    search: Optional[str] = None
    sort: ManagementSort = Field(default_factory=ManagementSort)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=12, ge=1, le=100)


class ManagementTaskQueryResponse(BaseModel):
    """Paginated task rows plus the reference data the filters need."""

    tasks: List[ManagementTask] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 12
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False
    group_counts: List[Dict[str, Any]] = Field(default_factory=list)
    boards: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[ManagementProject] = Field(default_factory=list)
    people: List[ManagementPerson] = Field(default_factory=list)
    generated_at: str = Field(default="")


class ManagementTaskUpdate(BaseModel):
    """
    Partial update of a single task.

    ``blocked`` does not exist on ``Chat``: the manager translates it into a
    status change (``true`` -> ``onhold``, ``false`` -> back to ``doing``).
    """

    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    assignees: Optional[List[str]] = None
    blocked: Optional[bool] = None


class ManagementTaskUpdateResponse(BaseModel):
    """Result of the task update endpoint."""

    task: ManagementTask


# ── Cost ───────────────────────────────────────────────────────────────────────


class ManagementBudgetProject(BaseModel):
    """Budget consumption of one project."""

    project_id: str
    project_name: str = ""
    color: Optional[str] = None
    budget: float = 0.0
    spent: float = 0.0
    pct: int = 0


class ManagementBudget(BaseModel):
    """Weekly AI budget envelope and its projection."""

    weekly_budget: float = 0.0
    spent: float = 0.0
    remaining: float = 0.0
    projected: float = 0.0
    pct: int = 0
    per_project: List[ManagementBudgetProject] = Field(default_factory=list)


class ManagementCost(BaseModel):
    """
    AI consumption payload.

    ``total``/``daily``/``by_*`` keep the raw analytics shape (``total_cxjcoins``,
    ``calls``, ``total_tokens``, ``input_tokens``, ``output_tokens``) so the UI
    renders real, unmodified numbers.
    """

    total: Dict[str, Any] = Field(default_factory=dict)
    daily: List[Dict[str, Any]] = Field(default_factory=list)
    by_project: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_model: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_user: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    budget: ManagementBudget = Field(default_factory=ManagementBudget)
    models: List[str] = Field(default_factory=list)
    projects: List[ManagementProject] = Field(default_factory=list)
    people: List[ManagementPerson] = Field(default_factory=list)
    generated_at: str = Field(default="")


# ── Section responses ──────────────────────────────────────────────────────────


class ManagementOverview(BaseModel):
    """Everything the Pulse section draws, in a single round trip."""

    range: Dict[str, str] = Field(default_factory=dict)
    projects: List[ManagementProject] = Field(default_factory=list)
    dashboard: ManagementDashboard
    forecast: List[ManagementForecast] = Field(default_factory=list)
    team_load: List[ManagementPerson] = Field(default_factory=list)
    cost: ManagementCost


class ManagementBlockersResponse(BaseModel):
    """Attention queue (the Blockers section)."""

    range: Dict[str, str] = Field(default_factory=dict)
    dashboard: ManagementDashboard
    projects: List[ManagementProject] = Field(default_factory=list)


class ManagementDeliveryResponse(BaseModel):
    """Forecast and burndown (the Delivery section)."""

    range: Dict[str, str] = Field(default_factory=dict)
    forecast: List[ManagementForecast] = Field(default_factory=list)
    burndown: ManagementBurndown = Field(default_factory=ManagementBurndown)
    projects: List[ManagementProject] = Field(default_factory=list)


class ManagementTeamResponse(BaseModel):
    """Capacity and workload (the Team section)."""

    range: Dict[str, str] = Field(default_factory=dict)
    team_load: List[ManagementPerson] = Field(default_factory=list)
    tasks: List[ManagementTask] = Field(default_factory=list)
    projects: List[ManagementProject] = Field(default_factory=list)


class ManagementCostResponse(ManagementCost):
    """Cost payload scoped to one window (the Cost & AI section)."""

    range: Dict[str, str] = Field(default_factory=dict)


# ── Assistant ──────────────────────────────────────────────────────────────────


class ManagementAssistantRequest(BaseModel):
    """A question about the current window."""

    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(default="")
    from_: Optional[str] = Field(default=None, alias="from")
    to: Optional[str] = None


class ManagementAssistantSource(BaseModel):
    """A section the answer was built from (the UI navigates to it)."""

    section: str = Field(description="pulse | work | blockers | delivery | team | cost")
    label: str = Field(default="")


class ManagementAssistantResponse(BaseModel):
    """Rule-based answer computed over the same numbers the screen renders."""

    answer: str = Field(default="")
    sources: List[ManagementAssistantSource] = Field(default_factory=list)


# Made with ❤️ by codx-junior