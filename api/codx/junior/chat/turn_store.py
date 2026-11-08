"""
Durable chat-turn records.

A chat **turn** is the unit that produces one assistant response
(``ChatEngine.chat_with_project``). The engine already persists the response
message incrementally (``ChatEventBridge``), but the *intent to run* lived only
in process memory: after an application restart (or a crash) the turn was gone
and its response message stayed forever at *"Processing request, please wait..."*
with no way for the client to stop it.

This module stores that intent on disk — one small JSON file per turn — and
guards it with an exclusive ``flock``:

* :meth:`ChatTurnStore.begin` records a turn before the AI call and holds the
  lock while it runs,
* :meth:`ChatTurnStore.complete` / ``fail`` / ``cancel`` remove the record and
  release the lock,
* :meth:`ChatTurnStore.list_active` is what the recovery worker
  (``turn_recovery.py``) scans after a restart: a record whose lock is free
  belongs to a dead process and is resumed,
* :func:`repair_incomplete_messages` turns orphaned ``done=False`` assistant
  messages into a terminal state, so clients stop rendering "processing".

The record is deliberately small: the conversation itself is already persisted
by ``ChatManager``. Only the identifiers needed to reload it survive here.

Storage layout::

    <codx_path>/chat_turns/<turn_id>.json
    <codx_path>/chat_turns/<turn_id>.lock
    <codx_path>/chat_turns/<turn_id>.cancel
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import socket
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Directory below ``settings.codx_path`` (which is already ``<project>/.codx``).
TURN_DIRNAME = "chat_turns"

# Turn lifecycle.
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

ACTIVE_STATUSES = frozenset({STATUS_QUEUED, STATUS_RUNNING})

# A restart may be caused by a real crash loop. The turn is retried a bounded
# number of times, then marked failed and the response message is repaired so
# the client never sees an endless "processing" state.
ENV_MAX_ATTEMPTS = "CODX_JUNIOR_CHAT_TURN_MAX_ATTEMPTS"
DEFAULT_MAX_ATTEMPTS = 3

# Note appended to an interrupted response message. The message is hidden from
# the prompt history (it is not a real assistant answer), but keeping the note
# helps forensic inspection of the chat file.
INTERRUPTED_NOTE = (
    "\n\n*(This response was interrupted by an application restart. "
    "The turn is being resumed automatically.)*"
)
FAILED_NOTE = (
    "\n\n*(This response was interrupted and could not be resumed. "
    "You can stop it or send a new message to continue.)*"
)


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _normalize_codx_path(codx_path: Any) -> str:
    """
    Return a stable absolute key for a project ``.codx`` path.

    The same project can be addressed through a query-string relative path and
    through settings; both must share one store instance (and therefore one set
    of lock file descriptors).
    """
    raw = str(codx_path or "").strip()
    return os.path.abspath(raw) if raw else ""


def _env_int(name: str, default: int) -> int:
    """Read a positive integer environment setting with a safe fallback."""
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return default


def _hostname() -> str:
    """Return the hostname (best effort; used only for diagnostics)."""
    try:
        return socket.gethostname()
    except OSError:  # pragma: no cover - defensive
        return ""


def _atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
    """
    Write *payload* as JSON atomically (temp file + ``os.replace``).

    Args:
        path: Destination file.
        payload: JSON-serialisable dict.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


class ChatTurnRecord(BaseModel):
    """Persisted intent to run one chat turn."""

    turn_id: str = Field(description="Unique turn identifier (also the file name).")
    chat_id: str = Field(description="Chat id of the turn (`Chat.id`).")
    codx_path: str = Field(description="Project `.codx` path that owns the chat.")
    owner_project_id: Optional[str] = Field(default=None, description="Project that owns the chat.")
    username: Optional[str] = Field(default=None, description="User that started the turn.")
    user: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Serialized CodxUser, used to rebuild the session after a restart.",
    )
    disable_knowledge: bool = Field(default=False, description="Turn option to replay.")
    append_references: bool = Field(default=True, description="Turn option to replay.")
    chat_mode: Optional[str] = Field(default=None, description="Turn mode override to replay.")
    system: Optional[str] = Field(default=None, description="Extra system prompt to replay.")
    status: str = Field(default=STATUS_QUEUED, description="queued | running | completed | failed | cancelled")
    attempts: int = Field(default=0, description="How many times the turn was started.")
    max_attempts: int = Field(default=DEFAULT_MAX_ATTEMPTS, description="Retry bound for restarts.")
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)
    started_at: Optional[str] = Field(default=None)
    finished_at: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)
    pid: int = Field(default=0, description="Owning process id (diagnostics only).")
    host: str = Field(default_factory=_hostname, description="Owning host (diagnostics only).")
    meta_data: Dict[str, Any] = Field(default_factory=dict, description="Free-form diagnostics.")


class ChatTurnStore:
    """
    File-backed store of active chat turns for one project.

    One instance per project path is shared inside the process (see
    :func:`get_turn_store`): the lock file descriptors must belong to the same
    instance so :meth:`release` can unlock exactly what :meth:`claim` locked.
    """

    def __init__(self, codx_path: str) -> None:
        """
        Args:
            codx_path: Project ``.codx`` path.
        """
        self.codx_path = _normalize_codx_path(codx_path)
        self.directory = os.path.join(self.codx_path, TURN_DIRNAME)
        self._locks: Dict[str, int] = {}
        self._locks_lock = threading.Lock()

    # -- paths ------------------------------------------------------------

    def turn_path(self, turn_id: str) -> str:
        """Return the JSON path of *turn_id*."""
        return os.path.join(self.directory, f"{turn_id}.json")

    def lock_path(self, turn_id: str) -> str:
        """Return the lock-file path of *turn_id*."""
        return os.path.join(self.directory, f"{turn_id}.lock")

    def cancel_path(self, turn_id: str) -> str:
        """Return the cancellation-marker path of *turn_id*."""
        return os.path.join(self.directory, f"{turn_id}.cancel")

    # -- persistence ------------------------------------------------------

    def save(self, record: ChatTurnRecord) -> ChatTurnRecord:
        """
        Persist *record* atomically.

        Args:
            record: The record to write (``updated_at`` is refreshed).

        Returns:
            The same record.
        """
        record.updated_at = _now()
        _atomic_write_json(self.turn_path(record.turn_id), record.model_dump())
        return record

    def load(self, turn_id: str) -> Optional[ChatTurnRecord]:
        """Load *turn_id*, returning ``None`` when it does not exist."""
        path = self.turn_path(turn_id)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return ChatTurnRecord(**json.load(f))
        except (OSError, ValueError) as ex:
            logger.warning("ChatTurnStore: cannot read turn '%s': %s", turn_id, ex)
            return None

    def list_active(self) -> List[ChatTurnRecord]:
        """Return every queued/running record, oldest first."""
        if not os.path.isdir(self.directory):
            return []
        records: List[ChatTurnRecord] = []
        for name in os.listdir(self.directory):
            if not name.endswith(".json"):
                continue
            record = self.load(name[:-5])
            if record is not None and record.status in ACTIVE_STATUSES:
                records.append(record)
        records.sort(key=lambda item: item.created_at)
        return records

    def find_active(self, chat_id: str) -> List[ChatTurnRecord]:
        """Return the active turn(s) of *chat_id*."""
        return [record for record in self.list_active() if record.chat_id == chat_id]

    # -- locking ----------------------------------------------------------

    def claim(self, record: ChatTurnRecord) -> bool:
        """
        Try to take exclusive ownership of *record*.

        The lock is an ``flock`` on ``<turn_id>.lock``: it is released by the
        OS when the process dies, which is exactly how the recovery worker
        distinguishes a live turn from an orphan.

        Args:
            record: The record to claim.

        Returns:
            True when this process now owns the turn.
        """
        with self._locks_lock:
            if record.turn_id in self._locks:
                return True
            os.makedirs(self.directory, exist_ok=True)
            try:
                fd = os.open(self.lock_path(record.turn_id), os.O_CREAT | os.O_RDWR, 0o644)
            except OSError as ex:
                logger.warning(
                    "ChatTurnStore: cannot open lock for turn '%s': %s",
                    record.turn_id,
                    ex,
                )
                return False
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                # Another live process (or a live turn of this process) owns it.
                os.close(fd)
                return False
            self._locks[record.turn_id] = fd
            return True

    def release(self, turn_id: str) -> None:
        """Release the process-local lock of *turn_id* (idempotent)."""
        with self._locks_lock:
            fd = self._locks.pop(turn_id, None)
        if fd is None:
            return
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:  # pragma: no cover - defensive
            pass
        try:
            os.close(fd)
        except OSError:  # pragma: no cover - defensive
            pass

    def is_owned(self, turn_id: str) -> bool:
        """Return True when this store instance owns the turn lock."""
        with self._locks_lock:
            return turn_id in self._locks

    def live_turn_ids(self) -> List[str]:
        """
        Return the active turn ids owned by a live process.

        A lock that can be taken (and immediately released) belongs to a dead
        process: that turn is an orphan and may be repaired/recovered. A lock
        that is held belongs to a live turn and must not be touched (e.g. a
        concurrent turn of the same chat).

        Returns:
            Turn ids whose lock is currently held somewhere.
        """
        live: List[str] = []
        for record in self.list_active():
            if self.is_owned(record.turn_id):
                live.append(record.turn_id)
                continue
            if self.claim(record):
                # Free lock: orphan. Release the probe immediately.
                self.release(record.turn_id)
            else:
                live.append(record.turn_id)
        return live

    # -- lifecycle --------------------------------------------------------

    def begin(
        self,
        chat: Any,
        *,
        user: Any = None,
        max_attempts: Optional[int] = None,
    ) -> Optional[ChatTurnRecord]:
        """
        Persist the intent to run *chat* and take ownership of the turn.

        Args:
            chat: The ``Chat`` about to be processed (must have an ``id``).
            user: User that started the turn (serialized for recovery).
            max_attempts: Override the retry bound.

        Returns:
            The new record, or ``None`` when the chat has no id / locking failed
            (the turn then runs exactly as before, without durability).
        """
        chat_id = str(getattr(chat, "id", "") or "")
        if not chat_id:
            logger.warning(
                "ChatTurnStore: chat has no id, the turn cannot be persisted "
                "for recovery"
            )
            return None

        # Any older orphan turn for this chat is superseded by this new one.
        for stale in self.find_active(chat_id=chat_id):
            if self.is_owned(stale.turn_id):
                logger.warning(
                    "ChatTurnStore: chat '%s' already has a live turn '%s'",
                    chat_id,
                    stale.turn_id,
                )
                continue
            if self.claim(stale):
                self.finalize(stale, STATUS_CANCELLED, error="Superseded by a newer turn")

        user_payload = None
        if hasattr(user, "model_dump"):
            try:
                user_payload = dict(user.model_dump())
                # Never persist credentials in a project file: recovery
                # resolves the user from global settings by username.
                user_payload.pop("api_key", None)
                user_payload.pop("token", None)
            except Exception:  # pragma: no cover - defensive
                user_payload = None

        record = ChatTurnRecord(
            turn_id=str(uuid.uuid4()),
            chat_id=chat_id,
            codx_path=self.codx_path,
            owner_project_id=getattr(chat, "owner_project_id", None),
            username=getattr(user, "username", None),
            user=user_payload,
            status=STATUS_QUEUED,
            max_attempts=max_attempts or _env_int(ENV_MAX_ATTEMPTS, DEFAULT_MAX_ATTEMPTS),
            pid=os.getpid(),
            host=_hostname(),
        )
        if not self.claim(record):
            logger.warning(
                "ChatTurnStore: could not lock new turn '%s'; running without "
                "durable recovery",
                record.turn_id,
            )
            return None
        try:
            self.save(record)
        except OSError as ex:
            logger.warning(
                "ChatTurnStore: cannot persist turn '%s': %s",
                record.turn_id,
                ex,
            )
            self.release(record.turn_id)
            return None
        logger.info(
            "ChatTurnStore: turn '%s' began for chat '%s' (attempt %d/%d)",
            record.turn_id,
            chat_id,
            record.attempts,
            record.max_attempts,
        )
        return record

    def mark_running(
        self,
        record: ChatTurnRecord,
        *,
        attempts: Optional[int] = None,
    ) -> ChatTurnRecord:
        """
        Mark *record* running (used by the engine and by recovery).

        Args:
            record: The record to update.
            attempts: Optional attempt override (recovery increments it).

        Returns:
            The persisted record.
        """
        record.status = STATUS_RUNNING
        if attempts is not None:
            record.attempts = int(attempts)
        record.started_at = record.started_at or _now()
        record.pid = os.getpid()
        record.host = _hostname()
        record.error = None
        try:
            self.save(record)
        except OSError as ex:  # pragma: no cover - defensive
            logger.warning(
                "ChatTurnStore: cannot persist running turn '%s': %s",
                record.turn_id,
                ex,
            )
        return record

    def complete(self, record: ChatTurnRecord) -> None:
        """Finish *record* successfully and release its lock."""
        self.finalize(record, STATUS_COMPLETED)

    def fail(self, record: ChatTurnRecord, error: Any) -> None:
        """Finish *record* as failed and release its lock."""
        self.finalize(record, STATUS_FAILED, error=str(error or "unknown error"))

    def cancel(self, record: ChatTurnRecord, reason: str = "cancelled") -> None:
        """Finish *record* as cancelled and release its lock."""
        self.finalize(record, STATUS_CANCELLED, error=reason)

    def finalize(
        self,
        record: ChatTurnRecord,
        status: str,
        *,
        error: Optional[str] = None,
    ) -> None:
        """
        Persist the terminal status of *record*, remove its files and unlock it.

        Args:
            record: The record to finish.
            status: Terminal status.
            error: Optional reason.
        """
        record.status = status
        record.error = error
        record.finished_at = _now()
        record.updated_at = record.finished_at
        try:
            _atomic_write_json(self.turn_path(record.turn_id), record.model_dump())
        except OSError as ex:  # pragma: no cover - defensive
            logger.warning(
                "ChatTurnStore: cannot persist terminal turn '%s': %s",
                record.turn_id,
                ex,
            )
        self.release(record.turn_id)
        # A terminal record has no recovery value: remove it (and its marker)
        # so a growing directory never looks like pending work.
        for path in (self.turn_path(record.turn_id), self.cancel_path(record.turn_id)):
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:  # pragma: no cover - defensive
                pass
        logger.info(
            "ChatTurnStore: turn '%s' finished as '%s' for chat '%s'",
            record.turn_id,
            status,
            record.chat_id,
        )

    # -- cancellation -----------------------------------------------------

    def request_cancel(self, turn_id: str) -> None:
        """
        Leave a durable cancellation marker for *turn_id*.

        Used when the in-memory owner is in another process: the marker makes
        sure a recovery does not restart a turn the user stopped, even if the
        owner dies before observing the cancellation token.
        """
        try:
            os.makedirs(self.directory, exist_ok=True)
            with open(self.cancel_path(turn_id), "w", encoding="utf-8") as f:
                f.write(_now())
        except OSError as ex:  # pragma: no cover - defensive
            logger.warning(
                "ChatTurnStore: cannot write cancel marker for '%s': %s",
                turn_id,
                ex,
            )

    def cancel_requested(self, turn_id: str) -> bool:
        """Return True when a durable cancellation marker exists."""
        return os.path.isfile(self.cancel_path(turn_id))

    def clear_cancel(self, turn_id: str) -> None:
        """Remove the cancellation marker of *turn_id* (idempotent)."""
        try:
            if os.path.isfile(self.cancel_path(turn_id)):
                os.remove(self.cancel_path(turn_id))
        except OSError:  # pragma: no cover - defensive
            pass

    def cancel_chat(self, chat_id: str, reason: str = "Stopped by user") -> int:
        """
        Stop every active turn of *chat_id*, including orphaned ones.

        A turn whose lock is free is finalized immediately (and its response
        message repaired by the caller). A live turn receives a durable cancel
        marker so it is never resumed, while the caller is expected to also
        cancel the in-flight ``CancellationToken``.

        Args:
            chat_id: Chat whose turns to stop.
            reason: Reason recorded on the terminal state.

        Returns:
            Number of turns that were found and marked.
        """
        stopped = 0
        for record in self.find_active(chat_id=chat_id):
            self.request_cancel(record.turn_id)
            if self.is_owned(record.turn_id):
                # The in-flight turn will observe the cancellation token and
                # finalize itself; releasing its lock here would let a recovery
                # worker start a second runner for the same turn.
                stopped += 1
                continue
            if self.claim(record):
                self.finalize(record, STATUS_CANCELLED, error=reason)
            stopped += 1
        return stopped


# ---------------------------------------------------------------------------
# Process-wide store registry
# ---------------------------------------------------------------------------
_STORES: Dict[str, ChatTurnStore] = {}
_STORES_LOCK = threading.Lock()


def get_turn_store(codx_path: str) -> ChatTurnStore:
    """
    Return the shared :class:`ChatTurnStore` for *codx_path*.

    A single instance per path is required so a lock taken by the engine can be
    released by the recovery worker (and vice versa) inside the same process.

    Args:
        codx_path: Project ``.codx`` path.

    Returns:
        The process-wide store for the project.
    """
    key = _normalize_codx_path(codx_path)
    with _STORES_LOCK:
        store = _STORES.get(key)
        if store is None:
            store = ChatTurnStore(key)
            _STORES[key] = store
        return store


class TurnCancellationWatcher:
    """
    Poll the durable cancel marker of a running turn and cancel its local token.

    A stop request may arrive in a *different* process than the one running the
    turn (e.g. the turn was resumed by the background worker and the user
    presses stop in the API process). The ``CancellationToken`` registry is
    process-local, so the owning process needs to observe the file marker and
    cancel its own token.

    Args:
        store: Store that owns the turn.
        turn_id: Turn to watch.
        token: The local cancellation token (``chat.cancellation.CancellationToken``
            or any object with ``cancel()``).
        interval_seconds: Poll interval.
    """

    def __init__(
        self,
        store: ChatTurnStore,
        turn_id: str,
        token: Any,
        interval_seconds: float = 1.0,
    ) -> None:
        self.store = store
        self.turn_id = turn_id
        self.token = token
        self.interval_seconds = max(0.2, float(interval_seconds or 1.0))
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> "TurnCancellationWatcher":
        """Start the watcher thread (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name=f"turn-cancel-{self.turn_id[:8]}",
            daemon=True,
        )
        self._thread.start()
        return self

    def stop(self) -> None:
        """Stop the watcher thread."""
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                if self.store.cancel_requested(self.turn_id):
                    logger.info(
                        "ChatTurnStore: durable cancel requested for turn '%s'; "
                        "cancelling the local token",
                        self.turn_id,
                    )
                    self.token.cancel()
                    return
            except Exception:  # pragma: no cover - defensive
                logger.exception(
                    "ChatTurnStore: error watching cancellation of turn '%s'",
                    self.turn_id,
                )
                return


def repair_incomplete_messages(
    chat: Any,
    chat_manager: Any,
    *,
    note: str = INTERRUPTED_NOTE,
    error: Optional[str] = None,
    hide: bool = True,
    skip_turn_ids: Optional[Any] = None,
) -> int:
    """
    Turn orphaned ``done=False`` assistant messages into a terminal state.

    These messages are the *"Processing request, please wait..."* placeholders
    persisted before the AI call. After a restart they would otherwise keep the
    client forever in the processing state and, worse, be rendered into the next
    prompt as a completed assistant answer.

    Args:
        chat: The chat to repair.
        chat_manager: Manager used to persist the repaired messages.
        note: Text appended to the interrupted message.
        error: Error recorded on the message (defaults to *note*).
        hide: Hide the message from the prompt/UI history (recommended).
        skip_turn_ids: Turn ids of LIVE turns; their in-flight messages must not
            be touched (e.g. a concurrent turn of the same chat).

    Returns:
        Number of messages repaired.
    """
    if chat is None:
        return 0

    skip = set(skip_turn_ids or ())
    repaired = 0
    for message in list(getattr(chat, "messages", []) or []):
        if getattr(message, "role", "") != "assistant":
            continue
        if getattr(message, "done", True) is not False:
            continue
        message_turn_id = str(
            (getattr(message, "meta_data", None) or {}).get("turn_id") or ""
        )
        if message_turn_id and message_turn_id in skip:
            continue

        content = str(getattr(message, "content", "") or "")
        if note and note.strip() not in content:
            content = (content.rstrip() + note) if content.strip() else note.strip()
        elif not note and "processing request" in content.lower():
            # Replace the placeholder with a terminal note: the client may not
            # filter ``hide`` locally, and "processing" must never survive.
            content = f"*({error or 'The turn was interrupted'})*"
        message.content = content
        message.done = True
        message.error = message.error or error or "The turn was interrupted"
        message.meta_data = {
            **(getattr(message, "meta_data", None) or {}),
            "interrupted": True,
            "interrupted_at": _now(),
        }
        message.hide = bool(hide)

        try:
            update = getattr(chat_manager, "update_message", None)
            if callable(update):
                update(chat=chat, message=message)
            else:  # pragma: no cover - defensive fallback
                chat_manager.save_chat(chat=chat)
            repaired += 1
        except Exception as ex:  # pragma: no cover - defensive
            logger.warning(
                "ChatTurnStore: could not persist repaired message '%s': %s",
                getattr(message, "doc_id", ""),
                ex,
            )
    if repaired:
        logger.info(
            "ChatTurnStore: repaired %d interrupted response message(s) of "
            "chat '%s'",
            repaired,
            getattr(chat, "id", ""),
        )
    return repaired
