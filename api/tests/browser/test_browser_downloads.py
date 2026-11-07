"""Tests for the durable download-directory mapping of browser sessions.

A download folder only works if it is written into the Chromium profile (which
is mounted at ``/config``, the container's ``$HOME``) *before* the browser
starts: ``Browser.setDownloadBehavior`` is scoped to the DevTools client that
sends it and is dropped on disconnect, and it never applies to a download the
user starts in the live VNC view.
"""

import json
import os
from unittest.mock import Mock

import pytest

from codx.junior.browser import download_settings
from codx.junior.browser.browser_manager import BrowserManager
from codx.junior.browser.docker_browser_manager import DockerBrowserManager
from codx.junior.browser.model import BrowserSession


def _preferences(profile_path):
    """Preferences file used when the profile is fresh (canonical location)."""
    return os.path.join(profile_path, ".config", "chromium", "Default", "Preferences")


def _read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------------------
# Preferences + fallback link
# ---------------------------------------------------------------------------

def test_fresh_profile_gets_the_download_directory(tmp_path):
    profile = str(tmp_path / "chromium_profile")

    report = download_settings.apply_download_settings(profile, "/downloads")

    assert report["download_dir"] == "/downloads"
    assert report["changed"] is True
    preferences = _read_json(_preferences(profile))
    assert preferences["download"]["default_directory"] == "/downloads"
    # Chromium keeps the value (no silent migration) and never asks for a path
    assert preferences["download"]["directory_upgrade"] is True
    assert preferences["download"]["prompt_for_download"] is False
    assert preferences["savefile"]["default_directory"] == "/downloads"


def test_home_downloads_fallback_is_linked_to_the_mapped_folder(tmp_path):
    profile = str(tmp_path / "chromium_profile")

    report = download_settings.apply_download_settings(profile, "/home/proj/downloads")

    link = os.path.join(profile, "Downloads")
    assert report["symlink"] == link
    assert os.path.islink(link)
    # The target is a container path: it dangles on the host on purpose
    assert os.readlink(link) == "/home/proj/downloads"


def test_existing_preferences_are_merged_not_replaced(tmp_path):
    profile = tmp_path / "chromium_profile"
    preferences_path = profile / ".config" / "chromium" / "Default" / "Preferences"
    preferences_path.parent.mkdir(parents=True)
    preferences_path.write_text(
        json.dumps({
            "download": {"default_directory": "/config/Downloads", "other": 1},
            "profile": {"name": "default"},
        }),
        encoding="utf-8",
    )

    download_settings.apply_download_settings(str(profile), "/home/proj/downloads")

    preferences = _read_json(str(preferences_path))
    assert preferences["download"]["default_directory"] == "/home/proj/downloads"
    # Unrelated settings survive the patch
    assert preferences["download"]["other"] == 1
    assert preferences["profile"]["name"] == "default"


def test_applying_twice_is_idempotent(tmp_path):
    profile = str(tmp_path / "chromium_profile")

    first = download_settings.apply_download_settings(profile, "/downloads")
    second = download_settings.apply_download_settings(profile, "/downloads")

    assert first["changed"] is True
    assert second["changed"] is False
    # The link is never recreated
    assert second["symlink"] is None
    assert first["preferences"] == second["preferences"]


def test_an_existing_downloads_folder_is_never_replaced(tmp_path):
    profile = tmp_path / "chromium_profile"
    downloads = profile / "Downloads"
    downloads.mkdir(parents=True)
    (downloads / "already-here.pdf").write_bytes(b"pdf")

    report = download_settings.apply_download_settings(str(profile), "/downloads")

    assert report["symlink"] is None
    assert (downloads / "already-here.pdf").exists()


def test_preferences_paths_prefers_existing_profiles(tmp_path):
    profile = tmp_path / "chromium_profile"
    chrome_preferences = profile / ".config" / "google-chrome" / "Default" / "Preferences"
    chrome_preferences.parent.mkdir(parents=True)
    chrome_preferences.write_text("{}", encoding="utf-8")

    paths = download_settings.preferences_paths(str(profile))

    assert paths == [str(chrome_preferences)]


def test_nothing_happens_without_a_download_directory(tmp_path):
    report = download_settings.apply_download_settings(str(tmp_path / "profile"), "")

    assert report["preferences"] == []
    assert report["symlink"] is None
    assert not os.path.exists(tmp_path / "profile")


# ---------------------------------------------------------------------------
# BrowserManager wiring
# ---------------------------------------------------------------------------

class _FakeDockerManager:
    """Docker manager double recording the state seen by ``docker run``."""

    MAX_SESSIONS = 10

    def __init__(self, profile_for, observed):
        self._profile_for = profile_for
        self._observed = observed

    def configure_share(self, session, **kwargs):
        # Same shape the real manager produces for a project-root share
        session.home_path = "/home/my-project"
        session.downloads_folder = f".codx/browser_downloads/{session.id}"
        session.downloads_mount = f"/home/my-project/.codx/browser_downloads/{session.id}"
        session.downloads_own_mount = False
        return session

    def start_container(self, session):
        # Chromium reads the profile at launch: the mapping must exist already
        preferences = _preferences(self._profile_for(session))
        self._observed.append(os.path.isfile(preferences))
        session.status = "running"
        session.container_id = "container-1"
        session.debug_url = "ws://browser:9223/devtools/browser/abc"
        return session


def _manager(tmp_path):
    manager = BrowserManager.__new__(BrowserManager)
    manager.sessions_path = str(tmp_path / "sessions")
    manager.settings = Mock(project_id="project-1", abs_project_path=str(tmp_path / "project"))
    manager.docker_manager = _FakeDockerManager(
        profile_for=manager._profile_folder,
        observed=[],
    )
    return manager


def test_create_session_writes_the_download_mapping_before_starting(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    monkeypatch.setattr(manager, "list_sessions", lambda: [])
    monkeypatch.setattr(manager, "_save_session_file", lambda session: None)
    monkeypatch.setattr(manager, "log_activity", lambda *args, **kwargs: {})
    monkeypatch.setattr(manager, "_open_keep_alive_tab", lambda session: None)

    session = manager.create_session("Downloads mapping")

    # The profile already pointed at the mapped folder when the container started
    assert manager.docker_manager._observed == [True]
    preferences = _read_json(_preferences(manager._profile_folder(session.id)))
    assert preferences["download"]["default_directory"] == session.downloads_mount
    assert os.readlink(
        os.path.join(manager._profile_folder(session.id), "Downloads")
    ) == session.downloads_mount


def test_create_session_survives_an_unwritable_profile(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    monkeypatch.setattr(manager, "list_sessions", lambda: [])
    monkeypatch.setattr(manager, "_save_session_file", lambda session: None)
    monkeypatch.setattr(manager, "log_activity", lambda *args, **kwargs: {})
    monkeypatch.setattr(manager, "_open_keep_alive_tab", lambda session: None)
    monkeypatch.setattr(
        download_settings,
        "apply_download_settings",
        Mock(side_effect=OSError("read-only profile")),
    )

    session = manager.create_session("Still starts")

    # A broken profile write must never block the session
    assert session.container_id == "container-1"


def test_restart_reapplies_the_download_mapping(tmp_path, monkeypatch):
    manager = _manager(tmp_path)
    session = BrowserSession(name="Restart", container_id="abc", status="running")
    session.downloads_mount = "/downloads"
    applied = []

    monkeypatch.setattr(
        manager, "_prepare_downloads", lambda target: applied.append(target.id) or {}
    )
    monkeypatch.setattr(manager, "_save_session_file", lambda target: None)
    monkeypatch.setattr(manager, "log_activity", lambda *args, **kwargs: {})
    # Chromium rewrites Preferences on exit: the mapping is re-asserted first
    manager.docker_manager.stop_container = lambda target, remove=True: applied.append("stop")
    manager.docker_manager.restart_container = lambda target: applied.append("start") or target

    manager._restart_browser(session, "restart")

    assert applied == [session.id, "stop", "start"]


# ---------------------------------------------------------------------------
# The mapping itself (unchanged behaviour, kept as a regression guard)
# ---------------------------------------------------------------------------

def test_downloads_folder_inside_a_mounted_folder_needs_no_extra_bind(tmp_path):
    project = tmp_path / "my-project"
    (project / "docs").mkdir(parents=True)
    docker = DockerBrowserManager(
        str(tmp_path / "sessions"),
        project_id="project-1",
        project_root_path=str(project),
    )
    session = BrowserSession(name="Docs downloads")

    docker.configure_share(session, share_folders=["docs"], downloads_folder="docs/downloads")

    assert session.downloads_mount == "/home/my-project/docs/downloads"
    assert session.downloads_own_mount is False
    assert docker._build_share_mounts(session) == [
        f"{project / 'docs'}:/home/my-project/docs"
    ]


def test_downloads_folder_outside_every_mount_gets_its_own_bind(tmp_path):
    project = tmp_path / "my-project"
    (project / "docs").mkdir(parents=True)
    docker = DockerBrowserManager(
        str(tmp_path / "sessions"),
        project_id="project-1",
        project_root_path=str(project),
    )
    session = BrowserSession(name="Own mount")

    docker.configure_share(session, share_folders=["docs"], downloads_folder="data/downloads")

    assert session.downloads_mount == "/downloads"
    assert session.downloads_own_mount is True
    assert f"{project / 'data' / 'downloads'}:/downloads" in docker._build_share_mounts(session)


def test_downloads_folder_outside_the_project_is_rejected(tmp_path):
    project = tmp_path / "my-project"
    project.mkdir()
    docker = DockerBrowserManager(
        str(tmp_path / "sessions"),
        project_id="project-1",
        project_root_path=str(project),
    )

    with pytest.raises(ValueError):
        docker.configure_share(
            BrowserSession(name="escape"), downloads_folder="../outside"
        )