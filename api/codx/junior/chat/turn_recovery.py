"""
Recovery of chat turns interrupted by an application restart.

``ChatEngine.chat_with_project`` persists a durable
:class:`~codx.junior.chat.turn_store.ChatTurnRecord` before starting a turn and
holds an exclusive ``flock`` for its whole duration. When the process dies, the
OS releases the lock but the record stays on disk — the recovery worker uses
that fact to distinguish an orphaned turn from a live one.

One sweep:

1. discover the projects (same discovery used by the background services),
2. list the active turn records of each project,
3. skip records still owned by a live process,
4. repair their orphaned "Processing..." response message,
5. resume the turn through the normal ``ChatEngine`` pipeline (profiles, tools,
   knowledge, streaming, cost — nothing special),
6. bound the retries (``CODX_JUNIOR_CHAT_TURN_MAX_ATTEMPTS``) and mark the turn
   failed when the bound is reached, so the client never stays in "processing".

The worker is idempotent and safe to run in both the API and the background
process: the per-turn ``flock`` guarantees only one process resumes a turn.
It can be disabled with ``CODX_JUNIOR_CHAT_TURN_RECOVERY=0``.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Set

from .turn_store import (
    ACTIVE_STATUSES,
    FAILED_NOTE,
    ChatTurnRecord,
    ChatTurnStore,
    get_turn_store,
    repair_incomplete_messages,
)

logger = logging.getLogger(__name__)

# Environment switches.
ENV_ENABLED = "CODX_JUNIOR_CHAT_TURN_RECOVERY"
ENV_INTERVAL = "CODX_JUNIOR_CHAT_TURN_RECOVERY_INTERVAL"

DEFAULT_INTERVAL_SECONDS = 20.0
MAX_INTERVAL_SECONDS = 300.0
DEFAULT_WORKERS = 2


def _env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment switch."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() not in {"0", "false", "no", "off", ""}


def _env_float(name: str, default: float) -> float:
    """Read a float environment setting with a safe fallback."""
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def recovery_enabled() -> bool:
    """Return True when chat-turn recovery is enabled."""
    return _env_bool(ENV_ENABLED, True)


class ChatTurnRecovery:
    """
    Background sweeper that resumes orphaned chat turns.

    Args:
        interval_seconds: Seconds between sweeps.
        max_workers: Concurrent resumed turns.
        stop_event: Optional shared stop event (``threading.Event`` or
            ``asyncio.Event``).
    """

    def __init__(
        self,
        interval_seconds: Optional[float] = None,
        max_workers: Optional[int] = None,
        stop_event: Any = None,
    ) -> None:
        self.interval_seconds = max(
            2.0,
            min(
                float(
                    interval_seconds
                    if interval_seconds is not None
                    else _env_float(ENV_INTERVAL, DEFAULT_INTERVAL_SECONDS)
                ),
                MAX_INTERVAL_SECONDS,
            ),
        )
        self.max_workers = max(1, min(int(max_workers or DEFAULT_WORKERS), 8))
        self.stop_event = stop_event
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._pool: Optional[ThreadPoolExecutor] = None
        self._inflight: Set[str] = set()
        self._inflight_lock = threading.Lock()
        self._cycles = 0
        self._recovered = 0
        self._failed = 0
        # Cross-process single-instance lock (uvicorn starts one recovery
        # worker per process otherwise).
        self._instance_lock: Optional[Any] = None

    # -- lifecycle --------------------------------------------------------

    def start(self) -> "ChatTurnRecovery":
        """Start the worker thread (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._pool = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="ChatTurnRecovery",
        )
        self._thread = threading.Thread(
            target=self._loop,
            name="ChatTurnRecovery",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Chat turn recovery started (interval=%.1fs, workers=%d)",
            self.interval_seconds,
            self.max_workers,
        )
        return self

    def stop(self) -> None:
        """Stop the worker and its pool."""
        self._stop.set()
        pool = self._pool
        self._pool = None
        if pool is not None:
            pool.shutdown(wait=False, cancel_futures=True)
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        from codx.junior.utils.single_instance import release_single_instance

        release_single_instance(self._instance_lock)
        self._instance_lock = None
        logger.info("Chat turn recovery stopped")

    @property
    def running(self) -> bool:
        """Return True while the loop thread is alive."""
        return bool(self._thread is not None and self._thread.is_alive())

    def _should_stop(self) -> bool:
        """Return True when the shared stop event is set."""
        if self._stop.is_set():
            return True
        try:
            return bool(self.stop_event is not None and self.stop_event.is_set())
        except Exception:  # pragma: no cover - defensive
            return False

    def _loop(self) -> None:
        """Run one sweep per interval until stopped."""
        while not self._should_stop():
            try:
                self.recover_once()
            except Exception as ex:  # pragma: no cover - never kill the worker
                logger.exception("Chat turn recovery cycle failed: %s", ex)
            self._cycles += 1
            deadline = time.time() + self.interval_seconds
            while time.time() < deadline:
                if self._should_stop():
                    return
                time.sleep(min(0.5, max(0.05, deadline - time.time())))

    # -- discovery --------------------------------------------------------

    def _projects(self) -> List[Any]:
        """Return all known project settings (empty list on failure)."""
        try:
            from codx.junior.project.project_discover import find_all_projects

            return list(find_all_projects().values())
        except Exception as ex:  # pragma: no cover - defensive
            logger.exception(
                "Chat turn recovery could not discover projects: %s", ex
            )
            return []

    # -- sweep ------------------------------------------------------------

    def recover_once(self) -> Dict[str, Any]:
        """
        Scan every project and resume its orphaned turns.

        Returns:
            Small diagnostic payload (useful in tests/logs).
        """
        if not recovery_enabled():
            return {"enabled": False, "recovered": [], "failed": []}

        recovered: List[str] = []
        failed: List[str] = []
        for settings in self._projects():
            codx_path = str(getattr(settings, "codx_path", "") or "")
            if not codx_path:
                continue
            try:
                store = get_turn_store(codx_path)
                for record in store.list_active():
                    outcome = self._recover_record(settings, store, record)
                    if outcome == "recovered":
                        recovered.append(record.turn_id)
                    elif outcome == "failed":
                        failed.append(record.turn_id)
            except Exception as ex:  # pragma: no cover - defensive
                logger.exception(
                    "Chat turn recovery failed for project '%s': %s",
                    codx_path,
                    ex,
                )
        if recovered or failed:
            logger.info(
                "Chat turn recovery: recovered=%d failed=%d cycles=%d",
                len(recovered),
                len(failed),
                self._cycles,
            )
        return {
            "enabled": True,
            "recovered": recovered,
            "failed": failed,
            "cycles": self._cycles,
        }

    def _recover_record(
        self,
        settings: Any,
        store: ChatTurnStore,
        record: ChatTurnRecord,
    ) -> Optional[str]:
        """
        Recover one record when possible.

        Args:
            settings: Project settings.
            store: Store that owns the record.
            record: Record to recover.

        Returns:
            ``"recovered"``, ``"failed"``, or ``None`` when skipped.
        """
        if record.turn_id in self._inflight:
            return None
        if store.is_owned(record.turn_id):
            return None
        if store.cancel_requested(record.turn_id):
            if store.claim(record):
                store.finalize(record, "cancelled", error="Stopped by user")
                self._audit(record, "turn_cancelled", reason="Stopped by user")
            return None

        if record.attempts >= record.max_attempts:
            if not store.claim(record):
                # A live process still owns it; it will finish on its own.
                return None
            self._repair_chat(settings, record, note=FAILED_NOTE)
            store.fail(
                record,
                f"Gave up after {record.attempts} interrupted attempt(s)",
            )
            self._audit(
                record,
                "turn_failed",
                attempts=record.attempts,
                max_attempts=record.max_attempts,
                error="Gave up after repeated interruptions",
            )
            self._notify(
                record,
                f"codx-junior could not finish the task in chat '{record.chat_id}': "
                f"the turn was interrupted {record.attempts} time(s). "
                "Send the message again to retry.",
            )
            return "failed"

        if not store.claim(record):
            # A live process owns it (racing sweep).
            return None

        record.attempts += 1
        store.mark_running(record)
        self._repair_chat(settings, record, note=None)
        # Register the restart of the interrupted turn in the harness audit
        # journal: an interruption must never be silent work.
        self._audit(
            record,
            "turn_resumed",
            attempt=record.attempts,
            max_attempts=record.max_attempts,
            chat_mode=record.chat_mode,
        )

        with self._inflight_lock:
            self._inflight.add(record.turn_id)
        pool = self._pool
        if pool is None:
            self._run_in_thread(settings, store, record)
        else:
            try:
                pool.submit(self._run_in_thread, settings, store, record)
            except RuntimeError:  # pool shutting down
                self._run_in_thread(settings, store, record)
        return "recovered"

    def _audit(self, record: ChatTurnRecord, event_type: str, **data: Any) -> None:
        """
        Register a recovery transition in the harness audit journal (best effort).

        Recovery is part of the harness lifecycle: an interrupted turn that is
        resumed (or given up) must leave a trace next to the run/step events.
        """
        try:
            from codx.junior.harness.audit import record_audit

            record_audit(
                record.codx_path,
                event_type,
                chat_id=record.chat_id,
                turn_id=record.turn_id,
                **data,
            )
        except Exception as ex:  # pragma: no cover - audit must never break recovery
            logger.warning("Chat turn recovery: could not audit '%s': %s", event_type, ex)

    def _notify(self, record: ChatTurnRecord, text: str) -> None:
        """Notify the user about a recovery outcome (best effort)."""
        try:
            from codx.junior.events.event_manager import EventManager

            EventManager(codx_path=record.codx_path).send_notification(
                type="notification",
                title="codx-junior",
                text=text,
                chat={"id": record.chat_id},
            )
        except Exception as ex:  # pragma: no cover - notifications are best effort
            logger.warning("Chat turn recovery: could not notify: %s", ex)

    def _repair_chat(
        self,
        settings: Any,
        record: ChatTurnRecord,
        *,
        note: Optional[str],
    ) -> None:
        """Repair the orphaned response message of *record* (best effort)."""
        try:
            from codx.junior.chat_manager import ChatManager

            manager = ChatManager(settings=settings)
            chat = manager.find_by_id(record.chat_id)
            if chat is None:
                return
            repair_incomplete_messages(
                chat,
                manager,
                note=note if note is not None else "",
                error="The turn was interrupted by an application restart",
                skip_turn_ids=set(get_turn_store(record.codx_path).live_turn_ids())
                - {record.turn_id},
            )
        except Exception as ex:  # pragma: no cover - defensive
            logger.warning(
                "Chat turn recovery: could not repair chat '%s': %s",
                record.chat_id,
                ex,
            )

    # -- execution --------------------------------------------------------

    def _run_in_thread(
        self,
        settings: Any,
        store: ChatTurnStore,
        record: ChatTurnRecord,
    ) -> None:
        """Run one recovered turn in this thread (own asyncio loop)."""
        error: Optional[Exception] = None
        try:
            result = self._execute(settings, record)
            if inspect.isawaitable(result):
                asyncio.run(result)
        except Exception as ex:
            error = ex
            logger.exception(
                "Chat turn recovery: turn '%s' failed: %s",
                record.turn_id,
                ex,
            )
        finally:
            if error is not None:
                self._failed += 1
                self._audit(record, "turn_failed", error=str(error)[:500])
            else:
                self._recovered += 1
                self._audit(record, "turn_recovered")
            with self._inflight_lock:
                self._inflight.discard(record.turn_id)
            # The engine finalizes the record itself. If it could not (session
            # creation failed before the engine ran), finish it here so the
            # lock is never leaked and the turn is retried/failed next sweep.
            if store.is_owned(record.turn_id):
                try:
                    latest = store.load(record.turn_id)
                    if latest is not None and latest.status in ACTIVE_STATUSES:
                        if error is not None:
                            store.fail(latest, error)
                        else:
                            store.fail(
                                latest,
                                "Recovery runner ended without finalizing the turn",
                            )
                        self._repair_chat(
                            settings,
                            latest,
                            note=FAILED_NOTE,
                        )
                    else:
                        store.release(record.turn_id)
                except Exception:  # pragma: no cover - defensive
                    store.release(record.turn_id)

    async def _execute(self, settings: Any, record: ChatTurnRecord) -> None:
        """
        Resume the turn through the normal chat engine.

        Args:
            settings: Project settings.
            record: Turn record (already marked running/claimed).
        """
        from codx.junior.chat.chat_engine import ChatEngine
        from codx.junior.chat_manager import ChatManager
        from codx.junior.engine import CODXJuniorSession
        from codx.junior.model.model import CodxUser

        store = get_turn_store(record.codx_path)
        if store.cancel_requested(record.turn_id):
            logger.info(
                "Chat turn recovery: turn '%s' was stopped before it could be "
                "resumed; finalizing as cancelled",
                record.turn_id,
            )
            store.cancel(record, reason="The turn was stopped by the user")
            return

        user = None
        if record.username:
            try:
                from codx.junior.security.user_management import UserSecurityManager

                user = UserSecurityManager().find_user(record.username)
            except Exception as ex:  # pragma: no cover - defensive
                logger.warning(
                    "Chat turn recovery: cannot resolve user '%s': %s",
                    record.username,
                    ex,
                )
        if user is None and record.user:
            try:
                user = CodxUser(**record.user)
            except Exception as ex:  # pragma: no cover - legacy payloads
                logger.warning(
                    "Chat turn recovery: invalid persisted user for turn '%s': %s",
                    record.turn_id,
                    ex,
                )

        manager = ChatManager(settings=settings)
        chat = manager.find_by_id(record.chat_id)
        if chat is None:
            raise RuntimeError(
                f"Chat '{record.chat_id}' no longer exists; cannot resume the turn"
            )

        # The process can die AFTER the response was persisted but BEFORE the
        # turn record was removed. Running the turn again would duplicate the
        # answer, so finalize the record when a completed assistant message
        # already follows the current user request.
        messages = list(getattr(chat, "messages", []) or [])
        last_user_index = -1
        for index, message in enumerate(messages):
            if getattr(message, "role", "") == "user":
                last_user_index = index
        if last_user_index >= 0:
            for message in messages[last_user_index + 1:]:
                meta = getattr(message, "meta_data", None) or {}
                if meta.get("interrupted"):
                    # A repaired "processing" placeholder, not a real answer.
                    continue
                if getattr(message, "hide", False):
                    # Hidden reasoning/tool messages are not a final answer.
                    continue
                if (
                    getattr(message, "role", "") == "assistant"
                    and getattr(message, "done", True) is not False
                ):
                    logger.info(
                        "Chat turn recovery: turn '%s' of chat '%s' already "
                        "has a completed response; finalizing without rerun",
                        record.turn_id,
                        record.chat_id,
                    )
                    store.complete(record)
                    return

        session = CODXJuniorSession(
            settings=settings,
            codx_path=getattr(settings, "codx_path", None),
            user=user,
        )
        engine = ChatEngine(
            settings=settings,
            event_manager=session.event_manager,
            user=user,
        )
        logger.info(
            "Chat turn recovery: resuming turn '%s' of chat '%s' (attempt %d/%d)",
            record.turn_id,
            record.chat_id,
            record.attempts,
            record.max_attempts,
        )
        await engine.chat_with_project(
            chat=chat,
            disable_knowledge=bool(record.disable_knowledge),
            append_references=bool(record.append_references),
            chat_mode=record.chat_mode,
            system=record.system,
            turn_id=record.turn_id,
            turn_attempt=record.attempts,
            turn_codx_path=record.codx_path,
        )
        try:
            await session.save_chat(chat)
        except Exception as ex:  # pragma: no cover - defensive
            logger.warning(
                "Chat turn recovery: final save of chat '%s' failed: %s",
                record.chat_id,
                ex,
            )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_WORKER: Optional[ChatTurnRecovery] = None
_WORKER_LOCK = threading.Lock()


def get_turn_recovery() -> Optional[ChatTurnRecovery]:
    """Return the running recovery worker (or None)."""
    return _WORKER


def start_turn_recovery(stop_event: Any = None) -> Optional[ChatTurnRecovery]:
    """
    Start the singleton recovery worker when enabled.

    Args:
        stop_event: Optional shared stop event of the host process.

    Returns:
        The worker, or None when disabled.
    """
    global _WORKER
    if not recovery_enabled():
        logger.info("Chat turn recovery disabled by environment")
        return None
    with _WORKER_LOCK:
        if _WORKER is not None and _WORKER.running:
            return _WORKER
        from codx.junior.utils.single_instance import acquire_single_instance

        # uvicorn runs this startup hook once per worker process: elect exactly
        # one recovery sweeper across them (per-turn flocks still protect the
        # work itself).
        instance_lock = acquire_single_instance("chat-turn-recovery")
        if instance_lock is None:
            logger.info(
                "Chat turn recovery already owned by another API worker; "
                "this process will not sweep"
            )
            return None
        _WORKER = ChatTurnRecovery(stop_event=stop_event)
        _WORKER._instance_lock = instance_lock
        _WORKER.start()
        return _WORKER


def stop_turn_recovery() -> None:
    """Stop the singleton recovery worker (idempotent)."""
    global _WORKER
    with _WORKER_LOCK:
        worker = _WORKER
        _WORKER = None
    if worker is not None:
        worker.stop()


def recover_chat_turns_once() -> Dict[str, Any]:
    """
    Run one recovery sweep (compatibility entry point / manual debugging).

    Returns:
        The sweep diagnostic payload.
    """
    worker = _WORKER or ChatTurnRecovery()
    return worker.recover_once()
