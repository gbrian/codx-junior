"""
Offline tests for the board-native orchestration runtime.

The tests use the real :class:`RunStore` (atomic JSON + flock) and small fakes
for the chat manager, board and executor, so they exercise the state machine,
plan graph, budget and parallelism without an AI provider or a database.

Run with::

    cd api && pytest tests/test_orchestration.py -q
"""

import asyncio
import os
import threading
import time
from types import SimpleNamespace

import pytest

from codx.junior.orchestration import constants as C
from codx.junior.orchestration.board import RunBoard
from codx.junior.orchestration.models import (
    PlanError,
    RunConfig,
    RunState,
    StepResult,
    merge_plan,
    next_actions,
    normalize_steps,
    parse_step_result,
    ready_steps,
    result_to_step_status,
)
from codx.junior.orchestration.service import OrchestrationService
from codx.junior.orchestration.store import RunLock, RunStore


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeChat:
    """The subset of ``Chat`` the orchestration runtime touches."""

    def __init__(self, chat_id, name="card", **kwargs):
        self.id = chat_id
        self.name = name
        self.description = ""
        self.cost = 0.0
        self.estimation_cost = None
        self.profiles = []
        self.messages = []
        self.status = "todo"
        self.board = "kanban"
        self.column = "tasks"
        self.sprints = []
        self.tags = []
        self.file_list = []
        self.run_id = None
        self.run_status = None
        self.run_step_id = None
        self.progress = 0
        self.updated_at = ""
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeChatManager:
    """In-memory ChatManager with the methods used by the service/board."""

    def __init__(self):
        self.chats = {}
        self.kanban = {"version": 2, "boards": {}, "tags": {}}
        self.persisted = []

    def add(self, chat):
        self.chats[chat.id] = chat
        return chat

    def find_by_id(self, chat_id):
        return self.chats.get(chat_id)

    def save_chat(self, chat, chat_only=False):
        self.chats[chat.id] = chat
        self.persisted.append(chat.id)
        return chat

    def add_message(self, chat, message):
        chat.messages.append(message)
        return chat

    def load_kanban(self):
        return self.kanban

    def save_kanban(self, kanban):
        self.kanban = kanban


class FakeBoard:
    """Board double used by service tests (records every transition)."""

    def __init__(self, manager):
        self.manager = manager
        self.calls = []
        self.delegate_cards = []

    def ensure_run(self, run):
        run.config.board = run.config.board or C.DEFAULT_BOARD
        run.config.sprint = run.config.sprint or f"Run: {run.name}"
        return run

    def create_main_task(self, run, profiles=None, estimation_cost=None):
        chat = FakeChat("main", name=run.name, run_id=run.run_id)
        chat.estimation_cost = estimation_cost
        self.manager.add(chat)
        return chat

    def create_step_card(self, run, step, content, description, profiles=None, estimation_cost=None):
        card = FakeChat(f"card-{step.id}", name=step.title)
        card.run_id = run.run_id
        card.run_step_id = step.id
        card.estimation_cost = estimation_cost
        card.messages.append(SimpleNamespace(role="user", content=content))
        self.manager.add(card)
        step.chat_id = card.id
        self.calls.append(("create_step", step.id))
        return card

    def update_step_card(self, run, step, result=None, persist=True):
        card = self.manager.find_by_id(step.chat_id)
        if card is not None:
            card.run_id = run.run_id
            card.run_step_id = step.id
            card.status = C.STEP_CHAT_STATUS.get(step.status, "todo")
        self.calls.append(("update_step", step.id, step.status))
        return card

    def attach_main(self, run, chat, persist=False, move=False, status=None, progress=None):
        chat.run_id = run.run_id
        chat.run_status = run.status
        if status:
            chat.status = status
        if progress is not None:
            chat.progress = progress
        return chat

    def update_main_card(self, run, **kwargs):
        card = self.manager.find_by_id(run.main_chat_id)
        if card is not None:
            if kwargs.get("status"):
                card.status = kwargs["status"]
            if kwargs.get("run_status"):
                card.run_status = kwargs["run_status"]
            if kwargs.get("progress") is not None:
                card.progress = kwargs["progress"]
            if kwargs.get("column_phase"):
                card.column = kwargs["column_phase"]
        self.calls.append(("update_main", kwargs))
        return card

    def create_delegate_card(self, parent_chat, **kwargs):
        card = FakeChat(f"delegate-{len(self.delegate_cards) + 1}", name=kwargs.get("name", "delegate"))
        card.mode = C.CHAT_MODE_DELEGATE
        card.parent_id = parent_chat.id
        card.messages.append(SimpleNamespace(role="user", content=kwargs.get("content", "")))
        self.manager.add(card)
        self.delegate_cards.append((card, kwargs))
        return card


class FakeExecutor:
    """Executor double: returns a done result and can simulate supervisor work."""

    def __init__(self, cost_per_step=0.0):
        self.calls = []
        self.cost_per_step = cost_per_step
        self.supervisor_calls = []
        self.supervisor_hook = None
        self.active = 0
        self.max_active = 0

    async def execute_step(self, run, step, chat, parent_token=None, timeout=None):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.01)
            self.calls.append(step.id)
            if self.cost_per_step:
                main = self._main_chat(run)
                if main is not None:
                    main.cost = float(main.cost or 0.0) + self.cost_per_step
            return StepResult(
                status=C.STEP_STATUS_DONE,
                summary=f"did {step.title}",
                files=["file.py"],
                verification="tests pass",
                cost_cxjcoins=self.cost_per_step,
            )
        finally:
            self.active -= 1

    async def execute_delegate(self, chat, parent_token=None, timeout=None):
        self.calls.append(("delegate", chat.id))
        return StepResult(status=C.STEP_STATUS_DONE, summary="delegated", verification="ok")

    async def run_supervisor(self, chat, timeout=None, parent_token=None):
        self.supervisor_calls.append(chat.id)
        if self.supervisor_hook is not None:
            result = self.supervisor_hook(chat)
            if asyncio.iscoroutine(result):
                await result
        return chat

    def _main_chat(self, run):
        # The fake board puts the main chat in the manager, but the executor has
        # no manager reference. The test sets this attribute when needed.
        return getattr(self, "manager", FakeChatManager()).find_by_id(run.main_chat_id)


def make_service(tmp_path, executor=None, board=None, manager=None):
    """Create a service with a real store and fakes."""
    store = RunStore(str(tmp_path / ".codx"))
    manager = manager or FakeChatManager()
    board = board or FakeBoard(manager)
    executor = executor or FakeExecutor()
    if hasattr(executor, "__dict__"):
        executor.manager = manager
    service = OrchestrationService(
        settings=SimpleNamespace(
            codx_path=str(tmp_path / ".codx"),
            project_id="project-1",
            project_name="test",
        ),
        chat_manager=manager,
        store=store,
        board=board,
        executor=executor,
        message_factory=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    return service, manager, board, executor, store


# ---------------------------------------------------------------------------
# Models / result contract
# ---------------------------------------------------------------------------


def test_parse_step_result_reads_fenced_contract():
    content = (
        "Work done.\n```json\n"
        '{"status":"done","summary":"implemented","files":["a.py"],'
        '"verification":"pytest","followups":["docs"]}'
        "\n```"
    )
    result = parse_step_result(content, cost_cxjcoins=0.5, duration_seconds=2.0)
    assert result.status == C.STEP_STATUS_DONE
    assert result.summary == "implemented"
    assert result.files == ["a.py"]
    assert result.verification == "pytest"
    assert result.followups == ["docs"]
    assert result.cost_cxjcoins == 0.5


def test_parse_step_result_falls_back_to_raw_answer():
    result = parse_step_result("I could not reach the service, it is blocked")
    assert result.status == C.STEP_STATUS_DONE
    assert "could not reach" in result.summary


def test_parse_step_result_runtime_error_wins():
    result = parse_step_result("partial", error="boom")
    assert result.status == C.STEP_STATUS_FAILED
    assert result.error == "boom"


def test_result_to_step_status_maps_blocked():
    assert result_to_step_status(StepResult(status="blocked")) == C.STEP_STATUS_BLOCKED
    assert result_to_step_status(StepResult(status="failed")) == C.STEP_STATUS_FAILED
    assert result_to_step_status(StepResult(status="done")) == C.STEP_STATUS_DONE


# ---------------------------------------------------------------------------
# Plan graph
# ---------------------------------------------------------------------------


def test_plan_requires_title_and_objective():
    with pytest.raises(PlanError):
        normalize_steps([{"title": "", "objective": "x"}])
    with pytest.raises(PlanError):
        normalize_steps([{"title": "x", "objective": ""}])


def test_plan_resolves_title_dependencies_and_reuses_ids():
    run = RunState(name="r", objective="o")
    first = normalize_steps(
        [{"title": "A", "objective": "a"}, {"title": "B", "objective": "b", "depends_on": ["A"]}]
    )
    run.steps = first
    assert first[1].depends_on == [first[0].id]

    merged = merge_plan(run, [{"title": "A", "objective": "a v2"}])
    assert merged[0].id == first[0].id
    assert merged[0].objective == "a v2"
    assert len(merged) == 2

    added = merge_plan(run, [{"title": "C", "objective": "c", "depends_on": ["B"]}])
    assert [step.title for step in added] == ["A", "B", "C"]


def test_plan_rejects_unknown_dependency_and_cycle():
    with pytest.raises(PlanError):
        normalize_steps([{"title": "A", "objective": "a", "depends_on": ["missing"]}])
    with pytest.raises(PlanError):
        normalize_steps([
            {"title": "A", "objective": "a", "depends_on": ["B"]},
            {"title": "B", "objective": "b", "depends_on": ["A"]},
        ])


def test_ready_steps_honours_dependencies_and_priority():
    run = RunState(name="r", objective="o")
    run.steps = normalize_steps([
        {"title": "low", "objective": "l", "priority": "low"},
        {"title": "high", "objective": "h", "priority": "high"},
        {"title": "after", "objective": "a", "depends_on": ["low"]},
    ])
    ready = ready_steps(run)
    assert [step.title for step in ready] == ["high", "low"]
    run.steps[0].status = C.STEP_STATUS_DONE  # low is first in the list
    # `low` is done now; `after` becomes ready together with `high`.
    ready = ready_steps(run)
    assert {step.title for step in ready} == {"high", "after"}


def test_next_actions_reports_verify_and_failed():
    run = RunState(name="r", objective="o")
    run.steps = normalize_steps([{"title": "A", "objective": "a"}])
    run.steps[0].status = C.STEP_STATUS_DONE
    assert next_actions(run)["reason"] == "verify"
    run.steps[0].status = C.STEP_STATUS_FAILED
    assert next_actions(run)["reason"] == "failed_steps"


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


def test_store_roundtrip_and_list(tmp_path):
    store = RunStore(str(tmp_path / ".codx"))
    run = RunState(name="one", objective="o", status=C.RUN_STATUS_RUNNING)
    store.save(run)
    loaded = store.load(run.run_id)
    assert loaded.name == "one"
    assert loaded.run_id == run.run_id
    assert store.exists(run.run_id)
    assert [item.run_id for item in store.list_runs()] == [run.run_id]
    assert run.run_id in store.active_run_ids()


def test_store_lock_is_exclusive(tmp_path):
    store = RunStore(str(tmp_path / ".codx"))
    run = RunState(name="lock", objective="o")
    store.save(run)
    lock = RunLock(store.lock_path(run.run_id))
    lock.acquire()
    try:
        second = RunLock(store.lock_path(run.run_id))
        with pytest.raises(Exception):
            second.acquire()
    finally:
        lock.release()
    # After release a new lock can be acquired.
    third = RunLock(store.lock_path(run.run_id))
    third.acquire()
    third.release()


def test_store_lock_path_keeps_the_run_stem(tmp_path):
    store = RunStore(str(tmp_path / ".codx"))
    run = RunState(name="lock", objective="o")
    run.run_id = "run.with.json.in.the.id"
    store.save(run)
    assert store.lock_path(run.run_id).endswith("run.with.json.in.the.id.lock")
    assert store.lock_path(run.run_id) == store.run_path(run.run_id)[:-5] + ".lock"


def test_store_worker_heartbeat(tmp_path):
    store = RunStore(str(tmp_path / ".codx"))
    assert store.worker_status()["present"] is False
    store.write_worker_heartbeat({"pid": 123})
    status = store.worker_status(ttl_seconds=60)
    assert status["present"] is True
    assert status["pid"] == 123


# ---------------------------------------------------------------------------
# Service lifecycle
# ---------------------------------------------------------------------------


def test_create_run_and_plan_persist(tmp_path):
    service, manager, board, executor, store = make_service(tmp_path)
    main = FakeChat("main", name="Main")
    manager.add(main)
    run = service.create_run(
        name="Run",
        objective="Do the thing",
        main_chat=main,
        config=RunConfig(budget_cxjcoins=10),
        start=True,
    )
    assert run.status == C.RUN_STATUS_RUNNING
    assert main.run_id == run.run_id
    assert main.run_status == C.RUN_STATUS_RUNNING
    assert main.estimation_cost == 10

    run = service.plan(run.run_id, [
        {"title": "A", "objective": "a"},
        {"title": "B", "objective": "b", "depends_on": ["A"]},
    ])
    assert len(run.steps) == 2
    assert store.load(run.run_id).steps[0].title == "A"


def test_status_payload_exposes_budget_and_total_steps(tmp_path):
    service, manager, board, executor, store = make_service(tmp_path)
    main = FakeChat("main", name="Main")
    manager.add(main)
    run = service.create_run(
        name="Run",
        objective="Do it",
        main_chat=main,
        config=RunConfig(budget_cxjcoins=7.5),
        start=True,
    )
    service.plan(run.run_id, [
        {"title": "A", "objective": "a"},
        {"title": "B", "objective": "b"},
    ])
    payload = service.status(run.run_id)
    # The ChatRunBar renders counts.total and budget_cxjcoins from the DETAIL
    # endpoint; keep the same fields the list payload already exposes.
    assert payload["counts"]["total"] == 2
    assert payload["budget_cxjcoins"] == 7.5
    assert payload["spent_cxjcoins"] == 0.0
    assert payload["remaining_cxjcoins"] == 7.5


def test_run_main_task_must_be_a_root(tmp_path):
    service, manager, board, executor, store = make_service(tmp_path)
    main = FakeChat("main", name="Child", parent_id="parent")
    manager.add(main)
    with pytest.raises(ValueError):
        service.create_run(name="Run", objective="Do it", main_chat=main, start=True)


def test_tick_dispatches_ready_steps_and_persists_results(tmp_path):
    service, manager, board, executor, store = make_service(tmp_path)
    main = FakeChat("main", name="Main")
    manager.add(main)
    run = service.create_run(name="Run", objective="Do it", main_chat=main, start=True)
    run = service.plan(run.run_id, [
        {"title": "A", "objective": "a"},
        {"title": "B", "objective": "b", "depends_on": ["A"]},
    ])

    asyncio.run(service.tick(run.run_id))
    run = store.load(run.run_id)
    assert run.step_by_title("A").status == C.STEP_STATUS_DONE
    assert run.step_by_title("B").status == C.STEP_STATUS_PENDING
    assert run.step_by_title("A").result.summary == "did A"
    assert run.step_by_title("A").chat_id.startswith("card-")

    asyncio.run(service.tick(run.run_id))
    run = store.load(run.run_id)
    assert run.step_by_title("B").status == C.STEP_STATUS_DONE
    assert run.pending_supervisor is True


def test_independent_steps_run_in_parallel(tmp_path):
    executor = FakeExecutor()
    service, manager, board, executor, store = make_service(tmp_path, executor=executor)
    main = FakeChat("main", name="Main")
    manager.add(main)
    run = service.create_run(
        name="Run",
        objective="Do it",
        main_chat=main,
        config=RunConfig(max_parallel=3),
        start=True,
    )
    service.plan(run.run_id, [
        {"title": "A", "objective": "a"},
        {"title": "B", "objective": "b"},
        {"title": "C", "objective": "c"},
    ])
    asyncio.run(service.tick(run.run_id))
    assert executor.max_active >= 2
    assert len(executor.calls) == 3


def test_budget_exhausted_stops_without_executor_call(tmp_path):
    service, manager, board, executor, store = make_service(tmp_path)
    main = FakeChat("main", name="Main", cost=1.0)
    manager.add(main)
    run = service.create_run(
        name="Run",
        objective="Do it",
        main_chat=main,
        config=RunConfig(budget_cxjcoins=1.0, supervisor_reserve=0.5),
        start=True,
    )
    service.plan(run.run_id, [{"title": "A", "objective": "a"}])
    asyncio.run(service.tick(run.run_id))
    run = store.load(run.run_id)
    assert run.status == C.RUN_STATUS_BUDGET_EXHAUSTED
    assert run.report_written is True
    assert executor.calls == []
    assert any("budget exhausted" in (getattr(m, "content", "") or "").lower()
               for m in main.messages)


def test_stagnation_finalizes_stalled(tmp_path):
    executor = FakeExecutor()
    service, manager, board, executor, store = make_service(tmp_path, executor=executor)
    main = FakeChat("main", name="Main")
    manager.add(main)
    run = service.create_run(
        name="Run",
        objective="Do it",
        main_chat=main,
        config=RunConfig(stagnation_limit=2),
        start=True,
    )
    asyncio.run(service.tick(run.run_id))
    asyncio.run(service.tick(run.run_id))
    run = store.load(run.run_id)
    assert run.status == C.RUN_STATUS_STALLED
    assert executor.calls == []


def test_finish_publishes_report_and_completes(tmp_path):
    service, manager, board, executor, store = make_service(tmp_path)
    main = FakeChat("main", name="Main")
    manager.add(main)
    run = service.create_run(name="Run", objective="Do it", main_chat=main, start=True)
    service.plan(run.run_id, [{"title": "A", "objective": "a"}])
    asyncio.run(service.tick(run.run_id))
    run = service.finish(run.run_id, "All requirements are met")
    assert run.status == C.RUN_STATUS_COMPLETED
    assert main.status == "done"
    assert main.run_status == C.RUN_STATUS_COMPLETED
    assert any(
        getattr(message, "meta_data", {}).get("orchestration_report")
        for message in main.messages
    )


def test_verification_none_completes_without_supervisor(tmp_path):
    executor = FakeExecutor()
    service, manager, board, executor, store = make_service(tmp_path, executor=executor)
    main = FakeChat("main", name="Main")
    manager.add(main)
    run = service.create_run(
        name="Run",
        objective="Do it",
        main_chat=main,
        config=RunConfig(verification="none"),
        start=True,
    )
    service.plan(run.run_id, [{"title": "A", "objective": "a"}])
    asyncio.run(service.tick(run.run_id))
    asyncio.run(service.tick(run.run_id))
    run = store.load(run.run_id)
    assert run.status == C.RUN_STATUS_COMPLETED
    assert executor.supervisor_calls == []
    assert run.report_written is True


def test_pause_resume_and_stop(tmp_path):
    service, manager, board, executor, store = make_service(tmp_path)
    main = FakeChat("main", name="Main")
    manager.add(main)
    run = service.create_run(name="Run", objective="Do it", main_chat=main, start=True)
    service.pause(run.run_id)
    assert store.load(run.run_id).status == C.RUN_STATUS_PAUSED
    assert main.status == "onhold"
    service.resume(run.run_id)
    assert store.load(run.run_id).status == C.RUN_STATUS_RUNNING
    service.stop(run.run_id, "done by user")
    stopped = store.load(run.run_id)
    assert stopped.status == C.RUN_STATUS_STOPPED
    assert stopped.report_written is True


def test_start_reopens_stopped_run_and_rejects_completed(tmp_path):
    service, manager, board, executor, store = make_service(tmp_path)
    main = FakeChat("main", name="Main")
    manager.add(main)
    run = service.create_run(name="Run", objective="Do it", main_chat=main, start=True)
    service.plan(run.run_id, [{"title": "A", "objective": "a"}])

    # Active runs are returned unchanged (idempotent UI retry).
    assert service.start(run.run_id).status == C.RUN_STATUS_RUNNING

    service.stop(run.run_id, "paused by user")
    assert store.load(run.run_id).status == C.RUN_STATUS_STOPPED
    restarted = service.start(run.run_id)
    assert restarted.status == C.RUN_STATUS_RUNNING
    assert restarted.finished_at == ""
    assert main.run_status == C.RUN_STATUS_RUNNING
    assert any(event.type == "run_started" for event in restarted.events)

    service.finish(run.run_id, "done")
    with pytest.raises(PlanError):
        service.start(run.run_id)

    # The reopen bump gives the new (completed) attempt its own delivery report
    # instead of being swallowed by the stop report's idempotency marker.
    reports = [
        message for message in main.messages
        if getattr(message, "meta_data", {}).get("orchestration_report")
    ]
    assert len(reports) == 2
    assert reports[-1].meta_data["report_generation"] == 1


def test_resume_stalled_run_publishes_a_new_delivery_report(tmp_path):
    service, manager, board, executor, store = make_service(tmp_path)
    main = FakeChat("main", name="Main")
    manager.add(main)
    run = service.create_run(name="Run", objective="Do it", main_chat=main, start=True)
    service.plan(run.run_id, [{"title": "A", "objective": "a"}])

    stalled = service._finalize_stalled(store.load(run.run_id), "no progress")
    assert stalled.status == C.RUN_STATUS_STALLED
    assert stalled.report_written is True
    stall_reports = [
        message for message in main.messages
        if getattr(message, "meta_data", {}).get("orchestration_report")
    ]
    assert len(stall_reports) == 1
    assert stall_reports[0].meta_data["report_generation"] == 0

    resumed = service.resume(run.run_id)
    assert resumed.status == C.RUN_STATUS_RUNNING
    # The stall report must not suppress the report of the resumed attempt.
    assert resumed.report_written is False
    assert resumed.report_generation == 1

    service.finish(run.run_id, "completed after resume")
    reports = [
        message for message in main.messages
        if getattr(message, "meta_data", {}).get("orchestration_report")
    ]
    assert len(reports) == 2
    assert reports[-1].meta_data["report_generation"] == 1
    assert store.load(run.run_id).last_report


def test_start_refuses_budget_exhausted_run(tmp_path):
    service, manager, board, executor, store = make_service(tmp_path)
    main = FakeChat("main", name="Main", cost=1.0)
    manager.add(main)
    run = service.create_run(
        name="Run",
        objective="Do it",
        main_chat=main,
        config=RunConfig(budget_cxjcoins=1.0, supervisor_reserve=0.5),
        start=True,
    )
    asyncio.run(service.tick(run.run_id))
    assert store.load(run.run_id).status == C.RUN_STATUS_BUDGET_EXHAUSTED
    with pytest.raises(PlanError):
        service.start(run.run_id)


def test_retry_step_resets_a_failed_step(tmp_path):
    service, manager, board, executor, store = make_service(tmp_path)
    main = FakeChat("main", name="Main")
    manager.add(main)
    run = service.create_run(name="Run", objective="Do it", main_chat=main, start=True)
    run = service.plan(run.run_id, [{"title": "A", "objective": "a"}])
    step = run.steps[0]
    step.status = C.STEP_STATUS_FAILED
    step.attempts = 2
    step.result = StepResult(status="failed", summary="nope")
    step.chat_id = "card-A"
    service._save(run)

    run = service.retry_step(run.run_id, step.id)
    step = run.steps[0]
    assert step.status == C.STEP_STATUS_PENDING
    assert step.attempts == 0
    assert step.result is None


# ---------------------------------------------------------------------------
# Board materialization
# ---------------------------------------------------------------------------


class FakeTaskManager:
    def __init__(self):
        self.created = []

    def create_task(self, **kwargs):
        self.created.append(kwargs)
        chat = FakeChat("created", name=kwargs.get("name", ""))
        chat.board = kwargs.get("board")
        chat.column = kwargs.get("column")
        chat.status = kwargs.get("status")
        chat.run_id = kwargs.get("run_id")
        chat.run_step_id = kwargs.get("run_step_id")
        return chat


def test_board_ensures_board_sprint_and_columns(tmp_path):
    manager = FakeChatManager()
    board = RunBoard(settings=SimpleNamespace(codx_path=str(tmp_path)), chat_manager=manager)
    run = RunState(name="My Run", objective="o")
    run.config.board = "Orchestration"
    run.config.sprint = "Run: My Run"
    board.ensure_run(run)
    kanban = manager.kanban
    assert "Orchestration" in kanban["boards"]
    assert "Run: My Run" in kanban["boards"]
    board_entry = kanban["boards"]["Orchestration"]
    titles = [column["title"] for column in board_entry["columns"]]
    assert "Backlog" in titles and "In progress" in titles
    sprint = kanban["boards"]["Run: My Run"]
    assert sprint["type"] == "sprint"
    assert [column["title"] for column in sprint["columns"]] == list(C.SPRINT_COLUMN_TITLES)


def test_board_step_card_is_linked_to_run_and_main(tmp_path):
    manager = FakeChatManager()
    main = FakeChat("main")
    manager.add(main)
    tasks = FakeTaskManager()
    board = RunBoard(
        settings=SimpleNamespace(codx_path=str(tmp_path)),
        chat_manager=manager,
        task_manager=tasks,
    )
    run = RunState(name="Run", objective="o", main_chat_id="main")
    run.config.board = "B"
    run.config.sprint = "S"
    step = normalize_steps([{"title": "A", "objective": "a"}])[0]
    board.create_step_card(
        run,
        step,
        content="contract",
        description="desc",
        profiles=["software_developer"],
        estimation_cost=1.5,
    )
    created = tasks.created[0]
    assert created["run_id"] == run.run_id
    assert created["run_step_id"] == step.id
    assert created["parent_chat"] is main
    assert created["estimation_cost"] == 1.5
    assert created["ignore_parent_knowledge"] is True
    assert created["board"] == "B"
    assert created["sprints"] == ["S"]
    assert step.chat_id == "created"


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------


def test_delegate_wait_creates_cards_and_returns_results(tmp_path):
    executor = FakeExecutor()
    service, manager, board, executor, store = make_service(tmp_path, executor=executor)
    parent = FakeChat("parent", name="Parent")
    manager.add(parent)
    outcome = asyncio.run(service.delegate(
        parent,
        ["Research A", "Research B"],
        concurrency=2,
        wait=True,
    ))
    assert outcome["mode"] == "wait"
    assert len(outcome["results"]) == 2
    assert all(result["status"] == "done" for result in outcome["results"])
    assert len(board.delegate_cards) == 2
    assert len(executor.calls) == 2


def test_delegate_rejects_recursive_delegation(tmp_path):
    service, manager, board, executor, store = make_service(tmp_path)
    parent = FakeChat("parent", mode=C.CHAT_MODE_DELEGATE)
    manager.add(parent)
    with pytest.raises(ValueError):
        asyncio.run(service.delegate(parent, ["task"], wait=True))


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------


def _load_orchestration_tools():
    """Import the tool module without executing the heavy tools package __init__."""
    import importlib
    import pathlib
    import sys
    import types

    package_name = "codx.junior.tools"
    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = [
            str(pathlib.Path(__file__).resolve().parents[1] / "codx" / "junior" / "tools")
        ]
        sys.modules[package_name] = package
    return importlib.import_module(f"{package_name}.orchestration_tools")


def test_tool_schemas_are_valid():
    module = _load_orchestration_tools()
    ORCHESTRATOR_TOOL_JSON = module.ORCHESTRATOR_TOOL_JSON
    DELEGATE_TOOL_JSON = module.DELEGATE_TOOL_JSON

    orchestrator = ORCHESTRATOR_TOOL_JSON["function"]
    assert orchestrator["name"] == "orchestrator"
    actions = orchestrator["parameters"]["properties"]["action"]["enum"]
    assert {"start", "plan", "status", "finish", "pause", "resume", "stop"} <= set(actions)
    assert "steps" in orchestrator["parameters"]["properties"]

    delegate = DELEGATE_TOOL_JSON["function"]
    assert delegate["name"] == "delegate"
    assert "tasks" in delegate["parameters"]["properties"]
    assert "wait" in delegate["parameters"]["properties"]


class _ToolSession:
    """Minimal session double for the orchestration tools."""

    def __init__(self, manager, chat):
        self._current_chat = chat
        self.event_manager = None
        self.user = None
        self.manager = manager

    def get_chat_manager(self):
        return self.manager


def test_orchestrator_add_step_tool_updates_the_plan(tmp_path):
    module = _load_orchestration_tools()
    manager = FakeChatManager()
    main = FakeChat("main", name="Main")
    manager.add(main)
    settings = SimpleNamespace(
        codx_path=str(tmp_path / ".codx"),
        project_id="project-1",
        project_name="test",
    )
    session = _ToolSession(manager, main)

    started = asyncio.run(module.orchestrator(
        action="start",
        objective="Do it",
        budget_cxjcoins=5,
        settings=settings,
        session=session,
    ))
    assert "started" in started.llm_response
    assert main.run_id

    # Regression: this branch used to reference an unassigned local `run` and
    # raised UnboundLocalError instead of adding the step.
    added = asyncio.run(module.orchestrator(
        action="add_step",
        step={"title": "A", "objective": "do a"},
        settings=settings,
        session=session,
    ))
    assert "1 step" in added.user_response
    assert '"status": "step_added"' in added.llm_response

# Made with ❤️ by codx-junior
