"""
Harness watchdog: keeps the orchestration worker alive.

The durable orchestration worker lives in the **background process** (the one
started with ``CODX_JUNIOR_API_BACKGROUND``). If that process dies, is
OOM-killed or gets wedged, active runs would stay frozen forever. The watchdog
runs in the **API process** (never in the background one) and detects this from
the durable worker heartbeat that the worker rewrites every tick:

* a project with **active runs** whose heartbeat is older than the stale
  threshold means the worker is down (or wedged),
* the watchdog registers the incident in the harness audit journal, notifies
  connected users and attempts to restart the background process —
  ``supervisorctl`` in the monolithic deployment, ``docker restart
  codx-junior-api-background`` in the Compose deployment, a loud CRITICAL log
  otherwise,
* a per-project cooldown (persisted in ``.codx/harness/watchdog.json``, guarded
  by an exclusive ``flock``) guarantees that many API workers can never trigger
  a restart storm.

The orchestration runtime itself is crash-safe: runs, steps and budgets are
durable, locks are OS ``flock`` (released on process death) and the worker's
tick recovers steps whose owner died. The watchdog therefore only has to bring
the worker process back; the run state machine does the rest.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import shutil
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

from .audit import harness_dir, record_audit, utcnow_iso

logger = logging.getLogger(__name__)

# Environment switches
ENV_WATCHDOG = "CODX_JUNIOR_HARNESS_WATCHDOG"
ENV_CHECK_SECONDS = "CODX_JUNIOR_HARNESS_WATCHDOG_SECONDS"
ENV_STALE_SECONDS = "CODX_JUNIOR_HARNESS_WATCHDOG_STALE_SECONDS"
ENV_AUTO_RESTART = "CODX_JUNIOR_HARNESS_WATCHDOG_RESTART"

DEFAULT_CHECK_SECONDS = 30.0
DEFAULT_STALE_SECONDS = 120.0
DEFAULT_RESTART_COOLDOWN_SECONDS = 300.0

BACKGROUND_PROGRAM = "codx-junior-api-background"
WATCHDOG_STATE_FILE = "watchdog.json"


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off", ""}


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or str(value).strip() == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def watchdog_enabled() -> bool:
    """Return True when the harness watchdog should run."""
    return _env_bool(ENV_WATCHDOG, True)


def auto_restart_enabled() -> bool:
    """Return True when the watchdog may restart the background process."""
    return _env_bool(ENV_AUTO_RESTART, True)


class HarnessWatchdog:
    """Thread that monitors the orchestration worker of every project."""

    def __init__(
        self,
        *,
        stop_event: Any = None,
        check_seconds: Optional[float] = None,
        stale_seconds: Optional[float] = None,
        restart_cooldown_seconds: Optional[float] = None,
    ) -> None:
        self.check_seconds = max(
            5.0,
            _env_float(ENV_CHECK_SECONDS, check_seconds or DEFAULT_CHECK_SECONDS),
        )
        self.stale_seconds = max(
            15.0,
            _env_float(ENV_STALE_SECONDS, stale_seconds or DEFAULT_STALE_SECONDS),
        )
        self.restart_cooldown_seconds = max(
            30.0,
            _env_float(
                ENV_WATCHDOG + "_COOLDOWN",
                restart_cooldown_seconds or DEFAULT_RESTART_COOLDOWN_SECONDS,
            ),
        )
        self.stop_event = stop_event
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock_handle: Optional[Any] = None
        # Cross-process single-instance lock (uvicorn starts this startup hook
        # once per worker process).
        self._instance_lock: Optional[Any] = None
        self._cycles = 0
        self._incidents = 0
        self._restarts = 0

    # -- lifecycle --------------------------------------------------------

    def start(self) -> "HarnessWatchdog":
        """Start the watchdog thread (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="HarnessWatchdog",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Harness watchdog started (check=%.1fs stale=%.1fs cooldown=%.1fs)",
            self.check_seconds,
            self.stale_seconds,
            self.restart_cooldown_seconds,
        )
        return self

    def stop(self) -> None:
        """Stop the watchdog thread."""
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=3.0)
        from codx.junior.utils.single_instance import release_single_instance

        release_single_instance(self._instance_lock)
        self._instance_lock = None
        logger.info("Harness watchdog stopped")

    @property
    def running(self) -> bool:
        return bool(self._thread is not None and self._thread.is_alive())

    @property
    def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "check_seconds": self.check_seconds,
            "stale_seconds": self.stale_seconds,
            "restart_cooldown_seconds": self.restart_cooldown_seconds,
            "cycles": self._cycles,
            "incidents": self._incidents,
            "restarts": self._restarts,
        }

    # -- loop -------------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.check_once()
            except Exception as ex:  # pragma: no cover - never kill the watchdog
                logger.exception("Harness watchdog cycle failed: %s", ex)
            self._cycles += 1
            deadline = time.time() + self.check_seconds
            while time.time() < deadline:
                if self._stop.is_set():
                    return
                time.sleep(min(0.5, max(0.05, deadline - time.time())))

    def _should_stop(self) -> bool:
        try:
            return bool(self.stop_event is not None and self.stop_event.is_set())
        except Exception:  # pragma: no cover - defensive
            return False

    # -- one cycle --------------------------------------------------------

    def check_once(self) -> List[Dict[str, Any]]:
        """
        Check every project once and restart the background worker when needed.

        Only ONE API worker performs the checks at a time: the cycle holds an
        exclusive non-blocking ``flock`` on the per-project watchdog lock, so
        the other workers (uvicorn runs several) skip the cycle instead of
        duplicating the work.

        Returns:
            List of incident payloads (one per stalled project).
        """
        if self._should_stop():
            return []
        incidents: List[Dict[str, Any]] = []
        try:
            from codx.junior.project.project_discover import find_all_projects
        except Exception as ex:  # pragma: no cover - defensive
            logger.warning("Harness watchdog could not import project discovery: %s", ex)
            return []

        try:
            projects = list(find_all_projects().values())
        except Exception as ex:  # pragma: no cover - defensive
            logger.exception("Harness watchdog could not discover projects: %s", ex)
            return []

        for settings in projects:
            if self._stop.is_set() or self._should_stop():
                break
            try:
                incident = self._check_project(settings)
                if incident:
                    incidents.append(incident)
            except Exception as ex:  # pragma: no cover - defensive
                logger.exception(
                    "Harness watchdog failed to check project '%s': %s",
                    getattr(settings, "project_name", settings),
                    ex,
                )
        return incidents

    def _check_project(self, settings: Any) -> Optional[Dict[str, Any]]:
        """Check one project; return an incident payload when the worker stalled."""
        from codx.junior.orchestration.store import RunStore

        codx_path = str(getattr(settings, "codx_path", "") or "")
        project_name = str(getattr(settings, "project_name", "") or codx_path)
        if not codx_path:
            return None
        # ``codx_path`` is the project's ``.codx`` directory, exactly like the
        # RunStore root: orchestration runs live at ``<codx_path>/orchestration``.
        orchestration_dir = os.path.join(codx_path, "orchestration")
        if not os.path.isdir(orchestration_dir):
            return None

        store = RunStore(codx_path)
        active = store.active_run_ids()
        if not active:
            # Nothing to advance: a stalled worker does not matter.
            return None

        status = store.worker_status(ttl_seconds=self.stale_seconds)
        if status.get("present"):
            return None

        # -- incident: the worker is down/wedged with active runs ----------
        age = status.get("age_seconds")
        incident = {
            "project": project_name,
            "codx_path": codx_path,
            "active_runs": active,
            "worker_age_seconds": age,
            "ts": utcnow_iso(),
        }
        self._incidents += 1
        logger.error(
            "Harness watchdog: worker stalled for project '%s' (%d active run(s), heartbeat age %ss)",
            project_name,
            len(active),
            age,
        )
        # The stall is audited and notified once per cooldown window (not every
        # cycle) to keep the journal and the user inbox meaningful.
        if self._should_report_stall(codx_path):
            record_audit(
                codx_path,
                "worker_stalled",
                project=project_name,
                active_runs=active,
                worker_age_seconds=age,
            )
            self._notify_stalled(codx_path, project_name, len(active))
        if auto_restart_enabled() and self._acquire_restart_lease(codx_path):
            try:
                method, detail = self._restart_background(project_name, codx_path)
                self._restarts += 1
                record_audit(
                    codx_path,
                    "worker_restarted",
                    project=project_name,
                    method=method,
                    detail=detail,
                )
            except Exception as ex:  # pragma: no cover - defensive
                record_audit(codx_path, "worker_restart_failed", project=project_name, error=str(ex)[:500])
                logger.exception("Harness watchdog: restart failed for '%s': %s", project_name, ex)
        return incident

    def _notify_stalled(self, codx_path: str, project_name: str, active_runs: int) -> None:
        """Tell connected users that the worker stalled (best effort)."""
        try:
            from codx.junior.events.event_manager import EventManager

            manager = EventManager(codx_path=codx_path)
            manager.send_notification(
                type="notification",
                title="codx-junior",
                text=(
                    f"The background worker for '{project_name}' stalled with "
                    f"{active_runs} active run(s). The harness watchdog is restarting it."
                ),
            )
        except Exception as ex:  # pragma: no cover - best effort
            logger.warning("Harness watchdog: could not notify about stall: %s", ex)

    def _should_report_stall(self, codx_path: str) -> bool:
        """
        Return True once per cooldown window for a stalled project.

        Uses the same persisted state file (and flock) as the restart lease so
        the audit journal and notifications do not repeat on every cycle.
        """
        state_path = os.path.join(harness_dir(codx_path), WATCHDOG_STATE_FILE)
        now = time.time()
        try:
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            with open(state_path, "a+", encoding="utf-8") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                handle.seek(0)
                raw = handle.read()
                try:
                    state = json.loads(raw) if raw.strip() else {}
                except (ValueError, TypeError):
                    state = {}
                last = float(state.get("last_stall_reported", 0.0) or 0.0)
                if last and now - last < self.restart_cooldown_seconds:
                    return False
                state["last_stall_reported"] = now
                handle.seek(0)
                handle.truncate()
                json.dump(state, handle)
                handle.flush()
                os.fsync(handle.fileno())
            return True
        except OSError as ex:  # pragma: no cover - defensive
            logger.warning("Harness watchdog: could not persist stall report state: %s", ex)
            return True

    # -- restart ----------------------------------------------------------

    def _acquire_restart_lease(self, codx_path: str) -> bool:
        """
        Return True when this watchdog may restart the worker for *codx_path*.

        The lease is per project, persisted in ``.codx/harness/watchdog.json``
        and guarded by an exclusive ``flock`` on that file: the next attempt is
        allowed only after the cooldown, across processes and across restarts
        of the API process, and concurrent API workers cannot race each other.
        """
        state_path = os.path.join(harness_dir(codx_path), WATCHDOG_STATE_FILE)
        now = time.time()
        try:
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            with open(state_path, "a+", encoding="utf-8") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                handle.seek(0)
                raw = handle.read()
                try:
                    state = json.loads(raw) if raw.strip() else {}
                except (ValueError, TypeError):
                    state = {}
                last = float(state.get("last_restart_attempt", 0.0) or 0.0)
                if last and now - last < self.restart_cooldown_seconds:
                    logger.info(
                        "Harness watchdog: restart attempt for '%s' still cooling down (%.0fs left)",
                        codx_path,
                        self.restart_cooldown_seconds - (now - last),
                    )
                    return False
                state["last_restart_attempt"] = now
                handle.seek(0)
                handle.truncate()
                json.dump(state, handle)
                handle.flush()
                os.fsync(handle.fileno())
            return True
        except OSError as ex:  # pragma: no cover - defensive
            logger.warning("Harness watchdog: could not persist restart lease: %s", ex)
            return False

    def _restart_background(self, project_name: str, codx_path: str) -> tuple:
        """
        Restart the background worker process.

        Tries, in order:
        1. ``supervisorctl`` (monolithic deployment) — the launcher's
           supervisor.conf defines ``codx-junior-api-background``.
        2. ``docker restart codx-junior-api-background`` (Compose deployment).
        3. Otherwise fail loudly: the incident is audited and logged, and the
           delivery of the restart is left to the OS/Docker layer.

        Returns:
            ``(method, detail)`` of the executed restart.
        """
        # 1. supervisord (monolith)
        supervisor_conf = os.path.join(
            os.environ.get("CODX_JUNIOR_PATH", ""), "supervisor.conf"
        )
        if supervisor_conf and os.path.isfile(supervisor_conf):
            supervisorctl = shutil.which("supervisorctl")
            if supervisorctl:
                result = subprocess.run(
                    [supervisorctl, "-c", supervisor_conf, "restart", BACKGROUND_PROGRAM],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                detail = (result.stderr or result.stdout or "").strip()[:400]
                if result.returncode == 0:
                    return "supervisorctl", detail or "restarted"
                raise RuntimeError(f"supervisorctl failed: {detail}")

        # 2. Docker (Compose deployment)
        docker = shutil.which("docker")
        if docker:
            result = subprocess.run(
                [docker, "restart", BACKGROUND_PROGRAM],
                capture_output=True,
                text=True,
                timeout=60,
            )
            detail = (result.stderr or result.stdout or "").strip()[:400]
            if result.returncode == 0:
                return "docker", detail or "restarted"
            raise RuntimeError(f"docker restart failed: {detail}")

        raise RuntimeError(
            "no restart mechanism available (no supervisor.conf/supervisorctl, no docker CLI)"
        )


# ---------------------------------------------------------------------------
# Module-level singleton (started by app.py in the API process only)
# ---------------------------------------------------------------------------

_WATCHDOG: Optional[HarnessWatchdog] = None
_WATCHDOG_LOCK = threading.Lock()


def get_harness_watchdog() -> Optional[HarnessWatchdog]:
    """Return the running watchdog (or None)."""
    return _WATCHDOG


def start_harness_watchdog(stop_event: Any = None) -> Optional[HarnessWatchdog]:
    """
    Start the singleton watchdog (API process only).

    Args:
        stop_event: Shared ``threading.Event`` of the background services.

    Returns:
        The watchdog, or None when it is disabled or this is the background
        process (the worker lives there, so there is nothing to watch).
    """
    global _WATCHDOG
    if os.environ.get("CODX_JUNIOR_API_BACKGROUND"):
        logger.debug("Harness watchdog not started: this is the background process")
        return None
    if not watchdog_enabled():
        logger.info("Harness watchdog disabled by environment")
        return None
    with _WATCHDOG_LOCK:
        if _WATCHDOG is not None and _WATCHDOG.running:
            return _WATCHDOG
        from codx.junior.utils.single_instance import acquire_single_instance

        # Only one API worker supervises the background process; the others
        # must not spin their own watchdog thread.
        instance_lock = acquire_single_instance("harness-watchdog")
        if instance_lock is None:
            logger.info(
                "Harness watchdog already owned by another API worker; "
                "this process will not watch"
            )
            return None
        _WATCHDOG = HarnessWatchdog(stop_event=stop_event)
        _WATCHDOG._instance_lock = instance_lock
        _WATCHDOG.start()
        return _WATCHDOG


def stop_harness_watchdog() -> None:
    """Stop the singleton watchdog (idempotent)."""
    global _WATCHDOG
    with _WATCHDOG_LOCK:
        watchdog = _WATCHDOG
        _WATCHDOG = None
    if watchdog is not None:
        watchdog.stop()
