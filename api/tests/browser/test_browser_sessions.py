"""Tests for the co-browsing session model, audit log, container command and folder sharing."""

import json
import os
from pathlib import Path

import pytest

from codx.junior.browser.activity import BrowserActivityLog
from codx.junior.browser.docker_browser_manager import DockerBrowserManager
from codx.junior.browser.model import BrowserSession, SharedFolder


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


# ---------------------------------------------------------------------------
# Project folder sharing
# ---------------------------------------------------------------------------

def _manager(tmp_path, project_name="my-project", folders=("docs", "data")):
    """Build a Docker manager over a temporary project with the given folders."""
    project = tmp_path / project_name
    project.mkdir(parents=True, exist_ok=True)
    for folder in folders:
        (project / folder).mkdir(parents=True, exist_ok=True)
    return project, DockerBrowserManager(
        str(tmp_path / "sessions"),
        project_id="project-1",
        project_root_path=str(project),
    )


def test_mounts_many_folders_under_the_project_home(tmp_path):
    project, manager = _manager(tmp_path)

    session = BrowserSession(name="Many folders")
    manager.configure_share(session, share_folders=["docs", "data"])

    assert session.home_path == "/home/my-project"
    assert {share.folder: share.mount_path for share in session.shared_folders} == {
        "docs": "/home/my-project/docs",
        "data": "/home/my-project/data",
    }
    # Listing folders never mounts the project root implicitly
    assert session.project_share() is None

    volumes = manager._build_share_mounts(session)
    assert f"{project / 'docs'}:/home/my-project/docs" in volumes
    assert f"{project / 'data'}:/home/my-project/data" in volumes
    # Downloads are not inside a mount, so they get their own bind
    assert session.downloads_own_mount is True
    assert session.downloads_mount == "/downloads"
    assert f"{session.downloads_path}:/downloads" in volumes


def test_mounts_the_project_root_by_default(tmp_path):
    project, manager = _manager(tmp_path, folders=())

    session = BrowserSession(name="Root share")
    manager.configure_share(session)

    assert [share.folder for share in session.shared_folders] == [""]
    assert session.shared_folders[0].mount_path == "/home/my-project"
    # The default downloads folder lives inside the mounted project
    assert session.downloads_folder == f".codx/browser_downloads/{session.id}"
    assert session.downloads_own_mount is False
    assert session.downloads_mount == f"/home/my-project/.codx/browser_downloads/{session.id}"
    assert manager._build_share_mounts(session) == [f"{project}:/home/my-project"]


def test_nested_folder_keeps_its_path_and_root_wins_when_both_are_mounted(tmp_path):
    project, manager = _manager(tmp_path, folders=("docs/api",))

    nested = BrowserSession(name="Nested")
    manager.configure_share(nested, share_folders=["docs/api"])
    assert nested.shared_folders[0].mount_path == "/home/my-project/docs/api"

    both = BrowserSession(name="Root plus nested")
    manager.configure_share(both, share_project=True, share_folders=["docs/api"])
    # The mounted root already exposes the nested folder
    assert [share.folder for share in both.shared_folders] == [""]


def test_maps_a_specific_folder_for_the_downloads(tmp_path):
    project, manager = _manager(tmp_path)

    session = BrowserSession(name="Downloads")
    manager.configure_share(
        session,
        share_folders=["docs"],
        downloads_folder="docs/downloads",
    )

    assert session.downloads_folder == "docs/downloads"
    assert session.downloads_path == str(project / "docs" / "downloads")
    assert os.path.isdir(session.downloads_path)
    # Already inside the mounted docs folder: no second bind
    assert session.downloads_own_mount is False
    assert session.downloads_mount == "/home/my-project/docs/downloads"
    assert manager._build_share_mounts(session) == [
        f"{project / 'docs'}:/home/my-project/docs"
    ]


def test_downloads_mount_can_be_forced(tmp_path):
    project, manager = _manager(tmp_path)

    session = BrowserSession(name="Own downloads mount")
    manager.configure_share(
        session,
        share_folders=["docs"],
        downloads_folder="docs/downloads",
        downloads_mount="/downloads",
    )

    assert session.downloads_own_mount is True
    assert session.downloads_mount == "/downloads"
    assert f"{project / 'docs' / 'downloads'}:/downloads" in manager._build_share_mounts(session)


def test_read_only_and_custom_mount_path(tmp_path):
    project, manager = _manager(tmp_path)

    session = BrowserSession(name="Read only")
    manager.configure_share(
        session,
        share_folders=[{"folder": "docs", "readonly": True, "mount_path": "/work/docs"}],
    )

    share = session.shared_folders[0]
    assert share.mount_path == "/work/docs"
    assert share.readonly is True
    assert manager._build_share_mounts(session)[0] == f"{project / 'docs'}:/work/docs:ro"


def test_configure_share_validates_every_folder(tmp_path):
    _, manager = _manager(tmp_path)

    with pytest.raises(ValueError):
        manager.configure_share(BrowserSession(name="escape"), share_folders=["../outside"])
    with pytest.raises(ValueError):
        manager.configure_share(BrowserSession(name="missing"), share_folders=["missing"])
    with pytest.raises(ValueError):
        manager.configure_share(BrowserSession(name="mount"), share_folders=[
            {"folder": "docs", "mount_path": "../escape"}
        ])
    with pytest.raises(ValueError):
        manager.configure_share(
            BrowserSession(name="downloads"), downloads_folder="../outside"
        )


def test_sharing_disabled_keeps_downloads_in_the_session_folder(tmp_path):
    _, manager = _manager(tmp_path)

    session = BrowserSession(name="No share")
    manager.configure_share(session, share_project=False)

    assert session.shared_folders == []
    assert session.downloads_folder is None
    assert session.downloads_path == str(tmp_path / "sessions" / session.id / "downloads")
    assert session.downloads_mount == "/downloads"
    assert os.path.isdir(session.downloads_path)


def test_session_migrates_the_legacy_single_share():
    session = BrowserSession(
        name="Legacy",
        shared_project_path="/repo",
        shared_project_mount="/project",
        shared_project_readonly=True,
    )

    assert len(session.shared_folders) == 1
    assert session.shared_folders[0].mount_path == "/project"
    assert session.shared_folders[0].readonly is True


def test_session_share_helpers_resolve_project_files(tmp_path):
    project = tmp_path / "project"
    (project / "docs").mkdir(parents=True)
    (project / "docs" / "report.md").write_text("# report", encoding="utf-8")

    session = BrowserSession(name="Shared")
    session.home_path = "/home/project"
    session.shared_folders = [
        SharedFolder(
            name="project",
            folder="",
            host_path=str(project),
            mount_path="/home/project",
        )
    ]
    session.downloads_path = str(project / ".codx" / "browser_downloads" / "s1")
    session.downloads_mount = "/home/project/.codx/browser_downloads/s1"

    assert session.shares_project()
    assert session.shares_files()
    assert session.project_file_path("docs/report.md") == str(project / "docs" / "report.md")
    assert session.container_project_path("docs/report.md") == "/home/project/docs/report.md"
    assert session.project_file_url("docs/report.md") == "file:///home/project/docs/report.md"
    assert session.covering_share(str(project / "docs")) is session.shared_folders[0]
    with pytest.raises(ValueError):
        session.project_file_path("../outside.txt")


def test_run_command_mounts_the_project_folders(tmp_path, monkeypatch):
    project, manager = _manager(tmp_path)
    monkeypatch.setattr(manager, "_ensure_image", lambda: None)
    proxy_path = tmp_path / "cdp_proxy.py"
    proxy_path.write_text("# proxy", encoding="utf-8")
    monkeypatch.setattr(manager, "_prepare_cdp_proxy", lambda session_id: str(proxy_path))

    session = BrowserSession(name="Mount test")
    session.id = "12345678-aaaa-bbbb-cccc-ddddeeeeffff"
    manager.configure_share(session, share_project=True, share_folders=["docs"])

    cmd = manager._build_run_command(
        session=session,
        container_name="browser_12345678",
        profile_path=str(tmp_path / "chromium_profile"),
        path_prefix=f"/browser/{session.id}/",
        router_name="codx-browser-12345678",
    )

    assert f"{project}:/home/my-project" in cmd


def test_get_shared_files_lists_downloads(tmp_path):
    from unittest.mock import Mock, patch

    from codx.junior.browser.browser_manager import BrowserManager

    project = tmp_path / "project"
    project.mkdir()
    manager = BrowserManager.__new__(BrowserManager)
    manager.settings = Mock(project_id="project-1", abs_project_path=str(project))
    manager.sessions_path = str(tmp_path / "sessions")

    session = BrowserSession(name="Files")
    downloads = project / ".codx" / "browser_downloads" / session.id
    downloads.mkdir(parents=True)
    (downloads / "report.pdf").write_bytes(b"pdf")
    (downloads / "report.pdf.crdownload").write_bytes(b"partial")
    session.downloads_path = str(downloads)
    session.downloads_folder = f".codx/browser_downloads/{session.id}"
    session.downloads_mount = f"/home/project/.codx/browser_downloads/{session.id}"

    with patch.object(BrowserManager, "get_session", return_value=session):
        paths = manager.get_shared_paths(session.id)
        files = manager.get_shared_files(session.id)

    assert paths["downloads_path"] == str(downloads)
    assert paths["folders"] == []
    assert [entry["name"] for entry in files] == ["report.pdf"]
    assert files[0]["container_path"] == (
        f"/home/project/.codx/browser_downloads/{session.id}/report.pdf"
    )
    assert files[0]["path"] == f".codx/browser_downloads/{session.id}/report.pdf"
    assert files[0]["size"] == 3