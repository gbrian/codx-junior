"""Tests for the co-browsing session model, audit log and container command."""

import json
import os
from pathlib import Path

import pytest

from codx.junior.browser.activity import BrowserActivityLog
from codx.junior.browser.docker_browser_manager import DockerBrowserManager
from codx.junior.browser.model import BrowserSession


def test_session_migrates_legacy_chat_id_and_tracks_action():
    session = BrowserSession(chat_id="legacy-chat", name="Co-browse")

    assert session.chat_ids == ["legacy-chat"]
    assert session.engine == "chromium"
    session.mark_action("navigate")
    assert session.last_action == "navigate"
    assert session.last_action_at


def test_activity_log_roundtrip(tmp_path):
    log = BrowserActivityLog(str(tmp_path))
    log.record(
        actor="ai",
        action="navigate",
        session_id="session-1",
        chat_id="chat-1",
        params={"url": "https://example.com", "settings": object()},
        url="https://example.com",
        title="Example",
        duration_ms=12.5,
    )
    log.record(actor="user", action="click", session_id="session-1", params={"selector": "#go"})

    entries = log.read(limit=10)
    assert [entry["actor"] for entry in entries] == ["ai", "user"]
    assert entries[0]["params"] == {"url": "https://example.com"}
    assert entries[1]["action"] == "click"
    # The log is append-only JSONL.
    lines = Path(tmp_path, "activity.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    json.loads(lines[0])


def test_run_command_targets_chromium_with_vnc_and_cdp_proxy(tmp_path, monkeypatch):
    manager = DockerBrowserManager(
        str(tmp_path),
        traefik_domain="example.test",
        project_id="project-1",
    )
    monkeypatch.setattr(manager, "_ensure_image", lambda: None)
    proxy_path = tmp_path / "cdp_proxy.py"
    proxy_path.write_text("# proxy", encoding="utf-8")
    monkeypatch.setattr(manager, "_prepare_cdp_proxy", lambda session_id: str(proxy_path))

    session = BrowserSession(name="Command test", current_url="https://example.com")
    session.id = "12345678-aaaa-bbbb-cccc-ddddeeeeffff"
    cmd = manager._build_run_command(
        session=session,
        container_name="browser_12345678",
        profile_path=str(tmp_path / "chromium_profile"),
        path_prefix=f"/browser/{session.id}/",
        router_name="codx-browser-12345678",
    )
    joined = " ".join(cmd)

    assert manager.image == "lscr.io/linuxserver/chromium:latest"
    assert "browser_12345678" in cmd
    assert "SUBFOLDER=/browser/12345678-aaaa-bbbb-cccc-ddddeeeeffff/" in cmd
    assert "CHROME_CLI=--remote-debugging-port=9222" in joined
    assert f"{proxy_path}:/cdp_proxy.py:ro" in cmd
    assert "--entrypoint" in cmd and "/bin/bash" in cmd
    assert "python3 /cdp_proxy.py" in joined
    assert "traefik.http.routers.codx-browser-12345678.rule=" in joined
    assert "PathPrefix(`/browser/12345678-aaaa-bbbb-cccc-ddddeeeeffff/`)" in joined
    # The live view is served by the container on 3000; no host port is published.
    assert "3000" in joined
    assert "-p" not in cmd


def test_resolve_debug_url_rewrites_loopback_host(tmp_path, monkeypatch):
    manager = DockerBrowserManager(str(tmp_path), traefik_domain="example.test")
    monkeypatch.setattr(
        manager,
        "_http_json",
        lambda url: {
            "webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/abc-123?x=1"
        },
    )

    assert manager._resolve_debug_url("browser_abc") == (
        "ws://browser_abc:9223/devtools/browser/abc-123?x=1"
    )


def test_cost_summary_combines_chat_cost_and_analytics(tmp_path, monkeypatch):
    from unittest.mock import Mock, patch

    from codx.junior.browser.browser_manager import BrowserManager
    from codx.junior.browser.model import BrowserSession

    manager = BrowserManager.__new__(BrowserManager)
    manager.settings = Mock(project_id="project-1")
    manager.sessions_path = str(tmp_path)
    session = BrowserSession(name="Cost test", chat_ids=["chat-1", "chat-2"])
    monkeypatch.setattr(manager, "get_session", lambda session_id: session)

    chat = Mock()
    chat.cost = 2.5
    chat.estimation_cost = 10.0
    chat.name = "Shared chat"
    chat_manager = Mock()
    chat_manager.find_by_id.return_value = chat

    analytics = Mock()
    analytics.get_chat_with_requests.return_value = {
        "llm_requests": [
            Mock(input_tokens=100, output_tokens=50),
            Mock(input_tokens=20, output_tokens=10),
        ],
        "tool_calls": [Mock(), Mock(), Mock()],
    }

    with patch("codx.junior.chat_manager.ChatManager", return_value=chat_manager), \
         patch("codx.junior.analytics.analytics.Analytics", return_value=analytics):
        summary = manager.get_cost_summary("session-1")

    assert summary["total_cost_cxjcoins"] == 5.0
    assert summary["total_input_tokens"] == 240
    assert summary["total_output_tokens"] == 120
    assert summary["total_llm_calls"] == 4
    assert summary["total_tool_calls"] == 6
    assert len(summary["chats"]) == 2


def test_save_session_to_chat_uses_chat_meta_data(tmp_path):
    from unittest.mock import Mock

    from codx.junior.browser.browser_manager import BrowserManager
    from codx.junior.db import Chat

    manager = BrowserManager.__new__(BrowserManager)
    manager.settings = Mock(project_id="project-1")
    manager.sessions_path = str(tmp_path)
    manager.docker_manager = Mock()

    session = BrowserSession(name="Chat-linked session")
    chat = Chat(id="chat-1", name="Test chat")

    manager.save_session_to_chat(session, chat)

    assert chat.meta_data["browser"]["id"] == session.id
    assert chat.id in session.chat_ids
    # The snapshot can be read back by the browser manager.
    loaded = manager.get_session_from_chat(chat)
    assert loaded is not None and loaded.id == session.id
