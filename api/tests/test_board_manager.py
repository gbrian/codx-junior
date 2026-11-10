"""
Offline tests of the board manager.

The tests exercise the whole review pipeline with a fake chat manager and an
injected runner, so no AI provider is needed:

    board config -> snapshot -> prompt -> JSON decision -> validated actions

Run with::

    cd api && pytest tests/test_board_manager.py -q
"""

import asyncio
from types import SimpleNamespace

import pytest

from codx.junior.board_manager import constants as C
from codx.junior.board_manager.actions import BoardContext
from codx.junior.board_manager.models import (
    BoardManagerConfig,
    parse_decision,
)
from codx.junior.board_manager.service import BoardManagerService
from codx.junior.board_manager.store import BoardManagerStore


class FakeChat:
    """The subset of ``Chat`` the board manager touches."""

    def __init__(self, chat_id, name="Task", **kwargs):
        self.id = chat_id
        self.name = name
        self.description = ""
        self.board = "Work"
        self.column = "Todo"
        self.status = "todo"
        self.priority = ""
        self.due_date = ""
        self.progress = 0
        self.profiles = []
        self.users = []
        self.assignees = []
        self.tags = []
        self.sprints = []
        self.messages = []
        self.updated_at = "2026-01-01T10:00:00"
        self.created_at = "2026-01-01T09:00:00"
        self.mode = "task"
        self.is_template = False
        self.run_id = None
        self.run_status = None
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeChatManager:
    """In-memory ChatManager used by the service."""

    def __init__(self, chats, kanban):
        self.chats = {chat.id: chat for chat in chats}
        self.kanban = kanban
        self.saved = []

    def list_chats(self):
        return list(self.chats.values())

    def find_by_id(self, chat_id):
        return self.chats.get(chat_id)

    def update_chat_metadata(self, chat, metadata):
        for key, value in metadata.items():
            setattr(chat, key, value)
        self.saved.append((chat.id, dict(metadata)))
        return chat

    def add_message(self, chat, message):
        chat.messages.append(message)
        self.saved.append((chat.id, {"message": message.content}))
        return chat

    def save_chat(self, chat, chat_only=False):
        self.chats[chat.id] = chat
        return chat

    def load_kanban(self):
        return self.kanban

    def save_kanban(self, kanban):
        self.kanban = kanban


class FakeSettings:
    """Project settings subset."""

    def __init__(self, codx_path):
        self.codx_path = str(codx_path)
        self.project_id = "project-1"
        self.project_name = "board-manager-test"
        self.llm_model = ""


def board_document(**overrides):
    board = {
        "id": "board-1",
        "title": "Work",
        "type": "kanban",
        "columns": [
            {"title": "Todo"},
            {"title": "Doing"},
            {"title": "Done"},
        ],
        "manager": {
            "enabled": True,
            "profile": "ProjectManager",
            "mode": "apply",
            "interval_minutes": 60,
            "max_actions": 5,
            "instructions": "Keep the board small.",
        },
    }
    board.update(overrides)
    return board


def make_service(tmp_path, chats=None, board=None, runner=None):
    board = board or board_document()
    kanban = {"version": 2, "boards": {"Work": board}, "tags": {}}
    manager = FakeChatManager(chats or [], kanban)
    settings = FakeSettings(tmp_path)
    service = BoardManagerService(
        settings=settings,
        chat_manager=manager,
        store=BoardManagerStore(settings.codx_path),
        runner=runner,
        message_factory=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    return service, manager, settings


def test_config_defaults_and_clamps():
    config = BoardManagerConfig.from_board({
        "assignee": "board-assistant",
        "manager": {
            "enabled": True,
            "interval_minutes": 1,
            "max_actions": 999,
            "mode": "weird",
            "instructions": "  keep it short  ",
        },
    })

    assert config.enabled is True
    assert config.profile == "board-assistant"
    assert config.interval_minutes == C.MIN_INTERVAL_MINUTES
    assert config.max_actions == C.MAX_ACTIONS_LIMIT
    assert config.mode == C.MODE_APPLY
    assert config.instructions == "keep it short"


def test_parse_decision_accepts_fenced_and_alias_actions():
    decision = parse_decision(
        'Sure\n```json\n{"summary":"ok","actions":[{"action":"move","task_id":"a",'
        '"to_column":"Doing"},{"type":"add_comment","task_id":"b","comment":"hi"}]}\n```'
    )

    assert decision.summary == "ok"
    assert decision.parse_error == ""
    assert [action.type for action in decision.actions] == ["move_task", "comment"]
    assert decision.actions[0].column == "Doing"


def test_parse_decision_without_contract_is_reported():
    decision = parse_decision("I think the board is fine.")
    assert decision.actions == []
    assert decision.parse_error
    assert decision.summary == "I think the board is fine."


def test_collect_tasks_respects_membership_done_flag_and_templates(tmp_path):
    chats = [
        FakeChat("a", name="Open", board="Work", column="Todo"),
        FakeChat("b", name="Done", board="Work", status="done", column="Done"),
        FakeChat("c", name="Other board", board="Other"),
        FakeChat("d", name="Template", is_template=True),
        FakeChat("e", name="Sprint task", board="Other", sprints=["Work"]),
    ]
    service, _, _ = make_service(tmp_path, chats=chats)
    context = BoardContext(
        title="Work",
        board_id="board-1",
        board_type="kanban",
        columns=board_document()["columns"],
        config=BoardManagerConfig(
            enabled=True, profile="ProjectManager", include_done=False
        ),
    )

    snapshot = service.collect_tasks(context)
    assert [task["id"] for task in snapshot] == ["a"]

    context.config.include_done = True
    snapshot = service.collect_tasks(context)
    assert {task["id"] for task in snapshot} == {"a", "b"}

    # A sprint board groups by membership, so the task stored on another kanban
    # board is included.
    sprint = BoardContext(
        title="Work",
        board_id="board-1",
        board_type="sprint",
        columns=board_document()["columns"],
        config=BoardManagerConfig(enabled=True, profile="ProjectManager", include_done=True),
    )
    snapshot = service.collect_tasks(sprint)
    assert {task["id"] for task in snapshot} == {"e"}


def test_run_applies_move_comment_close_and_update(tmp_path):
    chats = [
        FakeChat("move", name="Move me", board="Work", column="Todo"),
        FakeChat("comment", name="Comment me", board="Work", column="Todo"),
        FakeChat("close", name="Close me", board="Work", column="Doing"),
    ]

    async def runner(request):
        assert request.board == "Work"
        assert "Keep the board small." in request.system
        assert "`move`" in request.prompt
        return (
            '{"summary":"tidied","actions":['
            '{"type":"move_task","task_id":"move","column":"Doing","reason":"started"},'
            '{"type":"comment","task_id":"comment","comment":"Please add a test."},'
            '{"type":"close_task","task_id":"close","reason":"done"},'
            '{"type":"update_task","task_id":"move","priority":"high","progress":50}'
            ']}',
            0.25,
        )

    service, manager, _ = make_service(tmp_path, chats=chats, runner=runner)
    result = asyncio.run(service.run_board("Work", force=True))

    assert result["state"]["last_status"] == C.STATE_OK
    assert result["state"]["runs"] == 1
    assert result["state"]["last_cost"] == pytest.approx(0.25)

    move = manager.find_by_id("move")
    assert move.column == "Doing"
    assert move.priority == "high"
    assert move.progress == 50

    comment = manager.find_by_id("comment")
    assert comment.messages[-1].content == "Please add a test."
    assert comment.messages[-1].role == "assistant"

    closed = manager.find_by_id("close")
    assert closed.status == "done"
    assert closed.progress == 100
    assert closed.column == "Done"

    assert len(result["state"]["last_actions"]) == 4
    assert all(record["applied"] for record in result["state"]["last_actions"])


def test_suggest_mode_records_without_writing(tmp_path):
    chats = [FakeChat("a", name="Move me", board="Work", column="Todo")]

    async def runner(request):
        return (
            '{"summary":"suggestion","actions":['
            '{"type":"move_task","task_id":"a","column":"Doing"}]}',
            0.0,
        )

    board = board_document()
    board["manager"]["mode"] = "suggest"
    service, manager, _ = make_service(tmp_path, chats=chats, board=board, runner=runner)
    result = asyncio.run(service.run_board("Work", force=True))

    assert result["state"]["last_status"] == C.STATE_SUGGESTED
    assert manager.find_by_id("a").column == "Todo"
    assert result["state"]["last_actions"][0]["applied"] is False
    assert "Suggest moving" in result["state"]["last_actions"][0]["summary"]


def test_invalid_destination_is_reported_without_touching_the_task(tmp_path):
    chats = [FakeChat("a", name="Move me", board="Work", column="Todo")]

    async def runner(request):
        return (
            '{"summary":"bad","actions":['
            '{"type":"move_task","task_id":"a","column":"Nowhere"}]}',
            0.0,
        )

    service, manager, _ = make_service(tmp_path, chats=chats, runner=runner)
    result = asyncio.run(service.run_board("Work", force=True))

    assert result["state"]["last_status"] == C.STATE_ERROR
    assert manager.find_by_id("a").column == "Todo"
    record = result["state"]["last_actions"][0]
    assert record["applied"] is False
    assert "unknown column" in record["error"]


def test_active_run_card_is_never_modified(tmp_path):
    chats = [FakeChat(
        "a", name="Run card", board="Work", column="Todo",
        run_id="run-1", run_status="running",
    )]

    async def runner(request):
        return (
            '{"summary":"bad","actions":['
            '{"type":"move_task","task_id":"a","column":"Doing"}]}',
            0.0,
        )

    service, manager, _ = make_service(tmp_path, chats=chats, runner=runner)
    result = asyncio.run(service.run_board("Work", force=True))

    assert manager.find_by_id("a").column == "Todo"
    assert "active orchestration run" in result["state"]["last_actions"][0]["error"]


def test_max_actions_bounds_the_review(tmp_path):
    chats = [FakeChat("a", name="A", board="Work", column="Todo")]
    calls = {"count": 0}

    async def runner(request):
        return (
            '{"summary":"many","actions":['
            '{"type":"comment","task_id":"a","comment":"one"},'
            '{"type":"comment","task_id":"a","comment":"two"},'
            '{"type":"comment","task_id":"a","comment":"three"}]}',
            0.0,
        )

    board = board_document()
    board["manager"]["max_actions"] = 2
    service, _, _ = make_service(tmp_path, chats=chats, board=board, runner=runner)
    result = asyncio.run(service.run_board("Work", force=True))

    assert len(result["state"]["last_actions"]) == 2


def test_disabled_board_is_not_reviewed(tmp_path):
    chats = [FakeChat("a", name="A", board="Work")]
    called = {"runner": False}

    async def runner(request):
        called["runner"] = True
        return "{}", 0.0

    board = board_document()
    board["manager"]["enabled"] = False
    service, _, _ = make_service(tmp_path, chats=chats, board=board, runner=runner)
    result = asyncio.run(service.run_board("Work", force=True))

    assert called["runner"] is False
    assert result["state"]["last_status"] == C.STATE_SKIPPED


def test_run_due_honours_schedule_and_wake_request(tmp_path):
    chats = [FakeChat("a", name="A", board="Work")]
    runs = {"count": 0}

    async def runner(request):
        runs["count"] += 1
        return '{"summary":"ok","actions":[]}', 0.0

    board = board_document()
    board["manager"]["interval_minutes"] = 60
    service, _, _ = make_service(tmp_path, chats=chats, board=board, runner=runner)

    first = asyncio.run(service.run_due())
    assert len(first) == 1
    assert runs["count"] == 1

    # Not due until the interval elapses.
    second = asyncio.run(service.run_due())
    assert second == []
    assert runs["count"] == 1

    # "Run now" wakes it regardless of the schedule.
    service.request_run("Work")
    third = asyncio.run(service.run_due())
    assert len(third) == 1
    assert runs["count"] == 2


def test_request_run_requires_enabled_manager(tmp_path):
    board = board_document()
    board["manager"]["enabled"] = False
    service, _, _ = make_service(tmp_path, board=board)

    with pytest.raises(ValueError):
        service.request_run("Work")


def test_no_tasks_skips_the_ai_call(tmp_path):
    called = {"runner": False}

    async def runner(request):
        called["runner"] = True
        return "{}", 0.0

    service, _, _ = make_service(tmp_path, chats=[], runner=runner)
    result = asyncio.run(service.run_board("Work", force=True))

    assert called["runner"] is False
    assert result["state"]["last_status"] == C.STATE_NO_TASKS


def test_status_exposes_config_state_and_worker(tmp_path):
    service, _, _ = make_service(tmp_path, chats=[])
    status = service.status()

    assert status["worker_present"] is False
    entry = status["boards"][0]
    assert entry["board"] == "Work"
    assert entry["config"]["enabled"] is True
    assert entry["due"] is True
    assert entry["next_run_at"]


def test_store_roundtrip_and_heartbeat(tmp_path):
    store = BoardManagerStore(str(tmp_path))
    assert store.worker_present() is False
    store.write_worker_heartbeat({"project_id": "p1"})
    assert store.worker_present() is True

    state = store.get_state("board-1")
    state.board = "Work"
    store.put_state("board-1", state)
    assert store.get_state("board-1").board == "Work"
    assert store.get_state("other").board == ""
