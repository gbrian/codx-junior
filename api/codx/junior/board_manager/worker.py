"""
Background worker of the board manager.

The API process never runs a review inline: it reads state and writes the "run
now" intent. This thread — started from :mod:`codx.junior.background` — discovers
the projects, finds the boards whose manager is enabled and due, and runs one
review at a time per project.

A review is protected by a per-board ``flock`` (see
:meth:`BoardManagerStore.run_lock`), so even if two workers end up alive (API and
background process, or a restart overlap) the same board is never reviewed twice
at the same time.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from . import constants as C

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment switch."""
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off", ""}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    """Read an integer environment setting with a safe fallback and clamp."""
    value = os.environ.get(name)
    try:
        number = int(str(value)) if value is not None and str(value).strip() else default
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))


def board_manager_enabled() -> bool:
    """Return True when the board manager worker may run."""
    return _env_bool(C.ENV_ENABLED, True)


def _project_has_enabled_manager(settings: Any) -> bool:
    """Return True when at least one board of *settings* enables the manager."""
    try:
        from .models import BoardManagerConfig

        from codx.junior.chat_manager import ChatManager

        manager = ChatManager(settings=settings)
        kanban = manager.load_kanban() or {}
        boards = kanban.get("boards") if isinstance(kanban, dict) else {}
        if not isinstance(boards, dict):
            return False
        return any(
            BoardManagerConfig.from_board(board).enabled
            for board in boards.values()
            if isinstance(board, dict)
        )
    except Exception as ex:
        logger.debug("board manager: cannot inspect project: %s", ex)
        return False


class BoardManagerWorker:
    """Thread that reviews the due boards of every project."""

    def __init__(
        self,
        *,
        tick_seconds: Optional[int] = None,
        max_projects: Optional[int] = None,
        stop_event: Any = None,
    ) -> None:
        self.tick_seconds = max(
            5,
            min(
                int(tick_seconds if tick_seconds is not None else
                    _env_int(C.ENV_TICK_SECONDS, C.DEFAULT_TICK_SECONDS, 5, C.MAX_TICK_SECONDS)),
                C.MAX_TICK_SECONDS,
            ),
        )
        self.max_projects = max(
            1,
            min(
                int(max_projects if max_projects is not None else
                    _env_int(C.ENV_MAX_BOARDS, 2, 1, 8)),
                8,
            ),
        )
        self.stop_event = stop_event
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._pool: Optional[ThreadPoolExecutor] = None

    # -- lifecycle --------------------------------------------------------

    def start(self) -> "BoardManagerWorker":
        """Start the loop (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._pool = ThreadPoolExecutor(
            max_workers=self.max_projects,
            thread_name_prefix="BoardManager",
        )
        self._thread = threading.Thread(
            target=self._loop,
            name="BoardManagerWorker",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Board manager worker started (tick=%ss, max_projects=%d)",
            self.tick_seconds,
            self.max_projects,
        )
        return self

    def stop(self) -> None:
        """Stop the loop and its pool."""
        self._stop.set()
        pool = self._pool
        self._pool = None
        if pool is not None:
            pool.shutdown(wait=False, cancel_futures=True)
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        logger.info("Board manager worker stopped")

    @property
    def running(self) -> bool:
        """Return True while the loop thread is alive."""
        return bool(self._thread is not None and self._thread.is_alive())

    # -- loop -------------------------------------------------------------

    def _stopped(self) -> bool:
        """Return True when the loop must stop."""
        if self.stop_event is not None and getattr(self.stop_event, "is_set", lambda: False)():
            return True
        return self._stop.is_set()

    def _loop(self) -> None:
        """Loop body: run one pass, wait, repeat."""
        while not self._stopped():
            try:
                self.run_once()
            except Exception as ex:  # pragma: no cover - never kill the loop
                logger.exception("Board manager tick failed: %s", ex)
            self._stop.wait(self.tick_seconds)

    def run_once(self) -> List[Dict[str, Any]]:
        """
        Run one pass over every project with an enabled board manager.

        Returns:
            The review results (one dict per reviewed board).
        """
        from codx.junior.project.project_discover import find_all_projects

        projects = list(find_all_projects().values())
        eligible = [p for p in projects if _project_has_enabled_manager(p)]
        if not eligible:
            return []

        pool = self._pool
        if pool is None:
            pool = ThreadPoolExecutor(
                max_workers=self.max_projects,
                thread_name_prefix="BoardManagerOnce",
            )
            owns_pool = True
        else:
            owns_pool = False

        results: List[Dict[str, Any]] = []
        try:
            futures = [pool.submit(self._process_project, project) for project in eligible]
            for future in futures:
                try:
                    results.extend(future.result() or [])
                except Exception as ex:  # pragma: no cover - defensive
                    logger.exception("Board manager project pass failed: %s", ex)
        finally:
            if owns_pool:
                pool.shutdown(wait=True, cancel_futures=False)
        return results

    @staticmethod
    def _process_project(settings: Any) -> List[Dict[str, Any]]:
        """Review the due boards of one project in their own event loop."""
        from .service import BoardManagerService
        from .store import BoardManagerStore

        store = BoardManagerStore(getattr(settings, "codx_path", ""))
        store.write_worker_heartbeat({"project_id": getattr(settings, "project_id", "")})
        try:
            service = BoardManagerService(settings=settings, store=store)
            return asyncio.run(service.run_due())
        except Exception as ex:  # pragma: no cover - defensive
            logger.exception(
                "Board manager failed for project '%s': %s",
                getattr(settings, "project_name", ""),
                ex,
            )
            return []
        finally:
            # A review can take longer than the heartbeat TTL; refresh after it
            # so the UI does not report the worker as offline right afterwards.
            store.write_worker_heartbeat({"project_id": getattr(settings, "project_id", "")})


# ---------------------------------------------------------------------------
# Module-level singleton (started by background.start_background_services)
# ---------------------------------------------------------------------------

_worker: Optional[BoardManagerWorker] = None


def start_board_manager_worker(stop_event: Any = None) -> Optional[BoardManagerWorker]:
    """Start the singleton worker (idempotent)."""
    global _worker

    if not board_manager_enabled():
        logger.info("Board manager disabled via %s", C.ENV_ENABLED)
        return None
    if _worker is not None and _worker.running:
        return _worker
    _worker = BoardManagerWorker(stop_event=stop_event).start()
    return _worker


def stop_board_manager_worker() -> None:
    """Stop the singleton worker (idempotent)."""
    global _worker

    if _worker is not None:
        _worker.stop()
    _worker = None


def get_board_manager_worker() -> Optional[BoardManagerWorker]:
    """Return the running worker (tests/administration)."""
    return _worker

# Made with ❤️ by codx-junior
