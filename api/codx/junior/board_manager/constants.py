"""
Constants of the board manager (the "project manager" running on a board).

The board manager is a **background reviewer**: a profile is associated with a
board, a worker periodically collects the board tasks, asks the profile what
should change and applies the resulting actions (move, comment, close, update,
create). It is opt-in per board and never runs when the board manager is
disabled.

This module is dependency free so both the runtime and the tests can import it
without the AI stack.

Made with ❤️ by codx-junior
"""

#: Board document key that holds the manager configuration.
BOARD_CONFIG_KEY = "manager"

#: Profile used when neither the board manager nor the board assistant declares
#: one. It is the standard project-manager profile shipped with codx-junior.
DEFAULT_PROFILE = "ProjectManager"

#: How often a board is reviewed when it does not define an interval.
DEFAULT_INTERVAL_MINUTES = 60
MIN_INTERVAL_MINUTES = 5
MAX_INTERVAL_MINUTES = 7 * 24 * 60

#: Maximum number of actions applied in one review.
DEFAULT_MAX_ACTIONS = 5
MAX_ACTIONS_LIMIT = 20

#: How many tasks are put in front of the model.
DEFAULT_MAX_TASKS = 80
MAX_TASKS_LIMIT = 200

#: One review cannot run forever (seconds).
DEFAULT_TIMEOUT_SECONDS = 300

#: A "running" state older than this is considered crashed/abandoned and no
#: longer blocks the schedule (the AI timeout is shorter).
STALE_RUN_SECONDS = DEFAULT_TIMEOUT_SECONDS + 120

#: Background worker cadence (seconds).
DEFAULT_TICK_SECONDS = 30
MAX_TICK_SECONDS = 600

#: A worker heartbeat older than this means "no worker present".
WORKER_TTL_SECONDS = 120

#: Modes. ``apply`` writes the changes; ``suggest`` only records them.
MODE_APPLY = "apply"
MODE_SUGGEST = "suggest"
MODES = (MODE_APPLY, MODE_SUGGEST)

#: Action types understood by :mod:`codx.junior.board_manager.service`.
ACTION_MOVE = "move_task"
ACTION_COMMENT = "comment"
ACTION_CLOSE = "close_task"
ACTION_UPDATE = "update_task"
ACTION_CREATE = "create_task"
ACTION_TYPES = (
    ACTION_MOVE,
    ACTION_COMMENT,
    ACTION_CLOSE,
    ACTION_UPDATE,
    ACTION_CREATE,
)

#: Tolerant aliases: a model that writes "move" or "add_comment" still works.
ACTION_ALIASES = {
    "move": ACTION_MOVE,
    "move_to_column": ACTION_MOVE,
    "move_column": ACTION_MOVE,
    "add_comment": ACTION_COMMENT,
    "comment_task": ACTION_COMMENT,
    "close": ACTION_CLOSE,
    "complete": ACTION_CLOSE,
    "complete_task": ACTION_CLOSE,
    "close_task": ACTION_CLOSE,
    "update": ACTION_UPDATE,
    "edit_task": ACTION_UPDATE,
    "create": ACTION_CREATE,
    "new_task": ACTION_CREATE,
    "create_task": ACTION_CREATE,
}

#: Statuses considered closed. Used to avoid churning closed cards.
DONE_STATUSES = {"done", "closed", "completed"}

#: Run statuses of an orchestration card; the manager never moves/edits those
#: while the run is active (the orchestration worker owns the card).
ACTIVE_RUN_STATUSES = {"queued", "running"}

#: Folder under ``<codx_path>`` holding the manager state and locks.
BOARD_MANAGER_DIR = "board_manager"
STATE_FILE = "state.json"
WORKER_FILE = "worker.json"
LOCK_FILE = ".state.lock"
LOCKS_DIR = "locks"

#: Environment switches.
ENV_ENABLED = "CODX_JUNIOR_BOARD_MANAGER"
ENV_TICK_SECONDS = "CODX_JUNIOR_BOARD_MANAGER_TICK_SECONDS"
ENV_MAX_BOARDS = "CODX_JUNIOR_BOARD_MANAGER_MAX_BOARDS"

#: State statuses.
STATE_OK = "ok"
STATE_NO_ACTIONS = "no_actions"
STATE_SUGGESTED = "suggested"
STATE_NO_TASKS = "no_tasks"
STATE_SKIPPED = "skipped"
STATE_ERROR = "error"

# Made with ❤️ by codx-junior
