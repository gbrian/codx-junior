"""
Tests for the durable chat-turn store (restart recovery).

The tests use the real file-backed store in a temporary directory. No AI
provider, database or socket is involved.
"""

import os
from types import SimpleNamespace

from codx.junior.chat.turn_store import (
    ChatTurnStore,
    STATUS_QUEUED,
    STATUS_RUNNING,
    get_turn_store,
    repair_incomplete_messages,
)


def _chat(chat_id="chat-1", messages=None):
    return SimpleNamespace(
        id=chat_id,
        owner_project_id="project-1",
        messages=list(messages or []),
    )


def _message(**kwargs):
    defaults = {
        "role": "assistant",
        "content": "* Processing request, please wait...*",
        "done": False,
        "error": None,
        "hide": False,
        "meta_data": {},
        "doc_id": "message-1",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_begin_persists_and_locks_the_turn(tmp_path):
    store = get_turn_store(str(tmp_path))
    record = store.begin(chat=_chat())

    assert record is not None
    assert record.status == STATUS_QUEUED
    assert os.path.isfile(store.turn_path(record.turn_id))
    assert store.is_owned(record.turn_id)
    assert [item.turn_id for item in store.list_active()] == [record.turn_id]

    store.complete(record)
    assert store.list_active() == []
    assert not store.is_owned(record.turn_id)


def test_mark_running_increments_attempt_on_recovery(tmp_path):
    store = ChatTurnStore(str(tmp_path))
    record = store.begin(chat=_chat())
    record.attempts = 1
    store.mark_running(record, attempts=1)

    assert record.status == STATUS_RUNNING
    assert record.attempts == 1
    assert record.started_at


def test_cancel_chat_marks_orphan_and_repairs_message(tmp_path):
    store = ChatTurnStore(str(tmp_path))
    chat = _chat(messages=[_message()])
    record = store.begin(chat=chat)

    # Simulate a process death: the lock is released, the record stays.
    store.release(record.turn_id)

    manager_calls = []
    manager = SimpleNamespace(
        update_message=lambda chat, message: manager_calls.append(message.doc_id),
        save_chat=lambda chat: manager_calls.append("save"),
    )

    assert store.cancel_chat(chat.id) == 1
    assert store.list_active() == []

    repair_incomplete_messages(
        chat,
        manager,
        note="",
        error="The turn was stopped by the user",
    )
    assert chat.messages[0].done is True
    assert chat.messages[0].hide is True
    assert chat.messages[0].error == "The turn was stopped by the user"
    assert manager_calls == ["message-1"]


def test_cancel_live_turn_only_marks_the_marker(tmp_path):
    store = ChatTurnStore(str(tmp_path))
    record = store.begin(chat=_chat())

    assert store.cancel_chat(record.chat_id) == 1
    # The live owner must finalize the record itself; the lock is not stolen.
    assert store.is_owned(record.turn_id)
    assert store.cancel_requested(record.turn_id)
    assert store.list_active() == [record]


def test_repair_skips_live_turn_messages(tmp_path):
    store = ChatTurnStore(str(tmp_path))
    chat = _chat(messages=[_message(meta_data={"turn_id": "live-turn"})])
    manager = SimpleNamespace(
        update_message=lambda chat, message: None,
        save_chat=lambda chat: None,
    )

    repaired = repair_incomplete_messages(
        chat,
        manager,
        skip_turn_ids=["live-turn"],
    )
    assert repaired == 0
    assert chat.messages[0].done is False


def test_repair_hides_orphaned_processing_message():
    chat = _chat(
        messages=[
            _message(meta_data={"turn_id": "dead-turn"}),
            _message(doc_id="done", done=True, content="answer"),
        ]
    )
    manager = SimpleNamespace(
        update_message=lambda chat, message: None,
        save_chat=lambda chat: None,
    )

    assert repair_incomplete_messages(chat, manager) == 1
    assert chat.messages[0].done is True
    assert chat.messages[0].hide is True
    assert "interrupted" in chat.messages[0].meta_data
    # Completed messages are never touched.
    assert chat.messages[1].hide is False


class _FakeSettings:
    def __init__(self, codx_path):
        self.codx_path = codx_path
        self.project_id = "project-1"
        self.project_name = "Project 1"


def test_recovery_resumes_an_orphaned_turn(tmp_path, monkeypatch):
    from codx.junior.chat.turn_recovery import ChatTurnRecovery

    codx_path = str(tmp_path)
    store = ChatTurnStore(codx_path)
    chat = _chat(messages=[_message()])
    record = store.begin(chat=chat)

    # Simulate a crash: the record stays but the OS released its lock.
    store.release(record.turn_id)

    executed = []

    async def fake_execute(settings, recovered):
        executed.append(recovered.turn_id)
        store.complete(recovered)

    worker = ChatTurnRecovery(interval_seconds=60)
    monkeypatch.setattr(worker, "_projects", lambda: [_FakeSettings(codx_path)])
    monkeypatch.setattr(worker, "_repair_chat", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "_execute", fake_execute)

    result = worker.recover_once()

    assert result["recovered"] == [record.turn_id]
    assert executed == [record.turn_id]
    assert store.list_active() == []


def test_recovery_gives_up_after_max_attempts(tmp_path, monkeypatch):
    from codx.junior.chat.turn_recovery import ChatTurnRecovery

    codx_path = str(tmp_path)
    store = ChatTurnStore(codx_path)
    record = store.begin(chat=_chat(), max_attempts=1)
    record.attempts = 1
    store.save(record)
    store.release(record.turn_id)

    worker = ChatTurnRecovery(interval_seconds=60)
    monkeypatch.setattr(worker, "_projects", lambda: [_FakeSettings(codx_path)])
    monkeypatch.setattr(worker, "_repair_chat", lambda *args, **kwargs: None)

    result = worker.recover_once()

    assert result["failed"] == [record.turn_id]
    assert store.list_active() == []

