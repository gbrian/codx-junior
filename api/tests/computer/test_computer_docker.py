"""Tests for desktop/VM docker commands and folder mapping."""

import os

import pytest

from codx.junior.browser.docker_browser_manager import DockerBrowserManager
from codx.junior.browser.model import BrowserSession


def _manager(tmp_path, monkeypatch):
    manager = DockerBrowserManager(
        str(tmp_path),
        traefik_domain="example.test",
        project_id="project-1",
        project_root_path=str(tmp_path / "project"),
        project_name="My Project",
    )
    (tmp_path / "project").mkdir(exist_ok=True)
    monkeypatch.setattr(manager, "_ensure_image", lambda image=None: None)
    monkeypatch.setattr(manager, "_prepare_computer_agent", lambda sid: "/tmp/agent.py")
    return manager


def test_linux_run_command_uses_webtop_and_mounts_the_agent(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    session = BrowserSession(name="Linux", kind="linux")
    session.id = "12345678-aaaa-bbbb-cccc-ddddeeeeffff"
    manager.configure_share(session, share_project=True)
    cmd = manager._build_linux_run_command(
        session,
        "computer_12345678",
        str(tmp_path / "profile"),
        f"/computer/{session.id}/",
        "codx-computer-12345678",
    )
    joined = " ".join(cmd)

    assert manager.image_for(session) == "lscr.io/linuxserver/webtop:debian-kde"
    assert "computer_12345678" in cmd
    assert f"SUBFOLDER=/computer/{session.id}/" in cmd
    assert "/tmp/agent.py:/codx/computer_agent.py:ro" in cmd
    assert "SELKIES_MANUAL_WIDTH=1920" in joined
    assert "traefik.http.routers.codx-computer-12345678.rule=" in joined
    assert f"PathPrefix(`/computer/{session.id}/`)" in joined
    assert "3000" in joined
    assert manager.linux_image in cmd


def test_vm_run_command_has_kvm_vnc_and_single_shared_folder(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    session = BrowserSession(name="Windows", kind="windows", os_version="10")
    session.id = "22345678-aaaa-bbbb-cccc-ddddeeeeffff"
    manager.configure_share(session, share_project=True)
    cmd = manager._build_vm_run_command(session, "computer_22345678", str(tmp_path / "vm"))
    joined = " ".join(cmd)

    assert manager.image_for(session) == "dockurr/windows"
    assert "/dev/kvm" in cmd and "/dev/net/tun" in cmd
    assert "NET_ADMIN" in joined
    assert "VERSION=10" in joined
    assert f"127.0.0.1::{manager.vm_vnc_port}" in joined
    assert "-v" in cmd and "/shared" in joined
    assert session.guest_share_path.startswith("Z:\\")
    # One host folder is shared with the guest, not the multi-folder browser tree.
    assert any(arg.endswith(":/shared") for arg in cmd)
    assert "traefik.enable=true" not in joined


def test_vm_advanced_resources_override_host_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("CODX_COMPUTER_VM_RAM", "16G")
    monkeypatch.setenv("CODX_COMPUTER_VM_CPUS", "2")
    monkeypatch.setenv("CODX_COMPUTER_VM_DISK", "32G")
    manager = _manager(tmp_path, monkeypatch)
    session = BrowserSession(
        name="Windows",
        kind="windows",
        cpu_cores=8,
        ram_size="12G",
        disk_size="128G",
        extra_env={"FOO": "bar", "RAM_SIZE": "1G"},
    )
    manager.configure_share(session, share_project=False)
    cmd = manager._build_vm_run_command(session, "computer_abc", str(tmp_path / "vm"))
    joined = " ".join(cmd)

    assert "RAM_SIZE=12G" in joined
    assert "CPU_CORES=8" in joined
    assert "DISK_SIZE=128G" in joined
    assert "FOO=bar" in joined
    # Manager-owned variables cannot be overridden from the advanced settings.
    assert "RAM_SIZE=1G" not in joined


def test_linux_advanced_resources_and_extra_env(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    session = BrowserSession(
        name="Linux",
        kind="linux",
        cpu_cores=2,
        ram_size="4G",
        shm_size="3G",
        extra_env={"LC_ALL": "C.UTF-8", "SUBFOLDER": "/evil"},
    )
    session.id = "12345678-aaaa-bbbb-cccc-ddddeeeeffff"
    manager.configure_share(session, share_project=False)
    cmd = manager._build_linux_run_command(
        session,
        "computer_12345678",
        str(tmp_path / "profile"),
        f"/computer/{session.id}/",
        "codx-computer-12345678",
    )
    joined = " ".join(cmd)

    assert "--cpus 2" in joined
    assert "--memory 4G" in joined
    assert "--shm-size 3G" in joined
    assert "LC_ALL=C.UTF-8" in joined
    assert "SUBFOLDER=/evil" not in joined


def test_browser_advanced_window_size(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    proxy = tmp_path / "cdp_proxy.py"
    proxy.write_text("# proxy", encoding="utf-8")
    monkeypatch.setattr(manager, "_prepare_cdp_proxy", lambda sid: str(proxy))
    session = BrowserSession(
        name="Browser",
        desktop_width=1366,
        desktop_height=768,
        cpu_cores=1,
        shm_size="1G",
    )
    manager.configure_share(session, share_project=False)
    cmd = manager._build_browser_run_command(
        session,
        "browser_12345678",
        str(tmp_path / "profile"),
        f"/browser/{session.id}/",
        "codx-browser-12345678",
    )
    joined = " ".join(cmd)

    assert "--window-size=1366,768" in joined
    assert "--cpus 1" in joined
    assert "--shm-size 1G" in joined


def test_macos_vm_uses_macos_image_and_default_version(tmp_path, monkeypatch):
    monkeypatch.delenv("CODX_COMPUTER_VM_DISK", raising=False)
    monkeypatch.delenv("CODX_COMPUTER_MACOS_DISK", raising=False)
    manager = _manager(tmp_path, monkeypatch)
    session = BrowserSession(name="Mac", kind="macos")
    manager.configure_share(session, share_project=False)
    cmd = manager._build_vm_run_command(session, "computer_abc", str(tmp_path / "vm"))
    joined = " ".join(cmd)
    assert manager.image_for(session) == "dockurr/macos"
    assert "VERSION=15" in joined
    # macOS gets a larger default disk than Windows for Xcode/Simulator.
    assert "DISK_SIZE=128G" in joined
    assert "USERNAME=" not in joined


def test_browser_command_is_unchanged(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    proxy = tmp_path / "cdp_proxy.py"
    proxy.write_text("# proxy", encoding="utf-8")
    monkeypatch.setattr(manager, "_prepare_cdp_proxy", lambda sid: str(proxy))
    session = BrowserSession(name="Browser", current_url="https://example.com")
    session.id = "32345678-aaaa-bbbb-cccc-ddddeeeeffff"
    cmd = manager._build_run_command(
        session,
        "browser_12345678",
        str(tmp_path / "profile"),
        f"/browser/{session.id}/",
        "codx-browser-12345678",
    )
    joined = " ".join(cmd)
    assert manager.image in cmd
    assert "CHROME_CLI=--remote-debugging-port=9222" in joined
    assert "python3 /cdp_proxy.py" in joined
    assert "-p" not in cmd


def test_path_prefix_is_kind_aware(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    assert manager._path_prefix("abc", "browser") == "/browser/abc/"
    assert manager._path_prefix("abc", "linux") == "/computer/abc/"


def test_vm_without_project_does_not_mount_shared_twice(tmp_path, monkeypatch):
    manager = _manager(tmp_path, monkeypatch)
    session = BrowserSession(name="Isolated", kind="windows")
    session.id = "42345678-aaaa-bbbb-cccc-ddddeeeeffff"
    manager.configure_share(session, share_project=False)
    mounts = manager._build_share_mounts(session)
    assert len(mounts) == 1
    assert mounts[0].endswith(":/shared")
