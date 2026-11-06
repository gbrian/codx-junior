"""
Data model of a durable orchestration run.

A run is persisted as one JSON document under
``<project>/.codx/orchestration/runs/<run_id>.json`` (see ``store.py``). The
document is the **source of truth** for the plan, the step results and the
supervisor rounds; the main task (a normal ``Chat``) carries only the mirror
fields ``run_id`` / ``run_status`` so the board and the planning views can show
it, and every plan step is materialized as a child task card.

Why a dedicated store instead of storing the whole state on ``Chat``:

* the supervisor turn appends messages to the main chat while the worker updates
  the plan and the step cards — two writers would clobber each other on a
  full-document chat save,
* the run state is small and atomic to write, while a chat file grows with the
  conversation,
* a run can be inspected/recovered without loading the whole conversation.

The ``Chat.run_id`` back-reference keeps the board/sprint visibility: every card
of the run points to the same run id and to its step id.

This module is dependency-light (pydantic + standard library) so it can be
tested and imported without the AI stack.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, Field

from . import constants as C

logger = logging.getLogger(__name__)


class PlanError(ValueError):
    """The proposed plan is invalid (unknown dependency, cycle, too large...)."""


class RunNotFound(LookupError):
    """The run id does not exist in the project store."""


class RunLocked(RuntimeError):
    """Another worker is already advancing the run."""


class RunCorrupt(RuntimeError):
    """The run document exists but cannot be parsed."""


# ---------------------------------------------------------------------------
# Time / id helpers
# ---------------------------------------------------------------------------


def utcnow_iso() -> str:
    """Return the current UTC instant as an ISO-8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()


def new_run_id() -> str:
    """Return a new run id (UUID4 string)."""
    return str(uuid.uuid4())


def new_step_id() -> str:
    """Return a new step id (short, readable)."""
    return f"s{uuid.uuid4().hex[:8]}"


def _clip(value: Any, max_chars: int, default: str = "") -> str:
    """Convert *value* to a stripped string clipped to *max_chars*."""
    text = (str(value) if value is not None else default).strip()
    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n… (truncated)"
    return text


def _as_str_list(value: Any, max_items: int = 100, max_chars: int = 500) -> List[str]:
    """Normalize an arbitrary value into a de-duplicated list of short strings."""
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    result: List[str] = []
    try:
        items = list(value)
    except TypeError:
        items = [value]
    for item in items:
        text = _clip(item, max_chars)
        if text and text not in result:
            result.append(text)
        if len(result) >= max_items:
            break
    return result


# ---------------------------------------------------------------------------
# Step result contract
# ---------------------------------------------------------------------------


class StepResult(BaseModel):
    """
    Structured outcome of one worker turn.

    The worker is asked to finish with a JSON object; the runtime also accepts
    a fenced ```json block and falls back to the raw final answer when the model
    ignores the contract, so a result is never lost.
    """

    status: str = Field(default=C.STEP_STATUS_DONE, description="done | blocked | failed")
    summary: str = Field(default="", description="What the worker actually did")
    files: List[str] = Field(default_factory=list, description="Project files touched")
    verification: str = Field(default="", description="How the result was verified")
    followups: List[str] = Field(default_factory=list, description="Remaining work the worker found")
    cost_cxjcoins: float = Field(default=0.0, description="Cost of the worker turn")
    duration_seconds: float = Field(default=0.0, description="Wall clock duration of the worker")
    error: str = Field(default="", description="Runtime error, when the turn failed")
    raw_content: str = Field(default="", description="Final answer (clipped) for audit")

    def is_success(self) -> bool:
        """Return True when the worker reported a successful outcome."""
        return self.status in C.SUCCESSFUL_STEP_STATUSES


def _extract_json_candidates(text: str) -> List[str]:
    """
    Return JSON-looking fragments of *text*, most likely contract first.

    Order: fenced code blocks (last one first), then balanced ``{...}`` objects
    found from the end of the text. The caller tries ``json.loads`` on each.
    """
    candidates: List[str] = []
    for match in re.finditer(r"```(?:json)?\s*\n?(.*?)```", text, re.S | re.I):
        block = (match.group(1) or "").strip()
        if block.startswith("{"):
            candidates.append(block)
    # Balanced objects, scanning backwards: the contract is normally the last
    # thing the model writes.
    positions = [index for index, char in enumerate(text) if char == "{"]
    for start in reversed(positions[-50:]):
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start:index + 1])
                    break
    # Preserve order (fenced blocks first, then balanced objects) while
    # de-duplicating.
    seen = set()
    ordered: List[str] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def _normalize_result_status(value: Any) -> str:
    """Map the many words a model may use onto the three contract statuses."""
    text = str(value or "").strip().lower()
    if text in {"failed", "error", "failure", "aborted"}:
        return C.STEP_STATUS_FAILED
    if text in {"blocked", "block", "needs_help", "need_help", "partial", "stuck"}:
        return C.STEP_STATUS_BLOCKED
    return C.STEP_STATUS_DONE


def _strip_json_blocks(text: str) -> str:
    """Remove fenced JSON blocks from *text* (used for the fallback summary)."""
    cleaned = re.sub(r"```(?:json)?\s*\n?.*?```", "", text, flags=re.S | re.I)
    return cleaned.strip()


def parse_step_result(
    content: str,
    *,
    error: Optional[str] = None,
    cost_cxjcoins: float = 0.0,
    duration_seconds: float = 0.0,
) -> StepResult:
    """
    Parse the structured result contract out of a worker's final answer.

    Args:
        content: Final assistant text of the worker chat.
        error: Runtime error registered on the response message, if any.
        cost_cxjcoins: Cost of the worker turn.
        duration_seconds: Duration of the worker turn.

    Returns:
        A :class:`StepResult`. Never raises: an unparseable answer becomes a
        ``done`` result whose summary is the (clipped) answer, and a runtime
        error becomes a ``failed`` result.

    Example:
        >>> parse_step_result('All good\\n```json\\n{"status":"done","summary":"ok"}\\n```')
        StepResult(status='done', summary='ok', ...)
    """
    text = content or ""
    payload: Optional[Dict[str, Any]] = None
    for candidate in _extract_json_candidates(text):
        try:
            parsed = json.loads(candidate)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, dict) and (
            "status" in parsed or "summary" in parsed or "result" in parsed
        ):
            payload = parsed
            break

    if error:
        return StepResult(
            status=C.STEP_STATUS_FAILED,
            summary=_clip(payload.get("summary") if payload else _strip_json_blocks(text), 4000),
            files=_as_str_list(payload.get("files") if payload else []),
            verification=_clip(payload.get("verification") if payload else "", 2000),
            followups=_as_str_list(payload.get("followups") if payload else []),
            cost_cxjcoins=cost_cxjcoins,
            duration_seconds=duration_seconds,
            error=_clip(error, 4000),
            raw_content=_clip(text, 8000),
        )

    if payload:
        summary = payload.get("summary") or payload.get("result") or payload.get("message")
        return StepResult(
            status=_normalize_result_status(payload.get("status")),
            summary=_clip(summary or _strip_json_blocks(text), 4000),
            files=_as_str_list(payload.get("files")),
            verification=_clip(payload.get("verification"), 2000),
            followups=_as_str_list(payload.get("followups")),
            cost_cxjcoins=cost_cxjcoins,
            duration_seconds=duration_seconds,
            raw_content=_clip(text, 8000),
        )

    summary = _strip_json_blocks(text)
    return StepResult(
        status=C.STEP_STATUS_DONE,
        summary=_clip(summary or "(worker produced no final text)", 4000),
        cost_cxjcoins=cost_cxjcoins,
        duration_seconds=duration_seconds,
        raw_content=_clip(text, 8000),
    )


# ---------------------------------------------------------------------------
# Run configuration
# ---------------------------------------------------------------------------


class RunConfig(BaseModel):
    """
    Immutable-ish policy of a run: budget, parallelism and limits.

    The objective lives on :class:`RunState` because it is also the main task
    description and can be refined by the supervisor.
    """

    # Budget in cxjcoins. 0 means "no hard budget" (the step/round limits still
    # apply). The main task's `estimation_cost` mirrors this value.
    budget_cxjcoins: float = Field(default=0.0)
    per_step_budget: float = Field(default=0.0, description="0 = no per-step cap")
    supervisor_reserve: float = Field(
        default=0.0,
        description="Cost kept for the final supervisor turn. 0 = auto (10% of budget)",
    )

    max_steps: int = Field(default=C.DEFAULT_MAX_STEPS)
    max_rounds: int = Field(default=C.DEFAULT_MAX_ROUNDS)
    max_parallel: int = Field(default=C.DEFAULT_MAX_PARALLEL)
    max_attempts: int = Field(default=C.DEFAULT_MAX_ATTEMPTS)
    stagnation_limit: int = Field(default=C.DEFAULT_STAGNATION_LIMIT)

    step_timeout_seconds: int = Field(default=C.DEFAULT_STEP_TIMEOUT_SECONDS)
    supervisor_timeout_seconds: int = Field(
        default=C.DEFAULT_SUPERVISOR_TIMEOUT_SECONDS
    )

    # Chat mode of a worker card. "chat" keeps the self-contained contract as
    # the request (no document-refine rewriting); the planner may opt into
    # "task" per step when the step is genuinely a document refinement.
    step_mode: str = Field(default="chat")

    # Profiles composed into the supervisor / workers. The workers fall back to
    # the step profile, then to these, then to the main task profiles minus the
    # orchestrator profile.
    supervisor_profiles: List[str] = Field(default_factory=lambda: ["orchestrator"])
    default_profiles: List[str] = Field(default_factory=list)

    # Board/sprint names. `sprint` empty means "Run: <run name>".
    board: str = Field(default=C.DEFAULT_BOARD)
    sprint: str = Field(default="")
    columns: Dict[str, str] = Field(
        default_factory=lambda: dict(C.DEFAULT_RUN_COLUMNS)
    )

    verification: str = Field(
        default="supervisor",
        description="supervisor (verify in a supervisor round) | none",
    )

    created_by: str = Field(default="")

    def resolve_reserve(self) -> float:
        """
        Return the cost reserved for the final verification/report turn.

        Explicit ``supervisor_reserve`` wins; otherwise 10% of the budget. A run
        without a budget reserves nothing (the round limits still apply).
        """
        if self.supervisor_reserve and self.supervisor_reserve > 0:
            return float(self.supervisor_reserve)
        if self.budget_cxjcoins and self.budget_cxjcoins > 0:
            return float(self.budget_cxjcoins) * 0.10
        return 0.0

    def normalized(self) -> "RunConfig":
        """Return a copy with clamped numeric limits (never mutate the input)."""
        data = self.model_dump()
        data["budget_cxjcoins"] = max(0.0, float(data.get("budget_cxjcoins") or 0.0))
        data["per_step_budget"] = max(0.0, float(data.get("per_step_budget") or 0.0))
        data["supervisor_reserve"] = max(
            0.0, float(data.get("supervisor_reserve") or 0.0)
        )
        data["max_steps"] = max(1, min(int(data.get("max_steps") or 1), 100))
        data["max_rounds"] = max(1, min(int(data.get("max_rounds") or 1), 200))
        data["max_parallel"] = max(
            1, min(int(data.get("max_parallel") or 1), C.MAX_PARALLEL_LIMIT)
        )
        data["max_attempts"] = max(1, min(int(data.get("max_attempts") or 1), 5))
        data["stagnation_limit"] = max(
            1, min(int(data.get("stagnation_limit") or 1), 20)
        )
        data["step_timeout_seconds"] = max(
            60, min(int(data.get("step_timeout_seconds") or 60), 24 * 3600)
        )
        data["supervisor_timeout_seconds"] = max(
            60, min(int(data.get("supervisor_timeout_seconds") or 60), 24 * 3600)
        )
        board = str(data.get("board") or C.DEFAULT_BOARD).strip() or C.DEFAULT_BOARD
        data["board"] = board
        sprint = str(data.get("sprint") or "").strip()
        data["sprint"] = sprint
        data["verification"] = (
            "none" if str(data.get("verification") or "").lower() == "none" else "supervisor"
        )
        columns = data.get("columns") or {}
        merged = dict(C.DEFAULT_RUN_COLUMNS)
        for key, value in columns.items():
            if key in merged and str(value or "").strip():
                merged[key] = str(value).strip()
        data["columns"] = merged
        return RunConfig(**data)


# ---------------------------------------------------------------------------
# Plan step
# ---------------------------------------------------------------------------


class PlanStep(BaseModel):
    """One unit of work of a run. It is always materialized as a task card."""

    id: str = Field(default_factory=new_step_id)
    title: str
    objective: str
    acceptance: str = Field(default="")
    profile: str = Field(default="")
    depends_on: List[str] = Field(default_factory=list)
    files: List[str] = Field(default_factory=list)
    context: str = Field(default="")
    priority: str = Field(default="medium")
    mode: str = Field(default="", description="Per-step chat mode override")

    status: str = Field(default=C.STEP_STATUS_PENDING)
    attempts: int = Field(default=0)
    chat_id: str = Field(default="", description="Card chat id")
    board: str = Field(default="")
    column: str = Field(default="")
    chat_status: str = Field(default="", description="Mirror of Chat.status")
    result: Optional[StepResult] = Field(default=None)
    error: str = Field(default="")

    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)
    started_at: str = Field(default="")
    finished_at: str = Field(default="")

    def is_terminal(self) -> bool:
        """Return True when the step no longer needs the worker."""
        return self.status in C.TERMINAL_STEP_STATUSES

    def as_summary(self, max_result_chars: int = 800) -> Dict[str, Any]:
        """Return a compact, JSON-serializable view used by prompts/API."""
        result = self.result
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "attempts": self.attempts,
            "profile": self.profile,
            "depends_on": list(self.depends_on),
            "chat_id": self.chat_id,
            "board": self.board,
            "column": self.column,
            "summary": _clip(result.summary if result else "", max_result_chars),
            "verification": _clip(result.verification if result else "", max_result_chars),
            "files": list(result.files) if result else [],
            "followups": list(result.followups) if result else [],
            "error": self.error or (result.error if result else ""),
        }


# ---------------------------------------------------------------------------
# Run event log
# ---------------------------------------------------------------------------


class RunEvent(BaseModel):
    """One entry of the run timeline (surfaced by the API/tool/status view)."""

    at: str = Field(default_factory=utcnow_iso)
    type: str = Field(default="")
    message: str = Field(default="")
    data: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Run state
# ---------------------------------------------------------------------------


class RunState(BaseModel):
    """Complete durable state of one run."""

    version: int = Field(default=1)
    run_id: str = Field(default_factory=new_run_id)
    name: str = Field(default="")
    objective: str = Field(default="")
    main_chat_id: str = Field(default="")
    status: str = Field(default=C.RUN_STATUS_QUEUED)
    config: RunConfig = Field(default_factory=RunConfig)
    steps: List[PlanStep] = Field(default_factory=list)

    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)
    started_at: str = Field(default="")
    finished_at: str = Field(default="")

    rounds: int = Field(default=0, description="Supervisor rounds performed")
    supervisor_rounds: int = Field(default=0)
    step_runs: int = Field(default=0, description="Worker turns performed")
    stagnant_rounds: int = Field(default=0)
    pending_supervisor: bool = Field(default=True)
    wake_requested: bool = Field(default=False)

    # Informational mirrors; `spent` is recomputed from the main task cost by
    # the service on every tick (the root cost is the source of truth).
    spent_cxjcoins: float = Field(default=0.0)
    last_error: str = Field(default="")
    stop_reason: str = Field(default="")
    report_written: bool = Field(default=False)
    report_generation: int = Field(
        default=0,
        description=(
            "Number of times this run was explicitly reopened (start after "
            "stop/failure). Each generation publishes its own delivery/stop "
            "report; the idempotency marker on the main task includes it so a "
            "restarted run cannot silently lose its final report."
        )
    )

    events: List[RunEvent] = Field(default_factory=list)

    # -- helpers ---------------------------------------------------------

    def step_by_id(self, step_id: str) -> Optional[PlanStep]:
        """Return the step with *step_id*, or None."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def step_by_title(self, title: str) -> Optional[PlanStep]:
        """Return the step whose title matches (case-insensitive), or None."""
        wanted = (title or "").strip().lower()
        for step in self.steps:
            if step.title.strip().lower() == wanted:
                return step
        return None

    def add_event(self, event_type: str, message: str = "", **data: Any) -> RunEvent:
        """Append an event (bounded to the last 200) and return it."""
        event = RunEvent(type=event_type, message=_clip(message, 2000), data=data)
        self.events.append(event)
        if len(self.events) > 200:
            self.events = self.events[-200:]
        return event

    def touch(self) -> None:
        """Update the modification timestamp."""
        self.updated_at = utcnow_iso()

    def counts(self) -> Dict[str, int]:
        """Return the number of steps per status."""
        counts = {status: 0 for status in (
            C.STEP_STATUS_PENDING,
            C.STEP_STATUS_RUNNING,
            C.STEP_STATUS_DONE,
            C.STEP_STATUS_FAILED,
            C.STEP_STATUS_BLOCKED,
            C.STEP_STATUS_SKIPPED,
        )}
        for step in self.steps:
            counts[step.status] = counts.get(step.status, 0) + 1
        return counts

    def progress(self) -> int:
        """Return the completion percentage (done+skipped/total)."""
        if not self.steps:
            return 0
        finished = sum(
            1 for step in self.steps if step.status in C.SUCCESSFUL_STEP_STATUSES
        )
        return int(round(100 * finished / len(self.steps)))

    def is_terminal(self) -> bool:
        """Return True when the run no longer advances."""
        return self.status in C.TERMINAL_RUN_STATUSES

    def all_steps_terminal(self) -> bool:
        """Return True when every planned step reached a terminal status."""
        return bool(self.steps) and all(step.is_terminal() for step in self.steps)

    def has_failures(self) -> bool:
        """Return True when any step failed, was blocked or is retryable."""
        return any(
            step.status in (C.STEP_STATUS_FAILED, C.STEP_STATUS_BLOCKED)
            or (step.status == C.STEP_STATUS_PENDING and step.attempts > 0)
            for step in self.steps
        )

    def plan_signature(self) -> Tuple:
        """A cheap fingerprint of the plan, used to detect supervisor progress."""
        return tuple(
            (step.id, step.title, step.status, step.attempts)
            for step in self.steps
        )

    def remaining_budget(self) -> Optional[float]:
        """Return budget minus spent, or None when the run has no budget."""
        budget = float(self.config.budget_cxjcoins or 0.0)
        if budget <= 0:
            return None
        return budget - float(self.spent_cxjcoins or 0.0)


# ---------------------------------------------------------------------------
# Plan validation / graph
# ---------------------------------------------------------------------------


def _coerce_step(raw: Any) -> Dict[str, Any]:
    """Return a plain dict for a step given as a model or a mapping."""
    if isinstance(raw, PlanStep):
        return raw.model_dump()
    if isinstance(raw, dict):
        return dict(raw)
    raise PlanError(f"Invalid step definition: {type(raw).__name__}")


def normalize_steps(
    raw_steps: Sequence[Any],
    *,
    existing: Optional[Sequence[PlanStep]] = None,
    max_steps: int = C.DEFAULT_MAX_STEPS,
) -> List[PlanStep]:
    """
    Normalize a list of proposed steps into :class:`PlanStep` objects.

    Rules:

    * ``title`` and ``objective`` are mandatory (a task carries all its info),
    * an explicit ``id`` is kept; otherwise the id of an existing step with the
      same title is reused, and a fresh id is generated for new work,
    * ``depends_on`` may reference step ids **or** exact titles (resolved after
      every id is known),
    * unknown dependencies, self-dependencies and cycles are rejected.

    Existing steps that are not part of *raw_steps* are handled by the service
    (upsert semantics), not here.

    Args:
        raw_steps: Proposed steps (dicts or PlanStep).
        existing: Current plan, used to reuse ids by title.
        max_steps: Hard plan size.

    Returns:
        The normalized steps (status defaults to pending for new steps).

    Raises:
        PlanError: On invalid input, unknown dependency, self dependency, cycle
            or plan size overflow.
    """
    existing_by_title = {
        step.title.strip().lower(): step for step in (existing or [])
    }
    existing_by_id = {step.id: step for step in (existing or [])}

    normalized: List[PlanStep] = []
    used_ids = set(existing_by_id)
    for raw in raw_steps or []:
        data = _coerce_step(raw)
        title = _clip(data.get("title"), 300)
        objective = _clip(data.get("objective"), 8000)
        if not title:
            raise PlanError("Every step requires a non-empty title")
        if not objective:
            raise PlanError(f"Step '{title}' requires a non-empty objective")

        step_id = _clip(data.get("id"), 80)
        if not step_id:
            same_title = existing_by_title.get(title.lower())
            step_id = same_title.id if same_title else ""
        if not step_id:
            step_id = new_step_id()
        elif step_id in used_ids and step_id not in existing_by_id:
            # The proposed id collides with another new step: never produce a
            # duplicate, but keep an explicit id that identifies an existing
            # step (that is an update).
            step_id = new_step_id()
        while step_id in {step.id for step in normalized}:
            # Extremely unlikely, but never produce a duplicate id.
            step_id = new_step_id()

        previous = existing_by_id.get(step_id)
        # Status is owned by the runtime, never by a plan proposal: a supervisor
        # cannot mark a step done without a worker result.
        status = previous.status if previous else C.STEP_STATUS_PENDING
        step = PlanStep(
            id=step_id,
            title=title,
            objective=objective,
            acceptance=_clip(data.get("acceptance"), 4000),
            profile=_clip(data.get("profile"), 120).lstrip("@"),
            depends_on=_as_str_list(data.get("depends_on"), max_items=50, max_chars=120),
            files=_as_str_list(data.get("files"), max_items=100, max_chars=500),
            context=_clip(data.get("context"), 12000),
            priority=_clip(data.get("priority"), 20) or "medium",
            mode=_clip(data.get("mode"), 30),
            status=status,
            attempts=int(data.get("attempts") or (previous.attempts if previous else 0)),
            chat_id=_clip(data.get("chat_id"), 120) or (
                previous.chat_id if previous else ""
            ),
            board=_clip(data.get("board"), 200) or (previous.board if previous else ""),
            column=_clip(data.get("column"), 200) or (
                previous.column if previous else ""
            ),
            chat_status=_clip(data.get("chat_status"), 30) or (
                previous.chat_status if previous else ""
            ),
            result=(
                StepResult(**data["result"])
                if isinstance(data.get("result"), dict)
                else (data.get("result") if isinstance(data.get("result"), StepResult) else None)
            ) or (previous.result if previous else None),
            error=_clip(data.get("error"), 4000) or (previous.error if previous else ""),
            created_at=previous.created_at if previous else utcnow_iso(),
            updated_at=previous.updated_at if previous else utcnow_iso(),
            started_at=previous.started_at if previous else "",
            finished_at=previous.finished_at if previous else "",
        )
        normalized.append(step)
        used_ids.add(step_id)

    if len(normalized) > max_steps:
        raise PlanError(
            f"The plan has {len(normalized)} steps; the maximum for this run is {max_steps}"
        )

    # Resolve dependencies by title -> id. Dependencies may point at steps of
    # the current plan that are not part of this proposal (upsert semantics);
    # merge_plan validates the final graph again.
    by_title = {step.title.strip().lower(): step.id for step in normalized}
    for known in (existing or []):
        by_title.setdefault(known.title.strip().lower(), known.id)
    known_ids = {step.id for step in normalized} | set(existing_by_id)
    for step in normalized:
        resolved: List[str] = []
        for dependency in step.depends_on:
            dep_id = by_title.get(dependency.strip().lower(), dependency)
            if dep_id not in known_ids:
                raise PlanError(
                    f"Step '{step.title}' depends on unknown step '{dependency}'"
                )
            if dep_id == step.id:
                raise PlanError(f"Step '{step.title}' cannot depend on itself")
            if dep_id not in resolved:
                resolved.append(dep_id)
        step.depends_on = resolved

    detect_cycles(normalized)
    return normalized


def detect_cycles(steps: Sequence[PlanStep]) -> None:
    """
    Raise :class:`PlanError` when the dependency graph contains a cycle.

    Uses an iterative DFS (white/grey/black) so a large plan cannot hit the
    Python recursion limit.
    """
    by_id = {step.id: step for step in steps}
    white, grey, black = 0, 1, 2
    color = {step.id: white for step in steps}
    for root in steps:
        if color[root.id] != white:
            continue
        stack: List[Tuple[str, int]] = [(root.id, 0)]
        while stack:
            node_id, index = stack[-1]
            node = by_id[node_id]
            if index == 0:
                color[node_id] = grey
            if index < len(node.depends_on):
                stack[-1] = (node_id, index + 1)
                dep = node.depends_on[index]
                if color.get(dep) == grey:
                    raise PlanError(
                        f"Dependency cycle detected: '{node.title}' -> '{by_id[dep].title}'"
                    )
                if color.get(dep) == white:
                    stack.append((dep, 0))
            else:
                color[node_id] = black
                stack.pop()


def merge_plan(
    run: RunState,
    raw_steps: Sequence[Any],
    *,
    remove_step_ids: Optional[Sequence[str]] = None,
) -> List[PlanStep]:
    """
    Upsert *raw_steps* into *run*'s plan and return the new plan.

    Existing steps that are not mentioned are kept (so a supervisor does not
    accidentally drop completed work); ``remove_step_ids`` removes explicitly.
    A running step can never be removed or reset by a plan update.

    Args:
        run: The run being modified.
        raw_steps: New/updated steps.
        remove_step_ids: Step ids to remove (only non-running, non-done steps).

    Returns:
        The merged plan.

    Raises:
        PlanError: On validation errors or an attempt to modify a running step.
    """
    removals = {str(step_id).strip() for step_id in (remove_step_ids or []) if str(step_id).strip()}
    for step_id in removals:
        existing = run.step_by_id(step_id)
        if existing is None:
            raise PlanError(f"Cannot remove unknown step '{step_id}'")
        if existing.status == C.STEP_STATUS_RUNNING:
            raise PlanError(f"Cannot remove step '{existing.title}' while it is running")
        if existing.status in C.SUCCESSFUL_STEP_STATUSES:
            raise PlanError(f"Cannot remove completed step '{existing.title}'")

    proposed = normalize_steps(
        raw_steps,
        existing=run.steps,
        max_steps=run.config.max_steps,
    )

    merged_by_id = {step.id: step for step in run.steps if step.id not in removals}
    for step in proposed:
        previous = merged_by_id.get(step.id)
        if previous and previous.status == C.STEP_STATUS_RUNNING:
            # A running step keeps its execution identity; only descriptive
            # fields may be updated.
            previous.title = step.title
            previous.objective = step.objective
            previous.acceptance = step.acceptance or previous.acceptance
            previous.profile = step.profile or previous.profile
            previous.context = step.context or previous.context
            previous.files = step.files or previous.files
            previous.updated_at = utcnow_iso()
            continue
        if previous and previous.status in C.TERMINAL_STEP_STATUSES:
            # Never resurrect a terminal step implicitly; keeping the result is
            # important for the run report. A supervisor that wants a re-run
            # must use `retry_step` (or a new step).
            previous.title = step.title
            previous.objective = step.objective
            previous.acceptance = step.acceptance or previous.acceptance
            previous.profile = step.profile or previous.profile
            previous.context = step.context or previous.context
            previous.files = step.files or previous.files
            previous.depends_on = step.depends_on
            previous.updated_at = utcnow_iso()
            continue
        merged_by_id[step.id] = step

    merged = list(merged_by_id.values())
    # Recompute indices/order: keep the original order for existing steps and
    # append new ones in the order they were proposed.
    order: List[str] = []
    for step in run.steps:
        if step.id in merged_by_id and step.id not in removals:
            order.append(step.id)
    for step in proposed:
        if step.id not in order:
            order.append(step.id)
    ordered = [merged_by_id[step_id] for step_id in order if step_id in merged_by_id]

    # Validate dependencies after the merge (a removal can orphan a dependency).
    by_title = {step.title.strip().lower(): step.id for step in ordered}
    known_ids = {step.id for step in ordered}
    for step in ordered:
        resolved: List[str] = []
        for dependency in step.depends_on:
            dep_id = by_title.get(dependency.strip().lower(), dependency)
            if dep_id not in known_ids:
                raise PlanError(
                    f"Step '{step.title}' depends on removed/unknown step '{dependency}'"
                )
            if dep_id == step.id:
                raise PlanError(f"Step '{step.title}' cannot depend on itself")
            if dep_id not in resolved:
                resolved.append(dep_id)
        step.depends_on = resolved
    detect_cycles(ordered)

    if len(ordered) > run.config.max_steps:
        raise PlanError(
            f"The plan has {len(ordered)} steps; the maximum is {run.config.max_steps}"
        )
    return ordered


def ready_steps(run: RunState) -> List[PlanStep]:
    """
    Return the pending steps whose dependencies are all done/skipped.

    Order: priority (high > medium > low), then declaration order.
    """
    done = {
        step.id
        for step in run.steps
        if step.status in C.SUCCESSFUL_STEP_STATUSES
    }
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    ready = [
        step
        for step in run.steps
        if step.status == C.STEP_STATUS_PENDING
        and all(dependency in done for dependency in step.depends_on)
    ]
    ready.sort(key=lambda step: (
        priority_rank.get(str(step.priority or "").lower(), 1),
        step.created_at,
    ))
    return ready


def blocked_steps(run: RunState) -> List[PlanStep]:
    """Return pending steps that can never become ready (failed/missing deps)."""
    failed = {
        step.id
        for step in run.steps
        if step.status in (C.STEP_STATUS_FAILED, C.STEP_STATUS_BLOCKED)
    }
    blocked: List[PlanStep] = []
    for step in run.steps:
        if step.status != C.STEP_STATUS_PENDING:
            continue
        if any(dependency in failed for dependency in step.depends_on):
            blocked.append(step)
    return blocked


def next_actions(run: RunState) -> Dict[str, Any]:
    """Return a machine-readable diagnosis of what the worker should do next."""
    counts = run.counts()
    ready = ready_steps(run)
    running = counts.get(C.STEP_STATUS_RUNNING, 0)
    if running:
        return {"action": "wait", "reason": "steps_running", "steps": [s.id for s in run.steps if s.status == C.STEP_STATUS_RUNNING]}
    if ready:
        return {"action": "dispatch", "reason": "ready_steps", "steps": [s.id for s in ready]}
    if not run.steps:
        return {"action": "supervisor", "reason": "no_plan", "steps": []}
    if blocked_steps(run):
        return {"action": "supervisor", "reason": "blocked_steps", "steps": [s.id for s in blocked_steps(run)]}
    if run.all_steps_terminal():
        if run.has_failures():
            return {"action": "supervisor", "reason": "failed_steps", "steps": []}
        return {"action": "supervisor", "reason": "verify", "steps": []}
    return {"action": "supervisor", "reason": "no_progress", "steps": []}


def result_to_step_status(result: StepResult) -> str:
    """Map a :class:`StepResult` contract status onto a step status."""
    status = _normalize_result_status(result.status)
    if status in (C.STEP_STATUS_FAILED, C.STEP_STATUS_BLOCKED):
        return status
    return C.STEP_STATUS_DONE


# Made with ❤️ by codx-junior
