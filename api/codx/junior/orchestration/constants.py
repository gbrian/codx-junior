"""
Constants shared by the orchestration runtime and its callers.

This module is intentionally dependency free (standard library only) because it
is imported by both the agent runtime (``codx.junior.ai.smol``), the chat engine
and the orchestration package itself. Importing the heavy orchestration modules
from those places would create import cycles.

The orchestration runtime turns one **main task** (a normal ``Chat``) into a
durable, multi-step run:

* the main task owns the objective, the budget and the supervisor agent,
* every plan step is a **child task card** on a board and a sprint, so the work
  stays visible in the existing board/sprint UI,
* a background worker advances the run one tick at a time, surviving restarts.

Made with ❤️ by codx-junior
"""

# Internal AI request header that declares the orchestration role of the current
# chat. It is consumed by SmolAgent and never forwarded to the provider.
ORCHESTRATION_HEADER = "orchestration"

# Tool names. They are plain chat-scope tools registered in ``tools/TOOLS`` and
# injected per run (supervisor) or provided by the built-in orchestrator profile.
ORCHESTRATOR_TOOL = "orchestrator"
DELEGATE_TOOL = "delegate"

# Chat mode used by the main task of a run. Unknown modes behave like a normal
# chat (see ChatEngine._resolve_chat_mode_flags), which is exactly what the
# supervisor needs: a standard turn with the orchestrator profile composed.
CHAT_MODE_ORCHESTRATE = "orchestrate"

# Chat mode used by delegated subagent cards created by the ``delegate`` tool.
# A delegated chat cannot delegate again (single level), which keeps the tree
# finite and the budget predictable.
CHAT_MODE_DELEGATE = "delegate"

# ── Run statuses ────────────────────────────────────────────────────────────
RUN_STATUS_QUEUED = "queued"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_PAUSED = "paused"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_STOPPED = "stopped"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_BUDGET_EXHAUSTED = "budget_exhausted"
RUN_STATUS_STALLED = "stalled"

TERMINAL_RUN_STATUSES = frozenset({
    RUN_STATUS_COMPLETED,
    RUN_STATUS_STOPPED,
    RUN_STATUS_FAILED,
    RUN_STATUS_BUDGET_EXHAUSTED,
    RUN_STATUS_STALLED,
})

ACTIVE_RUN_STATUSES = frozenset({
    RUN_STATUS_QUEUED,
    RUN_STATUS_RUNNING,
})

# ── Step statuses ───────────────────────────────────────────────────────────
STEP_STATUS_PENDING = "pending"
STEP_STATUS_RUNNING = "running"
STEP_STATUS_DONE = "done"
STEP_STATUS_FAILED = "failed"
STEP_STATUS_BLOCKED = "blocked"
STEP_STATUS_SKIPPED = "skipped"

TERMINAL_STEP_STATUSES = frozenset({
    STEP_STATUS_DONE,
    STEP_STATUS_FAILED,
    STEP_STATUS_BLOCKED,
    STEP_STATUS_SKIPPED,
})

SUCCESSFUL_STEP_STATUSES = frozenset({
    STEP_STATUS_DONE,
    STEP_STATUS_SKIPPED,
})

# ── Kanban mapping ──────────────────────────────────────────────────────────
# Plan phase -> board column title. A run board is a normal kanban board whose
# columns describe the orchestration phases; the sprint of the run is a sprint
# board over the same cards (it groups by Chat.status).
DEFAULT_RUN_COLUMNS = {
    "backlog": "Backlog",
    "running": "In progress",
    "done": "Done",
    "blocked": "Blocked",
}

SPRINT_COLUMN_TITLES = ("To do", "Doing", "On hold", "Done")

# Card status (Chat.status) per step status.
STEP_CHAT_STATUS = {
    STEP_STATUS_PENDING: "todo",
    STEP_STATUS_RUNNING: "doing",
    STEP_STATUS_DONE: "done",
    STEP_STATUS_FAILED: "rejected",
    STEP_STATUS_BLOCKED: "onhold",
    STEP_STATUS_SKIPPED: "done",
}

# Board phase per step status.
STEP_BOARD_PHASE = {
    STEP_STATUS_PENDING: "backlog",
    STEP_STATUS_RUNNING: "running",
    STEP_STATUS_DONE: "done",
    STEP_STATUS_FAILED: "blocked",
    STEP_STATUS_BLOCKED: "blocked",
    STEP_STATUS_SKIPPED: "done",
}

# ── Toolset injected into isolated workers ──────────────────────────────────
# Workers run in their own chat (own context). The profile assigned to the step
# still adds its tools; this baseline guarantees that a worker can inspect and
# modify the project even when the run/step does not declare a profile.
DEFAULT_WORKER_TOOLS = (
    "project_search",
    "project_grep",
    "project_glob",
    "project_read_file",
    "project_write_file",
    "project_changes",
    "project_structure",
    "apply_file_changes",
    "code_writer",
    "fetch_webpage",
    "get_file_last_version",
    "repository_status",
    "repository_log",
)

# ── Limits / defaults ───────────────────────────────────────────────────────
DEFAULT_BOARD = "Orchestration"
DEFAULT_MAX_STEPS = 30
DEFAULT_MAX_ROUNDS = 40
DEFAULT_MAX_PARALLEL = 2
MAX_PARALLEL_LIMIT = 4
DEFAULT_MAX_ATTEMPTS = 2
DEFAULT_STAGNATION_LIMIT = 3
DEFAULT_STEP_TIMEOUT_SECONDS = 1800
DEFAULT_SUPERVISOR_TIMEOUT_SECONDS = 900
DEFAULT_MAX_DELEGATE_TASKS = 8
DEFAULT_DELEGATE_CONCURRENCY = 2

# Result contract: the worker must finish with this JSON object. The parser in
# ``models.parse_step_result`` also accepts a fenced JSON block.
STEP_RESULT_STATUSES = ("done", "blocked", "failed")
STEP_RESULT_INSTRUCTIONS = (
    'Finish with a JSON object (and nothing after it):\n'
    '{"status":"done"|"blocked"|"failed","summary":"what was done",'
    '"files":["paths touched"],"verification":"how you verified it",'
    '"followups":["remaining work"]}'
)

# Directories under ``<project>/.codx``.
ORCHESTRATION_DIR = "orchestration"
RUNS_DIR = "runs"
WORKER_FILE = "worker.json"

# Environment switches (documented in docs/orchestration.md).
ENV_ENABLED = "CODX_JUNIOR_ORCHESTRATION"
ENV_WORKER = "CODX_JUNIOR_ORCHESTRATION_WORKER"
ENV_TICK_SECONDS = "CODX_JUNIOR_ORCHESTRATION_TICK_SECONDS"
ENV_MAX_RUNS = "CODX_JUNIOR_ORCHESTRATION_MAX_RUNS"
ENV_WORKER_TTL = "CODX_JUNIOR_ORCHESTRATION_WORKER_TTL"

# Made with ❤️ by codx-junior
