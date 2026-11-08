"""
File persistence for companies.

Storage layout (one folder per company, mirroring ``.codx`` projects)::

    <companies_root>/<company_id>/company.json   # the Company document
    <companies_root>/<company_id>/journal.jsonl  # append-only event journal

Why one folder per company
--------------------------
* The id (not the name) is the folder name, so renaming a company never moves
  files or breaks references.
* Deleting a company is deleting one folder: there are no orphan rows.
* The journal is append-only and line-delimited, so a crash cannot corrupt the
  events already written and a human can read the history with ``tail``.

Concurrency
-----------
Writes are atomic (temp file + ``os.replace``) and each company has a file lock
(``fcntl.flock`` on POSIX, a process-local lock elsewhere). The autopilot and
the API therefore cannot interleave a read-modify-write on the same document.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading

from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from .models import Company, CompanyEvent, new_id, now_iso

logger = logging.getLogger(__name__)

COMPANY_FILE = "company.json"
JOURNAL_FILE = "journal.jsonl"

#: Environment variable that overrides the companies root (tests, containers).
COMPANIES_PATH_ENV = "CODX_JUNIOR_COMPANIES_PATH"

#: Default root, next to the other global codx-junior data folders.
DEFAULT_COMPANIES_PATH = "/home/codx-junior/companies"

#: Maximum number of journal entries kept in memory when a caller asks for all.
MAX_JOURNAL_ENTRIES = 5000

try:  # POSIX file locks; fall back to thread locks on other platforms.
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX
    fcntl = None  # type: ignore[assignment]


class CompanyStoreError(RuntimeError):
    """Raised when a company document cannot be read or written."""


class CompanyNotFound(CompanyStoreError):
    """The requested company id does not exist."""


def get_companies_root() -> str:
    """
    Resolve the root folder of every company.

    Resolution order: ``CODX_JUNIOR_COMPANIES_PATH``, the
    ``codx.junior.globals`` override when available, then
    :data:`DEFAULT_COMPANIES_PATH`.

    Returns:
        Absolute path of the companies root.
    """
    configured = os.environ.get(COMPANIES_PATH_ENV)
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    try:
        from codx.junior.globals import CODX_JUNIOR_COMPANIES_PATH

        if CODX_JUNIOR_COMPANIES_PATH:
            return os.path.abspath(os.path.expanduser(CODX_JUNIOR_COMPANIES_PATH))
    except Exception:  # pragma: no cover - import guard
        pass
    return DEFAULT_COMPANIES_PATH


def _atomic_write(path: str, content: str) -> None:
    """
    Write *content* to *path* atomically.

    A crash either leaves the previous file untouched or the complete new one,
    never a half-written JSON document.

    Args:
        path: Destination path.
        content: Full file content.

    Raises:
        OSError: If the file cannot be written.
    """
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".company-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


class CompanyStore:
    """
    Read/write companies and their journals.

    Args:
        root_path: Companies root. Defaults to :func:`get_companies_root`.
    """

    def __init__(self, root_path: Optional[str] = None):
        self.root_path = os.path.abspath(
            os.path.expanduser(root_path or get_companies_root())
        )
        self._locks: Dict[str, threading.RLock] = {}
        self._locks_guard = threading.Lock()

    # -- paths -------------------------------------------------------------

    def company_dir(self, company_id: str) -> str:
        """
        Return the folder of a company.

        The id is validated before touching the filesystem: an id containing a
        path separator could escape the root.

        Args:
            company_id: Company id.

        Returns:
            Absolute folder path.

        Raises:
            ValueError: If the id is empty, ``.``/``..`` or contains a separator.
        """
        company_id = (company_id or "").strip()
        if (
            not company_id
            or company_id in (".", "..")
            or "/" in company_id
            or "\\" in company_id
        ):
            raise ValueError(f"invalid company id: {company_id!r}")
        return os.path.join(self.root_path, company_id)

    def company_path(self, company_id: str) -> str:
        """Return the path of the ``company.json`` document."""
        return os.path.join(self.company_dir(company_id), COMPANY_FILE)

    def journal_path(self, company_id: str) -> str:
        """Return the path of the append-only journal."""
        return os.path.join(self.company_dir(company_id), JOURNAL_FILE)

    # -- existence / listing ----------------------------------------------

    def exists(self, company_id: str) -> bool:
        """Tell whether a company document exists."""
        try:
            return os.path.isfile(self.company_path(company_id))
        except ValueError:
            return False

    def list_ids(self) -> List[str]:
        """
        List every company id stored under the root.

        Returns:
            Company ids sorted by folder modification time (newest first), then
            name for a stable order.
        """
        if not os.path.isdir(self.root_path):
            return []
        entries: List[tuple] = []
        for name in os.listdir(self.root_path):
            if not os.path.isfile(os.path.join(self.root_path, name, COMPANY_FILE)):
                continue
            try:
                mtime = os.path.getmtime(os.path.join(self.root_path, name))
            except OSError:
                mtime = 0.0
            entries.append((mtime, name))
        entries.sort(key=lambda entry: (-entry[0], entry[1]))
        return [name for _, name in entries]

    # -- reads / writes ----------------------------------------------------

    def load(self, company_id: str) -> Company:
        """
        Load one company.

        Args:
            company_id: Company id.

        Returns:
            The validated company.

        Raises:
            CompanyNotFound: If the document does not exist.
            CompanyStoreError: If the document is unreadable or invalid.
        """
        path = self.company_path(company_id)
        if not os.path.isfile(path):
            raise CompanyNotFound(f"Company '{company_id}' not found")
        try:
            with open(path, "r", encoding="utf-8") as company_file:
                payload = json.load(company_file)
            return Company(**payload)
        except CompanyNotFound:
            raise
        except Exception as ex:
            raise CompanyStoreError(
                f"Company '{company_id}' could not be loaded: {ex}"
            ) from ex

    def save(self, company: Company) -> Company:
        """
        Persist a company atomically.

        Args:
            company: Company to persist (its ``updated_at`` is refreshed).

        Returns:
            The persisted company.

        Raises:
            CompanyStoreError: If the document cannot be written.
        """
        if not company.id:
            company.id = new_id("company")
        company.updated_at = now_iso()
        path = self.company_path(company.id)
        payload = company.model_dump()
        try:
            _atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False))
        except OSError as ex:
            raise CompanyStoreError(
                f"Company '{company.id}' could not be saved: {ex}"
            ) from ex
        return company

    def delete(self, company_id: str) -> None:
        """
        Delete a company folder (document + journal).

        Args:
            company_id: Company id.

        Raises:
            CompanyNotFound: If the company does not exist.
        """
        folder = self.company_dir(company_id)
        if not os.path.isdir(folder):
            raise CompanyNotFound(f"Company '{company_id}' not found")
        shutil.rmtree(folder)
        logger.info("Company deleted: %s", company_id)

    # -- journal -----------------------------------------------------------

    def append_event(self, company_id: str, event: CompanyEvent) -> CompanyEvent:
        """
        Append one event to the company journal.

        Journal failures never break the business operation: an audit line is
        important, but losing it must not roll back a mission dispatch.

        Args:
            company_id: Company id.
            event: Event to append.

        Returns:
            The event (with id/timestamp filled when missing).
        """
        if not event.id:
            event.id = new_id("event")
        if not event.at:
            event.at = now_iso()
        try:
            line = json.dumps(event.model_dump(), ensure_ascii=False)
            with open(self.journal_path(company_id), "a", encoding="utf-8") as journal:
                journal.write(line + "\n")
                journal.flush()
        except OSError as ex:  # pragma: no cover - defensive
            logger.warning(
                "Company journal append failed for '%s': %s", company_id, ex
            )
        return event

    def read_events(self, company_id: str, limit: int = 100) -> List[CompanyEvent]:
        """
        Read the most recent journal events, newest last.

        Args:
            company_id: Company id.
            limit: Maximum number of entries returned.

        Returns:
            Parsed events; malformed lines are skipped instead of hiding the
            rest of the journal.
        """
        path = self.journal_path(company_id)
        if not os.path.isfile(path):
            return []
        events: List[CompanyEvent] = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as journal:
                for line in journal:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(CompanyEvent(**json.loads(line)))
                    except Exception:
                        logger.debug("Skipping malformed company journal line")
        except OSError as ex:
            logger.warning("Company journal read failed for '%s': %s", company_id, ex)
            return []
        if limit and len(events) > limit:
            events = events[-limit:]
        return events

    # -- locking -----------------------------------------------------------

    def _thread_lock(self, company_id: str) -> threading.RLock:
        """Return the process-local lock of a company."""
        with self._locks_guard:
            if company_id not in self._locks:
                self._locks[company_id] = threading.RLock()
            return self._locks[company_id]

    @contextmanager
    def lock(self, company_id: str) -> Iterator[None]:
        """
        Serialize a read-modify-write on one company.

        Uses ``fcntl.flock`` so two processes (API + autopilot) cannot interleave
        updates; falls back to a thread lock when ``fcntl`` is unavailable.

        Args:
            company_id: Company id.

        Yields:
            Nothing; the lock is held while the context is active.
        """
        thread_lock = self._thread_lock(company_id)
        with thread_lock:
            if fcntl is None:
                yield
                return
            lock_path = os.path.join(self.company_dir(company_id), ".lock")
            os.makedirs(os.path.dirname(lock_path), exist_ok=True)
            handle = open(lock_path, "a+", encoding="utf-8")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                yield
            finally:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                finally:
                    handle.close()

    # -- helpers -----------------------------------------------------------

    def snapshot_paths(self) -> List[str]:
        """Return every existing company document path (diagnostics/tests)."""
        return [self.company_path(company_id) for company_id in self.list_ids()]

    def event(self, **kwargs: Any) -> CompanyEvent:
        """Build an event (small convenience used by the manager)."""
        return CompanyEvent(**kwargs)


# Made with ❤️ by codx-junior
