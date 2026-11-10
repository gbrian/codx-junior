"""
Outbound DSH agent channel.

DSH cannot be reached safely from codx-junior, so the direction is reversed:
the DSH Host plugin registers itself with codx-junior, sends heartbeats, and
long-polls a command queue. codx-junior never dials DSH.

The registry in this module is process-local. It keeps:

* one :class:`DshInstance` per registered DSH Host,
* one blocking command queue per instance,
* one waiter per in-flight command (the board request blocks until DSH posts a
  result, with a timeout).

The registry is intentionally thread-safe because FastAPI executes the
long-poll and result endpoints in its thread pool while board endpoints also
enqueue commands.
"""

from __future__ import annotations

import json
import os
import queue
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Tuple

from codx.junior.integrations.dsh import DshError, DshTask

# A heartbeat older than this makes an instance appear offline.
ONLINE_WINDOW_SECONDS = 35
DEFAULT_COMMAND_TIMEOUT = 25
DEFAULT_POLL_WAIT_SECONDS = 25
MAX_POLL_WAIT_SECONDS = 30
MAX_COMMANDS_PER_POLL = 20
TASK_CACHE_TTL_SECONDS = 30
AGENT_TOKEN_FILE = "token"


class DshAgentError(DshError):
    """The outbound agent channel could not complete an operation."""


class DshInstanceOffline(DshAgentError):
    """The requested DSH instance has not sent a recent heartbeat."""


class DshCommandTimeout(DshAgentError):
    """DSH did not post a command result before the deadline."""


class DshCommandFailed(DshAgentError):
    """DSH executed a command and reported an error."""


# ---------------------------------------------------------------------------
# Live content cache
# ---------------------------------------------------------------------------
# Message content is never written to the codx-junior task file. A short-lived
# in-memory cache avoids a command round-trip on every board refresh and keeps
# the last view usable for a few seconds if DSH reconnects.
_TASK_CACHE: Dict[Tuple[str, str], Tuple[Dict[str, Any], float]] = {}
_TASK_CACHE_LOCK = threading.Lock()


def cache_task_view(instance_id: str, session_id: str, payload: Mapping[str, Any]) -> None:
    with _TASK_CACHE_LOCK:
        _TASK_CACHE[(instance_id, session_id)] = (dict(payload), time.time())


def cached_task_view(instance_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    with _TASK_CACHE_LOCK:
        entry = _TASK_CACHE.get((instance_id, session_id))
        if entry is None:
            return None
        payload, stored_at = entry
        if time.time() - stored_at > TASK_CACHE_TTL_SECONDS:
            _TASK_CACHE.pop((instance_id, session_id), None)
            return None
        return dict(payload)


def clear_task_cache() -> None:
    with _TASK_CACHE_LOCK:
        _TASK_CACHE.clear()


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

def generate_agent_token() -> str:
    """Generate a high-entropy token for the DSH -> codx-junior channel."""
    return secrets.token_urlsafe(32)


def token_file_path(project_root: Optional[str]) -> Optional[str]:
    if not project_root:
        return None
    return os.path.join(project_root, ".dsh-codx-junior", AGENT_TOKEN_FILE)


def write_agent_token_file(project_root: Optional[str], token: str) -> Optional[str]:
    """Write ``<project>/.dsh-codx-junior/token`` with owner-only permissions."""
    path = token_file_path(project_root)
    if not path:
        return None
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(f"{token}\n")
        os.chmod(path, 0o600)
        return path
    except OSError:
        return None


def read_agent_token_file(project_root: Optional[str]) -> Optional[str]:
    path = token_file_path(project_root)
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = handle.read().strip()
        return value or None
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Instance / command model
# ---------------------------------------------------------------------------

def _now() -> float:
    return time.time()


def _iso(timestamp: Optional[float]) -> Optional[str]:
    return datetime.fromtimestamp(timestamp).isoformat() if timestamp else None


@dataclass
class DshInstance:
    """One running DSH Host registered with this codx-junior project."""

    id: str
    project_id: Optional[str]
    codx_path: Optional[str]
    name: str
    cwd: Optional[str] = None
    version: str = ""
    capabilities: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    registered_at: float = field(default_factory=_now)
    last_seen: float = field(default_factory=_now)
    status: str = "online"
    running: int = 0
    sessions: int = 0
    queue_depth: int = 0
    uptime_seconds: Optional[float] = None

    def online(self, now: Optional[float] = None) -> bool:
        return (now or _now()) - self.last_seen <= ONLINE_WINDOW_SECONDS

    def to_dict(self) -> Dict[str, Any]:
        online = self.online()
        return {
            "id": self.id,
            "name": self.name,
            "project_id": self.project_id,
            "codx_path": self.codx_path,
            "cwd": self.cwd,
            "version": self.version,
            "capabilities": list(self.capabilities),
            "status": "online" if online else "offline",
            "last_seen": _iso(self.last_seen),
            "last_seen_epoch": self.last_seen,
            "registered_at": _iso(self.registered_at),
            "running": self.running,
            "sessions": self.sessions,
            "queue_depth": self.queue_depth,
            "uptime_seconds": self.uptime_seconds,
            "meta": dict(self.meta),
        }


@dataclass
class DshCommand:
    """One command waiting for (or completed by) a DSH instance."""

    id: str
    instance_id: str
    type: str
    payload: Dict[str, Any]
    created_at: float = field(default_factory=_now)
    event: threading.Event = field(default_factory=threading.Event)
    result: Any = None
    error: Optional[str] = None
    completed_at: Optional[float] = None
    timed_out: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "payload": self.payload,
            "created_at": _iso(self.created_at),
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class DshAgentRegistry:
    """Thread-safe registry of DSH instances and their command channels."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._instances: Dict[str, DshInstance] = {}
        self._queues: Dict[str, "queue.Queue[DshCommand]"] = {}
        self._commands: Dict[str, DshCommand] = {}
        self._commands_by_instance: Dict[str, List[str]] = {}

    # -- lifecycle ---------------------------------------------------------

    def register(
        self,
        project_id: Optional[str],
        codx_path: Optional[str],
        payload: Mapping[str, Any],
    ) -> DshInstance:
        """Create or refresh the registration of one DSH Host."""
        with self._lock:
            instance_id = str(payload.get("instance_id") or uuid.uuid4())
            existing = self._instances.get(instance_id)
            if existing is not None and existing.project_id and project_id and existing.project_id != project_id:
                raise DshAgentError(
                    f"instance {instance_id} is already registered to another project"
                )
            name = str(
                payload.get("name")
                or (existing.name if existing else "")
                or f"DSH {instance_id[-8:]}"
            )
            now = _now()
            if existing is None:
                instance = DshInstance(
                    id=instance_id,
                    project_id=project_id,
                    codx_path=codx_path,
                    name=name,
                    cwd=payload.get("cwd") or None,
                    version=str(payload.get("version") or ""),
                    capabilities=list(payload.get("capabilities") or []),
                    meta=dict(payload.get("meta") or {}),
                    registered_at=now,
                    last_seen=now,
                )
                self._instances[instance_id] = instance
                self._queues[instance_id] = queue.Queue()
                self._commands_by_instance.setdefault(instance_id, [])
            else:
                instance = existing
                instance.last_seen = now
                instance.status = "online"
                instance.project_id = instance.project_id or project_id
                instance.codx_path = codx_path or instance.codx_path
                instance.name = name
                instance.cwd = payload.get("cwd") or instance.cwd
                if payload.get("version"):
                    instance.version = str(payload.get("version"))
                if payload.get("capabilities") is not None:
                    instance.capabilities = list(payload.get("capabilities") or [])
                if payload.get("meta") is not None:
                    instance.meta = dict(payload.get("meta") or {})
                self._queues.setdefault(instance_id, queue.Queue())
            return instance

    def unregister(self, instance_id: str, project_id: Optional[str] = None) -> bool:
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance is None:
                return False
            if project_id and instance.project_id and instance.project_id != project_id:
                return False
            instance.status = "offline"
            instance.last_seen = 0
            self._queues.pop(instance_id, None)
            return True

    def heartbeat(
        self,
        instance_id: str,
        project_id: Optional[str],
        payload: Mapping[str, Any],
    ) -> Optional[DshInstance]:
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance is None:
                return None
            if project_id and instance.project_id and instance.project_id != project_id:
                return None
            instance.last_seen = _now()
            instance.status = "online"
            instance.running = int(payload.get("running") or 0)
            instance.sessions = int(payload.get("sessions") or 0)
            instance.queue_depth = int(payload.get("queue_depth") or 0)
            uptime = payload.get("uptime_seconds")
            instance.uptime_seconds = float(uptime) if uptime is not None else instance.uptime_seconds
            if payload.get("version"):
                instance.version = str(payload.get("version"))
            return instance

    # -- reads -------------------------------------------------------------

    def get(self, instance_id: str) -> Optional[DshInstance]:
        with self._lock:
            return self._instances.get(instance_id)

    def list_instances(self, project_id: Optional[str] = None) -> List[DshInstance]:
        with self._lock:
            values = list(self._instances.values())
        if project_id:
            values = [item for item in values if item.project_id == project_id]
        return sorted(values, key=lambda item: (not item.online(), -item.last_seen))

    def default_instance(
        self,
        project_id: Optional[str],
        preferred_id: Optional[str] = None,
    ) -> Optional[DshInstance]:
        preferred = None
        if preferred_id:
            candidate = self.get(preferred_id)
            if candidate is not None and (not project_id or candidate.project_id == project_id):
                preferred = candidate
                if candidate.online():
                    return candidate
        instances = self.list_instances(project_id)
        for instance in instances:
            if instance.online():
                return instance
        return preferred or (instances[0] if instances else None)

    # -- command queue -----------------------------------------------------

    def enqueue(
        self,
        instance_id: str,
        command_type: str,
        payload: Mapping[str, Any],
        timeout: float = DEFAULT_COMMAND_TIMEOUT,
    ) -> Any:
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance is None:
                raise DshInstanceOffline(f"DSH instance {instance_id} is not registered")
            if not instance.online():
                raise DshInstanceOffline(
                    f"DSH instance {instance.name or instance_id} is offline"
                )
            command_queue = self._queues.get(instance_id)
            if command_queue is None:
                command_queue = queue.Queue()
                self._queues[instance_id] = command_queue
            command = DshCommand(
                id=str(uuid.uuid4()),
                instance_id=instance_id,
                type=command_type,
                payload=dict(payload),
            )
            self._commands[command.id] = command
            self._commands_by_instance.setdefault(instance_id, []).append(command.id)
            self._prune_locked(instance_id)
        command_queue.put(command)
        if not command.event.wait(timeout):
            command.timed_out = True
            raise DshCommandTimeout(
                f"DSH {instance.name or instance_id} did not answer '{command_type}' "
                f"within {timeout:.0f}s"
            )
        if command.error:
            raise DshCommandFailed(command.error)
        return command.result

    def take_commands(
        self,
        instance_id: str,
        wait_seconds: float = DEFAULT_POLL_WAIT_SECONDS,
        limit: int = MAX_COMMANDS_PER_POLL,
    ) -> List[DshCommand]:
        """Block until one command is available, then drain up to ``limit``."""
        with self._lock:
            if instance_id not in self._instances:
                return []
            command_queue = self._queues.get(instance_id)
            if command_queue is None:
                command_queue = queue.Queue()
                self._queues[instance_id] = command_queue
        wait = max(0.0, min(float(wait_seconds), MAX_POLL_WAIT_SECONDS))
        commands: List[DshCommand] = []
        try:
            commands.append(command_queue.get(timeout=wait))
        except queue.Empty:
            return []
        while len(commands) < max(1, min(int(limit), MAX_COMMANDS_PER_POLL)):
            try:
                commands.append(command_queue.get_nowait())
            except queue.Empty:
                break
        return commands

    def complete(
        self,
        command_id: str,
        instance_id: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> bool:
        with self._lock:
            command = self._commands.get(command_id)
            if command is None or command.instance_id != instance_id:
                return False
            if command.event.is_set():
                return False
            command.result = result
            command.error = error
            command.completed_at = _now()
            command.event.set()
            return True

    def pending_count(self, instance_id: Optional[str] = None) -> int:
        with self._lock:
            if instance_id:
                return len(
                    [
                        command_id
                        for command_id in self._commands_by_instance.get(instance_id, [])
                        if command_id in self._commands and not self._commands[command_id].event.is_set()
                    ]
                )
            return len([command for command in self._commands.values() if not command.event.is_set()])

    def _prune_locked(self, instance_id: str) -> None:
        ids = self._commands_by_instance.get(instance_id, [])
        keep: List[str] = []
        now = _now()
        for command_id in ids:
            command = self._commands.get(command_id)
            if command is None:
                continue
            if command.event.is_set() and command.completed_at and now - command.completed_at > 300:
                self._commands.pop(command_id, None)
                continue
            keep.append(command_id)
        self._commands_by_instance[instance_id] = keep[-500:]

    def reset(self) -> None:
        """Test helper: drop every instance, queue and waiter."""
        with self._lock:
            self._instances.clear()
            self._queues.clear()
            self._commands.clear()
            self._commands_by_instance.clear()
        clear_task_cache()


_REGISTRY = DshAgentRegistry()


def get_dsh_agent_registry() -> DshAgentRegistry:
    return _REGISTRY


class DshAgentClient:
    """The client shape used by :class:`DshSync`, backed by the command queue."""

    def __init__(
        self,
        registry: DshAgentRegistry,
        instance_id: str,
        timeout: float = DEFAULT_COMMAND_TIMEOUT,
    ) -> None:
        self.registry = registry
        self.instance_id = instance_id
        self.timeout = timeout

    def for_instance(self, instance_id: str) -> "DshAgentClient":
        return DshAgentClient(self.registry, instance_id, timeout=self.timeout)

    def instance(self) -> Optional[DshInstance]:
        return self.registry.get(self.instance_id)

    def health(self) -> Dict[str, Any]:
        instance = self.instance()
        if instance is None:
            raise DshInstanceOffline(f"DSH instance {self.instance_id} is not registered")
        return instance.to_dict()

    def _command(self, command_type: str, payload: Mapping[str, Any], timeout: Optional[float] = None) -> Any:
        return self.registry.enqueue(
            self.instance_id,
            command_type,
            payload,
            timeout=self.timeout if timeout is None else timeout,
        )

    def list_tasks(
        self,
        cwd: Optional[str] = None,
        include_blank: bool = False,
        limit: int = 500,
    ) -> List[DshTask]:
        result = self._command(
            "list_tasks",
            {"cwd": cwd, "include_blank": include_blank, "limit": limit},
        )
        return [DshTask.from_payload(item) for item in (result or {}).get("tasks", [])]

    def get_task(self, session_id: str) -> Dict[str, Any]:
        try:
            result = self._command("get_task", {"session_id": session_id})
            if isinstance(result, Mapping):
                cache_task_view(self.instance_id, session_id, result)
                return dict(result)
            raise DshAgentError("DSH returned an invalid get_task result")
        except DshError:
            cached = cached_task_view(self.instance_id, session_id)
            if cached is not None:
                return cached
            raise

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
        payload: Dict[str, Any] = {
            "title": title,
            "prompt": prompt,
            "cwd": cwd,
            "agent_preset": agent_preset,
            "codx_task_id": codx_task_id,
        }
        if model:
            payload["model"] = dict(model)
        if workspace_root:
            payload["workspace_root"] = workspace_root
        result = self._command(
            "create_task",
            payload,
            timeout=max(self.timeout, 45),
        )
        return result if isinstance(result, Mapping) else {"task": result}

    def prompt(self, session_id: str, text: str, mode: str = "queue") -> Dict[str, Any]:
        return self._command(
            "prompt",
            {"session_id": session_id, "text": text, "mode": mode},
            timeout=max(self.timeout, 30),
        )

    def cancel(self, session_id: str) -> Dict[str, Any]:
        return self._command("cancel", {"session_id": session_id}, timeout=max(self.timeout, 15))

    def rename(self, session_id: str, title: str) -> Dict[str, Any]:
        return self._command(
            "rename",
            {"session_id": session_id, "title": title},
            timeout=max(self.timeout, 20),
        )
