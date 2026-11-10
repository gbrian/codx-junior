"""
Tests for the DSH <-> codx-junior task mirror.

These exercise the bridge contract at the Python edge: the HTTP client shape,
webhook authentication, task/board mirroring, parent/subtask linkage and the
"live messages are never persisted" rule.
"""

import hashlib
import hmac
import json
import os
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from codx.junior.chat_manager import ChatManager
from codx.junior.integrations.dsh import (
    DshAuthError,
    DshClient,
    DshConfig,
    DshSync,
    DshTask,
    verify_webhook,
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
        self.codx_path = os.path.join(root, ".codx")
        self.abs_project_path = root
        self.project_id = "project-1"
        self.project_name = "test-project"


class FakeClient:
    """The narrow DSH client surface used by DshSync."""

    def __init__(self, tasks=None, detail=None):
        self.tasks = tasks or []
        self.detail = detail or {}
        self.prompts = []
        self.created = []

    def list_tasks(self, cwd=None, include_blank=False, limit=500):
        return [DshTask.from_payload(task) for task in self.tasks]

    def get_task(self, session_id):
        if session_id in self.detail:
            return self.detail[session_id]
        for task in self.tasks:
            if task.get("id") == session_id:
                return {"task": task, "messages": []}
        raise AssertionError(f"unexpected get_task({session_id})")

    def create_task(
        self,
        title,
        prompt="",
        cwd=None,
        agent_preset=None,
        codx_task_id=None,
        model=None,
        workspace_root=None,
    ):
        task = {
            "id": "session-created",
            "title": title,
            "status": "running",
            "running": True,
            "description": prompt,
            "webUrl": "http://dsh/?session=session-created",
            "model": (model or {}).get("name") if model else None,
        }
        self.created.append({
            "title": title,
            "prompt": prompt,
            "cwd": cwd,
            "codx_task_id": codx_task_id,
            "model": model,
            "workspace_root": workspace_root,
        })
        return {
            "ok": True,
            "sessionId": "session-created",
            "task": task,
            "modelApplied": bool(model),
            "modelSelection": {
                "requested": model,
                "applied": bool(model),
            } if model else None,
        }

    def prompt(self, session_id, text, mode="queue"):
        self.prompts.append((session_id, text, mode))
        return {"accepted": True}

    def cancel(self, session_id):
        return {"cancelled": True}

    def rename(self, session_id, title):
        return {"title": title}


@pytest.fixture()
def project(tmp_path):
    root = str(tmp_path)
    settings = FakeSettings(root)
    manager = ChatManager(settings=settings, event_manager=FakeEventManager())
    return root, settings, manager


def make_sync(root, manager, client=None):
    config = DshConfig(secret="test-secret", project_root=root, only_project=True)
    return DshSync(settings=FakeSettings(root), config=config, client=client or FakeClient()).for_chat_manager(manager)


def test_upsert_creates_board_and_parent_child_tree(project):
    root, settings, manager = project
    sync = make_sync(root, manager)
    root_chat, created = sync.upsert_task(
        DshTask(id="session-root", title="Main task", description="root", status="idle")
    )
    assert created is True
    assert root_chat.board == "DSH"
    assert root_chat.column == "Todo"
    assert root_chat.external_source == "dsh"
    assert root_chat.external_id == "session-root"

    board = manager.load_kanban()["boards"]["DSH"]
    assert [column["title"] for column in board["columns"]] == ["Todo", "Doing", "On hold", "Done"]

    child_chat, created_child = sync.upsert_task(
        DshTask(
            id="session-child",
            title="Child task",
            parent_id="session-root",
            description="child",
            status="running",
        )
    )
    assert created_child is True
    assert child_chat.parent_id == root_chat.id
    assert child_chat.root_id == root_chat.id
    assert child_chat.column == "Doing"
    assert child_chat.status == "doing"


def test_update_moves_running_task_to_doing_and_preserves_custom_column(project):
    root, settings, manager = project
    sync = make_sync(root, manager)
    chat, _ = sync.upsert_task(DshTask(id="session-1", title="Task", description="d", status="idle"))
    assert chat.column == "Todo"

    chat, created = sync.upsert_task(DshTask(id="session-1", title="Task renamed", description="d", status="running"))
    assert created is False
    assert chat.name == "Task renamed"
    assert chat.column == "Doing"
    assert chat.status == "doing"

    # A user move to a custom lane is not undone by a later running update.
    chat.column = "My lane"
    manager.save_chat(chat=chat, chat_only=True)
    chat, _ = sync.upsert_task(DshTask(id="session-1", title="Task renamed", description="d", status="running"))
    assert chat.column == "My lane"


def test_hydration_reads_live_messages_without_persisting_them(project):
    root, settings, manager = project
    detail = {
        "session-hydrate": {
            "task": {
                "id": "session-hydrate",
                "title": "Hydrated",
                "status": "running",
                "updatedAt": 1000,
                "webUrl": "http://dsh/?session=session-hydrate",
            },
            "messages": [
                {"id": "dsh-1", "role": "user", "content": "Fix it", "created_at": "2026-01-01T00:00:00"},
                {"id": "dsh-2", "role": "assistant", "content": "Working on it", "created_at": "2026-01-01T00:00:01"},
            ],
        }
    }
    sync = make_sync(root, manager, FakeClient(detail=detail))
    chat, _ = sync.upsert_task(DshTask(id="session-hydrate", title="Hydrated", description="live", status="idle"))
    hydrated = sync.hydrate_chat(chat)
    assert [message.content for message in hydrated.messages] == ["Fix it", "Working on it"]
    assert hydrated.messages[0].role == "user"
    assert hydrated.messages[1].is_answer is True

    # The stored task file contains no message copy.
    reloaded = manager.find_by_id(chat.id)
    assert reloaded.messages == []


def test_webhook_signature_is_verified():
    config = DshConfig(secret="hook-secret")
    body = json.dumps({"event": "session.updated", "task": {"id": "s"}}).encode()
    signature = "sha256=" + hmac.new(b"hook-secret", body, hashlib.sha256).hexdigest()
    verify_webhook(
        {"authorization": "Bearer hook-secret", "x-dsh-signature": signature},
        body,
        config,
    )
    with pytest.raises(DshAuthError):
        verify_webhook({"authorization": "Bearer wrong"}, body, config)
    with pytest.raises(DshAuthError):
        verify_webhook(
            {"authorization": "Bearer hook-secret", "x-dsh-signature": "sha256=deadbeef"},
            body,
            config,
        )


def test_sync_all_creates_every_task(project):
    root, settings, manager = project
    client = FakeClient(
        tasks=[
            {"id": "session-a", "title": "A", "description": "a", "status": "idle"},
            {"id": "session-b", "title": "B", "description": "b", "status": "running", "parentId": "session-a"},
        ]
    )
    sync = make_sync(root, manager, client)
    result = sync.sync_all()
    assert result["total"] == 2
    assert result["created"] == 2
    assert manager.find_by_id(sync.find_chat("session-b").id).parent_id == sync.find_chat("session-a").id


def test_create_task_triggers_dsh_and_mirrors_it(project):
    root, settings, manager = project
    client = FakeClient()
    sync = make_sync(root, manager, client)
    chat = sync.create_task(name="New DSH task", prompt="Do the work", board="DSH", column="Doing")
    assert client.created[0]["title"] == "New DSH task"
    assert client.created[0]["prompt"] == "Do the work"
    assert chat.external_id == "session-created"
    assert chat.harness == "dsh"
    assert chat.harness_mode == "managed"
    assert chat.harness_task_id == "session-created"
    assert chat.column == "Doing"
    assert chat.status == "doing"


def test_external_sessions_outside_project_are_skipped(project):
    root, settings, manager = project
    sync = make_sync(root, manager)
    chat, created = sync.upsert_task(
        DshTask(id="session-outside", title="Other project", cwd="/some/other/project", description="x")
    )
    assert chat is None
    assert created is False


class _BridgeHandler(BaseHTTPRequestHandler):
    requests = []

    def do_GET(self):  # noqa: N802 - http.server API
        headers = {key.lower(): value for key, value in self.headers.items()}
        self.requests.append(("GET", self.path, headers))
        body = json.dumps({"ok": True, "tasks": [{"id": "s1", "title": "T"}]}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802 - http.server API
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        self.requests.append(("POST", self.path, raw))
        body = json.dumps({"ok": True, "sessionId": "s-new"}).encode()
        self.send_response(201)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


def test_http_client_sends_bridge_auth_and_payload():
    _BridgeHandler.requests = []
    server = HTTPServer(("127.0.0.1", 0), _BridgeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config = DshConfig(url=f"http://127.0.0.1:{server.server_port}", secret="bridge-secret")
        client = DshClient(config)
        tasks = client.list_tasks(cwd="/project")
        assert tasks[0].id == "s1"
        created = client.create_task("Title", "Prompt", cwd="/project")
        assert created["sessionId"] == "s-new"
        get_request = _BridgeHandler.requests[0]
        assert get_request[1].startswith("/codx-junior/tasks?")
        assert "cwd=%2Fproject" in get_request[1]
        assert get_request[2]["authorization"] == "Bearer bridge-secret"
        post_request = _BridgeHandler.requests[1]
        assert post_request[0] == "POST"
        assert b'"title": "Title"' in post_request[2]
        assert b'"prompt": "Prompt"' in post_request[2]
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------------------
# HTTP router tests (FastAPI TestClient, with the heavy api/__init__ bypassed)
# ---------------------------------------------------------------------------


def _import_dsh_router():
    """Import the router without executing codx.junior.api.__init__.

    The package initializer imports the full engine and its optional
    knowledge/vector dependencies. The bridge router does not need them, so a
    package stub keeps this test focused on the HTTP contract.
    """
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


def test_router_accepts_signed_webhook_and_rejects_bad_signature(project, monkeypatch):
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient

    root, settings, manager = project
    monkeypatch.setenv("CODX_JUNIOR_DSH_SECRET", "router-secret")
    dsh_api = _import_dsh_router()

    class FakeSession:
        def __init__(self):
            self.settings = settings

        def get_chat_manager(self):
            return manager

    app = FastAPI()
    app.include_router(dsh_api.router, prefix="/api")

    @app.middleware("http")
    async def attach_session(request: Request, call_next):
        request.state.codx_junior_session = FakeSession()
        return await call_next(request)

    client = TestClient(app)
    payload = {
        "version": 1,
        "event": "session.created",
        "task": {
            "id": "router-session",
            "title": "From webhook",
            "status": "idle",
            "description": "webhook task",
        },
    }
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"router-secret", body, hashlib.sha256).hexdigest()
    response = client.post(
        "/api/dsh/events",
        content=body,
        headers={
            "content-type": "application/json",
            "authorization": "Bearer router-secret",
            "x-dsh-signature": signature,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 1
    expected_chat_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "dsh:router-session"))
    chat = manager.find_by_id(expected_chat_id)
    assert chat is not None
    assert chat.name == "From webhook"
    assert expected_chat_id == chat.id

    bad = client.post(
        "/api/dsh/events",
        content=body,
        headers={"content-type": "application/json", "authorization": "Bearer wrong"},
    )
    assert bad.status_code == 401


def test_router_create_task_endpoint(project, monkeypatch):
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    from codx.junior.db import Chat

    root, settings, manager = project
    monkeypatch.setenv("CODX_JUNIOR_DSH_SECRET", "router-secret")
    dsh_api = _import_dsh_router()

    class FakeSession:
        def __init__(self):
            self.settings = settings

        def get_chat_manager(self):
            return manager

    class FakeSync:
        def create_task(self, **kwargs):
            chat = Chat(
                id="created-chat",
                name=kwargs["name"],
                board=kwargs.get("board") or "DSH",
                column=kwargs.get("column") or "Todo",
                external_source="dsh",
                external_id="created-session",
            )
            manager.save_chat(chat=chat)
            return chat

    app = FastAPI()
    app.include_router(dsh_api.router, prefix="/api")

    @app.middleware("http")
    async def attach_session(request: Request, call_next):
        request.state.codx_junior_session = FakeSession()
        return await call_next(request)

    monkeypatch.setattr(dsh_api, "_resolve_instance_id", lambda request, preferred=None, session_id=None: "inst-1")
    monkeypatch.setattr(dsh_api, "_sync_for_instance", lambda request, instance_id: FakeSync())
    client = TestClient(app)
    response = client.post(
        "/api/dsh/tasks",
        json={"name": "Triggered", "prompt": "Go", "column": "Doing"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["session_id"] == "created-session"
    assert data["instance_id"] == "inst-1"
    assert data["chat"]["name"] == "Triggered"
    assert data["chat"]["column"] == "Doing"


def test_config_prefers_dashboard_settings_over_file(project, monkeypatch, tmp_path):
    root, settings, manager = project
    secret_file = os.path.join(root, ".dsh-codx-junior", "secret")
    os.makedirs(os.path.dirname(secret_file), exist_ok=True)
    with open(secret_file, "w", encoding="utf-8") as handle:
        handle.write("file-secret\n")

    class DashboardDsh:
        url = "http://dashboard-dsh:3080/"
        secret = "dashboard-secret"
        board = "Dashboard board"
        enabled = True
        only_project = False

    monkeypatch.setattr(
        "codx.junior.integrations.dsh._global_dsh_settings",
        lambda: DashboardDsh(),
    )
    config = DshConfig.from_settings(settings)
    assert config.url == "http://dashboard-dsh:3080"
    assert config.board == "Dashboard board"
    assert config.secret == "dashboard-secret"
    assert config.secret_source == "settings"
    assert config.only_project is False


def test_router_saves_dashboard_settings(project, monkeypatch):
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    from codx.junior.model.model import CodxUser, DshSettings

    root, settings, manager = project
    dsh_api = _import_dsh_router()
    saved = {}

    class FakeSession:
        def __init__(self):
            self.settings = settings

        def get_chat_manager(self):
            return manager

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
    monkeypatch.setattr(
        dsh_api,
        "_config",
        lambda project_settings: DshConfig(
            url="http://dsh-new:3080",
            secret="new-secret",
            board="DSH",
        ),
    )

    app = FastAPI()
    app.include_router(dsh_api.router, prefix="/api")
    app.dependency_overrides[dsh_api.get_authenticated_user] = lambda: CodxUser(
        username="admin", role="admin"
    )

    @app.middleware("http")
    async def attach_session(request: Request, call_next):
        request.state.codx_junior_session = FakeSession()
        return await call_next(request)

    client = TestClient(app)
    response = client.put(
        "/api/dsh/settings",
        json={
            "url": "http://dsh-new:3080/",
            "board": "DSH",
            "secret": "new-secret",
            "enabled": True,
            "only_project": False,
        },
    )
    assert response.status_code == 200, response.text
    assert saved["section"] == "dsh"
    assert saved["data"]["url"] == "http://dsh-new:3080"
    assert saved["data"]["secret"] == "new-secret"
    assert saved["data"]["only_project"] is False
    assert response.json()["config"]["secret_source"] == "missing"


def test_router_settings_requires_admin(project, monkeypatch):
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient

    root, settings, manager = project
    dsh_api = _import_dsh_router()

    class FakeSession:
        def __init__(self):
            self.settings = settings

        def get_chat_manager(self):
            return manager

    app = FastAPI()
    app.include_router(dsh_api.router, prefix="/api")
    app.dependency_overrides[dsh_api.get_authenticated_user] = lambda: None

    @app.middleware("http")
    async def attach_session(request: Request, call_next):
        request.state.codx_junior_session = FakeSession()
        return await call_next(request)

    client = TestClient(app)
    response = client.put("/api/dsh/settings", json={"url": "http://dsh:3080"})
    assert response.status_code == 403


def test_create_task_passes_codx_model_and_workspace(project, monkeypatch):
    root, settings, manager = project
    client = FakeClient()
    sync = make_sync(root, manager, client)

    monkeypatch.setattr(
        "codx.junior.integrations.dsh.harness_model_payload",
        lambda name, kind="dsh": {
            "name": name,
            "provider": "deepseek-official",
            "model": "deepseek-flash",
            "reasoning_effort": None,
            "mapped": True,
        },
    )
    chat = sync.create_task(
        name="Model task",
        prompt="Use the selected model",
        model="codx-fast",
    )
    assert client.created[0]["model"]["name"] == "codx-fast"
    assert client.created[0]["model"]["model"] == "deepseek-flash"
    assert client.created[0]["workspace_root"] == os.path.realpath(root)
    assert chat.harness_model == "codx-fast"
    assert chat.harness_metadata["model_selection"]["applied"] is True


def test_create_task_rejects_cwd_outside_project(project):
    root, settings, manager = project
    sync = make_sync(root, manager, FakeClient())
    with pytest.raises(ValueError):
        sync.create_task(
            name="Escaping task",
            prompt="Do not run outside",
            cwd="/some/other/project",
        )


def test_usage_is_mirrored_and_logged(project):
    root, settings, manager = project
    sync = make_sync(root, manager, FakeClient())
    chat, _ = sync.upsert_task(
        DshTask(
            id="session-usage",
            title="Measured task",
            description="usage",
            status="running",
            model="deepseek-flash",
            usage={"input_tokens": 120, "output_tokens": 30},
            cost=0.0042,
        )
    )
    assert chat.harness_usage == {"input_tokens": 120, "output_tokens": 30}
    assert chat.harness_cost == 0.0042
    assert chat.harness_model == "deepseek-flash"

    log_path = os.path.join(root, ".codx", "harness", "usage.jsonl")
    assert os.path.isfile(log_path)
    with open(log_path, encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle if line.strip()]
    assert records[-1]["task_id"] == chat.id
    assert records[-1]["usage"]["input_tokens"] == 120


def test_create_task_rejects_symlink_escape(project):
    root, settings, manager = project
    link = os.path.join(root, "escape")
    try:
        os.symlink("/", link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available")
    sync = make_sync(root, manager, FakeClient())
    with pytest.raises(ValueError):
        sync.create_task(name="Symlink escape", prompt="No", cwd=link)


def test_router_lists_codx_models(project, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from codx.junior.model.model import CodxUser

    root, settings, manager = project
    dsh_api = _import_dsh_router()
    monkeypatch.setattr(
        dsh_api,
        "list_llm_models",
        lambda kind="dsh": [
            {
                "name": "codx-fast",
                "ai_provider": "deepseek",
                "ai_model": "deepseek-flash",
                "model_type": "llm",
                "harness": {"dsh": {"provider": "deepseek-official", "model": "deepseek-flash", "mapped": True}},
            }
        ],
    )
    monkeypatch.setattr(
        dsh_api,
        "read_global_settings",
        lambda: type("Global", (), {"llm_model": "codx-fast"})(),
    )

    app = FastAPI()
    app.include_router(dsh_api.router, prefix="/api")
    app.dependency_overrides[dsh_api.get_authenticated_user] = lambda: CodxUser(
        username="admin", role="admin"
    )
    client = TestClient(app)
    response = client.get("/api/dsh/models")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["models"][0]["name"] == "codx-fast"
    assert data["default"]["name"] == "codx-fast"
