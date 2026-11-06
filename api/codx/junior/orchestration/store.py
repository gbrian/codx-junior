"""
Crash-safe persistence and single-flight locking for orchestration runs.

Layout under the project::

    .codx/orchestration/
      runs/<run_id>.json          # the run document (source of truth)
      runs/<run_id>.lock          # flock target for the worker
      worker.json                 # background-worker heartbeat

Every write is atomic (``tmp`` + ``os.replace``) so a crash can never leave a
half-written run. The worker holds an exclusive ``flock`` for the whole tick, so
the API process and the background process — or two background workers after a
misconfiguration — can never advance the same run twice. The OS releases the
lock when a process dies; a stale lock cannot wedge a run.

This module only depends on the standard library and :mod:`models`, so it is
safe to import from tools, the API and the worker.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import glob
import json
import logging
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from . import constants as C
from .models import (
    RunCorrupt,
    RunLocked,
    RunNotFound,
    RunState,
    utcnow_iso,
)

logger = logging.getLogger(__name__)

try:  # pragma: no cover - platform dependent
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - non POSIX
    fcntl = None  # type: ignore

# A worker heartbeat older than this is reported as offline by the API.
DEFAULT_WORKER_TTL_SECONDS = 45.0


class RunLock:
    """
    Exclusive lock over one run document.

    The file is created on first use and kept open for the lifetime of the lock.
    ``release`` unlocks and closes it. The object is a context manager.
    """

    def __init__(self, path: str, timeout: float = 0.0) -> None:
        self.path = path
        self.timeout = max(0.0, float(timeout))
        self._handle: Optional[Any] = None
        self._acquired = False

    def acquire(self) -> "RunLock":
        """Acquire the lock or raise :class:`RunLocked`."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        handle = open(self.path, "a+", encoding="utf-8")
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                if fcntl is None:  # pragma: no cover - non POSIX
                    # Without flock we cannot guarantee cross-process exclusion.
                    # The process-local worker still avoids double ticks.
                    break
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (BlockingIOError, OSError) as ex:
                if time.monotonic() >= deadline:
                    handle.close()
                    raise RunLocked(f"Run is already being processed ({self.path})") from ex
                time.sleep(0.05)
        self._handle = handle
        self._acquired = True
        self.touch()
        return self

    def touch(self) -> None:
        """Refresh the lock file mtime (diagnostics / stale-lock observation)."""
        if self._handle is None:
            return
        try:
            self._handle.seek(0)
            self._handle.truncate()
            self._handle.write(json.dumps({
                "pid": os.getpid(),
                "acquired_at": utcnow_iso(),
            }))
            self._handle.flush()
        except OSError as ex:  # pragma: no cover - defensive
            logger.warning("Could not write run lock heartbeat '%s': %s", self.path, ex)

    def release(self) -> None:
        """Release the lock (idempotent)."""
        if not self._acquired:
            return
        self._acquired = False
        handle = self._handle
        self._handle = None
        if handle is None:
            return
        try:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError as ex:  # pragma: no cover - defensive
            logger.warning("Could not unlock run lock '%s': %s", self.path, ex)
        finally:
            try:
                handle.close()
            except OSError:  # pragma: no cover - defensive
                pass

    def __enter__(self) -> "RunLock":
        return self.acquire()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()


class RunStore:
    """Filesystem-backed store of run documents."""

    def __init__(self, codx_path: str) -> None:
        """
        Args:
            codx_path: Project ``.codx`` folder (``CODXJuniorSettings.codx_path``).
        """
        if not codx_path:
            raise ValueError("RunStore requires the project's codx_path")
        self.codx_path = os.path.abspath(codx_path)
        self.root_dir = os.path.join(self.codx_path, C.ORCHESTRATION_DIR)
        self.runs_dir = os.path.join(self.root_dir, C.RUNS_DIR)
        os.makedirs(self.runs_dir, exist_ok=True)

    # -- paths -----------------------------------------------------------

    def run_path(self, run_id: str) -> str:
        """Return the JSON path of *run_id* (validated: basename only)."""
        safe_id = os.path.basename(str(run_id or "").strip())
        if not safe_id or safe_id in {".", ".."}:
            raise ValueError(f"Invalid run id '{run_id}'")
        return os.path.join(self.runs_dir, f"{safe_id}.json")

    def lock_path(self, run_id: str) -> str:
        """Return the lock path of *run_id*."""
        return self.run_path(run_id).replace(".json", ".lock")

    def worker_path(self) -> str:
        """Return the worker heartbeat path."""
        return os.path.join(self.root_dir, C.WORKER_FILE)

    # -- read / write ----------------------------------------------------

    def exists(self, run_id: str) -> bool:
        """Return True when the run document exists."""
        return os.path.isfile(self.run_path(run_id))

    def load(self, run_id: str) -> RunState:
        """
        Load one run.

        Raises:
            RunNotFound: When the document does not exist.
            RunCorrupt: When it cannot be parsed/validated.
        """
        path = self.run_path(run_id)
        if not os.path.isfile(path):
            raise RunNotFound(f"Run '{run_id}' does not exist")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            run = RunState(**data)
            # The filename is canonical: a copied/renamed document must not be
            # able to overwrite another run on the next save.
            run.run_id = os.path.basename(path)[:-5]
            return run
        except (OSError, ValueError, TypeError) as ex:
            raise RunCorrupt(f"Run '{run_id}' cannot be read: {ex}") from ex

    def save(self, run: RunState) -> RunState:
        """
        Atomically persist *run* and return it.

        The write goes to a temporary file in the same directory and is moved
        into place with ``os.replace``; readers never observe a half document.
        """
        run.touch()
        path = self.run_path(run.run_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = json.dumps(run.model_dump(), indent=2, default=str)
        safe_id = os.path.basename(run.run_id)
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=os.path.dirname(path),
            prefix=f".{safe_id}.",
            suffix=".tmp",
            delete=False,
        )
        temp_path = handle.name
        try:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
            os.replace(temp_path, path)
        finally:
            try:
                if not handle.closed:
                    handle.close()
            except OSError:  # pragma: no cover - defensive
                pass
            if os.path.isfile(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:  # pragma: no cover - defensive
                    pass
        return run

    def delete(self, run_id: str) -> None:
        """Remove a run document and its lock file (best effort)."""
        for path in (self.run_path(run_id), self.lock_path(run_id)):
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError as ex:  # pragma: no cover - defensive
                logger.warning("Could not remove run file '%s': %s", path, ex)

    def list_runs(self, status: Optional[str] = None) -> List[RunState]:
        """
        Return every readable run, newest first.

        Corrupt documents are logged and skipped: one broken run must never stop
        the worker from processing the others.

        Args:
            status: Optional status filter.
        """
        runs: List[RunState] = []
        pattern = os.path.join(self.runs_dir, "*.json")
        for path in glob.glob(pattern):
            run_id = os.path.basename(path)[:-5]
            try:
                run = self.load(run_id)
            except (RunNotFound, RunCorrupt) as ex:
                logger.error("Skipping unreadable orchestration run '%s': %s", path, ex)
                continue
            if status and run.status != status:
                continue
            runs.append(run)
        runs.sort(key=lambda item: item.created_at, reverse=True)
        return runs

    def active_run_ids(self) -> List[str]:
        """Return the ids of runs that still need the worker."""
        return [
            run.run_id
            for run in self.list_runs()
            if run.status in C.ACTIVE_RUN_STATUSES
            or run.wake_requested
        ]

    # -- locking ---------------------------------------------------------

    def lock(self, run_id: str, timeout: float = 0.0) -> RunLock:
        """Return a :class:`RunLock` for *run_id* (not acquired yet)."""
        return RunLock(self.lock_path(run_id), timeout=timeout)

    @contextmanager
    def locked(self, run_id: str, timeout: float = 0.0) -> Iterator[RunLock]:
        """Acquire the run lock for the duration of the context."""
        lock = self.lock(run_id, timeout=timeout)
        lock.acquire()
        try:
            yield lock
        finally:
            lock.release()

    # -- worker heartbeat ------------------------------------------------

    def write_worker_heartbeat(self, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Atomically write the background-worker heartbeat.

        The API process reads it to answer "worker_present" in the run detail,
        so a run is not reported as progressing when no worker is running.
        """
        payload = {
            "pid": os.getpid(),
            "updated_at": utcnow_iso(),
            "epoch": time.time(),
            **(data or {}),
        }
        path = self.worker_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=os.path.dirname(path),
            prefix=".worker.",
            suffix=".tmp",
            delete=False,
        )
        temp_path = handle.name
        try:
            json.dump(payload, handle)
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
            os.replace(temp_path, path)
        finally:
            try:
                if not handle.closed:
                    handle.close()
            except OSError:  # pragma: no cover - defensive
                pass
            if os.path.isfile(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:  # pragma: no cover - defensive
                    pass

    def worker_status(self, ttl_seconds: float = DEFAULT_WORKER_TTL_SECONDS) -> Dict[str, Any]:
        """
        Return the worker presence for this project.

        Returns:
            ``{"present": bool, "pid": ..., "updated_at": ..., "age_seconds": ...}``
        """
        path = self.worker_path()
        if not os.path.isfile(path):
            return {"present": False, "pid": None, "updated_at": None, "age_seconds": None}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError) as ex:
            logger.warning("Could not read worker heartbeat '%s': %s", path, ex)
            return {"present": False, "pid": None, "updated_at": None, "age_seconds": None}
        epoch = data.get("epoch")
        age: Optional[float] = None
        if isinstance(epoch, (int, float)):
            age = max(0.0, time.time() - float(epoch))
        elif data.get("updated_at"):
            try:
                updated = datetime.fromisoformat(str(data["updated_at"]).replace("Z", "+00:00"))
                age = max(0.0, (datetime.now(tz=timezone.utc) - updated).total_seconds())
            except ValueError:
                age = None
        present = age is not None and age <= float(ttl_seconds)
        return {
            "present": present,
            "pid": data.get("pid"),
            "updated_at": data.get("updated_at"),
            "age_seconds": round(age, 2) if age is not None else None,
        }

# Made with ❤️ by codx-junior
