"""Tests for the outbound DSH agent channel and its API."""

import json
import os
import threading
import time
import uuid

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from codx.junior.chat_manager import ChatManager
from codx.junior.integrations.dsh import DshConfig, DshSync, DshTask
from codx.junior.integrations.dsh_agent import (
    DshAgentRegistry,
    get_dsh_agent_registry,
)


class FakeEventManager:
    def __init__(self):
        self.events = []

    def chat_event(self, chat=None, message=None, event_type=None):
        self.events.append(("chat", getattr(chat, "id", None), event_type))

    def message_event(self, chat=None, message=None):
        self.events.append(("message", getattr(chat, "id", None)))

    def send_event(self, message=None):
        self.events.append(("send", message))


class FakeSettings:
    def __init__(self, root: str):
        self.codx_path = f"{root}/.codx"
        self.abs_project_path = root
        self.project_id = "project-1"
        self.project_name = "test-project"


class FakeSession:
    def __init__(self, settings, manager):
        self.settings = settings
        self.manager = manager

    def get_chat_manager(self):
        return self.manager


def _import_agent_router():
    import importlib
    import pathlib
    import sys
    import types

    package = sys.modules.get("codx.junior.api")
    if package is None:
        package = types.ModuleType("codx.junior.api")
        package.__path__ = [str(pathlib.Path(__file__).resolve().parents[1] / "codx" / "junior" / "api")]
        sys.modules["codx.junior.api"] = package
    return importlib.import_module("codx.junior.api.dsh_agent")


def _import_dsh_router():
    import importlib
    import pathlib
    import sys
    import types

    package = sys.modules.get("codx.junior.api")
    if package is None:
        package = types.ModuleType("codx.junior.api")
        package.__path__ = [str(pathlib.Path(__file__).resolve().parents[1] / "codx" / "junior" / "api")]
        sys.modules["codx.junior.api"] = package
    return importlib.import_module("codx.junior.api.dsh")


@pytest.fixture()
def project(tmp_path):
    root = str(tmp_path)
    settings = FakeSettings(root)
    manager = ChatManager(settings=settings, event_manager=FakeEventManager())
    registry = get_dsh_agent_registry()
    registry.reset()
    yield root, settings, manager, registry
    registry.reset()


@pytest.fixture()
def agent_env(monkeypatch):
    monkeypatch.setenv("CODX_JUNIOR_DSH_AGENT_TOKEN", "agent-secret")
    return "agent-secret"


def test_registry_enqueue_roundtrip(project):
    root, settings, manager, registry = project
    instance = registry.register("project-1", f"{root}/.codx", {
        "instance_id": "inst-1",
        "name": "Host 1",
        "cwd": root,
        "version": "1",
    })
    assert instance.id == "inst-1"
    assert instance.online()

    outcomes = []

    def worker():
        commands = registry.take_commands("inst-1", wait_seconds=2)
        registry.complete(commands[0].id, "inst-1", result={"pong": True})

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    time.sleep(0.1)
    result = registry.enqueue("inst-1", "ping", {}, timeout=3)
    thread.join(timeout=3)
    assert result == {"pong": True}
    assert not thread.is_alive()


def test_registry_marks_offline(project):
    root, settings, manager, registry = project
    registry.register("project-1", f"{root}/.codx", {"instance_id": "inst-2", "name": "Host 2"})
    instance = registry.get("inst-2")
    instance.last_seen = 0
    assert not instance.online()
    with pytest.raises(Exception):
        registry.enqueue("inst-2", "ping", {}, timeout=0.1)


def test_agent_api_register_heartbeat_commands_and_result(project, agent_env):
    root, settings, manager, registry = project
    dsh_api = _import_agent_router()
    app = FastAPI()
    app.include_router(dsh_api.router, prefix="/api")

    @app.middleware("http")
    async def attach_session(request: Request, call_next):
        request.state.codx_junior_session = FakeSession(settings, manager)
        return await call_next(request)

    client = TestClient(app)
    headers = {"authorization": f"Bearer {agent_env}"}
    registered = client.post(
        "/api/dsh/agent/register",
        json={"instance_id": "inst-api", "name": "Host API", "cwd": root, "version": "1"},
        headers=headers,
    )
    assert registered.status_code == 200, registered.text
    assert registered.json()["instance"]["id"] == "inst-api"

    heartbeat = client.post(
        "/api/dsh/agent/heartbeat",
        json={"instance_id": "inst-api", "running": 2, "sessions": 5},
        headers=headers,
    )
    assert heartbeat.status_code == 200, heartbeat.text
    assert heartbeat.json()["instance"]["running"] == 2

    outcomes = []

    def enqueue():
        outcomes.append(registry.enqueue("inst-api", "ping", {}, timeout=3))

    thread = threading.Thread(target=enqueue, daemon=True)
    thread.start()
    deadline = time.time() + 2
    while registry.pending_count("inst-api") == 0 and time.time() < deadline:
        time.sleep(0.01)
    commands = client.get(
        "/api/dsh/agent/commands",
        params={"instance_id": "inst-api", "wait": 1},
        headers=headers,
    )
    assert commands.status_code == 200, commands.text
    command = commands.json()["commands"][0]
    assert command["type"] == "ping"

    result = client.post(
        f"/api/dsh/agent/commands/{command['id']}/result",
        json={"instance_id": "inst-api", "ok": True, "result": {"pong": True}},
        headers=headers,
    )
    assert result.status_code == 200, result.text
    thread.join(timeout=3)
    assert outcomes == [{"pong": True}]


def test_agent_api_events_upsert_mirror(project, agent_env):
    root, settings, manager, registry = project
    registry.register("project-1", f"{root}/.codx", {"instance_id": "inst-evt", "name": "Host"})
    dsh_api = _import_agent_router()
    app = FastAPI()
    app.include_router(dsh_api.router, prefix="/api")

    @app.middleware("http")
    async def attach_session(request: Request, call_next):
        request.state.codx_junior_session = FakeSession(settings, manager)
        return await call_next(request)

    client = TestClient(app)
    response = client.post(
        "/api/dsh/agent/events",
        json={
            "instance_id": "inst-evt",
            "event": "session.created",
            "task": {
                "id": "session-event-1",
                "title": "Event task",
                "status": "idle",
                "description": "event",
            },
        },
        headers={"authorization": f"Bearer {agent_env}"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 1
    expected_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "dsh:session-event-1"))
    chat = manager.find_by_id(expected_id)
    assert chat is not None
    assert chat.external_instance_id == "inst-evt"


def test_status_requires_admin_and_lists_instances(project, monkeypatch):
    root, settings, manager, registry = project
    registry.register("project-1", f"{root}/.codx", {"instance_id": "inst-status", "name": "Host"})
    dsh_api = _import_dsh_router()
    app = FastAPI()
    app.include_router(dsh_api.router, prefix="/api")

    @app.middleware("http")
    async def attach_session(request: Request, call_next):
        request.state.codx_junior_session = FakeSession(settings, manager)
        return await call_next(request)

    from codx.junior.model.model import CodxUser

    app.dependency_overrides[dsh_api.get_authenticated_user] = lambda: CodxUser(
        username="admin", role="admin"
    )
    client = TestClient(app)
    response = client.get("/api/dsh/status")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["instances"][0]["id"] == "inst-status"
    assert data["online_instances"] == 1
    assert "agent_token" in data["config"]


def test_token_endpoint_writes_agent_token_file(project, monkeypatch):
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    from codx.junior.model.model import CodxUser, DshSettings

    root, settings, manager, registry = project
    dsh_api = _import_dsh_router()
    saved = {}
    monkeypatch.setattr(
        dsh_api,
        "read_global_settings",
        lambda: type("Global", (), {"dsh": DshSettings()})(),
    )
    monkeypatch.setattr(
        dsh_api,
        "write_settings_section",
        lambda section, data: saved.update({"section": section, "data": data}),
    )

    app = FastAPI()
    app.include_router(dsh_api.router, prefix="/api")

    @app.middleware("http")
    async def attach_session(request: Request, call_next):
        request.state.codx_junior_session = FakeSession(settings, manager)
        return await call_next(request)

    app.dependency_overrides[dsh_api.get_authenticated_user] = lambda: CodxUser(
        username="admin", role="admin"
    )
    client = TestClient(app)
    response = client.post("/api/dsh/token")
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    assert token
    assert saved["section"] == "dsh"
    assert saved["data"]["agent_token"] == token
    token_file = os.path.join(root, ".dsh-codx-junior", "token")
    assert os.path.isfile(token_file)
    with open(token_file, encoding="utf-8") as handle:
        assert handle.read().strip() == token
