"""Tests for the computer-session model and its backwards compatibility."""

import pytest

from codx.junior.browser.model import BrowserSession, ComputerSession, normalize_kind


def test_kind_aliases_and_defaults():
    assert normalize_kind("mac") == "macos"
    assert normalize_kind("win") == "windows"
    assert normalize_kind("ubuntu") == "linux"
    assert normalize_kind(None) == "browser"

    session = BrowserSession(name="Mac", kind="osx")
    assert session.kind == "macos"
    assert session.control == "vnc"
    assert session.engine == "desktop"
    assert "screenshot" in session.capabilities
    assert session.is_desktop is True
    assert session.is_browser is False


def test_linux_control_defaults_to_docker_and_browser_to_cdp():
    linux = BrowserSession(kind="linux")
    browser = BrowserSession(kind="browser")
    assert linux.control == "docker"
    assert browser.control == "cdp"
    assert ComputerSession is BrowserSession


def test_remote_session_requires_a_host_only_at_creation():
    session = BrowserSession(kind="remote", vnc_host="mac-mini.local", vnc_port=5901)
    assert session.vnc_host == "mac-mini.local"
    assert session.vnc_port == 5901
    assert session.control == "vnc"


def test_secrets_never_reach_the_public_record():
    session = BrowserSession(
        kind="remote",
        vnc_host="host",
        vnc_password="vnc-secret",
        ssh_password="ssh-secret",
        ssh_key_path="/home/user/.ssh/id_ed25519",
    )
    public = session.to_public_dict()
    assert "vnc_password" not in public
    assert "ssh_password" not in public
    assert "ssh_key_path" not in public
    # Persistence keeps them.
    assert session.to_dict()["vnc_password"] == "vnc-secret"


def test_legacy_session_migrates_to_browser_and_nullable_fields_reload():
    legacy = BrowserSession(chat_id="c1", engine="chromium")
    assert legacy.kind == "browser"
    assert legacy.control == "cdp"

    reloaded = BrowserSession.from_dict({
        **legacy.to_dict(),
        "vnc_port": None,
        "ssh_port": None,
        "desktop_width": None,
        "desktop_height": None,
    })
    assert reloaded.vnc_port == 5900
    assert reloaded.ssh_port == 22
    assert reloaded.desktop_width == 1920
    assert reloaded.desktop_height == 1080


def test_unknown_kind_is_rejected():
    with pytest.raises(Exception):
        BrowserSession(kind="beos")


def test_profile_path_alias_mirrors_browser_profile_path():
    session = BrowserSession(kind="linux", profile_path="/tmp/profile")
    assert session.browser_profile_path == "/tmp/profile"
    session2 = BrowserSession(kind="linux", browser_profile_path="/tmp/other")
    assert session2.profile_path == "/tmp/other"


def test_advanced_resource_settings_are_normalized():
    session = BrowserSession(
        kind="windows",
        cpu_cores=6,
        ram_size="8g",
        disk_size="64GiB",
        shm_size="2gb",
        extra_env="FOO=bar\n# ignored comment\nBAZ=1",
        desktop_width=2560,
        desktop_height=1440,
    )

    assert session.cpu_cores == 6
    assert session.ram_size == "8G"
    assert session.disk_size == "64G"
    assert session.shm_size == "2G"
    assert session.extra_env == {"FOO": "bar", "BAZ": "1"}
    assert session.to_public_dict()["ram_size"] == "8G"


def test_advanced_settings_are_optional_and_bounded():
    # Empty form fields mean "use the image/manager default".
    session = BrowserSession(kind="linux", cpu_cores=0, ram_size="", disk_size=None, shm_size="")
    assert session.cpu_cores is None
    assert session.ram_size is None
    assert session.disk_size is None
    assert session.shm_size is None
    assert session.extra_env == {}

    for invalid in (
        {"ram_size": "8"},          # bytes are too easy to get wrong
        {"disk_size": "large"},
        {"shm_size": "-1G"},
        {"cpu_cores": 129},
        {"extra_env": {"BAD KEY": "x"}},
        {"extra_env": ["NO_EQUALS"]},
    ):
        with pytest.raises(ValueError):
            BrowserSession(kind="windows", **invalid)


def test_extra_env_accepts_mapping_list_and_lines():
    session = BrowserSession(
        kind="linux",
        extra_env=["A=1", "B=two"],
    )
    assert session.extra_env == {"A": "1", "B": "two"}

    session = BrowserSession(
        kind="linux",
        extra_env={"A": 1, "B": None},
    )
    assert session.extra_env == {"A": "1", "B": ""}


def test_manager_update_session_persists_advanced_settings(monkeypatch):
    from codx.junior.browser.browser_manager import BrowserManager

    manager = BrowserManager.__new__(BrowserManager)
    session = BrowserSession(kind="macos", name="Mac")
    saved = []
    monkeypatch.setattr(manager, "get_session", lambda sid: session)
    monkeypatch.setattr(manager, "_save_session_file", lambda item: saved.append(item))
    monkeypatch.setattr(manager, "log_activity", lambda *args, **kwargs: {})

    updated = manager.update_session(
        session.id,
        name="Mac build",
        advanced={"disk_size": "256g", "cpu_cores": 8},
    )

    assert updated.name == "Mac build"
    assert updated.disk_size == "256G"
    assert updated.cpu_cores == 8
    assert saved == [session]

    with pytest.raises(ValueError):
        manager.update_session(session.id, advanced={"disk_size": "nope"})
    assert session.disk_size == "256G"


def test_manager_update_session_re_resolves_linux_image_profile(monkeypatch):
    from types import SimpleNamespace

    from codx.junior.browser.browser_manager import BrowserManager

    manager = BrowserManager.__new__(BrowserManager)
    session = BrowserSession(kind="linux", image="lscr.io/linuxserver/webtop:debian-kde")
    monkeypatch.setattr(manager, "get_session", lambda sid: session)
    monkeypatch.setattr(manager, "_save_session_file", lambda item: None)
    monkeypatch.setattr(manager, "log_activity", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        "codx.junior.computer.images.resolve_image",
        lambda image, **kwargs: SimpleNamespace(
            image="kasmweb/core-ubuntu-jammy:1.18.0",
            provider="kasmweb",
            live_view="kasmvnc",
            live_port=6901,
            live_scheme="https",
            strip_prefix=True,
            viewer_user="kasm_user",
        ),
    )

    manager.update_session(session.id, advanced={"image": "kasmweb/core-ubuntu-jammy:1.18.0"})

    assert session.image == "kasmweb/core-ubuntu-jammy:1.18.0"
    assert session.image_provider == "kasmweb"
    assert session.live_view == "kasmvnc"
    assert session.live_port == 6901
    assert session.strip_prefix is True
    assert session.viewer_password  # generated for the KasmVNC viewer


def test_apply_advanced_settings_updates_and_clears():
    session = BrowserSession(kind="macos", ram_size="8G", disk_size="64G")
    session.apply_advanced_settings({
        "disk_size": "128g",
        "cpu_cores": 6,
        "ram_size": "",
        "extra_env": "FOO=bar",
        "desktop_width": 2560,
    })
    assert session.disk_size == "128G"
    assert session.cpu_cores == 6
    assert session.ram_size is None
    assert session.extra_env == {"FOO": "bar"}
    assert session.desktop_width == 2560

    # Invalid updates must not leave a half-applied record.
    with pytest.raises(ValueError):
        session.apply_advanced_settings({"disk_size": "huge", "cpu_cores": 2})
    assert session.disk_size == "128G"
    assert session.cpu_cores == 6
