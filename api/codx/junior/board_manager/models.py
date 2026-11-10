"""
Data model of the board manager.

The board document keeps only the **configuration** (enabled, profile,
interval, mode, instructions). Everything that changes at runtime (last run,
actions taken, last report, cost) lives in the project state store
(:mod:`codx.junior.board_manager.store`), so a review never rewrites the board
catalogue and a task save never races with a manager write.

The decision contract parsed here is deliberately small and strict: the model
returns ``{"summary": "...", "actions": [...]}`` and the service validates every
action against the real board before applying it.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from pydantic import BaseModel, Field

from . import constants as C

logger = logging.getLogger(__name__)


def utcnow_iso() -> str:
    """Return the current UTC instant as an ISO-8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()


def _clip(value: Any, max_chars: int) -> str:
    """Convert *value* to a stripped string clipped to *max_chars*."""
    text = ("" if value is None else str(value)).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"


def _as_str_list(value: Any, max_items: int = 50, max_chars: int = 200) -> List[str]:
    """Normalize a string/iterable into a de-duplicated list of short strings."""
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


def _as_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    """Clamp *value* into ``[minimum, maximum]`` with a safe fallback."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))


# ---------------------------------------------------------------------------
# Configuration (stored on the board document)
# ---------------------------------------------------------------------------


class BoardManagerConfig(BaseModel):
    """
    Per-board automation policy.

    Attributes:
        enabled: When False the worker never reviews the board.
        profile: Profile name that acts as the board manager. Empty falls back
            to the board assistant (``board.assignee``) and then to
            :data:`codx.junior.board_manager.constants.DEFAULT_PROFILE`.
        mode: ``apply`` writes the actions, ``suggest`` only records them.
        interval_minutes: Minimum time between two automatic reviews.
        max_actions: Upper bound of actions applied in one review.
        include_done: Whether closed tasks are also sent to the model (they are
            never modified; they provide context).
        instructions: Extra, board-specific policy written by the user.
        max_tasks: How many tasks the prompt includes.
    """

    enabled: bool = False
    profile: str = ""
    mode: str = C.MODE_APPLY
    interval_minutes: int = C.DEFAULT_INTERVAL_MINUTES
    max_actions: int = C.DEFAULT_MAX_ACTIONS
    include_done: bool = False
    instructions: str = ""
    max_tasks: int = C.DEFAULT_MAX_TASKS

    def normalized(self) -> "BoardManagerConfig":
        """Return a clamped copy (never mutate the input)."""
        data = self.model_dump()
        data["profile"] = _clip(data.get("profile"), 120).lstrip("@")
        mode = str(data.get("mode") or C.MODE_APPLY).strip().lower()
        data["mode"] = mode if mode in C.MODES else C.MODE_APPLY
        data["interval_minutes"] = _as_int(
            data.get("interval_minutes"),
            C.DEFAULT_INTERVAL_MINUTES,
            C.MIN_INTERVAL_MINUTES,
            C.MAX_INTERVAL_MINUTES,
        )
        data["max_actions"] = _as_int(
            data.get("max_actions"),
            C.DEFAULT_MAX_ACTIONS,
            1,
            C.MAX_ACTIONS_LIMIT,
        )
        data["max_tasks"] = _as_int(
            data.get("max_tasks"),
            C.DEFAULT_MAX_TASKS,
            1,
            C.MAX_TASKS_LIMIT,
        )
        data["instructions"] = _clip(data.get("instructions"), 8000)
        data["enabled"] = bool(data.get("enabled"))
        data["include_done"] = bool(data.get("include_done"))
        return BoardManagerConfig(**data)

    @classmethod
    def from_board(cls, board: Optional[Dict[str, Any]]) -> "BoardManagerConfig":
        """
        Read the manager configuration of a board document.

        The board assistant (``assignee``) is the fallback profile: a board that
        already declares who answers its chat has a sensible default manager
        without a second selection.
        """
        board = board if isinstance(board, dict) else {}
        raw = board.get(C.BOARD_CONFIG_KEY)
        if not isinstance(raw, dict):
            raw = {}
        profile = _clip(raw.get("profile"), 120) or _clip(board.get("assignee"), 120)
        return cls(
            enabled=bool(raw.get("enabled")),
            profile=profile,
            mode=raw.get("mode") or C.MODE_APPLY,
            interval_minutes=raw.get("interval_minutes") or C.DEFAULT_INTERVAL_MINUTES,
            max_actions=raw.get("max_actions") or C.DEFAULT_MAX_ACTIONS,
            include_done=bool(raw.get("include_done")),
            instructions=raw.get("instructions") or "",
            max_tasks=raw.get("max_tasks") or C.DEFAULT_MAX_TASKS,
        ).normalized()

    def to_board_value(self, fallback_profile: str = "") -> Dict[str, Any]:
        """Return the JSON value stored on the board document."""
        data = self.normalized().model_dump()
        if not data["profile"]:
            data["profile"] = _clip(fallback_profile, 120)
        return data


# ---------------------------------------------------------------------------
# Decision contract
# ---------------------------------------------------------------------------


class ManagerAction(BaseModel):
    """One requested change. Unknown fields from the model are kept as extras."""

    type: str = Field(default="")
    task_id: str = Field(default="")
    column: str = Field(default="")
    status: str = Field(default="")
    comment: str = Field(default="")
    reason: str = Field(default="")
    priority: str = Field(default="")
    due_date: str = Field(default="")
    progress: Optional[int] = Field(default=None)
    assignees: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    name: str = Field(default="")
    description: str = Field(default="")


class ManagerDecision(BaseModel):
    """The parsed answer of the manager profile."""

    summary: str = Field(default="")
    actions: List[ManagerAction] = Field(default_factory=list)
    parse_error: str = Field(default="")
    raw_content: str = Field(default="")


def _extract_json_candidates(text: str) -> List[str]:
    """
    Return JSON-looking fragments of *text*, most likely contract first.

    Fenced blocks first (the contract asks for a fenced JSON answer), then
    balanced objects scanning backwards because the contract is normally the
    last thing the model writes.
    """
    candidates: List[str] = []
    for match in re.finditer(r"```(?:json)?\s*\n?(.*?)```", text, re.S | re.I):
        block = (match.group(1) or "").strip()
        if block.startswith(("{", "[")):
            candidates.append(block)

    positions = [index for index, char in enumerate(text) if char in "{["]
    for start in reversed(positions[-50:]):
        opening = text[start]
        closing = "}" if opening == "{" else "]"
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
            elif char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    candidates.append(text[start:index + 1])
                    break

    seen = set()
    ordered: List[str] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def normalize_action_type(value: Any) -> str:
    """Map the many verbs a model may use onto the supported action types."""
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return C.ACTION_ALIASES.get(text, text)


def _coerce_action(raw: Any) -> Optional[ManagerAction]:
    """Build a :class:`ManagerAction` from a model-provided mapping."""
    if not isinstance(raw, dict):
        return None
    action = ManagerAction(
        type=normalize_action_type(raw.get("type") or raw.get("action")),
        task_id=_clip(
            raw.get("task_id") or raw.get("chat_id") or raw.get("id"), 120
        ),
        column=_clip(raw.get("column") or raw.get("to_column"), 200),
        status=_clip(raw.get("status") or raw.get("state"), 80),
        comment=_clip(raw.get("comment") or raw.get("message") or raw.get("note"), 4000),
        reason=_clip(raw.get("reason"), 1000),
        priority=_clip(raw.get("priority"), 40).lower(),
        due_date=_clip(raw.get("due_date") or raw.get("due"), 40),
        progress=(
            _as_int(raw.get("progress"), 0, 0, 100)
            if raw.get("progress") is not None
            else None
        ),
        assignees=_as_str_list(raw.get("assignees") or raw.get("users")),
        tags=_as_str_list(raw.get("tags")),
        name=_clip(raw.get("name") or raw.get("title"), 300),
        description=_clip(raw.get("description"), 8000),
    )
    return action


def parse_decision(content: str) -> ManagerDecision:
    """
    Parse the manager answer into a :class:`ManagerDecision`.

    Never raises: a model that ignores the contract yields a decision with no
    actions and a ``parse_error`` (the report still reaches the user). A fenced
    JSON block, a bare object and a bare list of actions are all accepted.
    """
    text = content or ""
    payload: Any = None
    for candidate in _extract_json_candidates(text):
        try:
            parsed = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if isinstance(parsed, dict) and (
            "actions" in parsed or "summary" in parsed or "report" in parsed
        ):
            payload = parsed
            break
        if isinstance(parsed, list):
            payload = {"actions": parsed}
            break

    if payload is None:
        return ManagerDecision(
            summary=_clip(text, 8000),
            parse_error=(
                "The manager answer did not contain a JSON object with an "
                "'actions' list"
            ),
            raw_content=_clip(text, 12000),
        )

    if isinstance(payload, dict):
        raw_actions = payload.get("actions")
        if raw_actions is None:
            raw_actions = []
        if not isinstance(raw_actions, list):
            raw_actions = []
        actions = [
            action for action in (_coerce_action(raw) for raw in raw_actions) if action
        ]
        summary = payload.get("summary") or payload.get("report") or payload.get("message")
        return ManagerDecision(
            summary=_clip(summary, 8000),
            actions=actions,
            raw_content=_clip(text, 12000),
        )

    return ManagerDecision(raw_content=_clip(text, 12000))


# ---------------------------------------------------------------------------
# Runtime state
# ---------------------------------------------------------------------------


class ActionRecord(BaseModel):
    """What happened to one proposed action."""

    at: str = Field(default_factory=utcnow_iso)
    type: str = Field(default="")
    task_id: str = Field(default="")
    task_name: str = Field(default="")
    proposed: Dict[str, Any] = Field(default_factory=dict)
    applied: bool = Field(default=False)
    summary: str = Field(default="")
    error: str = Field(default="")


class ManagerState(BaseModel):
    """Persisted runtime state of one board manager."""

    board: str = Field(default="")
    board_id: str = Field(default="")
    running: bool = Field(default=False)
    wake_requested: bool = Field(default=False)
    last_run_at: str = Field(default="")
    last_finished_at: str = Field(default="")
    last_status: str = Field(default="")
    last_error: str = Field(default="")
    last_summary: str = Field(default="")
    last_report: str = Field(default="")
    last_cost: float = Field(default=0.0)
    total_cost: float = Field(default=0.0)
    runs: int = Field(default=0)
    duration_ms: float = Field(default=0.0)
    last_profile: str = Field(default="")
    last_actions: List[ActionRecord] = Field(default_factory=list)

    def mark_run_started(self, board: str, board_id: str, profile: str) -> None:
        """
        Set the in-flight markers before the AI call.

        The previous report/actions are kept: the UI shows "running" while the
        review is in flight and the last useful report remains visible until the
        new one replaces it (or an error is recorded).
        """
        self.board = board
        self.board_id = board_id
        self.running = True
        self.wake_requested = False
        self.last_run_at = utcnow_iso()
        self.last_profile = profile

    def mark_finished(
        self,
        *,
        status: str,
        report: str = "",
        summary: str = "",
        error: str = "",
        cost: float = 0.0,
        duration_ms: float = 0.0,
        actions: Optional[Sequence[ActionRecord]] = None,
    ) -> None:
        """Record a finished review (success or failure)."""
        self.running = False
        self.wake_requested = False
        self.last_finished_at = utcnow_iso()
        self.last_status = status
        self.last_report = _clip(report, 20000)
        self.last_summary = _clip(summary, 8000)
        self.last_error = _clip(error, 4000)
        self.last_cost = max(0.0, float(cost or 0.0))
        self.total_cost = float(self.total_cost or 0.0) + self.last_cost
        self.duration_ms = max(0.0, float(duration_ms or 0.0))
        self.runs = int(self.runs or 0) + 1
        self.last_actions = list(actions or [])

    def public(self) -> Dict[str, Any]:
        """Return the API/UI shape of the state."""
        return self.model_dump()

# Made with ❤️ by codx-junior
