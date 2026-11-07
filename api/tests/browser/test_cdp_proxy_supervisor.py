"""Tests for the in-container Chromium supervisor and the stable browser id.

The supervisor is the piece that puts the browser back when the user closes every
tab (Chromium exits, the container keeps running).  Everything is exercised with
injected probes/openers/restarters, so no container, no Chromium and no s6 are
needed.
"""

import asyncio

import pytest

from codx.junior.browser import cdp_proxy


def _clock(start=1000.0):
    """Build a controllable monotonic clock and its handle."""
    now = [start]

    def clock():
        return now[0]

    def advance(seconds):
        now[0] += seconds

    return clock, advance


# ---------------------------------------------------------------------------
# Stable browser id
# ---------------------------------------------------------------------------

def test_rewrite_request_line_points_to_the_running_browser():
    assert cdp_proxy.rewrite_request_line(
        "GET /devtools/browser/stale-id HTTP/1.1", "/devtools/browser/fresh-id"
    ) == "GET /devtools/browser/fresh-id HTTP/1.1"


def test_rewrite_request_line_keeps_other_requests_untouched():
    original = "GET /json/version HTTP/1.1"
    assert cdp_proxy.rewrite_request_line(original, "/devtools/browser/fresh-id") == original
    # No resolved path (browser not reachable): never break the handshake
    assert cdp_proxy.rewrite_request_line(
        "GET /devtools/browser/stale HTTP/1.1", None
    ) == "GET /devtools/browser/stale HTTP/1.1"


def test_rewrite_headers_rewrites_host_and_browser_id():
    raw = b"GET /devtools/browser/stale HTTP/1.1\r\nHost: browser_abc:9223\r\nUpgrade: websocket\r\n\r\n"

    rewritten = cdp_proxy._rewrite_headers(raw, "/devtools/browser/fresh").decode("latin-1")

    assert rewritten.startswith("GET /devtools/browser/fresh HTTP/1.1\r\n")
    assert f"Host: {cdp_proxy.REWRITE_HOST}" in rewritten
    assert "browser_abc" not in rewritten
    assert "Upgrade: websocket" in rewritten


def test_current_browser_path_is_cached_and_invalidated(monkeypatch):
    calls = []

    def fake_http_json(url, **kwargs):
        calls.append(url)
        return {"webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/abc-123"}

    monkeypatch.setattr(cdp_proxy, "_http_json", fake_http_json)
    cdp_proxy.invalidate_browser_path()

    assert cdp_proxy.current_browser_path() == "/devtools/browser/abc-123"
    assert cdp_proxy.current_browser_path() == "/devtools/browser/abc-123"
    # Cached: the browser is asked once
    assert len(calls) == 1

    cdp_proxy.invalidate_browser_path()
    assert cdp_proxy.current_browser_path() == "/devtools/browser/abc-123"
    assert len(calls) == 2


def test_current_browser_path_returns_none_when_the_browser_is_down(monkeypatch):
    def failing(url, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(cdp_proxy, "_http_json", failing)
    cdp_proxy.invalidate_browser_path()

    assert cdp_proxy.current_browser_path() is None


# ---------------------------------------------------------------------------
# DevTools probes
# ---------------------------------------------------------------------------

def test_devtools_status_counts_only_page_targets(monkeypatch):
    def fake_http_json(url, **kwargs):
        if url.endswith("/json/version"):
            return {"Browser": "Chrome/120"}
        return [
            {"type": "page", "url": "https://a.test"},
            {"type": "page", "url": "about:blank"},
            {"type": "service_worker", "url": "https://a.test/sw.js"},
            {"type": "page", "url": "https://closed.test", "closed": True},
        ]

    monkeypatch.setattr(cdp_proxy, "_http_json", fake_http_json)

    status = cdp_proxy.devtools_status()

    assert status["alive"] is True
    assert status["pages"] == 2


def test_devtools_status_reports_a_dead_endpoint(monkeypatch):
    def failing(url, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(cdp_proxy, "_http_json", failing)

    status = cdp_proxy.devtools_status()

    assert status["alive"] is False
    assert status["pages"] == 0
    assert "refused" in status["error"]


def test_devtools_status_keeps_the_browser_alive_when_the_list_fails(monkeypatch):
    def fake_http_json(url, **kwargs):
        if url.endswith("/json/version"):
            return {"Browser": "Chrome/120"}
        raise OSError("still starting")

    monkeypatch.setattr(cdp_proxy, "_http_json", fake_http_json)

    status = cdp_proxy.devtools_status()

    assert status["alive"] is True
    assert status["pages"] == 0


def test_open_tab_falls_back_to_get_when_put_is_rejected(monkeypatch):
    attempts = []

    def fake_http_json(url, method="GET", **kwargs):
        attempts.append(method)
        if method == "PUT":
            raise OSError("405 method not allowed")
        return {"id": "tab-1"}

    monkeypatch.setattr(cdp_proxy, "_http_json", fake_http_json)

    assert cdp_proxy.open_tab() is True
    assert attempts == ["PUT", "GET"]


# ---------------------------------------------------------------------------
# s6 service restart
# ---------------------------------------------------------------------------

def test_chromium_service_dirs_are_discovered(tmp_path):
    root = tmp_path / "service"
    (root / "svc-chromium").mkdir(parents=True)
    (root / "svc-selkies").mkdir()
    (root / "svc-openbox").mkdir()

    assert cdp_proxy.chromium_service_dirs((str(root),)) == [str(root / "svc-chromium")]


def test_chromium_service_dirs_ignores_missing_roots(tmp_path):
    assert cdp_proxy.chromium_service_dirs((str(tmp_path / "missing"),)) == []


def test_restart_chromium_service_signals_restart_and_up():
    calls = []

    def runner(flag, service_dir):
        calls.append((flag, service_dir))
        return True

    assert cdp_proxy.restart_chromium_service(dirs=["/run/service/svc-chromium"], runner=runner) is True
    # Both are sent: -r restarts a running browser, -u brings back an exited one
    assert calls == [
        ("-r", "/run/service/svc-chromium"),
        ("-u", "/run/service/svc-chromium"),
    ]


def test_restart_chromium_service_without_a_service_reports_failure():
    assert cdp_proxy.restart_chromium_service(dirs=[], runner=lambda flag, path: True) is False


def test_run_s6_command_tries_the_command_folder(monkeypatch):
    attempts = []

    class _Result:
        returncode = 0
        stderr = ""

    def fake_run(args, **kwargs):
        attempts.append(args[0])
        if args[0] == "s6-svc":
            raise FileNotFoundError(args[0])
        return _Result()

    monkeypatch.setattr(cdp_proxy.subprocess, "run", fake_run)

    assert cdp_proxy._run_s6_command("-r", "/run/service/svc-chromium") is True
    assert attempts == ["s6-svc", "/command/s6-svc"]


# ---------------------------------------------------------------------------
# Supervisor state machine
# ---------------------------------------------------------------------------

def test_supervisor_is_quiet_while_the_browser_has_tabs():
    supervisor = cdp_proxy.ChromiumSupervisor(
        grace=0,
        probe=lambda: {"alive": True, "pages": 2},
        opener=lambda: pytest.fail("must not open tabs"),
        restarter=lambda: pytest.fail("must not restart"),
    )

    assert supervisor.check()["action"] == "ok"


def test_supervisor_opens_a_tab_when_every_tab_was_closed():
    opened = []
    supervisor = cdp_proxy.ChromiumSupervisor(
        grace=0,
        probe=lambda: {"alive": True, "pages": 0},
        opener=lambda: opened.append(True) or True,
        restarter=lambda: pytest.fail("must not restart the browser"),
    )

    result = supervisor.check()

    assert result["action"] == "opened"
    assert opened == [True]
    assert supervisor.opened_tabs == 1


def test_supervisor_waits_for_the_threshold_before_restarting():
    restarts = []
    supervisor = cdp_proxy.ChromiumSupervisor(
        grace=0,
        dead_threshold=3,
        probe=lambda: {"alive": False, "pages": 0, "error": "connection refused"},
        opener=lambda: pytest.fail("must not open tabs"),
        restarter=lambda: restarts.append(True) or True,
    )

    assert supervisor.check()["action"] == "unreachable"
    assert supervisor.check()["action"] == "unreachable"
    assert restarts == []
    assert supervisor.check()["action"] == "restarted"
    assert restarts == [True]
    assert supervisor.restarts == 1


def test_supervisor_respects_the_restart_cooldown():
    clock, advance = _clock()
    restarts = []
    supervisor = cdp_proxy.ChromiumSupervisor(
        grace=0,
        dead_threshold=1,
        cooldown=15,
        clock=clock,
        probe=lambda: {"alive": False, "pages": 0},
        opener=lambda: pytest.fail("must not open tabs"),
        restarter=lambda: restarts.append(True) or True,
    )

    assert supervisor.check()["action"] == "restarted"
    advance(1)
    assert supervisor.check()["action"] == "restart_cooldown"
    assert len(restarts) == 1

    advance(20)
    assert supervisor.check()["action"] == "restarted"
    assert len(restarts) == 2


def test_supervisor_bounces_the_service_when_new_tabs_keep_failing():
    restarts = []
    supervisor = cdp_proxy.ChromiumSupervisor(
        grace=0,
        dead_threshold=3,
        probe=lambda: {"alive": True, "pages": 0},
        opener=lambda: False,
        restarter=lambda: restarts.append(True) or True,
    )

    assert supervisor.check()["action"] == "open_failed"
    assert supervisor.check()["action"] == "restarted"
    assert restarts == [True]


def test_supervisor_gives_chromium_time_to_start():
    clock, advance = _clock()
    supervisor = cdp_proxy.ChromiumSupervisor(
        grace=30,
        clock=clock,
        dead_threshold=1,
        probe=lambda: pytest.fail("must not probe during the grace period"),
        opener=lambda: pytest.fail("must not open tabs"),
        restarter=lambda: pytest.fail("must not restart"),
    )

    assert supervisor.check()["action"] == "grace"

    advance(31)
    assert supervisor.check()["action"] in ("ok", "restarted", "unreachable", "opened")


def test_supervisor_reports_when_the_browser_cannot_be_relaunched():
    supervisor = cdp_proxy.ChromiumSupervisor(
        grace=0,
        dead_threshold=1,
        probe=lambda: {"alive": False, "pages": 0},
        restarter=lambda: False,
    )

    assert supervisor.check()["action"] == "restart_failed"
    assert supervisor.restarts == 0


def test_supervisor_survives_a_failing_probe():
    def failing_probe():
        raise OSError("boom")

    supervisor = cdp_proxy.ChromiumSupervisor(grace=0, probe=failing_probe)

    with pytest.raises(OSError):
        supervisor.check()


def test_supervisor_run_exits_when_stopped():
    event = asyncio.Event()
    supervisor = cdp_proxy.ChromiumSupervisor(
        interval=0.01,
        grace=0,
        probe=lambda: {"alive": True, "pages": 1},
    )

    async def scenario():
        task = asyncio.ensure_future(supervisor.run(event))
        await asyncio.sleep(0.03)
        event.set()
        await asyncio.wait_for(task, timeout=2)

    asyncio.run(scenario())