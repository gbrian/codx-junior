"""
Prompt and report builders for the orchestration runtime.

Keeping the prompts in one dependency-light module has two benefits:

* the supervisor and the worker contracts are versioned and testable without an
  AI call,
* the text the model sees is exactly the text the documentation describes.

The design mirrors the execution model of DSH (goal + plan + isolated workers +
verification) while the *visibility* stays in codx-junior: every step is a task
card on a board and in a sprint, and the supervisor's rounds are messages of the
main task.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

from typing import List, Optional

from . import constants as C
from .models import RunState


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------

SUPERVISOR_SYSTEM_PROMPT = """\
You are the ORCHESTRATOR (supervisor) of a durable, multi-step run inside
codx-junior. You do not do the bulk of the work yourself: you plan it, delegate
it to isolated workers, verify the results and finish the run.

## The system you run on

* The run is attached to this main task (a kanban card). Every step you plan is
  materialized as a child task card on a board and in the run sprint, so the work
  is visible to humans exactly like any other task.
* Workers run in their own chat, with their own context. They do NOT see this
  conversation: the only information they have is the step description you write.
  Therefore every step must be self-contained.
* A background worker dispatches the steps you plan. You do not need to wait:
  after your turn the worker executes the ready steps and calls you again with
  their results.
* You control the run only through the `orchestrator` tool. Never claim a step is
  running or finished unless the tool result says so.

## Your loop

1. Call `orchestrator(action="status")` when you need the current plan, budget
   and step table.
2. PLAN: decompose the objective into small, independently executable steps and
   call `orchestrator(action="plan", steps=[...])`.
3. The worker executes ready steps (respecting `depends_on`) and returns their
   structured results in the next round.
4. VERIFY: compare every result with the step's acceptance criteria. Reject weak
   results, add remediation or verification steps, or finish.
5. FINISH: call `orchestrator(action="finish", summary="...")` only when the
   objective is demonstrably achieved (or honestly report what is blocked).

## Planning rules

* Plan the smallest useful batch first (2-5 steps). For large work, plan the next
  batch after the first results; do not invent a 30-step waterfall.
* Every step must state:
  - `title`: imperative and specific,
  - `objective`: what to do, with enough context for a worker that cannot see
    this chat (paths, symbols, expected behaviour, constraints),
  - `acceptance`: how a reviewer verifies it,
  - `profile`: who should do it (pick from the available profiles/team; use an
    engineering profile for code, an analysis profile for investigation),
  - `depends_on`: ids/titles of steps that MUST be done first,
  - `files`: known relevant files (optional),
  - `context`: extra facts the worker needs (optional).
* Steps that can run at the same time must NOT depend on each other: the worker
  dispatches independent ready steps in parallel.
* Never duplicate work that is already done or running. Read the RUN STATE table.
* Add a final verification step when the acceptance of the objective is not
  trivially observable from the worker summaries.
* Prefer small, reviewable changes. Do not modify unrelated files.
* Respect the budget: each step costs money. If the remaining budget is small,
  plan fewer/smaller steps and reserve the final round for the report.

## Finishing rules

* `finish` is allowed only when every requirement of the objective is met and
  the acceptance evidence is in the results.
* The summary becomes the human delivery report: what was built, how to test it,
  files touched, known gaps.
* If the run is blocked by missing information/credentials or an unrecoverable
  error, finish with an honest blocked report instead of looping.
* If a step failed, either add a remediation step (with a different approach) or
  finish as blocked. Never repeat the exact same failed step blindly.

## Style

* Keep your visible answer short: the plan/decision in 5-15 lines.
* Put the detail in the tool arguments (steps), not in prose.
* Do not ask the user questions: choose the best reasonable interpretation.
* The RUN STATE block below is the ground truth; trust it over your memory.
"""


STEP_SYSTEM_PROMPT = """\
You are an isolated WORKER of an orchestrated run in codx-junior.

* You own exactly one step. Do the work, verify it, and report the result.
* You cannot see the supervisor conversation; your step description is your full
  contract. If a detail is missing, choose the most reasonable interpretation and
  state it in the summary. Do not ask questions.
* Use the project tools to inspect the code before changing it. Keep changes
  small, reviewable and limited to the step.
* Never touch files outside the step scope unless the step explicitly asks for it.
* Run the relevant tests or checks when possible.
* Finish with a short summary and the JSON result object requested in the step.
"""


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _clip(text: Optional[str], max_chars: int) -> str:
    """Clip *text* to *max_chars*."""
    value = (text or "").strip()
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + "\n… (truncated)"


def _step_line(step, max_summary: int = 400) -> str:
    """Render one step as a compact markdown row/block."""
    result = step.result
    summary = _clip(result.summary if result else "", max_summary)
    verification = _clip(result.verification if result else "", max_summary)
    lines = [
        f"#### [{step.id}] {step.title} — **{step.status}**"
        f" (attempt {step.attempts}, profile `{step.profile or 'default'}`)",
    ]
    if step.depends_on:
        lines.append(f"- depends on: {', '.join(step.depends_on)}")
    if step.chat_id:
        lines.append(f"- card: `{step.chat_id}`" + (
            f" ({step.board} / {step.column})" if step.board or step.column else ""
        ))
    if summary:
        lines.append(f"- summary: {summary}")
    if verification:
        lines.append(f"- verification: {verification}")
    if result and result.files:
        lines.append(f"- files: {', '.join(result.files[:20])}")
    if result and result.followups:
        lines.append(f"- follow-ups: {'; '.join(result.followups[:10])}")
    if step.error:
        lines.append(f"- error: {_clip(step.error, 1200)}")
    if result and result.error and result.error != step.error:
        lines.append(f"- runtime error: {_clip(result.error, 1200)}")
    return "\n".join(lines)


def render_plan_table(run: RunState) -> str:
    """Render the plan as a markdown table (used by the status tool/API)."""
    if not run.steps:
        return "_(no plan yet)_"
    lines = [
        "| # | Step | Status | Attempts | Profile | Depends on | Card |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, step in enumerate(run.steps, start=1):
        card = step.chat_id[:8] if step.chat_id else "—"
        dependencies = ",".join(step.depends_on) or "—"
        lines.append(
            f"| {index} | {step.title.replace('|', '\\|')} | `{step.status}` | "
            f"{step.attempts} | `{step.profile or 'default'}` | {dependencies} | {card} |"
        )
    return "\n".join(lines)


def render_run_state(run: RunState, max_result_chars: int = 900) -> str:
    """
    Render the full RUN STATE block used by the supervisor prompt.

    The block is intentionally bounded: step summaries are clipped and only the
    latest events are included, so a long run cannot blow up the supervisor
    context.
    """
    counts = run.counts()
    remaining = run.remaining_budget()
    budget_line = (
        f"budget {run.config.budget_cxjcoins:.4f} cxjcoins, "
        f"spent {run.spent_cxjcoins:.4f}, "
        f"remaining {remaining:.4f}"
        if remaining is not None
        else f"spent {run.spent_cxjcoins:.4f} cxjcoins, no hard budget"
    )
    lines = [
        "## RUN STATE",
        f"- Run: **{run.name}** (`{run.run_id}`)",
        f"- Status: **{run.status}** · round {run.rounds}/{run.config.max_rounds} · "
        f"supervisor rounds {run.supervisor_rounds}",
        f"- Objective: {_clip(run.objective, 4000)}",
        f"- {budget_line}",
        f"- Steps: {counts.get(C.STEP_STATUS_DONE, 0)} done, "
        f"{counts.get(C.STEP_STATUS_RUNNING, 0)} running, "
        f"{counts.get(C.STEP_STATUS_PENDING, 0)} pending, "
        f"{counts.get(C.STEP_STATUS_FAILED, 0)} failed, "
        f"{counts.get(C.STEP_STATUS_BLOCKED, 0)} blocked, "
        f"{counts.get(C.STEP_STATUS_SKIPPED, 0)} skipped",
        f"- Board: `{run.config.board}` · Sprint: `{run.config.sprint or 'auto'}` · "
        f"parallelism {run.config.max_parallel}",
    ]
    if run.last_error:
        lines.append(f"- Last error: {_clip(run.last_error, 1500)}")
    if run.stop_reason:
        lines.append(f"- Stop reason: {_clip(run.stop_reason, 1500)}")

    lines.append("")
    lines.append("### Plan")
    lines.append(render_plan_table(run))

    if run.steps:
        lines.append("")
        lines.append("### Step results")
        for step in run.steps:
            if step.status == C.STEP_STATUS_PENDING and not step.result:
                continue
            lines.append(_step_line(step, max_summary=max_result_chars))

    if run.events:
        lines.append("")
        lines.append("### Recent run events")
        for event in run.events[-8:]:
            lines.append(f"- {event.at} · {event.type}: {_clip(event.message, 300)}")

    return "\n".join(lines)


def build_supervisor_prompt(run: RunState, reason: str) -> str:
    """
    Build the user message of a supervisor round.

    Args:
        run: Current run state (already refreshed by the service).
        reason: ``plan`` | ``verify`` | ``replan`` | ``resume``.
    """
    plan_text = (
        "No plan exists yet. Inspect the project with your tools, decompose the "
        "objective and call `orchestrator(action=\"plan\", steps=[...])`."
    )
    verify_text = (
        "Every planned step is terminal. Verify the acceptance criteria against the "
        "results. If the objective is demonstrably achieved call `orchestrator(action=\"finish\", summary=\"...\")`; "
        "otherwise add the remediation/verification steps that are still required."
    )
    replan_text = (
        "Some steps failed, are blocked, or the plan cannot advance. Decide one of: "
        "add a remediation step with a DIFFERENT approach, retry a failed step with "
        "`orchestrator(action=\"retry_step\", step_id=...)`, remove an obsolete pending step, "
        "or finish with an honest blocked report. Never repeat the same failed step blindly."
    )
    reason_text = {
        "plan": plan_text,
        "no_plan": plan_text,
        "verify": verify_text,
        "replan": replan_text,
        "failed_steps": replan_text,
        "blocked_steps": replan_text,
        "no_progress": replan_text,
        "resume": (
            "The run was resumed. Re-read the state and continue from where it stopped."
        ),
    }.get(reason, plan_text)
    return "\n".join([
        f"### ORCHESTRATION ROUND {run.rounds + 1}",
        reason_text,
        "",
        "Remember: every step is executed by an isolated worker that cannot see this chat.",
        "",
        render_run_state(run),
        "",
        "Use the `orchestrator` tool to update the plan or finish. Your visible answer is "
        "a short note for the human watching the main task.",
    ])


# ---------------------------------------------------------------------------
# Worker contract
# ---------------------------------------------------------------------------


def build_step_contract(run: RunState, step) -> str:
    """
    Build the self-contained user message of a worker card.

    Everything a worker needs is in this text: the run objective, the step
    objective, acceptance, context and the exact result contract.
    """
    lines = [
        "# ORCHESTRATED STEP",
        f"Run: **{run.name}**",
        f"Step: **{step.title}** (`{step.id}`)",
        "",
        "## Run objective",
        _clip(run.objective, 6000),
        "",
        "## Step objective",
        _clip(step.objective, 8000),
    ]
    if step.acceptance:
        lines += ["", "## Acceptance criteria", _clip(step.acceptance, 4000)]
    if step.files:
        lines += ["", "## Known files", "\n".join(f"- `{path}`" for path in step.files[:100])]
    if step.context:
        lines += ["", "## Context", _clip(step.context, 12000)]
    lines += [
        "",
        "## Rules",
        "- Work only on this step; do not start unrelated refactors.",
        "- Inspect the code before changing it and keep the change reviewable.",
        "- Verify your work (tests, build, manual check) and say how.",
        "- If you are blocked, explain exactly what is missing instead of guessing forever.",
        "",
        "## Result contract",
        C.STEP_RESULT_INSTRUCTIONS,
    ]
    return "\n".join(lines)


def build_delegate_contract(task: str, context: str = "", parent_name: str = "") -> str:
    """Build the user message of a one-off delegated subagent card."""
    lines = ["# DELEGATED TASK"]
    if parent_name:
        lines.append(f"Requested from: **{parent_name}**")
    lines += [
        "",
        _clip(task, 8000),
    ]
    if context:
        lines += ["", "## Context", _clip(context, 12000)]
    lines += [
        "",
        "## Rules",
        "- You are an isolated subagent: this task is your full contract.",
        "- Use the project tools, keep changes scoped and verify the result.",
        "- Do not ask questions; choose the best reasonable interpretation.",
        "",
        "## Result contract",
        C.STEP_RESULT_INSTRUCTIONS,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def _report_header(run: RunState, title: str) -> List[str]:
    """Common header of a delivery/report message."""
    remaining = run.remaining_budget()
    return [
        f"## {title}",
        f"**Run:** {run.name} (`{run.run_id}`)  ",
        f"**Status:** `{run.status}`  ",
        f"**Spent:** {run.spent_cxjcoins:.4f} cxjcoins"
        + (f" of {run.config.budget_cxjcoins:.4f}" if remaining is not None else "")
        + "  ",
        f"**Rounds:** {run.rounds} · **Steps:** {run.progress()}% complete",
        "",
    ]


def _result_lines(run: RunState) -> List[str]:
    """Render the per-step result list used by reports."""
    lines = ["### Steps", ""]
    for step in run.steps:
        result = step.result
        summary = _clip(result.summary if result else "", 900) or "(no result)"
        lines.append(f"- **[{step.id}] {step.title}** — `{step.status}` · {summary}")
        if result and result.verification:
            lines.append(f"  - verification: {_clip(result.verification, 600)}")
        if result and result.files:
            lines.append(f"  - files: {', '.join(f'`{path}`' for path in result.files[:20])}")
        if step.error:
            lines.append(f"  - error: {_clip(step.error, 600)}")
    return lines


def build_delivery_report(run: RunState, summary: str) -> str:
    """Build the final delivery report published on the main task."""
    lines = _report_header(run, "Run delivery report")
    lines += [
        "### Summary",
        _clip(summary, 8000) or "_No summary provided._",
        "",
    ]
    lines += _result_lines(run)
    if run.config.budget_cxjcoins > 0:
        lines += [
            "",
            f"_Budget: {run.spent_cxjcoins:.4f} / {run.config.budget_cxjcoins:.4f} cxjcoins._",
        ]
    return "\n".join(lines)


def build_budget_report(run: RunState) -> str:
    """Build the no-AI report used when the budget is exhausted."""
    lines = _report_header(run, "Run stopped: budget exhausted")
    lines += [
        "The run reached its budget before finishing. No additional AI turn was spent.",
        "",
        "### What was completed",
        "",
    ]
    lines += _result_lines(run)
    lines += [
        "",
        "### Remaining work",
        "",
        "Review the pending/blocked steps above and start a new run (or raise the "
        "budget) to continue. The cards and their contexts are preserved on the board.",
    ]
    return "\n".join(lines)


def build_stall_report(run: RunState, reason: str) -> str:
    """Build the no-AI report used when the run stalls."""
    lines = _report_header(run, "Run stopped: stalled")
    lines += [
        f"The run made no progress for {run.stagnant_rounds} supervisor round(s): "
        f"{_clip(reason, 1500)}",
        "",
        "### What was completed",
        "",
    ]
    lines += _result_lines(run)
    lines += [
        "",
        "### Next step for a human",
        "",
        "Inspect the blocked/failed cards, adjust the objective or the plan, then "
        "resume the run (or start a new one).",
    ]
    return "\n".join(lines)


def build_failure_report(run: RunState, error: str) -> str:
    """Build the report used when the run fails unrecoverably."""
    lines = _report_header(run, "Run failed")
    lines += [
        "### Error",
        _clip(error, 4000) or "_Unknown error._",
        "",
    ]
    lines += _result_lines(run)
    return "\n".join(lines)


def build_stopped_report(run: RunState, reason: str = "") -> str:
    """Build the report used when a human stops the run."""
    lines = _report_header(run, "Run stopped by user")
    if reason:
        lines += ["### Reason", _clip(reason, 2000), ""]
    lines += _result_lines(run)
    return "\n".join(lines)

# Made with ❤️ by codx-junior
