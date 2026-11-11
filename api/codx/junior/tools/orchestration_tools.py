"""
LLM tools of the orchestration runtime.

Two tools are exposed:

``orchestrator``
    Run control for the **main task** of a run: start (promote this chat to a
    run), plan/add/retry/remove steps, inspect status, pause/resume/stop and
    finish. Injected by the agent runtime for run supervisors, and available to
    the built-in ``orchestrator`` profile for normal chats.

``delegate``
    DSH-style subagent/fan-out for a **normal chat**: one or more self-contained
    tasks are executed in isolated contexts and materialized as cards on the
    board. With ``wait=False`` the delegation becomes a durable run processed by
    the background worker.

Both tools are stateful and therefore opt out of the SmolAgent tool cache.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from .model import ToolResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

_STEP_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "description": "Step id (omit for new steps; reuse to update an existing step).",
        },
        "title": {
            "type": "string",
            "description": "Short imperative title (it becomes the card title).",
        },
        "objective": {
            "type": "string",
            "description": (
                "Self-contained work description. The worker cannot see this "
                "conversation, so include paths, symbols, expected behaviour and "
                "constraints."
            ),
        },
        "acceptance": {
            "type": "string",
            "description": "How a reviewer verifies the step (tests, observable behaviour).",
        },
        "profile": {
            "type": "string",
            "description": "Profile that should execute the step (e.g. software_developer, analyst).",
        },
        "depends_on": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Ids or exact titles of steps that must finish first.",
        },
        "files": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Known relevant project files.",
        },
        "context": {
            "type": "string",
            "description": "Extra facts the worker needs (decisions, constraints, prior findings).",
        },
        "priority": {
            "type": "string",
            "enum": ["high", "medium", "low"],
            "description": "Ordering hint for ready steps.",
        },
        "mode": {
            "type": "string",
            "description": "Optional chat mode override for the worker card (task, chat...).",
        },
    },
    "required": ["title", "objective"],
}

ORCHESTRATOR_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "orchestrator",
        "description": (
            "Control a durable, board-native orchestration run attached to this "
            "task. Use action='status' to read the plan, 'plan' to decompose the "
            "objective into isolated worker steps, 'finish' when the objective is "
            "demonstrably achieved. Every step becomes a task card on a board and "
            "in the run sprint; a background worker executes the ready steps and "
            "returns their structured results in the next round. The full run "
            "state is persisted and survives restarts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "start",
                        "plan",
                        "add_step",
                        "status",
                        "finish",
                        "pause",
                        "resume",
                        "stop",
                        "retry_step",
                        "remove_step",
                    ],
                    "description": "Operation to perform.",
                },
                "name": {
                    "type": "string",
                    "description": "Run name (action='start').",
                },
                "objective": {
                    "type": "string",
                    "description": "What the run must achieve (action='start'). Include all context.",
                },
                "budget_cxjcoins": {
                    "type": "number",
                    "description": "Hard budget for the whole run (0 = no hard budget).",
                },
                "per_step_budget": {
                    "type": "number",
                    "description": "Optional cap per worker step.",
                },
                "supervisor_reserve": {
                    "type": "number",
                    "description": "Cost reserved for the final supervisor/verification round.",
                },
                "max_steps": {"type": "integer", "description": "Maximum plan size."},
                "max_rounds": {"type": "integer", "description": "Maximum supervisor rounds."},
                "max_parallel": {
                    "type": "integer",
                    "description": "Maximum independent steps executed at the same time (1-4).",
                },
                "verification": {
                    "type": "string",
                    "enum": ["supervisor", "none"],
                    "description": "How results are verified.",
                },
                "board": {"type": "string", "description": "Board title for the step cards."},
                "sprint": {"type": "string", "description": "Sprint title for the run (default 'Run: <name>')."},
                "profiles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Supervisor profile(s) for the run.",
                },
                "steps": {
                    "type": "array",
                    "items": _STEP_SCHEMA,
                    "description": "Steps to upsert into the plan (action='plan').",
                },
                "step": {
                    "type": "object",
                    "description": "Single step to add (action='add_step').",
                },
                "step_id": {
                    "type": "string",
                    "description": "Step id (action='retry_step').",
                },
                "step_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Step ids to remove (action='remove_step').",
                },
                "summary": {
                    "type": "string",
                    "description": "Delivery/stop summary (action='finish').",
                },
            },
            "required": ["action"],
        },
    },
}

DELEGATE_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "delegate",
        "description": (
            "Delegate one or more self-contained tasks to isolated subagents. "
            "Each task runs in its own chat with a fresh context and is "
            "materialized as a visible task card on the board/sprint. Use this "
            "for independent research or workstreams that should not consume "
            "this conversation's context. With wait=false the work becomes a "
            "durable run that the background worker executes; with wait=true the "
            "structured results are returned in this turn."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Single self-contained task (alternative to 'tasks').",
                },
                "tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Self-contained tasks (max 8). Independent tasks run in parallel.",
                },
                "profile": {
                    "type": "string",
                    "description": "Optional profile for the subagents.",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Relevant project files shared by every subagent.",
                },
                "context": {
                    "type": "string",
                    "description": "Extra context added to every task contract.",
                },
                "board": {"type": "string", "description": "Board for the subagent cards."},
                "column": {"type": "string", "description": "Column for the subagent cards."},
                "concurrency": {
                    "type": "integer",
                    "description": "Maximum simultaneous subagents (1-4).",
                },
                "wait": {
                    "type": "boolean",
                    "description": "True: return the results now. False: create a durable run.",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Per-subagent timeout in seconds.",
                },
            },
            "required": [],
        },
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _current_chat(session: Any, settings: Any) -> Any:
    """Resolve the chat that is executing the current turn."""
    chat = getattr(session, "_current_chat", None) if session is not None else None
    if chat is None:
        active = getattr(settings, "_active_session", None)
        chat = getattr(active, "_current_chat", None)
    if chat is None:
        raise ValueError(
            "orchestration tools require an active chat (the agent runtime must "
            "inject the session/chat context)"
        )
    return chat


def _service(settings: Any, session: Any):
    """Build an OrchestrationService bound to the current project/session."""
    from codx.junior.orchestration.service import OrchestrationService

    chat_manager = None
    if session is not None:
        try:
            chat_manager = session.get_chat_manager()
        except Exception:  # pragma: no cover - defensive
            chat_manager = None
    return OrchestrationService(
        settings=settings,
        chat_manager=chat_manager,
        event_manager=getattr(session, "event_manager", None) if session is not None else None,
        user=getattr(session, "user", None) if session is not None else None,
    )


def _json(payload: Any) -> str:
    """Serialize a tool payload for the model."""
    try:
        return json.dumps(payload, default=str)
    except (TypeError, ValueError):
        return json.dumps(str(payload))


def _config_from_args(
    *,
    budget_cxjcoins: Optional[float],
    per_step_budget: Optional[float],
    supervisor_reserve: Optional[float],
    max_steps: Optional[int],
    max_rounds: Optional[int],
    max_parallel: Optional[int],
    verification: Optional[str],
    board: Optional[str],
    sprint: Optional[str],
    profiles: Optional[List[str]],
):
    """Build a RunConfig from the tool arguments (only provided values)."""
    from codx.junior.orchestration.models import RunConfig

    data: Dict[str, Any] = {}
    for key, value in (
        ("budget_cxjcoins", budget_cxjcoins),
        ("per_step_budget", per_step_budget),
        ("supervisor_reserve", supervisor_reserve),
        ("max_steps", max_steps),
        ("max_rounds", max_rounds),
        ("max_parallel", max_parallel),
        ("verification", verification),
        ("board", board),
        ("sprint", sprint),
    ):
        if value is not None and value != "":
            data[key] = value
    if profiles:
        data["supervisor_profiles"] = [str(name).lstrip("@") for name in profiles]
    return RunConfig(**data)


def _status_text(payload: Dict[str, Any]) -> str:
    """Human-readable run status for the chat (the user sees this)."""
    lines = [
        f"### Run `{payload.get('name')}` — **{payload.get('status')}**",
        f"- Progress: {payload.get('progress', 0)}% · rounds {payload.get('rounds', 0)}",
        f"- Budget: spent {payload.get('spent_cxjcoins', 0):.4f}"
        + (
            f" / {payload.get('config', {}).get('budget_cxjcoins', 0):.4f}"
            if payload.get("config", {}).get("budget_cxjcoins")
            else " (no hard budget)"
        ),
        f"- Board `{payload.get('config', {}).get('board')}` · "
        f"Sprint `{payload.get('config', {}).get('sprint')}`",
        "",
        payload.get("plan_table", ""),
    ]
    if payload.get("next_action"):
        action = payload["next_action"]
        lines += ["", f"- Next: `{action.get('action')}` ({action.get('reason')})"]
    return "\n".join(line for line in lines if line is not None)


# ---------------------------------------------------------------------------
# `orchestrator` handler
# ---------------------------------------------------------------------------


async def orchestrator(
    action: str,
    name: Optional[str] = None,
    objective: Optional[str] = None,
    budget_cxjcoins: Optional[float] = None,
    per_step_budget: Optional[float] = None,
    supervisor_reserve: Optional[float] = None,
    max_steps: Optional[int] = None,
    max_rounds: Optional[int] = None,
    max_parallel: Optional[int] = None,
    verification: Optional[str] = None,
    board: Optional[str] = None,
    sprint: Optional[str] = None,
    profiles: Optional[List[str]] = None,
    steps: Optional[List[Dict[str, Any]]] = None,
    step: Optional[Dict[str, Any]] = None,
    step_id: Optional[str] = None,
    step_ids: Optional[List[str]] = None,
    summary: Optional[str] = None,
    settings: Any = None,
    session: Any = None,
) -> ToolResponse:
    """
    Execute one ``orchestrator`` action.

    See :data:`ORCHESTRATOR_TOOL_JSON` for the schema. Every action validates
    that it is executed from the run's main task.
    """
    if settings is None:
        raise ValueError("orchestrator requires project settings")
    chat = _current_chat(session=session, settings=settings)
    service = _service(settings, session)
    action = (action or "").strip().lower()

    if action == "start":
        if getattr(chat, "run_id", None):
            run = service.get(chat.run_id)
            return ToolResponse(
                user_response=f"ℹ️ This task is already the main task of run `{run.name}`.",
                llm_response=_json({
                    "status": "exists",
                    "run": service.summary(run.run_id),
                }),
            )
        # Default supervisor: the profiles active in THIS chat (the mentioned
        # profiles, e.g. `codx-junior`). The harness profile therefore stays
        # the accountable supervisor of its own run instead of falling back to
        # the generic orchestrator profile.
        if not profiles:
            profiles = [
                str(name).strip().lstrip("@")
                for name in (getattr(chat, "profiles", None) or [])
                if str(name).strip().lstrip("@")
            ]
        config = _config_from_args(
            budget_cxjcoins=budget_cxjcoins,
            per_step_budget=per_step_budget,
            supervisor_reserve=supervisor_reserve,
            max_steps=max_steps,
            max_rounds=max_rounds,
            max_parallel=max_parallel,
            verification=verification,
            board=board,
            sprint=sprint,
            profiles=profiles,
        )
        run = service.attach_run(
            chat,
            name=name or getattr(chat, "name", "") or "Orchestration run",
            objective=objective or "",
            config=config,
            created_by=getattr(getattr(session, "user", None), "username", "") or "",
            start=True,
            persist_main=False,
        )
        return ToolResponse(
            user_response=(
                f"🚀 Run **{run.name}** started.\n"
                f"- Board: `{run.config.board}` · Sprint: `{run.config.sprint}`\n"
                f"- Budget: {run.config.budget_cxjcoins or 'none'} cxjcoins\n"
                "The background worker will plan the first steps on the next tick."
            ),
            llm_response=_json({
                "status": "started",
                "run": service.summary(run.run_id),
            }),
        )

    if not getattr(chat, "run_id", None):
        if action == "status":
            return ToolResponse(
                user_response=(
                    "ℹ️ This task is not an orchestration run yet. Use "
                    "`orchestrator(action=\"start\", objective=..., budget_cxjcoins=...)` "
                    "to turn it into a durable run."
                ),
                llm_response=_json({"status": "no_run"}),
            )
        raise ValueError(
            "This task is not an orchestration run. Call action='start' first "
            "(with an objective and a budget)."
        )

    run_id = chat.run_id
    if action == "status":
        payload = service.status(run_id, include_events=False)
        return ToolResponse(
            user_response=_status_text(payload),
            llm_response=_json(payload),
        )

    if action == "plan":
        if not steps:
            raise ValueError("action='plan' requires a non-empty 'steps' array")
        run = service.plan(run_id, steps, actor_chat_id=chat.id)
        payload = service.status(run_id, include_events=False)
        return ToolResponse(
            user_response=(
                f"🗂️ Plan updated: **{len(run.steps)} step(s)**.\n\n"
                f"{payload['plan_table']}"
            ),
            llm_response=_json({
                "status": "planned",
                "steps": [step.as_summary() for step in run.steps],
                "next_action": payload["next_action"],
            }),
        )

    if action == "add_step":
        if not step:
            raise ValueError("action='add_step' requires a 'step' object")
        run = service.add_step(run_id, step, actor_chat_id=chat.id)
        payload = service.status(run_id, include_events=False)
        return ToolResponse(
            user_response=(
                f"➕ Step added. Plan now has **{len(run.steps)} step(s)**.\n\n"
                f"{payload['plan_table']}"
            ),
            llm_response=_json({
                "status": "step_added",
                "steps": [item.as_summary() for item in run.steps],
                "next_action": payload["next_action"],
            }),
        )

    if action == "retry_step":
        if not step_id:
            raise ValueError("action='retry_step' requires 'step_id'")
        service.retry_step(run_id, step_id, actor_chat_id=chat.id)
        return ToolResponse(
            user_response=f"🔁 Step `{step_id}` queued for retry.",
            llm_response=_json({"status": "retry", "step_id": step_id}),
        )

    if action == "remove_step":
        if not step_ids:
            raise ValueError("action='remove_step' requires 'step_ids'")
        run = service.remove_steps(run_id, step_ids, actor_chat_id=chat.id)
        return ToolResponse(
            user_response=f"🗑️ Removed {len(step_ids)} step(s). Plan now has {len(run.steps)}.",
            llm_response=_json({"status": "removed", "steps": len(run.steps)}),
        )

    if action == "finish":
        if not summary:
            raise ValueError("action='finish' requires a 'summary' delivery report")
        run = service.finish(run_id, summary, actor_chat_id=chat.id, main_chat=chat)
        # Keep the IN-MEMORY chat in sync: the engine saves this object at the
        # end of the turn and would otherwise overwrite the completed mirror.
        chat.status = "done"
        chat.run_status = run.status
        chat.progress = 100
        return ToolResponse(
            user_response="✅ Run marked as **completed**. The delivery report is on the main task.",
            llm_response=_json({
                "status": "completed",
                "run_id": run.run_id,
                "progress": run.progress(),
            }),
        )

    if action in ("pause", "resume", "stop"):
        # Control actions are only valid from the main task as well.
        service.assert_actor(service.get(run_id), chat.id)
        if action == "pause":
            run = service.pause(run_id, summary or "")
            chat.status = "onhold"
        elif action == "resume":
            run = service.resume(run_id)
            chat.status = "doing"
        else:
            run = service.stop(run_id, summary or "", main_chat=chat)
            chat.status = "onhold"
        chat.run_status = run.status
        return ToolResponse(
            user_response=f"Run **{run.name}** is now `{run.status}`.",
            llm_response=_json({"status": run.status, "run_id": run.run_id}),
        )

    raise ValueError(f"Unknown orchestrator action '{action}'")


# ---------------------------------------------------------------------------
# `delegate` handler
# ---------------------------------------------------------------------------


async def delegate(
    task: Optional[str] = None,
    tasks: Optional[List[str]] = None,
    profile: Optional[str] = None,
    files: Optional[List[str]] = None,
    board: Optional[str] = None,
    column: Optional[str] = None,
    concurrency: Optional[int] = None,
    wait: bool = True,
    context: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    settings: Any = None,
    session: Any = None,
) -> ToolResponse:
    """
    Execute a ``delegate`` call: isolated subagents as visible task cards.

    Args:
        task/tasks: One task or a list of self-contained tasks.
        profile: Optional profile for the subagents.
        files: Relevant files.
        board/column: Card destination.
        concurrency: Max simultaneous subagents.
        wait: Wait for results (True) or create a durable run (False).
        context: Extra context for every contract.
        timeout_seconds: Per-subagent timeout.
    """
    if settings is None:
        raise ValueError("delegate requires project settings")
    chat = _current_chat(session=session, settings=settings)
    service = _service(settings, session)

    clean_tasks: List[str] = []
    if task and str(task).strip():
        clean_tasks.append(str(task).strip())
    for item in tasks or []:
        text = str(item or "").strip()
        if text:
            clean_tasks.append(text)
    if not clean_tasks:
        raise ValueError("delegate requires 'task' or 'tasks'")

    outcome = await service.delegate(
        chat,
        clean_tasks,
        profile=(profile or "").lstrip("@"),
        files=files,
        board=board,
        column=column,
        concurrency=int(concurrency or 2),
        wait=bool(wait),
        context=context or "",
        timeout=float(timeout_seconds) if timeout_seconds else None,
    )

    if outcome.get("mode") == "run":
        return ToolResponse(
            user_response=(
                "🚀 Delegation queued as a durable run "
                f"`{outcome.get('run_id')}`. The cards and the sprint are on the board; "
                "the background worker will execute the tasks."
            ),
            llm_response=_json(outcome),
        )

    results = outcome.get("results") or []
    lines = [f"### Delegation finished ({len(results)} task(s))", ""]
    for index, result in enumerate(results, start=1):
        lines.append(
            f"{index}. **{result.get('status')}** — {result.get('summary')}"
            + (f" (card `{result.get('chat_id')}`)" if result.get("chat_id") else "")
        )
        if result.get("verification"):
            lines.append(f"   - verification: {result['verification']}")
    return ToolResponse(
        user_response="\n".join(lines),
        llm_response=_json(outcome),
    )

# Made with ❤️ by codx-junior
