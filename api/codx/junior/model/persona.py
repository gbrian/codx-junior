"""
Persona models.

A **persona** is an autonomous worker of the project team: a registered
:class:`~codx.junior.model.user.CodxUser` (so it is subject to the same
permissions/budgets as a human user) bound to a **profile** (prompt + tools) and
to one or more **triggers** that describe *when* the persona runs and *which
task* (a registered task-handler id plus an optional prompt) it runs.

Nothing here is specific to the project manager: "Tony" is just data
(:data:`codx.junior.personas.persona_manager.DEFAULT_PERSONAS`), so defining
another persona requires configuration only.

This module also carries the request/response models of the
``POST /api/personas/{persona_name}/board-review`` action, because they are part
of the persona contract (the client asks a persona to review a board).
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from codx.junior.model.user import CodxUser

# Trigger types understood by the persona runtime.
TRIGGER_INTERVAL = "interval"
TRIGGER_EVENT = "event"
TRIGGER_MANUAL = "manual"
TRIGGER_TYPES = (TRIGGER_INTERVAL, TRIGGER_EVENT, TRIGGER_MANUAL)

# Registered task handlers (see codx.junior.personas.task_handlers).
TASK_BOARD_REVIEW = "board_task_review"
TASK_PROMPT = "prompt"

# How a persona reacts to a task that another run is already processing.
ON_PROCESSING_SKIP = "skip"
ON_PROCESSING_WAIT = "wait"
ON_PROCESSING_VALUES = (ON_PROCESSING_SKIP, ON_PROCESSING_WAIT)


class PersonaTrigger(BaseModel):
    """
    One activation rule of a persona.

    The trigger binds a scheduling mechanism (``interval``, ``event`` or
    ``manual``) to the task the persona performs: the id of a registered task
    handler plus the optional prompt (the "task text") handed to it.

    Example — review a board every 30 minutes and on demand::

        [
          {"type": "interval", "interval_minutes": 30, "task": "board_task_review"},
          {"type": "manual", "task": "board_task_review", "board": "kanban"}
        ]
    """

    type: str = Field(
        default=TRIGGER_MANUAL,
        description="Activation trigger: 'interval', 'event' or 'manual'",
    )
    task: str = Field(
        default=TASK_BOARD_REVIEW,
        description="Registered task handler id ('board_task_review' or 'prompt')",
    )
    event: Optional[str] = Field(
        default=None,
        description="Event name when type='event' (e.g. 'task.created')",
    )
    interval_minutes: Optional[int] = Field(
        default=None,
        description="Minimum minutes between runs when type='interval'",
    )
    board: Optional[str] = Field(
        default=None,
        description="Board the task works on (handler default when omitted)",
    )
    prompt: Optional[str] = Field(
        default=None,
        description="Optional task text/template assigned to this trigger",
    )
    window_days: int = Field(
        default=30,
        description="How many days of task history the task must consider",
    )


class Persona(BaseModel):
    """
    An autonomous team member: a registered user bound to a profile.

    The ``user`` is what makes a persona accountable: it is the identity written
    into the messages it posts and the subject of the permissions and spending
    limits enforced by the rest of the platform.
    """

    name: str = Field(..., description="Unique persona name")
    profile: str = Field(..., description="Profile name this persona runs with")
    user: CodxUser = Field(
        default_factory=CodxUser,
        description="Registered user backing this persona (permissions/budgets)",
    )
    enabled: bool = Field(default=True, description="Whether this persona is active")
    project_ids: List[str] = Field(
        default_factory=list,
        description="Project scope; an empty list means every project",
    )
    decision_model: Optional[str] = Field(
        default="laya",
        description="Decision model used by structured review tasks",
    )
    triggers: List[PersonaTrigger] = Field(
        default_factory=list,
        description="Activation rules and the task each one runs",
    )

    @property
    def username(self) -> str:
        """Return the registered username backing this persona."""
        return self.user.username or self.name

    def trigger_for(self, task: Optional[str] = None) -> Optional[PersonaTrigger]:
        """
        Return the first trigger of the persona, optionally for a given task.

        :param task: Registered task handler id to look for.
        :return: The matching trigger, or the first one, or ``None``.
        """
        if not self.triggers:
            return None
        if not task:
            return self.triggers[0]
        return next((t for t in self.triggers if t.task == task), self.triggers[0])


class BoardTasksReviewRequest(BaseModel):
    """
    Body of ``POST /api/personas/{persona_name}/board-review``.

    The persona reviews every task of ``board`` (optionally restricted to
    ``columns``/``statuses``/``task_ids``), decides which tasks need an update,
    applies the state change and/or posts a message asking for an action.

    ``on_processing`` decides what happens with a task that is being processed
    right now (an AI run in flight, a streaming message or another persona
    review): ``skip`` leaves it for the next run, ``wait`` waits up to
    ``wait_timeout_seconds`` before skipping it.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    board: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Board name, id or title whose tasks are reviewed",
    )
    columns: Optional[List[str]] = Field(
        default=None,
        description="Restrict the review to these columns (default: every column)",
    )
    statuses: Optional[List[str]] = Field(
        default=None,
        description="Restrict the review to these task statuses (default: all)",
    )
    task_ids: Optional[List[str]] = Field(
        default=None,
        description="Review only these task ids (default: the whole board)",
    )
    window_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Only tasks updated within the last N days are reviewed",
    )
    persona: Optional[str] = Field(
        default=None,
        description=(
            "Persona to run. The path parameter wins; this field exists so the "
            "action can also be triggered from a place without a path."
        ),
    )
    dry_run: bool = Field(
        default=False,
        description="Decide and report, but do not change tasks nor post messages",
    )
    post_comment: bool = Field(
        default=True,
        description="Post a message on every task that is updated or needs action",
    )
    on_processing: str = Field(
        default=ON_PROCESSING_SKIP,
        description="What to do with a task being processed: 'skip' or 'wait'",
    )
    wait_timeout_seconds: int = Field(
        default=60,
        ge=0,
        le=280,
        description="Maximum wait per task when on_processing='wait'",
    )


class TaskReviewOutcome(BaseModel):
    """What the persona decided and did for one task."""

    task_id: str = Field(description="Task (chat) id")
    name: str = Field(default="")
    board: str = Field(default="")
    column: str = Field(default="")
    status_before: Optional[str] = Field(default=None)
    status_after: Optional[str] = Field(default=None)
    updates: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata fields the persona changed (empty on dry runs)",
    )
    decisions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata fields the persona decided to change (dry runs included)",
    )
    reason: str = Field(default="", description="Why the task was updated")
    commented: bool = Field(default=False, description="A message was posted")
    skipped: bool = Field(default=False, description="The task was not reviewed")
    skip_reason: Optional[str] = Field(
        default=None,
        description="'processing' when another run is using the task, 'not_found'…",
    )


class BoardTasksReviewResponse(BaseModel):
    """Result of one board review run."""

    project_name: str = Field(default="")
    project_id: Optional[str] = Field(default=None)
    board: str = Field(default="", description="Resolved board name")
    persona: str = Field(default="")
    profile: str = Field(default="")
    decision_model: str = Field(default="")
    dry_run: bool = Field(default=False)
    total_tasks: int = Field(default=0, description="Tasks of the board in the window")
    reviewed: int = Field(default=0, description="Tasks the persona looked at")
    skipped: int = Field(default=0, description="Tasks left out (processing/…)")
    updated: int = Field(default=0, description="Tasks whose metadata changed")
    commented: int = Field(default=0, description="Tasks that received a message")
    results: List[TaskReviewOutcome] = Field(default_factory=list)

# Made with ❤️ by codx-junior
