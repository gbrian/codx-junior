"""
Debounced, background wiki updates.

Editing a project produces a stream of file changes. Regenerating documentation
for every single save would keep the wiki perpetually refreshing (and burn AI
tokens while the developer is still working). This scheduler collects changes
per project and only runs once the project has been quiet for a configurable
period (default 60s), with a hard cap (default 10 min) so a long editing session
still gets documentation updates.

Only the changed files are regenerated. The docs-site manifest is rebuilt once
per batch, so the site navigation and the AI assistant get fresh content
without a full wiki rebuild.

```mermaid
flowchart LR
    E[File change] --> Q[Queue file per project]
    Q --> D{Project quiet for debounce?}
    D -- no --> Q
    D -- yes --> U[Update changed pages]
    U --> M[Rebuild docs manifest]
    M --> P[Refresh parent site]
```
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

logger = logging.getLogger(__name__)

DEFAULT_DEBOUNCE_SECONDS = 60
DEFAULT_MAX_DELAY_SECONDS = 600
STATUS_FILE_NAME = "update_status.json"

_WORKER_INTERVAL_SECONDS = 1.0
_MAX_WORKERS = 2


def _project_key(settings: Any) -> str:
    """Stable scheduler key for a project."""
    return str(
        getattr(settings, "project_id", None)
        or getattr(settings, "codx_path", None)
        or getattr(settings, "project_name", "unknown")
    )


def _as_int(value: Any, default: int) -> int:
    try:
        number = int(value)
        return number if number >= 0 else default
    except (TypeError, ValueError):
        return default


def _status_path(settings: Any) -> str:
    return os.path.join(settings.get_project_wiki_path(), STATUS_FILE_NAME)


def _write_status(settings: Any, status: Dict[str, Any]) -> None:
    """Persist the scheduler status so the API process can read it."""
    try:
        path = _status_path(settings)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(status, handle, indent=2)
        os.replace(tmp, path)
    except OSError as ex:  # pragma: no cover - best effort only
        logger.debug("Cannot persist wiki update status: %s", ex)


def read_update_status(settings: Any) -> Dict[str, Any]:
    """Read the persisted update status for a project (API-process safe)."""
    try:
        with open(_status_path(settings), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


@dataclass
class PendingUpdate:
    """One project's queued wiki work."""

    settings: Any
    files: Set[str] = field(default_factory=set)
    first_scheduled_at: float = field(default_factory=time.time)
    last_change_at: float = field(default_factory=time.time)
    due_at: float = field(default_factory=time.time)
    reason: str = "change"
    site_only: bool = False
    processing: bool = False

    @property
    def key(self) -> str:
        return _project_key(self.settings)

    def add_files(self, files: Iterable[str]) -> None:
        self.files.update(str(file) for file in files if file)

    def to_status(self) -> Dict[str, Any]:
        return {
            "project": getattr(self.settings, "project_name", ""),
            "pending": True,
            "files": sorted(self.files),
            "file_count": len(self.files),
            "reason": self.reason,
            "site_only": self.site_only,
            "first_scheduled_at": int(self.first_scheduled_at),
            "last_change_at": int(self.last_change_at),
            "next_run_at": int(self.due_at),
            "processing": self.processing,
        }


class WikiUpdateScheduler:
    """
    Process-wide debounced wiki updater.

    The scheduler keeps one worker thread that polls queued projects. Heavy work
    (AI page generation) runs in a small thread pool so one slow project does not
    block the queue for the others.
    """

    def __init__(
        self,
        processor: Optional[Callable[[Any, List[str], str], None]] = None,
        site_refresher: Optional[Callable[[Any], None]] = None,
        notify_parent: bool = True,
    ) -> None:
        self._lock = threading.RLock()
        self._pending: Dict[str, PendingUpdate] = {}
        self._running: Set[str] = set()
        self._last_runs: Dict[str, Dict[str, Any]] = {}
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._executor = ThreadPoolExecutor(
            max_workers=_MAX_WORKERS,
            thread_name_prefix="WikiUpdate",
        )
        self._processor = processor
        self._site_refresher = site_refresher
        self._notify_parent_projects = notify_parent

    # ── lifecycle ───────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the polling thread (idempotent)."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._loop,
                name="WikiUpdateScheduler",
                daemon=True,
            )
            self._thread.start()
            logger.info("Wiki update scheduler started")

    def is_running(self) -> bool:
        """Return whether this process has a live scheduler thread."""
        return bool(self._thread and self._thread.is_alive())

    def stop(self) -> None:
        """Stop the polling thread and wait for in-flight work to drain."""
        self._stop_event.set()
        thread = self._thread
        if thread:
            thread.join(timeout=5)
        self._executor.shutdown(wait=False, cancel_futures=False)
        logger.info("Wiki update scheduler stopped")

    # ── queueing ────────────────────────────────────────────────────────────

    def schedule(
        self,
        settings: Any,
        files: Optional[Iterable[str]] = None,
        reason: str = "change",
        debounce_seconds: Optional[int] = None,
        max_delay_seconds: Optional[int] = None,
        site_only: bool = False,
    ) -> bool:
        """
        Queue a debounced update for a project.

        Args:
            settings: Project settings.
            files: Changed source files. Empty means "refresh the site manifest only".
            reason: Short reason recorded in status/logs.
            debounce_seconds: Override the project debounce.
            max_delay_seconds: Override the project hard cap.
            site_only: Do not regenerate pages, only the manifest.

        Returns:
            True when the update was queued, False when wiki updates are off.
        """
        files = [str(file) for file in (files or []) if file]
        site_only = site_only or not files
        if not site_only and not _wiki_updates_enabled(settings):
            return False
        if site_only and not getattr(settings, "project_wiki", False):
            return False

        debounce = _as_int(
            debounce_seconds if debounce_seconds is not None else getattr(
                settings, "wiki_update_debounce_seconds", DEFAULT_DEBOUNCE_SECONDS
            ),
            DEFAULT_DEBOUNCE_SECONDS,
        )
        max_delay = _as_int(
            max_delay_seconds if max_delay_seconds is not None else getattr(
                settings, "wiki_update_max_delay_seconds", DEFAULT_MAX_DELAY_SECONDS
            ),
            DEFAULT_MAX_DELAY_SECONDS,
        )
        now = time.time()
        self.start()
        with self._lock:
            key = _project_key(settings)
            pending = self._pending.get(key)
            if pending is None:
                pending = PendingUpdate(
                    settings=settings,
                    first_scheduled_at=now,
                    last_change_at=now,
                    reason=reason,
                    site_only=site_only,
                )
                self._pending[key] = pending
            pending.add_files(files)
            pending.last_change_at = now
            pending.reason = reason
            pending.site_only = pending.site_only and site_only
            pending.due_at = min(
                pending.first_scheduled_at + max_delay,
                now + debounce,
            )
            status = pending.to_status()
            status.update(self._last_runs.get(key, {}))
            status["pending"] = True
            _write_status(settings, status)
            logger.debug(
                "Wiki update queued for %s (%d file(s), due in %ds)",
                settings.project_name,
                len(pending.files),
                max(0, pending.due_at - now),
            )
            return True

    def status(self, settings: Any) -> Dict[str, Any]:
        """Return queued/running/last-run information for a project."""
        key = _project_key(settings)
        with self._lock:
            pending = self._pending.get(key)
            status = dict(self._last_runs.get(key, {}))
            if pending and not pending.processing:
                status.update(pending.to_status())
            status["running"] = key in self._running or bool(
                pending and pending.processing
            )
            status["debounce_seconds"] = _as_int(
                getattr(settings, "wiki_update_debounce_seconds", DEFAULT_DEBOUNCE_SECONDS),
                DEFAULT_DEBOUNCE_SECONDS,
            )
            status["max_delay_seconds"] = _as_int(
                getattr(settings, "wiki_update_max_delay_seconds", DEFAULT_MAX_DELAY_SECONDS),
                DEFAULT_MAX_DELAY_SECONDS,
            )
            status["auto_update"] = bool(getattr(settings, "wiki_auto_update", True))
        persisted = read_update_status(settings)
        for field_name, value in persisted.items():
            status.setdefault(field_name, value)
        return status

    def flush(self, settings: Any) -> None:
        """Process a project immediately (used by explicit refresh buttons)."""
        key = _project_key(settings)
        with self._lock:
            pending = self._pending.pop(key, None)
        if pending:
            self._run_pending(pending)
        else:
            self.schedule(settings, files=[], reason="refresh", debounce_seconds=0, site_only=True)
            with self._lock:
                pending = self._pending.pop(key, None)
            if pending:
                self._run_pending(pending)

    # ── worker ──────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._dispatch_due()
            except Exception as ex:  # pragma: no cover - defensive
                logger.exception("Wiki update scheduler loop error: %s", ex)
            self._stop_event.wait(_WORKER_INTERVAL_SECONDS)

    def _dispatch_due(self) -> None:
        now = time.time()
        due: List[PendingUpdate] = []
        with self._lock:
            for key, pending in list(self._pending.items()):
                if pending.processing:
                    continue
                if pending.due_at > now:
                    continue
                # Remove it before work starts: a change arriving while the
                # batch runs creates a fresh pending entry for the next pass
                # instead of being discarded when this batch finishes.
                self._pending.pop(key, None)
                pending.processing = True
                self._running.add(key)
                due.append(pending)
        for pending in due:
            self._executor.submit(self._run_pending, pending)

    def _run_pending(self, pending: PendingUpdate) -> None:
        key = pending.key
        started = time.time()
        try:
            self._process(pending)
            self._last_runs[key] = {
                "pending": False,
                "last_run_at": int(started),
                "last_success_at": int(time.time()),
                "last_duration_seconds": round(time.time() - started, 2),
                "last_files": sorted(pending.files),
                "last_reason": pending.reason,
                "last_error": "",
            }
            _write_status(pending.settings, self._last_runs[key])
        except Exception as ex:
            logger.exception(
                "Wiki update failed for %s: %s",
                getattr(pending.settings, "project_name", key),
                ex,
            )
            self._last_runs[key] = {
                "pending": False,
                "last_run_at": int(started),
                "last_success_at": self._last_runs.get(key, {}).get("last_success_at"),
                "last_duration_seconds": round(time.time() - started, 2),
                "last_files": sorted(pending.files),
                "last_reason": pending.reason,
                "last_error": str(ex),
            }
            _write_status(pending.settings, self._last_runs[key])
        finally:
            with self._lock:
                self._running.discard(key)
                pending.processing = False

    def _process(self, pending: PendingUpdate) -> None:
        if pending.site_only or not pending.files:
            self._refresh_site(pending.settings)
        elif self._processor:
            self._processor(pending.settings, sorted(pending.files), pending.reason)
        else:
            from codx.junior.wiki.wiki_manager import WikiManager

            WikiManager(settings=pending.settings).update_files(
                files=sorted(pending.files),
                reason=pending.reason,
            )
        if self._notify_parent_projects:
            self._notify_parent(pending.settings)

    def _refresh_site(self, settings: Any) -> None:
        if self._site_refresher:
            self._site_refresher(settings)
            return
        from codx.junior.wiki.site import WikiSiteBuilder

        WikiSiteBuilder(settings=settings).build()

    def _notify_parent(self, settings: Any) -> None:
        """Refresh the parent wiki manifest so child cards stay current."""
        try:
            from codx.junior.project.project_discover import (
                find_all_projects,
                is_path_child_of,
            )

            parents = [
                project
                for project in find_all_projects().values()
                if project.project_id != settings.project_id
                and is_path_child_of(settings.abs_project_path, project.abs_project_path)
            ]
            if not parents:
                return
            parent = max(parents, key=lambda project: len(project.abs_project_path))
            self.schedule(
                parent,
                files=[],
                reason="child-update",
                debounce_seconds=5,
                site_only=True,
            )
        except Exception as ex:  # pragma: no cover - discovery is optional
            logger.debug("Cannot refresh parent wiki manifest: %s", ex)

    # ── status helpers ──────────────────────────────────────────────────────

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)


def _wiki_updates_enabled(settings: Any) -> bool:
    """Return whether automatic wiki updates are enabled for a project."""
    return bool(getattr(settings, "project_wiki", False)) and bool(
        getattr(settings, "wiki_auto_update", True)
    )


_SCHEDULER: Optional[WikiUpdateScheduler] = None
_SCHEDULER_LOCK = threading.Lock()


def get_wiki_scheduler() -> WikiUpdateScheduler:
    """Return the process-wide scheduler singleton."""
    global _SCHEDULER
    if _SCHEDULER is None:
        with _SCHEDULER_LOCK:
            if _SCHEDULER is None:
                _SCHEDULER = WikiUpdateScheduler()
    return _SCHEDULER


def start_wiki_scheduler() -> WikiUpdateScheduler:
    """Start the singleton scheduler (called by background services)."""
    scheduler = get_wiki_scheduler()
    scheduler.start()
    return scheduler


def stop_wiki_scheduler() -> None:
    """Stop the singleton scheduler on application shutdown."""
    if _SCHEDULER is not None:
        _SCHEDULER.stop()


def schedule_wiki_update(
    settings: Any,
    files: Optional[Iterable[str]] = None,
    reason: str = "change",
    **kwargs: Any,
) -> bool:
    """Convenience wrapper used by the change manager and API endpoints."""
    return get_wiki_scheduler().schedule(settings, files=files, reason=reason, **kwargs)
