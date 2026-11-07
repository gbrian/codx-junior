"""Tests for the co-browsing primitives added on top of the browser tools.

Covers:
* the human/AI control lease (handoff, take, release, recent input);
* the tail read + secret redaction of the activity log;
* the deterministic step runner (aliases, variables, stop-on-error, outputs).
"""

import asyncio
import json

from codx.junior.browser.activity import BrowserActivityLog, _safe_params
from codx.junior.browser.actions import (
    StepError,
    interpolate,
    normalize_step,
    run_steps,
)
from codx.junior.browser.model import BrowserSession


def test_control_lease_handoff_and_release():
    session = BrowserSession(name="co-browsing")
    assert session.controller == "ai"
    assert session.can_ai_act() is True

    session.request_handoff("MFA required", chat_id="chat-1")
    assert session.controller == "user"
    assert session.handoff_reason == "MFA required"
    assert session.can_ai_act() is False
    assert session.user_is_active() is True

    session.set_controller("ai")
    assert session.controller == "ai"
    assert session.handoff_reason is None
    assert session.user_active_until is None
    assert session.can_ai_act() is True


def test_recent_user_input_pauses_ai_but_can_expire(monkeypatch):
    session = BrowserSession(name="co-browsing")
    session.mark_user_active(seconds=30)
    assert session.user_is_active() is True
    assert session.can_ai_act() is False

    # A zero-length window is immediately idle.
    session.mark_user_active(seconds=1)
    session.user_active_until = "2000-01-01T00:00:00"
    assert session.user_is_active() is False
    assert session.can_ai_act() is True


def test_activity_tail_reads_only_the_end(tmp_path):
    log = BrowserActivityLog(str(tmp_path))
    for index in range(5000):
        log.record(actor="ai", action="click", params={"index": index})
    entries = log.read(limit=3)
    assert [entry["params"]["index"] for entry in entries] == [4997, 4998, 4999]


def test_activity_redacts_input_values():
    assert _safe_params({"value": "hunter2", "selector": "#password"}, "fill") == {
        "value_redacted": True,
        "value_length": 7,
        "selector": "#password",
    }
    # A click has no secret value to redact.
    assert _safe_params({"value": "visible"}, "click")["value"] == "visible"


def test_normalize_step_accepts_aliases_and_targets():
    assert normalize_step({"type": "goto", "url": "https://x"})["action"] == "navigate"
    assert normalize_step({"action": "type", "target": {"selector": "#q"}})["selector"] == "#q"
    assert normalize_step({"action": "click", "target": "button.save"})["selector"] == "button.save"
    assert interpolate({"url": "https://x/{{path}}"}, {"path": "a"}) == {"url": "https://x/a"}


class _FakeBrowser:
    def __init__(self):
        self.calls = []

    async def navigate(self, url):
        self.calls.append(("navigate", url))
        return "Title"

    async def click(self, selector):
        self.calls.append(("click", selector))

    async def click_ref(self, ref):
        self.calls.append(("click_ref", ref))

    async def fill(self, selector, value):
        self.calls.append(("fill", selector, value))

    async def wait_for_text(self, text, timeout=0):
        self.calls.append(("wait", text, timeout))

    async def execute_script(self, script):
        self.calls.append(("js", script))
        return 1

    async def get_screenshot(self, full_page=False):
        return "data:image/png;base64,AAAA"


def test_run_steps_aliases_variables_and_outputs():
    browser = _FakeBrowser()
    steps = [
        {"action": "goto", "url": "https://example.com/{{path}}"},
        {"action": "type", "selector": "#q", "value": "{{query}}"},
        {"action": "click", "ref": "e3"},
        {"action": "wait_for", "text": "Results", "timeout": 2500},
        {"action": "evaluate", "script": "return 1", "as": "value"},
        {"action": "assert", "expr": "outputs.value === 1"},
    ]
    result = asyncio.run(run_steps(browser, steps, {"path": "search", "query": "hello"}))
    assert result["ok"] is True
    assert result["failed_step"] is None
    assert browser.calls[0] == ("navigate", "https://example.com/search")
    assert browser.calls[1] == ("fill", "#q", "hello")
    assert browser.calls[2] == ("click_ref", "e3")
    assert browser.calls[3] == ("wait", "Results", 2500)


def test_run_steps_stops_at_first_failure():
    class Failing(_FakeBrowser):
        async def click(self, selector):
            raise RuntimeError("not found")

    browser = Failing()
    result = asyncio.run(run_steps(browser, [
        {"action": "click", "selector": "#missing"},
        {"action": "click", "selector": "#never"},
    ]))
    assert result["ok"] is False
    assert result["failed_step"] == 0
    assert "not found" in result["error"]
    assert len(result["steps"]) == 1


def test_run_steps_handles_optional_failure():
    class Failing(_FakeBrowser):
        async def click(self, selector):
            raise RuntimeError("not found")

    result = asyncio.run(run_steps(Failing(), [
        {"action": "click", "selector": "#missing", "optional": True},
        {"action": "navigate", "url": "https://example.com"},
    ]))
    assert result["ok"] is True
    assert len(result["steps"]) == 2


def test_control_fields_round_trip_through_json():
    session = BrowserSession(name="co-browsing")
    session.request_handoff("captcha", chat_id="chat-1")
    restored = BrowserSession.from_json(session.to_json())
    assert restored.controller == "user"
    assert restored.handoff_reason == "captcha"
    assert restored.controller_chat_id == "chat-1"


def test_run_browser_script_tool_uses_the_deterministic_runtime(tmp_path, monkeypatch):
    from codx.junior.browser.model import BrowserSession
    from codx.junior.browser.scripts import BrowserScriptStore
    from codx.junior.tools import browser_script_tools

    store = BrowserScriptStore(str(tmp_path))
    script = store.save_script(
        title="Example flow",
        site="example.com",
        code=[{"action": "goto", "url": "https://example.com"}],
    )

    session = BrowserSession(name="Script session", chat_ids=["chat-1"], status="running")
    calls = []

    class Runtime:
        async def run_steps(self, steps, variables):
            calls.append((steps, variables))
            return {"ok": True, "steps": [{"index": 0, "action": "navigate", "ok": True, "ms": 1}], "outputs": {}, "ms": 1}

    class Manager:
        def get_session_for_chat(self, chat_id):
            return session

        async def get_runtime(self, target):
            return Runtime()

        def log_activity(self, *args, **kwargs):
            calls.append(kwargs.get("action"))

        def get_session(self, session_id):
            return session

    class Settings:
        project_path = str(tmp_path)

    monkeypatch.setattr(
        "codx.junior.browser.browser_manager.get_browser_manager",
        lambda settings: Manager(),
    )

    result = asyncio.run(browser_script_tools.run_browser_script(
        script_id=script.id,
        chat_id="chat-1",
        settings=Settings(),
    ))
    assert "completed" in result.llm_response
    assert calls[0][0][0]["action"] == "goto"
    assert "run_script" in calls
