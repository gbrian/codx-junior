"""
Task review models and state tracking.

Defines the data structures used to track review requests, state, and history.
These are stored on the Chat to track which profile reviewed the task and what
they found.

Made with ❤️ by codx-junior
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Review state constants
REVIEW_STATUS_IDLE = "idle"
REVIEW_STATUS_PENDING = "pending"
REVIEW_STATUS_RUNNING = "running"
REVIEW_STATUS_APPROVED = "approved"
REVIEW_STATUS_CHANGES_REQUESTED = "changes_requested"
REVIEW_STATUS_COMMENTED = "commented"
REVIEW_STATUS_ERROR = "error"

# Review verdict constants (what the profile decides)
REVIEW_VERDICT_APPROVE = "approve"
REVIEW_VERDICT_REQUEST_CHANGES = "request_changes"
REVIEW_VERDICT_COMMENT = "comment"

REVIEW_VERDICTS = [
    REVIEW_VERDICT_APPROVE,
    REVIEW_VERDICT_REQUEST_CHANGES,
    REVIEW_VERDICT_COMMENT,
]

# Review mode constants (what action to take based on verdict)
REVIEW_MODE_COMMENT = "comment"
REVIEW_MODE_MOVE = "move"
REVIEW_MODE_GATE = "gate"

REVIEW_MODES = [REVIEW_MODE_COMMENT, REVIEW_MODE_MOVE, REVIEW_MODE_GATE]

# Review triggers
REVIEW_TRIGGER_MESSAGE = "message"
REVIEW_TRIGGER_STATUS = "status"
REVIEW_TRIGGER_MOVE = "move"
REVIEW_TRIGGER_SPEC = "spec"
REVIEW_TRIGGER_PLANNING = "planning"

REVIEW_TRIGGERS = [
    REVIEW_TRIGGER_MESSAGE,
    REVIEW_TRIGGER_STATUS,
    REVIEW_TRIGGER_MOVE,
    REVIEW_TRIGGER_SPEC,
    REVIEW_TRIGGER_PLANNING,
]


class TaskReviewState(BaseModel):
    """Current review state of a task."""

    fingerprint: str = Field(
        default="",
        description="Last reviewed content fingerprint (hash of reviewed state)"
    )
    status: str = Field(
        default=REVIEW_STATUS_IDLE,
        description="Current review status: idle|pending|running|approved|changes_requested|commented|error"
    )
    assignee: str = Field(
        default="",
        description="Profile that reviewed this task"
    )
    last_review_at: Optional[str] = Field(
        default=None,
        description="ISO timestamp of last review"
    )
    last_request_id: Optional[str] = Field(
        default=None,
        description="ID of last review request"
    )
    attempts: int = Field(
        default=0,
        description="Number of review attempts (for backoff)"
    )
    reviews_today: int = Field(
        default=0,
        description="Number of reviews completed today"
    )
    reviews_day: str = Field(
        default="",
        description="YYYY-MM-DD date of the reviews_today counter (for reset)"
    )
    skipped_reason: Optional[str] = Field(
        default=None,
        description="Reason why review was skipped, if any"
    )


class TaskReviewFinding(BaseModel):
    """A single finding from a review."""

    aspect: str = Field(
        description="Category: scope|tests|docs|risk|spec"
    )
    severity: str = Field(
        description="Severity level: low|med|high"
    )
    note: str = Field(
        description="Human-readable finding note"
    )


class TaskReviewRecord(BaseModel):
    """Audit trail entry for a review."""

    request_id: str = Field(
        description="Unique identifier for this review request"
    )
    assignee: str = Field(
        description="Profile that performed the review"
    )
    fingerprint: str = Field(
        description="Content fingerprint that was reviewed"
    )
    triggers: List[str] = Field(
        default=[],
        description="Triggers that caused this review"
    )
    verdict: str = Field(
        default=REVIEW_VERDICT_COMMENT,
        description="Review verdict: approve|request_changes|comment"
    )
    summary: str = Field(
        default="",
        description="2-line summary of the review"
    )
    findings: List[TaskReviewFinding] = Field(
        default=[],
        description="Detailed findings from the review"
    )
    message_id: Optional[str] = Field(
        default=None,
        description="ID of the review message posted to the chat"
    )
    at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp when the review was completed"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the review failed"
    )


class ReviewRequest(BaseModel):
    """A task review request queued for processing."""

    request_id: str = Field(
        description="Unique request identifier"
    )
    chat_id: str = Field(
        description="Task (chat) ID to review"
    )
    board: str = Field(
        description="Board the task is on"
    )
    assignee: str = Field(
        description="Profile to perform the review"
    )
    fingerprint: str = Field(
        description="Content fingerprint that triggered the review"
    )
    triggers: List[str] = Field(
        default=[],
        description="What caused this review request"
    )
    requested_by: Optional[str] = Field(
        default=None,
        description="Username that requested the review (system or manual)"
    )
    requested_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp when review was requested"
    )


class BoardReviewPolicy(BaseModel):
    """Review policy for a board."""

    enabled: bool = Field(
        default=False,
        description="Whether review is enabled for this board"
    )
    triggers: List[str] = Field(
        default=[REVIEW_TRIGGER_MESSAGE, REVIEW_TRIGGER_STATUS, REVIEW_TRIGGER_MOVE, REVIEW_TRIGGER_SPEC, REVIEW_TRIGGER_PLANNING],
        description="Which changes trigger a review"
    )
    mode: str = Field(
        default=REVIEW_MODE_COMMENT,
        description="Action mode: comment|move|gate"
    )
    review_column: str = Field(
        default="review",
        description="Column to move cards to in move mode"
    )
    quiet_seconds: int = Field(
        default=60,
        description="Seconds to wait after last change before reviewing"
    )
    max_per_task_per_day: int = Field(
        default=3,
        description="Maximum reviews per task per day"
    )
    disable_knowledge: bool = Field(
        default=False,
        description="Skip knowledge search during review"
    )
    llm_model: Optional[str] = Field(
        default=None,
        description="Override LLM model for reviews (None = use default)"
    )


# Made with ❤️ by codx-junior
