"""
Tests for the admin-only interactive container shell.

The suite is split in two layers:

* :mod:`codx.junior.infra.shell` units — ticket rules, shell validation, CLI
  argv construction, PTY streaming and the running-container guard.
* The FastAPI router — the admin-only ticket endpoint and the WebSocket ticket
  consumption / frame relay.

The router tests stub ``codx.junior.api`` (its real package initializer pulls
the whole engine and optional knowledge dependencies) and replace the Docker
manager with a small fake, so no Docker daemon is required.
"""

import base64
import importlib
import pathlib
import queue
import sys
import types
from dataclasses import replace
from types import SimpleNamespace

import pytest

from codx.junior.infra import shell
from codx.junior.infra.docker_client import DockerAPIError


# ── Shell module: validation / command construction ──────────────────────────


def test_normalize_shell_accepts_allow_listed_values():
    assert shell.normalize_shell(None) == shell.DEFAULT_SHELL
    assert shell.normalize_shell("  /bin/bash  ") == "/bin/bash"
    assert shell.normalize_shell("sh") == "sh"


@pytest.mark.parametrize(
    "value",
    ["sh -c whoami", "/bin/sh; id", "../bin/sh", "/usr/bin/python", "bash\t-c id"],
)
def test_normalize_shell_rejects_arbitrary_commands(value):
    with pytest.raises(shell.ShellValidationError):
        shell.normalize_shell(value)


def test_clamp_size_bounds_and_defaults():
    assert shell.clamp_size(120, 32) == (120, 32)
    assert shell.clamp_size(1, 1) == (shell.MIN_COLS, shell.MIN_ROWS)
    assert shell.clamp_size(9999, 9999) == (shell.MAX_COLS, shell.MAX_ROWS)
    assert shell.clamp_size("bad", None) == (120, 32)


def test_build_exec_command_local_default_socket():
    argv, env = shell.build_exec_command(
        "my-container", "/bin/bash", docker_bin="/usr/bin/docker"
    )
    assert argv[0] == "/usr/bin/docker"
    assert "-H" not in argv
    assert argv[1:6] == ["exec", "-i", "-t", "-e", "TERM=xterm-256color"]
    assert argv[-2:] == ["my-container", "/bin/bash"]
    assert env["TERM"] == "xterm-256color"


def test_build_exec_command_remote_host_gets_dash_h():
    argv, env = shell.build_exec_command(
        "db",
        "/bin/sh",
        endpoint="tcp://10.0.0.21:2376",
        docker_bin="/usr/bin/docker",
        is_local=False,
    )
    assert argv[1:3] == ["-H", "tcp://10.0.0.21:2376"]
    assert env["TERM"] == "xterm-256color"


def test_build_exec_command_https_enables_tls_and_maps_to_tcp():
    argv, env = shell.build_exec_command(
        "db",
        "/bin/sh",
        endpoint="https://docker.example:2376",
        docker_bin="/usr/bin/docker",
        is_local=False,
    )
    assert "tcp://docker.example:2376" in argv
    assert env["DOCKER_TLS_VERIFY"] == "1"


def test_build_exec_command_rejects_unknown_scheme():
    with pytest.raises(shell.ShellValidationError):
        shell.build_exec_command(
            "db", "/bin/sh", endpoint="ftp://example", docker_bin="/usr/bin/docker"
        )


def test_build_exec_command_requires_container_id():
    with pytest.raises(shell.ShellValidationError):
        shell.build_exec_command("   ", "/bin/sh", docker_bin="/usr/bin/docker")


# ── Ticket store ──────────────────────────────────────────────────────────────

ADMIN = SimpleNamespace(username="root", role="admin")
USER = SimpleNamespace(username="alice", role="user")


def test_ticket_store_requires_admin():
    store = shell.ShellTicketStore()
    with pytest.raises(shell.ShellAccessDeniedError):
        store.issue(USER, "abc", "host-local", "/bin/sh")
    with pytest.raises(shell.ShellAccessDeniedError):
        store.issue(None, "abc", "host-local", "/bin/sh")


def test_ticket_is_single_use_and_bound_to_its_request():
    store = shell.ShellTicketStore()
    ticket = store.issue(ADMIN, "abc123", "host-local", "/bin/bash")
    assert ticket.role == "admin"
    assert ticket.container_id == "abc123"
    assert ticket.shell == "/bin/bash"

    consumed = store.consume(ticket.value)
    assert consumed is not None
    assert consumed.username == "root"

    # A ticket is popped on the first consume, so a leaked URL cannot replay it.
    assert store.consume(ticket.value) is None
    assert store.consume("does-not-exist") is None


def test_ticket_expiry_is_enforced():
    store = shell.ShellTicketStore()
    ticket = store.issue(ADMIN, "abc", "host-local", "/bin/sh")
    store._tickets[ticket.value] = replace(ticket, expires_at=0)
    assert store.consume(ticket.value) is None


def test_ticket_cap_drops_oldest_instead_of_growing():
    store = shell.ShellTicketStore(max_tickets=2)
    first = store.issue(ADMIN, "one", "host-local", "/bin/sh")
    second = store.issue(ADMIN, "two", "host-local", "/bin/sh")
    third = store.issue(ADMIN, "three", "host-local", "/bin/sh")
    assert store.consume(first.value) is None
    assert store.consume(second.value) is not None
    assert store.consume(third.value) is not None


# ── Running-container guard ──────────────────────────────────────────────────


class FakeDockerClient:
    def __init__(self, detail=None, error=None):
        self.detail = detail or {}
        self.error = error

    def get_json(self, path, params=None):
        if self.error:
            raise self.error
        return self.detail


class FakeManager:
    def __init__(self, detail=None, error=None):
        self.client_obj = FakeDockerClient(detail=detail, error=error)

    def client(self, host_id=None):
        return self.client_obj

    def host_config(self, host_id=None):
        return SimpleNamespace(
            id=host_id or "host-local",
            endpoint="unix:///var/run/docker.sock",
            is_local=True,
        )


def test_ensure_running_returns_canonical_id():
    manager = FakeManager({"Id": "deadbeef", "State": {"Running": True, "Paused": False}})
    assert shell.ensure_running(manager, "my-container", "host-local") == "deadbeef"


@pytest.mark.parametrize(
    "state",
    [
        {"Running": False, "Status": "exited"},
        {"Running": True, "Paused": True, "Status": "paused"},
    ],
)
def test_ensure_running_rejects_stopped_or_paused(state):
    manager = FakeManager({"Id": "abc", "State": state})
    with pytest.raises(shell.ShellConflictError):
        shell.ensure_running(manager, "abc", "host-local")


def test_ensure_running_maps_404_to_validation_error():
    manager = FakeManager(error=DockerAPIError(404, "no such container", "/containers/x/json"))
    with pytest.raises(shell.ShellValidationError):
        shell.ensure_running(manager, "x", "host-local")


# ── PTY session ──────────────────────────────────────────────────────────────


def test_pty_session_streams_output_and_exit_code():
    session = shell.ContainerShellSession(
        argv=["/bin/sh", "-c", "printf hello; exit 3"]
    ).start()
    try:
        output = b""
        while True:
            kind, payload = session.events.get(timeout=5)
            if kind == "output":
                output += payload
            elif kind == "exit":
                assert payload == 3
                break
        assert b"hello" in output
    finally:
        session.close()


def test_pty_session_resize_and_input():
    session = shell.ContainerShellSession(argv=["/bin/sh"], cols=80, rows=24).start()
    try:
        assert session.resize(120, 40) is True
        assert (session.cols, session.rows) == (120, 40)
        assert session.write(b"printf 'INPUT_OK\\n'; exit 0\n") is True
        output = b""
        while True:
            kind, payload = session.events.get(timeout=5)
            if kind == "output":
                output += payload
            elif kind == "exit":
                break
        assert b"INPUT_OK" in output
    finally:
        session.close()


# ── Frame helpers ────────────────────────────────────────────────────────────


def test_decode_input_and_encode_output_round_trip():
    raw = "hello\nworld".encode()
    encoded = shell.encode_output(raw)
    assert isinstance(encoded, str)
    assert shell.decode_input({"data": encoded}) == raw


def test_decode_input_rejects_invalid_base64_and_oversized_frames():
    with pytest.raises(shell.ShellValidationError):
        shell.decode_input({"data": "not base64!"})
    with pytest.raises(shell.ShellValidationError):
        shell.decode_input({"data": base64.b64encode(b"x" * (shell.MAX_INPUT_BYTES + 1)).decode()})


# ── Router: admin-only ticket + WebSocket ────────────────────────────────────


def _require_admin_stub():
    """Dependency replacement used while importing the router in isolation."""
    return ADMIN


def _import_infra_router():
    """Import ``api.infra`` without executing the heavy ``api`` package init."""
    package = sys.modules.get("codx.junior.api")
    if package is None:
        package = types.ModuleType("codx.junior.api")
        package.__path__ = [
            str(pathlib.Path(__file__).resolve().parents[1] / "codx" / "junior" / "api")
        ]
        sys.modules["codx.junior.api"] = package
    if not hasattr(package, "require_admin"):
        package.require_admin = _require_admin_stub
    sys.modules.pop("codx.junior.api.infra", None)
    return importlib.import_module("codx.junior.api.infra")


@pytest.fixture()
def router_app(monkeypatch):
    """FastAPI app with the infra router and a fake Docker manager."""
    from fastapi import FastAPI, HTTPException

    infra_api = _import_infra_router()

    manager = FakeManager(
        {"Id": "abc123", "State": {"Running": True, "Paused": False}}
    )
    monkeypatch.setattr(infra_api, "get_infra_manager", lambda: manager)
    monkeypatch.setattr(
        infra_api,
        "shell_tickets",
        shell.ShellTicketStore(),
    )
    # Keep the global registry clean between tests.
    shell.shell_sessions.close_all()

    app = FastAPI()
    app.include_router(infra_api.router, prefix="/api")

    def deny():
        raise HTTPException(status_code=403, detail="Admins only")

    app.dependency_overrides[infra_api.require_admin] = _require_admin_stub
    return SimpleNamespace(app=app, api=infra_api, manager=manager, deny=deny)


def _client(router_app):
    from fastapi.testclient import TestClient

    return TestClient(router_app.app)


def test_ticket_endpoint_returns_single_use_websocket_path(router_app):
    client = _client(router_app)
    response = client.post(
        "/api/infra/containers/abc123/shell",
        json={"shell": "/bin/bash", "host_id": "host-local", "cols": 120, "rows": 32},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["container_id"] == "abc123"
    assert body["host_id"] == "host-local"
    assert body["shell"] == "/bin/bash"
    assert body["expires_in"] == shell.shell_tickets.ttl
    assert body["websocket_path"].startswith("/api/infra/containers/abc123/shell?ticket=")

    ticket = body["ticket"]
    assert router_app.api.shell_tickets.consume(ticket) is not None


def test_ticket_endpoint_rejects_non_admin(router_app):
    from fastapi import HTTPException

    def deny():
        raise HTTPException(status_code=403, detail="Admins only")

    router_app.app.dependency_overrides[router_app.api.require_admin] = deny
    client = _client(router_app)
    response = client.post(
        "/api/infra/containers/abc123/shell",
        json={"shell": "/bin/sh", "host_id": "host-local"},
    )
    assert response.status_code == 403


def test_ticket_endpoint_rejects_stopped_container(router_app):
    router_app.manager.client_obj.detail = {
        "Id": "abc123",
        "State": {"Running": False, "Status": "exited"},
    }
    client = _client(router_app)
    response = client.post(
        "/api/infra/containers/abc123/shell",
        json={"shell": "/bin/sh", "host_id": "host-local"},
    )
    assert response.status_code == 409


def test_ticket_endpoint_rejects_unlisted_shell(router_app):
    client = _client(router_app)
    response = client.post(
        "/api/infra/containers/abc123/shell",
        json={"shell": "/usr/bin/python", "host_id": "host-local"},
    )
    assert response.status_code == 400


def test_websocket_rejects_invalid_ticket(router_app):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    client = TestClient(router_app.app)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/infra/containers/abc123/shell?ticket=nope") as ws:
            ws.receive_json()


class FakeShellSession:
    """Minimal session surface used by the WebSocket relay."""

    def __init__(self):
        self.events = queue.Queue()
        self.cols = 120
        self.rows = 32
        self.writes = []
        self.resizes = []
        self.closed = False
        self.events.put(("output", b"hello from container\n"))

    def write(self, data):
        self.writes.append(data)
        return True

    def resize(self, cols, rows):
        self.resizes.append((cols, rows))
        return True

    def close(self):
        self.closed = True


def test_websocket_relays_frames_for_valid_admin_ticket(router_app, monkeypatch):
    from fastapi.testclient import TestClient

    fake = FakeShellSession()
    monkeypatch.setattr(
        router_app.api, "create_container_shell", lambda *args, **kwargs: fake
    )

    ticket = router_app.api.shell_tickets.issue(
        ADMIN, "abc123", "host-local", "/bin/sh"
    )
    client = TestClient(router_app.app)
    with client.websocket_connect(
        f"/api/infra/containers/abc123/shell?ticket={ticket.value}"
    ) as ws:
        ready = ws.receive_json()
        assert ready["type"] == "ready"
        assert ready["container_id"] == "abc123"
        assert ready["shell"] == "/bin/sh"

        output = ws.receive_json()
        assert output["type"] == "output"
        assert base64.b64decode(output["data"]) == b"hello from container\n"

        ws.send_json({"type": "input", "data": base64.b64encode(b"ls\n").decode()})
        ws.send_json({"type": "resize", "cols": 100, "rows": 40})
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"

        # The session exits only now, so the assertions above are ordered.
        fake.events.put(("exit", 0))
        exit_frame = ws.receive_json()
        assert exit_frame == {"type": "exit", "code": 0}

    assert fake.writes == [b"ls\n"]
    assert fake.resizes == [(100, 40)]
    assert fake.closed is True


# Made with ❤️ by codx-junior
