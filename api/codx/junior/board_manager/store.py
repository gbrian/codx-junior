"""
Runtime persistence of the board manager.

Two files live under ``<codx_path>/board_manager``:

* ``state.json`` — one record per board (last run, actions, report, cost). It is
  written atomically while holding a project-level ``fcntl`` lock, so the API
  process (status/read, wake) and the background worker (write) never lose each
  other's update.
* ``worker.json`` — heartbeat of the background worker, used by the UI to say
  whether automatic reviews can run.

The board **configuration** is not stored here: it lives on the board document
(``tasks/boards/<id>/board.json``) and is written by the normal board settings
flow. Keeping the two apart is what makes a review independent from a catalogue
save.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterator, Optional

try:  # POSIX only; the container always has it.
    import fcntl
except ImportError:  # pragma: no cover - non POSIX fallback
    fcntl = None

from . import constants as C
from .models import ManagerState, utcnow_iso

logger = logging.getLogger(__name__)

STATE_VERSION = 1


def _board_lock_name(board_key: str) -> str:
    """Return a filesystem-safe lock file name for *board_key*."""
    digest = hashlib.sha1(str(board_key or "").encode("utf-8")).hexdigest()[:16]
    return f"{digest}.lock"


class BoardManagerStore:
    """
    Persistence of the board manager runtime state.

    Args:
        codx_path: Absolute ``<project>/.codx`` folder.
    """

    def __init__(self, codx_path: str) -> None:
        self.codx_path = str(codx_path or "")
        self.base_path = os.path.join(self.codx_path, C.BOARD_MANAGER_DIR)
        self.state_path = os.path.join(self.base_path, C.STATE_FILE)
        self.worker_path = os.path.join(self.base_path, C.WORKER_FILE)
        self.lock_path = os.path.join(self.base_path, C.LOCK_FILE)
        self.locks_path = os.path.join(self.base_path, C.LOCKS_DIR)
        self._thread_lock = threading.RLock()

    # -- low level --------------------------------------------------------

    @staticmethod
    def _read_json(path: str) -> Optional[dict]:
        """Read a JSON object, returning None when missing/unreadable."""
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.loads(handle.read())
            return data if isinstance(data, dict) else None
        except (OSError, ValueError) as ex:
            logger.warning("board manager: cannot read '%s': %s", path, ex)
            return None

    @staticmethod
    def _write_json(path: str, data: dict) -> None:
        """Write *data* atomically (tmp + replace)."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, indent=2))
        os.replace(tmp_path, path)

    @contextmanager
    def locked(self) -> Iterator[None]:
        """Hold the project-level state lock (cross process)."""
        os.makedirs(self.base_path, exist_ok=True)
        handle = open(self.lock_path, "a+", encoding="utf-8")
        try:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            with self._thread_lock:
                yield
        finally:
            try:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()

    @contextmanager
    def run_lock(self, board_key: str) -> Iterator[bool]:
        """
        Try to acquire the exclusive lock of one board review.

        Yields True when the lock was acquired and False when another process /
        thread is already reviewing the board. The lock is non blocking so two
        workers never execute the same board twice.
        """
        os.makedirs(self.locks_path, exist_ok=True)
        lock_path = os.path.join(self.locks_path, _board_lock_name(board_key))
        handle = open(lock_path, "a+", encoding="utf-8")
        acquired = True
        try:
            if fcntl is not None:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    acquired = False
            yield acquired
        finally:
            if acquired and fcntl is not None:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
            handle.close()

    # -- state ------------------------------------------------------------

    def _load_unlocked(self) -> Dict[str, Any]:
        """Read the raw state document (caller holds the lock)."""
        data = self._read_json(self.state_path) or {}
        boards = data.get("boards")
        if not isinstance(boards, dict):
            boards = {}
        return {"version": data.get("version") or STATE_VERSION, "boards": boards}

    def load(self) -> Dict[str, Any]:
        """Return ``{"version", "boards": {board_key: state_dict}}``."""
        with self.locked():
            return self._load_unlocked()

    def save(self, data: Dict[str, Any]) -> None:
        """Persist the whole state document under the lock."""
        with self.locked():
            self._write_json(self.state_path, data)

    def get_state(self, board_key: str) -> ManagerState:
        """Return the persisted state of *board_key* (empty when unknown)."""
        data = self.load()
        raw = data["boards"].get(str(board_key)) or {}
        try:
            return ManagerState(**raw)
        except (TypeError, ValueError) as ex:
            logger.warning("board manager: invalid state for '%s': %s", board_key, ex)
            return ManagerState(board_id=str(board_key))

    def put_state(self, board_key: str, state: ManagerState) -> ManagerState:
        """Persist one board state without losing other boards."""
        key = str(board_key)
        with self.locked():
            data = self._load_unlocked()
            data["boards"][key] = state.model_dump()
            self._write_json(self.state_path, data)
        return state

    def mutate_state(
        self,
        board_key: str,
        callback: Callable[[ManagerState], ManagerState],
    ) -> ManagerState:
        """
        Read-modify-write one board state under the state lock.

        The callback receives the current state and returns the state to save.
        """
        key = str(board_key)
        with self.locked():
            data = self._load_unlocked()
            try:
                current = ManagerState(**(data["boards"].get(key) or {}))
            except (TypeError, ValueError):
                current = ManagerState(board_id=key)
            updated = callback(current)
            data["boards"][key] = updated.model_dump()
            self._write_json(self.state_path, data)
        return updated

    def request_wake(self, board_key: str, board: str = "") -> ManagerState:
        """Mark the board as "review as soon as possible" (manual Run now)."""
        def _wake(state: ManagerState) -> ManagerState:
            state.board_id = str(board_key)
            if board:
                state.board = board
            state.wake_requested = True
            return state

        return self.mutate_state(board_key, _wake)

    # -- worker heartbeat -------------------------------------------------

    def write_worker_heartbeat(self, payload: Optional[Dict[str, Any]] = None) -> None:
        """Publish the background worker heartbeat (best effort)."""
        data = {
            "pid": os.getpid(),
            "at": utcnow_iso(),
            **(payload or {}),
        }
        try:
            self._write_json(self.worker_path, data)
        except OSError as ex:  # pragma: no cover - read-only filesystem
            logger.debug("board manager: cannot write worker heartbeat: %s", ex)

    @staticmethod
    def _parse_iso(value: Any) -> Optional[datetime]:
        """Parse an ISO instant into an aware datetime."""
        try:
            parsed = datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def worker_present(self, ttl_seconds: int = C.WORKER_TTL_SECONDS) -> bool:
        """Return True when a background worker heartbeat is recent enough."""
        data = self._read_json(self.worker_path) or {}
        at = self._parse_iso(data.get("at"))
        if at is None:
            return False
        age = (datetime.now(tz=timezone.utc) - at).total_seconds()
        return 0 <= age <= max(1, int(ttl_seconds))

# Made with ❤️ by codx-junior
