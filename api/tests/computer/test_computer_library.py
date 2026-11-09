"""Saved-computer library: commit metadata, profile archives and reuse."""

import asyncio
import base64
import json
import os
from types import SimpleNamespace

from codx.junior.browser.model import BrowserSession
from codx.junior.computer.library import (
    SavedComputer,
    SavedComputerLibrary,
    archive_profile,
    restore_profile,
    save_session_to_library,
    saved_image_name,
)


def _manifest(folder, name="demo", live_view="selkies"):
    item = SavedComputer(
        id="11111111-2222-3333-4444-555555555555",
        name=name,
        image="codx-saved/project/demo:20260101-000000",
        provider="linuxserver",
        live_view=live_view,
        live_port=3000,
        live_scheme="http",
        strip_prefix=False,
        control="docker",
        created_at="2026-01-01T00:00:00+00:00",
    )
    library = SavedComputerLibrary(str(folder), project_id="p", project_name="Project")
    library.save(item)
    return library, item


def test_library_roundtrip_and_delete(tmp_path):
    library, item = _manifest(tmp_path)
    assert library.get(item.id).name == "demo"
    assert [entry.id for entry in library.list()] == [item.id]
    assert library.delete(item.id, remove_image=False) is True
    assert library.get(item.id) is None


def test_saved_image_name_is_docker_safe():
    image = saved_image_name("My Project!", "Android SDK / Dev")
    assert image.startswith("codx-saved/my-project/android-sdk-dev:")
    assert image == image.lower()
    assert " " not in image and "!" not in image


def test_archive_skips_caches_and_restores(tmp_path):
    profile = tmp_path / "profile"
    profile.mkdir()
    (profile / ".config").mkdir()
    (profile / ".config" / "app.conf").write_text("setting=1")
    (profile / ".cache").mkdir()
    (profile / ".cache" / "huge.bin").write_bytes(b"cache")
    archive = tmp_path / "profile.tar.gz"

    size = archive_profile(str(profile), str(archive))
    assert size > 0
    target = tmp_path / "restored"
    item = SavedComputer(
        id="x", name="x", image="img", created_at="now",
        include_profile=True, has_profile=True,
    )
    library = SimpleNamespace(profile_path=lambda _id: str(archive))
    restore_profile(item, library, str(target))
    assert (target / ".config" / "app.conf").read_text() == "setting=1"
    assert not (target / ".cache").exists()


class _FakeDocker:
    def __init__(self, profile_path):
        self.profile_path = str(profile_path)

    def _desktop_profile_path(self, session_id):
        return self.profile_path


class _FakeRuntime:
    async def screenshot(self, **kwargs):
        return {"image": "data:image/png;base64," + base64.b64encode(b"PNGDATA").decode()}


class _FakeManager:
    def __init__(self, codx_path, profile_path):
        self.settings = SimpleNamespace(
            codx_path=str(codx_path),
            project_id="project-1",
            project_name="My Project",
        )
        self.docker_manager = _FakeDocker(profile_path)
        self.activity = []

    async def get_runtime(self, session):
        return _FakeRuntime()

    def log_activity(self, session, **kwargs):
        self.activity.append(kwargs)


def test_save_session_commits_and_stores_preview_profile(tmp_path, monkeypatch):
    import codx.junior.computer.library as library_module

    profile = tmp_path / "desktop_profile"
    profile.mkdir()
    (profile / ".config").mkdir()
    (profile / ".config" / "xfce.conf").write_text("theme=dark")
    (profile / ".cache").mkdir()
    (profile / ".cache" / "cache.bin").write_bytes(b"x" * 100)
    manager = _FakeManager(tmp_path / "codx", profile)
    session = BrowserSession(
        name="Custom desktop",
        kind="linux",
        image="lscr.io/linuxserver/webtop:ubuntu-xfce",
        image_provider="linuxserver",
        live_view="selkies",
        live_port=3000,
        live_scheme="http",
        strip_prefix=False,
        control="docker",
    )
    session.id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    session.container_id = "container-1"
    session.container_name = "computer_aaaaaaaa"
    session.status = "running"
    session.profile_path = str(profile)
    session.cpu_cores = 4
    session.ram_size = "8G"
    session.shm_size = "1g"
    session.extra_env = {"FOO": "bar"}

    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="sha256:abc", stderr="")

    monkeypatch.setattr(library_module.subprocess, "run", fake_run)
    monkeypatch.setattr(library_module, "image_size", lambda image: 123456)

    item = asyncio.run(save_session_to_library(
        manager,
        session,
        name="Android SDK desktop",
        description="SDK installed",
        include_profile=True,
        created_by="alice",
    ))

    assert calls[0][:2] == ["docker", "commit"]
    assert item.provider == "linuxserver"
    assert item.live_view == "selkies"
    assert item.image.startswith("codx-saved/my-project/android-sdk-desktop:")
    assert item.base_image == "lscr.io/linuxserver/webtop:ubuntu-xfce"
    assert item.image_size_bytes == 123456
    assert item.created_by == "alice"
    assert item.has_profile is True
    assert item.profile_size_bytes and item.profile_size_bytes > 0
    assert item.has_preview is True
    assert item.defaults["cpu_cores"] == 4
    assert item.defaults["extra_env"] == {"FOO": "bar"}
    assert manager.activity and manager.activity[0]["action"] == "save_library"

    library = SavedComputerLibrary(str(tmp_path / "codx"))
    stored = library.get(item.id)
    assert stored.name == "Android SDK desktop"
    assert (tmp_path / "codx" / "computer_library" / item.id / "preview.png").read_bytes() == b"PNGDATA"

    target = tmp_path / "new_profile"
    restore_profile(stored, library, str(target))
    assert (target / ".config" / "xfce.conf").read_text() == "theme=dark"
    assert not (target / ".cache").exists()


def test_save_rejects_vm_and_remote_like_sessions(tmp_path):
    manager = _FakeManager(tmp_path / "codx", tmp_path / "profile")
    session = BrowserSession(name="Windows", kind="windows")
    session.id = "bbbbbbbb-bbbb-cccc-dddd-eeeeeeeeeeee"
    session.container_id = "container-2"
    session.status = "running"
    try:
        asyncio.run(save_session_to_library(manager, session, name="VM"))
    except ValueError as ex:
        assert "Linux desktop" in str(ex)
    else:
        raise AssertionError("VM save should be rejected")


def test_api_routes_expose_library_before_dynamic_session_route():
    from codx.junior.api.computer import router

    paths = [getattr(route, "path", "") for route in router.routes]
    assert "/computers/library" in paths
    assert paths.index("/computers/library") < paths.index("/computers/{session_id}")
    assert "/computers/{session_id}/save" in paths
