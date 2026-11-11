"""
Tests for the cross-process "chat is processing" guard.

The orchestration worker runs in the background process while user turns run in
the API process, so the in-process cancellation registry is not enough: the
durable turn flock must prevent the worker from injecting a supervisor round
into a chat that is already executing a turn.

Run with::

    cd api && pytest tests/harness/test_turn_processing_guard.py -q
"""

from types import SimpleNamespace

from codx.junior.chat.turn_store import STATUS_CANCELLED, get_turn_store
from codx.junior.orchestration.service import OrchestrationService
from codx.junior.orchestration.store import RunStore


def _chat(chat_id="chat-1"):
    return SimpleNamespace(id=chat_id, owner_project_id="project-1")


def test_chat_is_processing_sees_a_live_turn_from_another_store(tmp_path):
    codx_path = str(tmp_path)
    owner = get_turn_store(codx_path)
    other = get_turn_store(codx_path)

    record = owner.begin(_chat("chat-1"))
    assert record is not None
    # A second store instance behaves like another process: it must see the
    # turn as live (the flock is held by the first instance).
    assert other.chat_is_processing("chat-1") is True
    assert other.chat_is_processing("chat-2") is False

    owner.finalize(record, STATUS_CANCELLED, error="test cleanup")
    assert other.chat_is_processing("chat-1") is False


def test_orchestration_service_guard_uses_the_durable_turn(tmp_path):
    service = OrchestrationService(
        settings=SimpleNamespace(
            codx_path=str(tmp_path),
            project_id="project-1",
            project_name="test",
        ),
        chat_manager=SimpleNamespace(),
        store=RunStore(str(tmp_path)),
        board=SimpleNamespace(),
        message_factory=lambda **kwargs: SimpleNamespace(**kwargs),
    )
    store = get_turn_store(str(tmp_path))
    record = store.begin(_chat("chat-1"))
    assert store is not None and record is not None

    assert service._chat_is_processing("chat-1") is True
    store.finalize(record, STATUS_CANCELLED, error="test cleanup")
    assert service._chat_is_processing("chat-1") is False
    assert service._chat_is_processing("") is False
