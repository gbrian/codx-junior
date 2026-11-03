"""
Kanban board maintenance actions.

This package holds project-manager style operations that review a whole board
instead of a single task. The first member is the **board status review**:
a profile (``project_manager`` by default) reviews every task of a board and
either updates the task state/metadata or posts a message on the task asking
for an action.

Public API:

    - :func:`review_board_tasks`  : run a review (optionally as a dry run).
    - :func:`board_review_status` : cheap status probe used by the client.
    - :func:`is_task_processing`  : whether a task's AI turn is in flight.
    - :class:`BoardReviewRequest` / :class:`BoardReviewResponse` : models.
    - :class:`BoardReviewBusy` / :class:`BoardReviewError` : control errors.

Made with ❤️ by codx-junior
"""

from codx.junior.kanban.board_status_review import (
    DEFAULT_PROFILE,
    BoardReviewBusy,
    BoardReviewError,
    BoardReviewRequest,
    BoardReviewResponse,
    AppliedDecision,
    SkippedTask,
    board_review_status,
    is_board_review_running,
    is_task_processing,
    review_board_tasks,
)

__all__ = [
    "DEFAULT_PROFILE",
    "BoardReviewBusy",
    "BoardReviewError",
    "BoardReviewRequest",
    "BoardReviewResponse",
    "AppliedDecision",
    "SkippedTask",
    "board_review_status",
    "is_board_review_running",
    "is_task_processing",
    "review_board_tasks",
]

# Made with ❤️ by codx-junior
