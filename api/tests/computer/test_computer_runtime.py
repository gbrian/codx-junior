"""Desktop runtime: control lease, serialized actions, activity and batches."""

import asyncio
from unittest.mock import Mock

import pytest

from codx.junior.browser.model import BrowserSession
from codx.junior.computer import runtime as runtime_module
from codx.junior.computer.runtime import ComputerControlError, DesktopRuntime


class _FakeBackend:
    def __init__(self):
        self.calls = []
        self.closed = False

    async def run(self, action, **params):
        self.calls.append((action, params))
        if action == "screenshot":
            return {"image": "data:image/png;base64,x", "width": 1280, "height": 800, "text": "hello"}
        return {"action": action, **params}

    async def close(self):
        self.closed = True


def _runtime(monkeypatch, session=None):
    session = session or BrowserSession(name="desktop", kind="linux")
    backend = _FakeBackend()
    monkeypatch.setattr(runtime_module, "get_backend", lambda session, runtime=None: backend)
    manager = Mock()
    manager.log_activity = Mock()
    manager.save_session = Mock()
    runtime = DesktopRuntime(manager, session)
    return runtime, backend, manager, session


def test_ai_action_logs_and_updates_session(monkeypatch):
    runtime, backend, manager, session = _runtime(monkeypatch)

    result = asyncio.run(runtime.run("click", x=10, y=20))

    assert result["action"] == "click"
    assert backend.calls == [("click", {"x": 10, "y": 20})]
    assert session.last_action == "click"
    assert manager.log_activity.call_count == 1
    entry = manager.log_activity.call_args.kwargs
    assert entry["actor"] == "ai"
    assert entry["action"] == "click"
    manager.save_session.assert_called()


def test_read_only_screenshot_works_while_user_controls(monkeypatch):
    session = BrowserSession(name="desktop", kind="linux")
    session.set_controller("user", reason="MFA")
    runtime, backend, manager, _ = _runtime(monkeypatch, session)

    result = asyncio.run(runtime.run("screenshot"))

    assert result["width"] == 1280
    assert backend.calls[0][0] == "screenshot"


def test_state_changing_action_is_blocked_while_user_controls(monkeypatch):
    session = BrowserSession(name="desktop", kind="linux")
    session.set_controller("user", reason="MFA")
    runtime, backend, manager, _ = _runtime(monkeypatch, session)

    with pytest.raises(ComputerControlError) as error:
        asyncio.run(runtime.run("click", x=1, y=1))
    assert "MFA" in str(error.value)
    assert backend.calls == []
    assert manager.log_activity.call_args.kwargs["success"] is False


def test_user_api_action_forces_and_marks_user_active(monkeypatch):
    runtime, backend, manager, session = _runtime(monkeypatch)

    asyncio.run(runtime.run("click", x=3, y=4, force=True, actor="user"))

    assert backend.calls == [("click", {"x": 3, "y": 4})]
    assert session.user_is_active() is True
    assert manager.log_activity.call_args.kwargs["actor"] == "user"


def test_batch_interpolates_variables(monkeypatch):
    runtime, backend, manager, session = _runtime(monkeypatch)

    async def fake_run(action, **params):
        return {"action": action, **params}

    backend.run = fake_run

    result = asyncio.run(runtime.run_steps(
        [{"action": "type", "text": "{{who}}"}],
        {"who": "world"},
    ))

    assert result == {"action": "batch", "steps": [{"action": "type", "text": "world"}]}


def test_close_is_idempotent(monkeypatch):
    runtime, backend, manager, session = _runtime(monkeypatch)
    asyncio.run(runtime.close())
    asyncio.run(runtime.close())
    assert backend.closed is True
