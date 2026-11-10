"""
DSH task mirroring for codx-junior.

The DSH Harness owns the conversation (its append-only Session log). This
module keeps a *linked* :class:`~codx.junior.db.Chat` in codx-junior's boards:
id, title, parent/subtask relationship and task state live here, while the
messages are fetched from DSH on demand and never persisted in the codx task
file.

Two directions are supported:

* DSH -> codx-junior: the DSH plugin posts ``session.created`` /
  ``session.updated`` / ``session.disposed`` events to
  ``POST /api/dsh/events``. Each event upserts the linked task.
* codx-junior -> DSH: :class:`DshSync.create_task` asks the DSH bridge to create
  a Session and prompt it, then mirrors the returned Session as a task.

Configuration is environment based so the bridge can be enabled without
touching project settings:

* ``CODX_JUNIOR_DSH_URL``          DSH web origin (default ``http://127.0.0.1:3080``)
* ``CODX_JUNIOR_DSH_SECRET``       shared bridge secret (optional)
* ``CODX_JUNIOR_DSH_SECRET_FILE``  secret file (default ``<project>/.dsh-codx-junior/secret``)
* ``CODX_JUNIOR_DSH_BOARD``        board title (default ``DSH``)
* ``CODX_JUNIOR_DSH_ENABLED``      set to ``0`` to disable mirroring
* ``CODX_JUNIOR_DSH_ONLY_PROJECT`` set to ``0`` to sync sessions outside the project
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from hmac import compare_digest
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from codx.junior.db import Chat, Message
from codx.junior.identity import attach_root_id
from codx.junior.integrations.harness_models import harness_model_payload
from codx.junior.integrations.harness_sandbox import (
    ensure_project_cwd,
    is_path_within,
    project_root,
)
from codx.junior.integrations.harness_usage import log_usage

logger = logging.getLogger(__name__)

DSH_SOURCE = "dsh"
DEFAULT_BOARD = "DSH"
DEFAULT_COLUMNS = ("Todo", "Doing", "On hold", "Done")
DEFAULT_URL = "http://127.0.0.1:3080"
# Board columns are display labels: their order and colors are codx-junior's.
COLUMN_COLORS = {
    "Todo": "#94a3b8",
    "Doing": "#3b82f6",
    "On hold": "#f59e0b",
    "Done": "#22c55e",
}


class DshError(RuntimeError):
    """A DSH bridge request failed."""

    def __init__(self, message: str, status: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


class DshAuthError(DshError):
    """A webhook or bridge request failed authentication."""


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _global_dsh_settings() -> Any:
    """Read the dashboard-managed DSH section, tolerating an early import."""
    try:
        from codx.junior.global_settings import get_global_settings

        return getattr(get_global_settings(), "dsh", None)
    except Exception:  # pragma: no cover - settings may not be loaded yet
        return None


def _read_secret_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = handle.read().strip()
        return value or None
    except OSError:
        return None


@dataclass(frozen=True)
class DshConfig:
    """Resolved bridge configuration for one codx-junior project."""

    url: str = DEFAULT_URL
    secret: Optional[str] = None
    codx_path: Optional[str] = None
    project_root: Optional[str] = None
    board: str = DEFAULT_BOARD
    columns: Tuple[str, ...] = DEFAULT_COLUMNS
    timeout: float = 15.0
    enabled: bool = True
    only_project: bool = True
    sandbox_enabled: bool = True
    secret_source: str = "missing"
    agent_token: Optional[str] = None
    agent_token_source: str = "missing"
    default_instance_id: Optional[str] = None

    @classmethod
    def from_settings(cls, settings: Any) -> "DshConfig":
        """Build the config from env, dashboard settings and the secret file.

        Precedence is deliberately env -> Global Settings ``dsh`` -> workspace
        secret file -> built-in default. Environment variables remain available
        for container deployments, while the dashboard is the normal path.
        """
        codx_path = getattr(settings, "codx_path", None)
        project_root = (
            os.environ.get("CODX_JUNIOR_DSH_PROJECT_ROOT")
            or getattr(settings, "abs_project_path", None)
            or (os.path.dirname(codx_path) if codx_path else None)
        )
        dsh = _global_dsh_settings()

        def configured(env_name: str, attr: str, default: Any) -> Any:
            value = os.environ.get(env_name)
            if value not in (None, ""):
                return value
            value = getattr(dsh, attr, None) if dsh is not None else None
            if value not in (None, ""):
                return value
            return default

        url = str(configured("CODX_JUNIOR_DSH_URL", "url", DEFAULT_URL)).strip().rstrip("/")
        board = str(configured("CODX_JUNIOR_DSH_BOARD", "board", DEFAULT_BOARD)).strip() or DEFAULT_BOARD

        secret = (os.environ.get("CODX_JUNIOR_DSH_SECRET") or "").strip() or None
        secret_source = "env" if secret else "missing"
        if not secret and dsh is not None:
            stored = (getattr(dsh, "secret", "") or "").strip()
            if stored:
                secret = stored
                secret_source = "settings"
        if not secret:
            secret_file = (
                os.environ.get("CODX_JUNIOR_DSH_SECRET_FILE")
                or (os.path.join(project_root, ".dsh-codx-junior", "secret") if project_root else "")
            )
            if secret_file:
                secret = _read_secret_file(secret_file)
                if secret:
                    secret_source = "file"

        agent_token = (os.environ.get("CODX_JUNIOR_DSH_AGENT_TOKEN") or "").strip() or None
        agent_token_source = "env" if agent_token else "missing"
        if not agent_token and dsh is not None:
            stored_token = (getattr(dsh, "agent_token", "") or "").strip()
            if stored_token:
                agent_token = stored_token
                agent_token_source = "settings"
        if not agent_token:
            token_file = (
                os.environ.get("CODX_JUNIOR_DSH_TOKEN_FILE")
                or (os.path.join(project_root, ".dsh-codx-junior", "token") if project_root else "")
            )
            if token_file:
                try:
                    with open(token_file, "r", encoding="utf-8") as handle:
                        file_token = handle.read().strip()
                except OSError:
                    file_token = ""
                if file_token:
                    agent_token = file_token
                    agent_token_source = "file"

        default_instance_id = (
            os.environ.get("CODX_JUNIOR_DSH_DEFAULT_INSTANCE")
            or (getattr(dsh, "default_instance_id", "") if dsh is not None else "")
            or None
        )

        return cls(
            url=url or DEFAULT_URL,
            secret=secret,
            codx_path=codx_path,
            project_root=project_root,
            board=board,
            timeout=float(os.environ.get("CODX_JUNIOR_DSH_TIMEOUT", "15") or 15),
            enabled=_env_bool("CODX_JUNIOR_DSH_ENABLED", bool(getattr(dsh, "enabled", True))),
            only_project=_env_bool(
                "CODX_JUNIOR_DSH_ONLY_PROJECT",
                bool(getattr(dsh, "only_project", True)),
            ),
            sandbox_enabled=_env_bool(
                "CODX_JUNIOR_DSH_SANDBOX",
                bool(getattr(dsh, "sandbox_enabled", True)),
            ),
            secret_source=secret_source,
            agent_token=agent_token,
            agent_token_source=agent_token_source,
            default_instance_id=str(default_instance_id).strip() if default_instance_id else None,
        )

    def require_secret(self) -> str:
        """Return the shared secret or raise a useful configuration error."""
        if not self.secret:
            raise DshError(
                "DSH bridge secret is missing. Open Global Settings → DSH Harness "
                "and paste the secret, or start the DSH plugin once so it writes "
                ".dsh-codx-junior/secret, or set CODX_JUNIOR_DSH_SECRET."
            )
        return self.secret


@dataclass
class DshTask:
    """A normalized task payload sent by the DSH bridge."""

    id: str
    title: str = ""
    parent_id: Optional[str] = None
    status: str = "idle"
    origin: str = "session"
    cwd: Optional[str] = None
    web_url: Optional[str] = None
    description: str = ""
    last_message: str = ""
    updated_at: Optional[int] = None
    created_at: Optional[int] = None
    running: bool = False
    blank: bool = False
    model: Optional[str] = None
    usage: Dict[str, Any] = field(default_factory=dict)
    cost: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status == "running":
            self.running = True

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "DshTask":
        """Normalize a DSH bridge task or webhook task."""
        data = dict(payload or {})
        task_id = str(data.get("id") or data.get("sessionId") or "").strip()
        return cls(
            id=task_id,
            title=str(data.get("title") or data.get("name") or "").strip(),
            parent_id=(str(data["parentId"]) if data.get("parentId") else None),
            status=str(data.get("status") or ("running" if data.get("running") else "idle")),
            origin=str(data.get("origin") or ("subagent" if data.get("isSubagent") else "session")),
            cwd=(str(data["cwd"]) if data.get("cwd") else None),
            web_url=(str(data["webUrl"]) if data.get("webUrl") else None),
            description=str(data.get("description") or ""),
            last_message=str(data.get("lastMessage") or ""),
            updated_at=_as_ms(data.get("updatedAt")),
            created_at=_as_ms(data.get("createdAt")),
            running=bool(data.get("running") or data.get("status") == "running"),
            blank=bool(data.get("blank")),
            model=(str(data["model"]) if data.get("model") else None),
            usage=(dict(data.get("usage") or {}) if isinstance(data.get("usage"), dict) else {}),
            cost=(data.get("cost") if isinstance(data.get("cost"), (int, float)) else None),
            raw=data,
        )


def _as_ms(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() * 1000)
    except (TypeError, ValueError):
        return None


def _iso(ms: Optional[int]) -> Optional[str]:
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000.0).isoformat()


def _is_under(path: Optional[str], root: Optional[str]) -> bool:
    """Return True when *path* resolves inside *root* (symlinks included)."""
    if not path or not root:
        return True
    return is_path_within(path, root)


def _chat_id_for(session_id: str) -> str:
    """Stable codx-junior chat id for one DSH session."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"dsh:{session_id}"))


def _message_from_dsh(entry: Mapping[str, Any]) -> Message:
    """Convert one live DSH message into a codx-junior message (in memory)."""
    role = str(entry.get("role") or "assistant")
    if role not in {"user", "assistant", "system"}:
        role = "assistant"
    created = entry.get("created_at") or datetime.now().isoformat()
    return Message(
        doc_id=str(entry.get("id") or uuid.uuid4()),
        role=role,
        content=str(entry.get("content") or ""),
        think=entry.get("think") or None,
        is_answer=role == "assistant",
        created_at=str(created),
        updated_at=str(created),
        meta_data={
            "external": {
                "source": DSH_SOURCE,
                **(entry.get("meta_data") or {}),
            }
        },
    )


class DshClient:
    """Small stdlib-only client for the DSH codx-junior bridge."""

    def __init__(self, config: DshConfig):
        self.config = config

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Mapping[str, Any]] = None,
        query: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        if not self.config.enabled:
            raise DshError("DSH mirroring is disabled (CODX_JUNIOR_DSH_ENABLED=0)")
        secret = self.config.require_secret()
        url = f"{self.config.url}{path}"
        if query:
            clean = {key: value for key, value in query.items() if value not in (None, "")}
            if clean:
                url = f"{url}?{urlencode(clean)}"
        data = None
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {secret}",
            "x-dsh-secret": secret,
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["content-type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.config.timeout) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            message = parsed.get("message") if isinstance(parsed, dict) else raw
            raise DshError(
                f"DSH bridge returned {error.code}: {message or error.reason}",
                status=error.code,
                body=parsed,
            ) from error
        except URLError as error:
            raise DshError(f"Cannot reach the DSH bridge at {self.config.url}: {error.reason}") from error

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/codx-junior/health")

    def list_tasks(
        self,
        cwd: Optional[str] = None,
        include_blank: bool = False,
        limit: int = 500,
    ) -> List[DshTask]:
        payload = self._request(
            "GET",
            "/codx-junior/tasks",
            query={"cwd": cwd, "includeBlank": "1" if include_blank else None, "limit": limit},
        )
        return [DshTask.from_payload(item) for item in payload.get("tasks", [])]

    def get_task(self, session_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/codx-junior/tasks/{quote(session_id, safe='')}")

    def create_task(
        self,
        title: str,
        prompt: str = "",
        cwd: Optional[str] = None,
        agent_preset: Optional[str] = None,
        codx_task_id: Optional[str] = None,
        model: Optional[Mapping[str, Any]] = None,
        workspace_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "title": title,
            "prompt": prompt,
            "cwd": cwd,
            "agentPreset": agent_preset,
            "codxTaskId": codx_task_id,
        }
        if model:
            body["model"] = dict(model)
        if workspace_root:
            body["workspaceRoot"] = workspace_root
        return self._request("POST", "/codx-junior/tasks", body=body)

    def prompt(self, session_id: str, text: str, mode: str = "queue") -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/codx-junior/tasks/{quote(session_id, safe='')}/prompt",
            body={"text": text, "mode": mode},
        )

    def cancel(self, session_id: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/codx-junior/tasks/{quote(session_id, safe='')}/cancel",
            body={},
        )

    def rename(self, session_id: str, title: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/codx-junior/tasks/{quote(session_id, safe='')}/title",
            body={"title": title},
        )


class DshSync:
    """Mirror DSH tasks into one codx-junior project's boards."""

    def __init__(
        self,
        settings: Any,
        config: Optional[DshConfig] = None,
        client: Optional[Any] = None,
        instance_id: Optional[str] = None,
    ):
        self.settings = settings
        self.config = config or DshConfig.from_settings(settings)
        self.client = client or DshClient(self.config)
        self.instance_id = instance_id
        self.chat_manager = None
        self._parent_cache: Dict[str, Chat] = {}

    # -- project plumbing ---------------------------------------------------

    def for_chat_manager(self, chat_manager: Any) -> "DshSync":
        self.chat_manager = chat_manager
        return self

    def client_for(self, instance_id: Optional[str] = None):
        """Return the client bound to *instance_id* when one is available."""
        target = instance_id or self.instance_id
        if target and getattr(self.client, "instance_id", None) != target:
            for_instance = getattr(self.client, "for_instance", None)
            if callable(for_instance):
                return for_instance(target)
        return self.client

    def _manager(self, chat_manager: Any = None) -> Any:
        manager = chat_manager or self.chat_manager
        if manager is None:
            raise DshError("DshSync requires a ChatManager")
        return manager

    def _project_root(self) -> Optional[str]:
        root = self.config.project_root or project_root(self.settings)
        return os.path.realpath(root) if root else None

    def _accepts(self, task: DshTask) -> bool:
        if not task.id:
            return False
        # The sandbox check is independent from the "only this project" sync
        # preference: even when a project opts into seeing other sessions, a
        # harness event may never attach a path outside its workspace.
        if task.cwd and (self.config.sandbox_enabled or self.config.only_project):
            if not _is_under(task.cwd, self._project_root()):
                logger.debug("dsh: ignoring session %s outside project (%s)", task.id, task.cwd)
                return False
        return True

    # -- board --------------------------------------------------------------

    def ensure_board(self, chat_manager: Any = None) -> None:
        """Create the configured DSH board when the project catalogue lacks it."""
        manager = self._manager(chat_manager)
        kanban = manager.load_kanban() or {}
        boards = kanban.get("boards") or {}
        wanted = self.config.board
        existing = next(
            (title for title in boards if str(title).strip().lower() == wanted.lower()),
            None,
        )
        if existing:
            return
        boards[wanted] = {
            "title": wanted,
            "type": "kanban",
            "columns": [
                {
                    "title": title,
                    "color": COLUMN_COLORS.get(title),
                    "index": index,
                }
                for index, title in enumerate(self.config.columns)
            ],
        }
        kanban["boards"] = boards
        manager.save_kanban(kanban)
        logger.info("dsh: created board '%s'", wanted)

    # -- lookup -------------------------------------------------------------

    def find_chat(self, session_id: str, chat_manager: Any = None) -> Optional[Chat]:
        manager = self._manager(chat_manager)
        chat = manager.find_by_id(_chat_id_for(session_id))
        if chat is not None:
            return chat
        # Backward/defensive lookup: an older mirror may have another id.
        try:
            for candidate in manager.list_chats():
                same_source = (
                    getattr(candidate, "harness", None) == DSH_SOURCE
                    or getattr(candidate, "external_source", None) == DSH_SOURCE
                )
                same_id = (
                    getattr(candidate, "harness_task_id", None) == session_id
                    or getattr(candidate, "external_id", None) == session_id
                )
                if same_source and same_id:
                    return candidate
        except Exception:  # pragma: no cover - list errors must not block events
            logger.debug("dsh: external-id fallback lookup failed", exc_info=True)
        return None

    # -- upsert -------------------------------------------------------------

    def upsert_task(
        self,
        task: DshTask,
        chat_manager: Any = None,
        parent_chat: Optional[Chat] = None,
        force_board: Optional[str] = None,
        force_column: Optional[str] = None,
        allow_create: bool = True,
        instance_id: Optional[str] = None,
        harness_mode: str = "mirror",
    ) -> Tuple[Optional[Chat], bool]:
        """Create or update the linked chat for one DSH task."""
        manager = self._manager(chat_manager)
        instance = instance_id or self.instance_id
        if not self._accepts(task):
            return None, False
        if task.blank and not (task.description or task.last_message):
            logger.debug("dsh: skipping blank session %s", task.id)
            return None, False

        existing = self.find_chat(task.id, manager)
        parent = parent_chat
        if parent is None and task.parent_id:
            parent = self._parent_cache.get(task.parent_id)
            if parent is None:
                parent = self._load_parent(task.parent_id, manager)
        if parent is None and getattr(task, "raw", {}).get("parentChatId"):
            parent = manager.find_by_id(str(task.raw["parentChatId"]))

        if existing is None:
            if not allow_create:
                return None, False
            self.ensure_board(manager)
            board = force_board or self.config.board
            column = force_column or self._column_for(task)
            chat = Chat(
                id=_chat_id_for(task.id),
                name=task.title or f"DSH {task.id[-8:]}",
                # Identity + link only: the conversation (including the first
                # prompt) is fetched live from DSH, never copied into the task.
                description=f"Live DSH session `{task.id}`. Open the task to read the conversation in DSH.",
                mode="chat",
                board=board,
                column=column,
                status=self._status_for(task, None),
                tags=[DSH_SOURCE],
                harness=DSH_SOURCE,
                harness_instance_id=instance,
                harness_task_id=task.id,
                harness_parent_task_id=task.parent_id,
                harness_mode=harness_mode,
                harness_status=self._harness_status_for(task),
                harness_model=task.model,
                harness_usage=dict(task.usage or {}),
                harness_cost=task.cost,
                harness_metadata={
                    "origin": task.origin,
                    "cwd": task.cwd,
                    "is_subagent": bool(getattr(task, "raw", {}).get("isSubagent")),
                },
                external_source=DSH_SOURCE,
                external_id=task.id,
                external_parent_id=task.parent_id,
                external_instance_id=instance,
                external_status=task.status,
                external_url=task.web_url,
                external_updated_at=_iso(task.updated_at or task.created_at),
            )
            if parent is not None:
                chat.parent_id = parent.id
            attach_root_id(chat=chat, parent_chat=parent)
            saved = manager.save_chat(chat=chat)
            log_usage(
                project_root=self._project_root(),
                project_name=getattr(self.settings, "project_name", None),
                chat=saved,
                task=task,
                instance_id=instance,
                source="created",
            )
            logger.info("dsh: mirrored new session %s as chat %s", task.id, saved.id)
            return saved, True

        changed = False
        usage_changed = False
        if task.title and existing.name != task.title:
            existing.name = task.title
            changed = True
        for attr, value in (
            ("harness", DSH_SOURCE),
            ("harness_instance_id", instance or existing.harness_instance_id),
            ("harness_task_id", task.id),
            ("harness_parent_task_id", task.parent_id),
            ("harness_status", self._harness_status_for(task)),
            ("external_source", DSH_SOURCE),
            ("external_id", task.id),
            ("external_parent_id", task.parent_id),
            ("external_instance_id", instance or existing.external_instance_id),
            ("external_status", task.status),
            ("external_url", task.web_url or existing.external_url),
            ("external_updated_at", _iso(task.updated_at or task.created_at)),
        ):
            if getattr(existing, attr, None) != value:
                setattr(existing, attr, value)
                changed = True
        if not existing.harness_mode:
            existing.harness_mode = harness_mode
            changed = True
        # The model reported in later session events is the harness-side id;
        # keep the codx-junior model name selected at creation when one exists.
        if task.model and not existing.harness_model:
            existing.harness_model = task.model
            changed = True
        if task.usage and existing.harness_usage != task.usage:
            existing.harness_usage = dict(task.usage)
            changed = True
            usage_changed = True
        if task.cost is not None and existing.harness_cost != task.cost:
            existing.harness_cost = task.cost
            changed = True
            usage_changed = True
        metadata = dict(existing.harness_metadata or {})
        metadata.update({
            "origin": task.origin,
            "cwd": task.cwd,
            "is_subagent": bool(getattr(task, "raw", {}).get("isSubagent")),
        })
        if metadata != (existing.harness_metadata or {}):
            existing.harness_metadata = metadata
            changed = True
        status = self._status_for(task, existing.status)
        if status != existing.status:
            existing.status = status
            changed = True
        # Only follow the running transition when the user has not moved the
        # card to a custom lane: board placement belongs to codx-junior.
        if (task.running or task.status == "running") and existing.column in (self.config.columns[0], "Todo", "todo"):
            existing.column = force_column or "Doing"
            changed = True
        if task.status == "error" and existing.column in (self.config.columns[0], "Todo", "todo"):
            existing.column = "On hold"
            changed = True
        if task.status == "closed" and existing.column in ("Todo", "Doing", "On hold"):
            existing.column = "Done"
            changed = True
        if parent is not None and existing.parent_id != parent.id:
            existing.parent_id = parent.id
            attach_root_id(chat=existing, parent_chat=parent)
            changed = True
        if changed:
            saved = manager.save_chat(chat=existing, chat_only=True)
            if usage_changed:
                log_usage(
                    project_root=self._project_root(),
                    project_name=getattr(self.settings, "project_name", None),
                    chat=saved,
                    task=task,
                    instance_id=instance,
                    source="updated",
                )
            logger.info("dsh: updated mirrored session %s as chat %s", task.id, saved.id)
            return saved, False
        return existing, False

    def _column_for(self, task: DshTask) -> str:
        if task.status == "running":
            return "Doing"
        if task.status == "error":
            return "On hold"
        if task.status == "closed":
            return "Done"
        return self.config.columns[0] if self.config.columns else "Todo"

    def _status_for(self, task: DshTask, previous: Optional[str]) -> str:
        if task.status == "running":
            return "doing"
        if task.status == "error":
            return "onhold"
        if task.status == "closed":
            return "done"
        return previous or "todo"

    def _harness_status_for(self, task: DshTask) -> str:
        """Execution status shown next to the workflow status."""
        if task.status == "running":
            return "running"
        if task.status == "error":
            return "failed"
        if task.status == "closed":
            return "completed"
        return "idle"

    def _load_parent(self, parent_id: str, chat_manager: Any) -> Optional[Chat]:
        existing = self.find_chat(parent_id, chat_manager)
        if existing is not None:
            self._parent_cache[parent_id] = existing
            return existing
        try:
            payload = self.client.get_task(parent_id)
        except DshError:
            logger.warning("dsh: parent session %s is not readable", parent_id)
            return None
        task = DshTask.from_payload(payload.get("task") or {})
        parent, _ = self.upsert_task(task, chat_manager=chat_manager)
        if parent is not None:
            self._parent_cache[parent_id] = parent
        return parent

    # -- event entry points -------------------------------------------------

    def handle_event(
        self,
        payload: Mapping[str, Any],
        instance_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle one event or snapshot from the DSH plugin."""
        event = str(payload.get("event") or "")
        manager = self._manager()
        created = updated = skipped = 0
        if event == "sync.snapshot":
            tasks = [DshTask.from_payload(item) for item in payload.get("tasks") or []]
            for task in tasks:
                chat, was_created = self.upsert_task(
                    task,
                    chat_manager=manager,
                    instance_id=instance_id,
                )
                if chat is None:
                    skipped += 1
                elif was_created:
                    created += 1
                else:
                    updated += 1
            return {"event": event, "created": created, "updated": updated, "skipped": skipped}

        task = DshTask.from_payload(payload.get("task") or {})
        if event == "session.disposed":
            task.status = "closed"
        chat, was_created = self.upsert_task(
            task,
            chat_manager=manager,
            instance_id=instance_id,
        )
        if chat is None:
            skipped += 1
        elif was_created:
            created += 1
        else:
            updated += 1
        return {
            "event": event,
            "sessionId": task.id,
            "chatId": chat.id if chat else None,
            "created": created,
            "updated": updated,
            "skipped": skipped,
        }

    def sync_all(self, cwd: Optional[str] = None) -> Dict[str, Any]:
        """Pull every DSH task and upsert it. Idempotent."""
        manager = self._manager()
        # Make the destination visible even when DSH has no tasks yet.
        self.ensure_board(manager)
        project_cwd = ensure_project_cwd(cwd or self._project_root(), self.settings)
        tasks = self.client.list_tasks(cwd=project_cwd, limit=1000)
        created = updated = skipped = 0
        for task in tasks:
            chat, was_created = self.upsert_task(
                task,
                chat_manager=manager,
                instance_id=self.instance_id,
            )
            if chat is None:
                skipped += 1
            elif was_created:
                created += 1
            else:
                updated += 1
        return {"total": len(tasks), "created": created, "updated": updated, "skipped": skipped}

    # -- codx-junior -> DSH --------------------------------------------------

    def create_task(
        self,
        name: str,
        prompt: str,
        chat_manager: Any = None,
        board: Optional[str] = None,
        column: Optional[str] = None,
        parent_id: Optional[str] = None,
        agent_preset: Optional[str] = None,
        model: Optional[str] = None,
        cwd: Optional[str] = None,
    ) -> Chat:
        """Create a DSH Session from codx-junior and mirror it back."""
        manager = self._manager(chat_manager)
        name = (name or "").strip()
        if not name:
            raise ValueError("name is required")
        parent_chat = manager.find_by_id(parent_id) if parent_id else None
        if parent_id and parent_chat is None:
            raise ValueError(f"parent chat '{parent_id}' was not found")

        # The session may only start inside this project's workspace. The
        # plugin repeats this check; keeping it here fails fast with a clear
        # error before a command is queued.
        project_cwd = ensure_project_cwd(cwd or self._project_root(), self.settings)
        model_payload = harness_model_payload(model, kind="dsh") if model else None

        codx_task_id = str(uuid.uuid4())
        payload = self.client.create_task(
            title=name,
            prompt=(prompt or "").strip(),
            cwd=project_cwd,
            agent_preset=agent_preset,
            codx_task_id=codx_task_id,
            model=model_payload,
            workspace_root=self._project_root(),
        )
        task = DshTask.from_payload(payload.get("task") or {})
        if not task.id:
            session_id = payload.get("sessionId")
            if not session_id:
                raise DshError("DSH did not return a session id")
            task.id = str(session_id)
        task.title = task.title or name
        model_selection = payload.get("modelSelection") if isinstance(payload, Mapping) else None
        model_applied = bool(payload.get("modelApplied")) if isinstance(payload, Mapping) else False
        if model_payload and not isinstance(model_selection, Mapping):
            model_selection = {
                "requested": model_payload,
                "applied": None,
                "error": "the DSH plugin did not report a model selection",
            }
        if model_payload and model_applied:
            task.model = str(model_payload.get("name") or "")
        # The caller explicitly asked for this task, so it must be visible even
        # before the first prompt is consumed.
        task.blank = False
        chat, _ = self.upsert_task(
            task,
            chat_manager=manager,
            parent_chat=parent_chat,
            force_board=board,
            force_column=column,
            instance_id=self.instance_id,
            harness_mode="managed",
        )
        if chat is None:
            raise DshError(f"DSH created session {task.id} but it was not mirrored")
        # A webhook may have created the mirror before this endpoint returned.
        # The explicit placement requested by the caller wins over the default.
        placement_changed = False
        if chat.harness_mode != "managed":
            chat.harness_mode = "managed"
            placement_changed = True
        if isinstance(model_selection, Mapping):
            metadata = dict(chat.harness_metadata or {})
            metadata["model_selection"] = dict(model_selection)
            if metadata != (chat.harness_metadata or {}):
                chat.harness_metadata = metadata
                placement_changed = True
        if model_payload and model_applied and chat.harness_model != model_payload.get("name"):
            chat.harness_model = str(model_payload.get("name"))
            placement_changed = True
        if board and chat.board != board:
            chat.board = board
            placement_changed = True
        if column and chat.column != column:
            chat.column = column
            placement_changed = True
        if placement_changed:
            chat = manager.save_chat(chat=chat, chat_only=True)
        self.ensure_board(manager)
        return chat

    def prompt(self, session_id: str, text: str, mode: str = "queue") -> Dict[str, Any]:
        if not (text or "").strip():
            raise ValueError("text is required")
        return self.client.prompt(session_id, text.strip(), mode=mode)

    def cancel(self, session_id: str) -> Dict[str, Any]:
        return self.client.cancel(session_id)

    def rename(self, session_id: str, title: str) -> Dict[str, Any]:
        if not (title or "").strip():
            raise ValueError("title is required")
        return self.client.rename(session_id, title.strip())

    # -- live content --------------------------------------------------------

    def hydrate_chat(self, chat: Chat) -> Chat:
        """Fill one mirror chat with the live DSH messages (never persisted)."""
        if not chat or getattr(chat, "external_source", None) != DSH_SOURCE:
            return chat
        if not getattr(chat, "external_id", None):
            return chat
        try:
            payload = self.client_for(getattr(chat, "external_instance_id", None)).get_task(
                chat.external_id
            )
        except DshError as error:
            logger.warning("dsh: cannot hydrate chat %s: %s", chat.id, error)
            return chat
        task = DshTask.from_payload(payload.get("task") or {})
        # Reasoning-only/tool-only steps project to an empty assistant text;
        # they are useful in DSH but would render as empty bubbles on the board.
        chat.messages = [
            _message_from_dsh(entry)
            for entry in payload.get("messages") or []
            if str(entry.get("content") or "").strip()
        ]
        if task.title:
            chat.name = task.title
        chat.harness = DSH_SOURCE
        chat.harness_task_id = task.id
        chat.harness_instance_id = getattr(chat, "harness_instance_id", None) or self.instance_id
        chat.harness_status = self._harness_status_for(task)
        if task.model:
            chat.harness_model = task.model
        if task.usage:
            chat.harness_usage = dict(task.usage)
        if task.cost is not None:
            chat.harness_cost = task.cost
        chat.external_status = task.status
        chat.external_url = task.web_url or chat.external_url
        chat.external_updated_at = _iso(task.updated_at or task.created_at)
        return chat


def verify_webhook(headers: Mapping[str, str], body: bytes, config: DshConfig) -> None:
    """Authenticate a DSH -> codx-junior webhook.

    The bridge sends both a bearer secret and an HMAC over the exact body. The
    HMAC is checked when present; the bearer secret is always required.
    """
    secret = config.require_secret()
    authorization = headers.get("authorization") or headers.get("Authorization") or ""
    presented = authorization[7:].strip() if authorization.startswith("Bearer ") else ""
    if not presented:
        presented = headers.get("x-dsh-secret") or headers.get("X-DSH-Secret") or ""
    if not compare_digest(presented, secret):
        raise DshAuthError("invalid DSH webhook secret")
    signature = headers.get("x-dsh-signature") or headers.get("X-DSH-Signature")
    if signature:
        expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        if not compare_digest(signature, expected):
            raise DshAuthError("invalid DSH webhook signature")


def dsh_chats(chat_manager: Any) -> Iterable[Chat]:
    """Yield mirrored DSH chats in a project (used by diagnostics)."""
    for chat in chat_manager.list_chats():
        if (
            getattr(chat, "harness", None) == DSH_SOURCE
            or getattr(chat, "external_source", None) == DSH_SOURCE
        ):
            yield chat
