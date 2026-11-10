"""
Board manager: a profile that reviews and maintains the tasks of a board.

A board can associate a profile (``board.manager.profile``, falling back to the
board assistant) and a background worker periodically sends that profile a
snapshot of the board. The profile answers with a small JSON decision — move a
task, add a comment, close a task, update it, create a follow-up — and the
service validates and applies every action.

Public surface:

* :class:`BoardManagerConfig` / :class:`ManagerState` — configuration and state.
* :class:`BoardManagerService` — one review, status and scheduling.
* :class:`BoardManagerStore` — atomic runtime state.
* :func:`start_board_manager_worker` — background loop.

Made with ❤️ by codx-junior
"""

from .constants import DEFAULT_PROFILE
from .models import (
    BoardManagerConfig,
    ManagerAction,
    ManagerDecision,
    ManagerState,
    parse_decision,
)
from .service import BoardManagerService, ManagerRequest
from .store import BoardManagerStore

__all__ = [
    "DEFAULT_PROFILE",
    "BoardManagerConfig",
    "BoardManagerService",
    "BoardManagerStore",
    "ManagerAction",
    "ManagerDecision",
    "ManagerRequest",
    "ManagerState",
    "parse_decision",
]

# Made with ❤️ by codx-junior
