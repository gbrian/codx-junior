"""
Background worker that advances orchestration runs.

The worker lives in the **background process** (the one started with
``CODX_JUNIOR_API_BACKGROUND``), never in the API process: an API request must
stay short, while a run can last hours. Two processes can safely coexist because
each run is guarded by an exclusive ``flock`` (see :mod:`.store`).

One cycle:

1. discover the projects that have an orchestration folder,
2. write/refresh the per-project worker heartbeat (the API reports
   ``worker_present`` from it),
3. submit every active run that is not already in flight to a small thread pool
   (each thread runs its own asyncio loop, mirroring the project-check pattern),
4. sleep the configured interval.

A run is never advanced twice concurrently: the in-flight set avoids duplicates
inside the process and the run lock avoids duplicates across processes.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

DEFAULT_TICK_SECONDS = 5.0
DEFAULT_MAX_RUNS = 2
MAX_TICK_SECONDS = 300.0


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment switch."""
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off", ""}


def _env_float(name: str, default: float) -> float:
    """Read a float environment setting with a safe fallback."""
    value = os.environ.get(name)
    if value is None or str(value).strip() == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def orchestration_enabled() -> bool:
    """Return True when the orchestration feature is enabled."""
    from . import constants as C

    return _env_bool(C.ENV_ENABLED, True)


def worker_enabled() -> bool:
    """Return True when the background worker should run."""
    from . import constants as C

    return orchestration_enabled() and _env_bool(C.ENV_WORKER, True)


class OrchestrationWorker:
    """Thread-based worker that ticks every active run of every project."""

    def __init__(
        self,
        *,
        tick_seconds: Optional[float] = None,
        max_runs: Optional[int] = None,
        stop_event: Any = None,
    ) -> None:
        from . import constants as C

        self.tick_seconds = max(
            1.0,
            min(
                float(
                    tick_seconds
                    if tick_seconds is not None
                    else _env_float(C.ENV_TICK_SECONDS, DEFAULT_TICK_SECONDS)
                ),
                MAX_TICK_SECONDS,
            ),
        )
        self.max_runs = max(
            1,
            min(
                int(
                    max_runs
                    if max_runs is not None
                    else _env_float(C.ENV_MAX_RUNS, DEFAULT_MAX_RUNS)
                ),
                8,
            ),
        )
        self.stop_event = stop_event
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._pool: Optional[ThreadPoolExecutor] = None
        self._inflight: Set[str] = set()
        self._inflight_lock = threading.Lock()
        self._last_tick: Optional[float] = None
        self._cycles = 0
        self._errors = 0

    # -- lifecycle --------------------------------------------------------

    def start(self) -> "OrchestrationWorker":
        """Start the loop thread (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._pool = ThreadPoolExecutor(
            max_workers=self.max_runs,
            thread_name_prefix="OrchestrationRun",
        )
        self._thread = threading.Thread(
            target=self._loop,
            name="OrchestrationWorker",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Orchestration worker started (tick=%.1fs, max_runs=%d)",
            self.tick_seconds,
            self.max_runs,
        )
        return self

    def stop(self) -> None:
        """Stop the loop and the thread pool."""
        self._stop.set()
        pool = self._pool
        self._pool = None
        if pool is not None:
            pool.shutdown(wait=False, cancel_futures=True)
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        logger.info("Orchestration worker stopped")

    @property
    def running(self) -> bool:
        """Return True while the loop thread is alive."""
        return bool(self._thread is not None and self._thread.is_alive())

    # -- loop -------------------------------------------------------------

    def _loop(self) -> None:
        """Worker loop: one tick per interval until stopped."""
        while not self._stop.is_set() and not self._should_stop():
            try:
                self.tick_once()
            except Exception as ex:  # pragma: no cover - never kill the worker
                self._errors += 1
                logger.exception("Orchestration worker cycle failed: %s", ex)
            self._last_tick = time.time()
            self._cycles += 1
            # Wait in small slices so stop() is responsive.
            deadline = time.time() + self.tick_seconds
            while time.time() < deadline:
                if self._stop.is_set() or self._should_stop():
                    return
                time.sleep(min(0.5, max(0.05, deadline - time.time())))

    def _should_stop(self) -> bool:
        """Return True when the shared background stop event is set."""
        try:
            return bool(self.stop_event is not None and self.stop_event.is_set())
        except Exception:  # pragma: no cover - defensive
            return False

    # -- one cycle --------------------------------------------------------

    def tick_once(self) -> Dict[str, Any]:
        """
        Discover and submit the active runs of every project.

        Returns a small diagnostic payload (useful in tests/logs).
        """
        from . import constants as C
        from .store import RunStore

        submitted: List[str] = []
        projects = self._projects()
        for settings in projects:
            codx_path = str(getattr(settings, "codx_path", "") or "")
            if not codx_path:
                continue
            orchestration_dir = os.path.join(codx_path, C.ORCHESTRATION_DIR)
            if not os.path.isdir(orchestration_dir):
                # No run was ever created for this project: nothing to do.
                continue
            store = RunStore(codx_path)
            store.write_worker_heartbeat({
                "tick_seconds": self.tick_seconds,
                "max_runs": self.max_runs,
                "cycles": self._cycles,
                "errors": self._errors,
            })
            for run_id in store.active_run_ids():
                if not self._claim(run_id):
                    continue
                submitted.append(run_id)
                self._submit(settings, run_id)
        if submitted:
            logger.info("Orchestration worker submitted %d run(s): %s", len(submitted), submitted)
        return {"submitted": submitted, "cycles": self._cycles, "errors": self._errors}

    def _projects(self) -> List[Any]:
        """Return all known projects (empty list when discovery fails)."""
        try:
            from codx.junior.project.project_discover import find_all_projects

            return list(find_all_projects().values())
        except Exception as ex:  # pragma: no cover - defensive
            logger.exception("Orchestration worker could not discover projects: %s", ex)
            return []

    def _claim(self, run_id: str) -> bool:
        """Mark *run_id* in flight (returns False when already in flight)."""
        with self._inflight_lock:
            if run_id in self._inflight:
                return False
            self._inflight.add(run_id)
            return True

    def _release(self, run_id: str) -> None:
        """Release the in-flight marker of *run_id*."""
        with self._inflight_lock:
            self._inflight.discard(run_id)

    def _submit(self, settings: Any, run_id: str) -> None:
        """Submit one run tick to the pool."""
        pool = self._pool
        if pool is None:
            self._release(run_id)
            return
        try:
            pool.submit(self._process, settings, run_id)
        except RuntimeError as ex:  # pool shutting down
            logger.debug("Orchestration worker could not submit '%s': %s", run_id, ex)
            self._release(run_id)

    def _process(self, settings: Any, run_id: str) -> None:
        """Run one tick in its own event loop (thread-safe)."""
        from .models import RunLocked, RunNotFound
        from .service import OrchestrationService
        from .store import RunStore

        try:
            # Best effort: let the run timeline reach connected clients. The
            # background process may not have a socket client, in which case the
            # event is simply not delivered; REST polling stays authoritative.
            event_manager = None
            try:
                from codx.junior.events.event_manager import EventManager

                event_manager = EventManager(codx_path=str(getattr(settings, "codx_path", "")))
            except Exception:  # pragma: no cover - optional notification path
                event_manager = None
            service = OrchestrationService(settings=settings, event_manager=event_manager)
            asyncio.run(service.tick(run_id))
            logger.info("Orchestration worker advanced run '%s'", run_id)
        except RunLocked:
            logger.debug("Orchestration worker: run '%s' is locked by another worker", run_id)
        except RunNotFound:
            logger.warning("Orchestration worker: run '%s' disappeared", run_id)
        except Exception as ex:
            self._errors += 1
            logger.exception("Orchestration worker failed to advance run '%s': %s", run_id, ex)
            try:
                store = RunStore(str(getattr(settings, "codx_path", "")))
                store.write_worker_heartbeat({
                    "tick_seconds": self.tick_seconds,
                    "max_runs": self.max_runs,
                    "cycles": self._cycles,
                    "errors": self._errors,
                    "last_error": str(ex)[:1000],
                })
            except Exception:  # pragma: no cover - defensive
                pass
        finally:
            self._release(run_id)


# ---------------------------------------------------------------------------
# Module-level singleton (started by background.start_background_services)
# ---------------------------------------------------------------------------

_WORKER: Optional[OrchestrationWorker] = None
_WORKER_LOCK = threading.Lock()


def get_orchestration_worker() -> Optional[OrchestrationWorker]:
    """Return the running worker (or None)."""
    return _WORKER


def start_orchestration_worker(stop_event: Any = None) -> Optional[OrchestrationWorker]:
    """
    Start the singleton worker when the feature is enabled.

    Args:
        stop_event: Shared ``threading.Event`` of the background services.

    Returns:
        The worker, or None when the feature is disabled.
    """
    global _WORKER
    if not worker_enabled():
        logger.info("Orchestration worker disabled by environment")
        return None
    with _WORKER_LOCK:
        if _WORKER is not None and _WORKER.running:
            return _WORKER
        _WORKER = OrchestrationWorker(stop_event=stop_event).start()
        return _WORKER


def stop_orchestration_worker() -> None:
    """Stop the singleton worker (idempotent)."""
    global _WORKER
    with _WORKER_LOCK:
        worker = _WORKER
        _WORKER = None
    if worker is not None:
        worker.stop()


def check_orchestration_runs() -> None:
    """
    One worker cycle (compatibility entry point).

    Kept as a module function so it can be called from a shell/debug job
    without starting the loop.
    """
    worker = _WORKER or OrchestrationWorker()
    worker.tick_once()

# Made with ❤️ by codx-junior
