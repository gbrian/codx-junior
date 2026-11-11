"""
Tests for the harness watchdog (``codx/junior/harness/watchdog.py``).

Only the restart-lease, restart-selection and stall-detection logic is tested
offline: no supervisor or Docker daemon is contacted, and the project discovery
is faked.

Run with::

    cd api && pytest tests/harness/test_harness_watchdog.py -q
"""

import json
import os
import time
from types import SimpleNamespace

import pytest

from codx.junior.harness import watchdog
from codx.junior.harness.watchdog import HarnessWatchdog


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeWorkerStatus:
    def __init__(self, present=True, age=None):
        self._present = present
        self._age = age

    def worker_status(self, ttl_seconds=None):
        if self._present:
            return {"present": True, "pid": 1, "updated_at": "now", "age_seconds": self._age or 1.0}
        return {"present": False, "pid": None, "updated_at": None, "age_seconds": self._age}


class FakeStore(FakeWorkerStatus):
    def __init__(self, active_run_ids, present=True, age=None):
        super().__init__(present=present, age=age)
        self._active = list(active_run_ids)

    def active_run_ids(self):
        return list(self._active)


class FakeSettings:
    def __init__(self, codx_path, project_name="p"):
        self.codx_path = str(codx_path)
        self.project_name = project_name


# ---------------------------------------------------------------------------
# Restart lease
# ---------------------------------------------------------------------------


def test_lease_granted_once_then_cooldown(tmp_path):
    wd = HarnessWatchdog(check_seconds=60, stale_seconds=60, restart_cooldown_seconds=30)
    assert wd._acquire_restart_lease(str(tmp_path)) is True
    assert wd._acquire_restart_lease(str(tmp_path)) is False  # cooling down
    state_path = os.path.join(tmp_path, "harness", "watchdog.json")
    state = json.load(open(state_path, encoding="utf-8"))
    # Simulate the cooldown passing (it is floored at 30 s).
    state["last_restart_attempt"] = time.time() - 60
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)
    assert wd._acquire_restart_lease(str(tmp_path)) is True


# ---------------------------------------------------------------------------
# Restart mechanism selection
# ---------------------------------------------------------------------------


def test_restart_prefers_supervisorctl(tmp_path, monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        result = SimpleNamespace(returncode=0, stdout="ok", stderr="")
        return result

    monkeypatch.setattr(watchdog.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(watchdog.os, "environ", {"CODX_JUNIOR_PATH": str(tmp_path)})
    supervisor_conf = tmp_path / "supervisor.conf"
    supervisor_conf.write_text("")
    monkeypatch.setattr(watchdog.subprocess, "run", fake_run)

    wd = HarnessWatchdog()
    method, detail = wd._restart_background("p", str(tmp_path))
    assert method == "supervisorctl"
    assert "supervisorctl" in calls[0][0]


def test_restart_falls_back_to_docker(tmp_path, monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(watchdog.shutil, "which", lambda name: "/usr/bin/docker")
    # No supervisor.conf anywhere: CODX_JUNIOR_PATH points at an empty dir so
    # the relative/absolute conf lookup fails and docker is used.
    monkeypatch.setattr(watchdog.os, "environ", {"CODX_JUNIOR_PATH": "/nonexistent-codx-path"})
    monkeypatch.setattr(watchdog.subprocess, "run", fake_run)

    wd = HarnessWatchdog()
    method, _ = wd._restart_background("p", str(tmp_path))
    assert method == "docker"
    assert calls[0] == ["/usr/bin/docker", "restart", "codx-junior-api-background"]


def test_restart_without_mechanism_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog.shutil, "which", lambda name: None)
    monkeypatch.setattr(watchdog.os, "environ", {})
    wd = HarnessWatchdog()
    with pytest.raises(RuntimeError):
        wd._restart_background("p", str(tmp_path))


# ---------------------------------------------------------------------------
# Stall detection
# ---------------------------------------------------------------------------


def _patch_store(monkeypatch, store):
    monkeypatch.setattr(
        "codx.junior.orchestration.store.RunStore",
        lambda codx_path: store,
        raising=False,
    )


def test_check_project_healthy_worker_no_incident(tmp_path, monkeypatch):
    store = FakeStore(active_run_ids=["r1"], present=True, age=5.0)
    _patch_store(monkeypatch, store)
    wd = HarnessWatchdog(stale_seconds=60)
    (tmp_path / "orchestration").mkdir(parents=True)
    incident = wd._check_project(FakeSettings(tmp_path))
    assert incident is None


def test_check_project_stalled_worker_produces_incident(tmp_path, monkeypatch):
    store = FakeStore(active_run_ids=["r1"], present=False, age=300.0)
    _patch_store(monkeypatch, store)
    monkeypatch.setattr(watchdog, "auto_restart_enabled", lambda: False)
    wd = HarnessWatchdog(stale_seconds=60)
    (tmp_path / "orchestration").mkdir(parents=True)
    incident = wd._check_project(FakeSettings(tmp_path))
    assert incident is not None
    assert incident["active_runs"] == ["r1"]
    # The incident must be registered in the audit journal.
    journal = tmp_path / "harness" / "audit.jsonl"
    assert journal.is_file()
    entries = [json.loads(line) for line in journal.read_text().splitlines()]
    assert entries[0]["event"] == "worker_stalled"
    # ...but not re-reported on every cycle while the stall persists.
    wd._check_project(FakeSettings(tmp_path))
    entries = [json.loads(line) for line in journal.read_text().splitlines()]
    stalled = [entry for entry in entries if entry["event"] == "worker_stalled"]
    assert len(stalled) == 1


def test_check_project_no_runs_means_no_incident(tmp_path, monkeypatch):
    store = FakeStore(active_run_ids=[], present=False, age=300.0)
    _patch_store(monkeypatch, store)
    wd = HarnessWatchdog(stale_seconds=60)
    (tmp_path / "orchestration").mkdir(parents=True)
    assert wd._check_project(FakeSettings(tmp_path)) is None


def test_check_project_without_orchestration_dir_skipped(tmp_path, monkeypatch):
    wd = HarnessWatchdog(stale_seconds=60)
    assert wd._check_project(FakeSettings(tmp_path)) is None


def test_watchdog_disabled_by_environment(monkeypatch):
    monkeypatch.setattr(watchdog.os, "environ", {watchdog.ENV_WATCHDOG: "0"})
    assert watchdog.watchdog_enabled() is False
    monkeypatch.setattr(watchdog.os, "environ", {watchdog.ENV_WATCHDOG: "1"})
    assert watchdog.watchdog_enabled() is True
    monkeypatch.setattr(watchdog.os, "environ", {})
    assert watchdog.watchdog_enabled() is True  # on by default
