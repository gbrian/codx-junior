"""
Tests for the harness completion notification and audit wiring.

The notification must be sent exactly once per terminal status (the durable
``notification_sent`` flag survives duplicate ticks/restarts), and every run
transition must be registered in the audit journal.

Run with::

    cd api && pytest tests/harness/test_harness_notification.py -q
"""

import json
import os
from types import SimpleNamespace

from codx.junior.harness.audit import audit_path
from codx.junior.orchestration import constants as C
from codx.junior.orchestration.service import OrchestrationService
from codx.junior.orchestration.store import RunStore


class FakeChat:
    def __init__(self, chat_id, name="card", **kwargs):
        self.id = chat_id
        self.name = name
        self.description = ""
        self.cost = 0.0
        self.estimation_cost = None
        self.profiles = []
        self.messages = []
        self.status = "todo"
        self.column = "tasks"
        self.run_id = None
        self.run_status = None
        self.progress = 0
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeChatManager:
    def __init__(self):
        self.chats = {}

    def add(self, chat):
        self.chats[chat.id] = chat
        return chat

    def find_by_id(self, chat_id):
        return self.chats.get(chat_id)

    def save_chat(self, chat, chat_only=False):
        self.chats[chat.id] = chat
        return chat

    def add_message(self, chat, message):
        chat.messages.append(message)
        return chat


class FakeBoard:
    def __init__(self, manager):
        self.manager = manager

    def ensure_run(self, run):
        run.config.board = run.config.board or C.DEFAULT_BOARD
        run.config.sprint = run.config.sprint or f"Run: {run.name}"
        return run

    def attach_main(self, run, chat, persist=False, move=False, status=None, progress=None):
        chat.run_id = run.run_id
        chat.run_status = run.status
        if status:
            chat.status = status
        if progress is not None:
            chat.progress = progress
        return chat

    def update_main_card(self, run, **kwargs):
        return None


class FakeEventManager:
    """Records notifications and orchestration events."""

    def __init__(self):
        self.notifications = []
        self.events = []

    def send_notification(self, **kwargs):
        self.notifications.append(kwargs)

    def orchestration_event(self, payload):
        self.events.append(payload)


def make_service(tmp_path):
    manager = FakeChatManager()
    events = FakeEventManager()
    service = OrchestrationService(
        settings=SimpleNamespace(
            codx_path=str(tmp_path / ".codx"),
            project_id="project-1",
            project_name="test",
        ),
        chat_manager=manager,
        event_manager=events,
        store=RunStore(str(tmp_path / ".codx")),
        board=FakeBoard(manager),
        message_factory=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    return service, manager, events


def read_audit(tmp_path):
    path = audit_path(str(tmp_path / ".codx"))
    if not os.path.isfile(path):
        return []
    return [json.loads(line) for line in open(path, encoding="utf-8").read().splitlines()]


def test_finish_notifies_once_and_audits(tmp_path):
    service, manager, events = make_service(tmp_path)
    chat = FakeChat("main", name="My task")
    manager.add(chat)
    run = service.create_run(
        name="My run",
        objective="Do the thing",
        main_chat=chat,
        created_by="alice",
    )
    run = service.finish(run.run_id, "All done", actor_chat_id=chat.id)
    assert run.status == C.RUN_STATUS_COMPLETED
    assert run.notification_sent is True

    # Exactly one toast notification, addressed to the main task.
    assert len(events.notifications) == 1
    notification = events.notifications[0]
    assert notification["type"] == "notification"
    assert notification["chat"]["id"] == "main"
    assert notification["run_id"] == run.run_id
    assert notification["status"] == C.RUN_STATUS_COMPLETED

    # Replaying the notification (crash recovery / duplicate tick) is a no-op.
    service._notify_completion(service.get(run.run_id))
    assert len(events.notifications) == 1

    # The run lifecycle is registered in the audit journal.
    audit = read_audit(tmp_path)
    audit_events = [entry["event"] for entry in audit]
    assert "run_event" in audit_events
    run_events = [entry["run_event"] for entry in audit if entry["event"] == "run_event"]
    assert "run_created" in run_events
    assert "run_completed" in run_events
    assert any(entry["event"] == "notification_sent" for entry in audit)


def test_finalize_notifies_for_failure(tmp_path):
    service, manager, events = make_service(tmp_path)
    chat = FakeChat("main", name="My task")
    manager.add(chat)
    run = service.create_run(
        name="My run",
        objective="Do the thing",
        main_chat=chat,
        created_by="alice",
    )
    run = service._finalize(
        run,
        C.RUN_STATUS_FAILED,
        "boom report",
        chat_status="rejected",
        column_phase="blocked",
        error="boom",
    )
    assert run.status == C.RUN_STATUS_FAILED
    assert run.notification_sent is True
    assert len(events.notifications) == 1
    assert events.notifications[0]["status"] == C.RUN_STATUS_FAILED
    assert events.notifications[0]["text"].startswith("Run 'My run' finished")


def test_resume_resets_notification_flag(tmp_path):
    service, manager, events = make_service(tmp_path)
    chat = FakeChat("main", name="My task")
    manager.add(chat)
    run = service.create_run(
        name="My run",
        objective="Do the thing",
        main_chat=chat,
        created_by="alice",
    )
    service.pause(run.run_id)
    run = service.resume(run.run_id)
    assert run.notification_sent is False
    # Completing the resumed run notifies again.
    run = service.finish(run.run_id, "Done after resume", actor_chat_id=chat.id)
    assert len(events.notifications) == 1
