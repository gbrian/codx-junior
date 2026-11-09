"""
Persistent runtime for one desktop computer session.

Each desktop session keeps one backend (``docker exec`` agent or RFB client) and
one lock.  That gives the AI and the human the same guarantees as the browser
runtime:

* actions never interleave (two chats or a user click cannot race a drag);
* control hand-off is respected (:meth:`BrowserSession.can_ai_act`);
* read-only screen reads do not pause the AI;
* every action is written to the shared activity log with duration and result;
* the session record (mouse position is not stored, but window size and last
  action are) is persisted after state-changing actions.

The runtime is cached by ``BrowserManager``/``ComputerManager`` and resolved by
the API and the tools through ``manager.get_runtime(session)``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from codx.junior.computer.backend import (
    DEFAULT_MAX_WIDTH,
    READ_ONLY_ACTIONS,
    get_backend,
    normalize_action,
)

logger = logging.getLogger(__name__)


class ComputerControlError(RuntimeError):
    """The AI is not allowed to act because the human owns the screen."""


class DesktopRuntime:
    """Serialized access to one shared desktop."""

    def __init__(self, manager, session):
        self.manager = manager
        self.session = session
        self.backend = get_backend(session, runtime=self)
        self._lock = asyncio.Lock()
        self._closed = False
        self._last_used = 0.0

    @property
    def session_id(self) -> str:
        """Session identifier."""
        return self.session.id

    async def run(
        self,
        action: str,
        *,
        force: bool = False,
        user_wait: float = 0.0,
        actor: str = "ai",
        log: bool = True,
        **params: Any,
    ) -> Any:
        """
        Execute one action on the shared desktop.

        Args:
            action: Action name (aliases accepted, see ``backend``).
            force: Allow the action even when the AI control lease is paused
                (used by user-originated API actions).
            user_wait: Seconds to wait while the human is recently active before
                giving up (AI actions only).
            actor: ``ai`` (default) or ``user`` for the audit log; user actions
                also mark the human active so the AI yields.
            log: Write an activity entry (default true). The UI polling a
                screenshot sets false so the audit trail is not flooded.
            **params: Action parameters.
        """
        action = normalize_action(action)
        read_only = action in READ_ONLY_ACTIONS
        if not force and not read_only:
            if not self.session.can_ai_act():
                if user_wait > 0:
                    await self._wait_for_user(user_wait)
                if not self.session.can_ai_act():
                    reason = self.session.handoff_reason or "the user is driving the computer"
                    message = (
                        f"The AI cannot perform '{action}': {reason}. "
                        "Call computer_control(action='status') and wait for the "
                        "user to give control back."
                    )
                    self.manager.log_activity(
                        self.session,
                        actor=actor,
                        action=action,
                        params=params,
                        success=False,
                        error=message,
                    )
                    raise ComputerControlError(message)

        async with self._lock:
            started_at = time.monotonic()
            self._last_used = started_at
            try:
                result = await self.backend.run(action, **params)
            except Exception as ex:
                self.manager.log_activity(
                    self.session,
                    actor=actor,
                    action=action,
                    params=params,
                    success=False,
                    error=str(ex),
                    duration_ms=(time.monotonic() - started_at) * 1000,
                )
                raise
            self._apply_result(action, result)
            if log:
                self.manager.log_activity(
                    self.session,
                    actor=actor,
                    action=action,
                    params=params,
                    duration_ms=(time.monotonic() - started_at) * 1000,
                    result=_activity_summary(action, result),
                )
            if not read_only:
                self.session.mark_action(action)
                if actor == "user":
                    self.session.mark_user_active(seconds=10)
                try:
                    self.manager.save_session(self.session)
                except Exception as ex:  # persistence must never fail an action
                    logger.debug("Could not persist computer session %s: %s", self.session.id, ex)
            return result

    async def _wait_for_user(self, seconds: float) -> None:
        """Wait until the human has been idle for up to *seconds*."""
        deadline = time.monotonic() + max(0.0, float(seconds))
        while time.monotonic() < deadline:
            if not self.session.user_is_active():
                return
            await asyncio.sleep(0.25)

    def _apply_result(self, action: str, result: Any) -> None:
        """Update the session record from an action result."""
        if not isinstance(result, dict):
            return
        if "width" in result and result.get("width"):
            try:
                self.session.desktop_width = int(result["width"])
            except (TypeError, ValueError):
                pass
        if "height" in result and result.get("height"):
            try:
                self.session.desktop_height = int(result["height"])
            except (TypeError, ValueError):
                pass
        window = result.get("window")
        if isinstance(window, dict) and window.get("title"):
            self.session.current_title = window["title"]
        if action == "windows" and result.get("windows"):
            active = next((item for item in result["windows"] if item.get("active")), None)
            if active:
                self.session.current_title = active.get("title")
        if action in ("screenshot", "ocr") and result.get("image"):
            self.session.current_title = self.session.current_title or None

    # -- control lease helpers (shared API surface with BrowserRuntime) ----
    async def state(self) -> Dict[str, Any]:
        """Return the control state consumed by the REST control endpoint."""
        return {
            "controller": self.session.controller,
            "controller_chat_id": self.session.controller_chat_id,
            "user_active": self.session.user_is_active(),
            "handoff_reason": self.session.handoff_reason,
            "user_active_until": self.session.user_active_until,
            "connected": self.session.status == "running",
            "kind": self.session.kind,
        }

    def request_handoff(self, reason: str, chat_id: Optional[str] = None) -> None:
        """Pause the AI and ask the human to take over."""
        self.session.request_handoff(reason, chat_id=chat_id)
        self.manager.save_session(self.session)

    def take_control(self, chat_id: Optional[str] = None, reason: Optional[str] = None) -> None:
        """Give control to the human."""
        self.session.set_controller("user", chat_id=chat_id, reason=reason)
        self.session.mark_user_active(seconds=600)
        self.manager.save_session(self.session)

    def release(self, chat_id: Optional[str] = None) -> None:
        """Give control back to the AI."""
        self.session.set_controller("ai", chat_id=chat_id)
        self.manager.save_session(self.session)

    async def screenshot(
        self,
        include_text: bool = True,
        max_width: int = DEFAULT_MAX_WIDTH,
        actor: str = "user",
        log: bool = False,
    ) -> Dict[str, Any]:
        """Capture a screenshot (read-only convenience)."""
        return await self.run(
            "screenshot",
            include_text=bool(include_text),
            max_width=int(max_width or DEFAULT_MAX_WIDTH),
            force=True,
            actor=actor,
            log=log,
        )

    async def run_steps(
        self,
        steps,
        variables: Optional[Dict[str, Any]] = None,
        force: bool = False,
        actor: str = "ai",
    ) -> Dict[str, Any]:
        """Run a batch on the same desktop connection."""
        from codx.junior.browser.actions import interpolate

        values = variables or {}
        prepared = [interpolate(step, values) for step in (steps or [])]
        return await self.run("batch", steps=prepared, force=force, actor=actor)

    async def close(self) -> None:
        """Release the backend."""
        if self._closed:
            return
        self._closed = True
        try:
            await self.backend.close()
        except Exception as ex:
            logger.debug("Error closing computer backend: %s", ex)


def _activity_summary(action: str, result: Any) -> Dict[str, Any]:
    """Keep activity entries small (no screenshot payloads)."""
    if not isinstance(result, dict):
        return {"result": str(result)[:500]}
    summary = {}
    for key in (
        "width", "height", "image_width", "image_height", "windows", "window",
        "exit_code", "stdout", "stderr", "typed", "keys", "x", "y", "steps",
        "success",
    ):
        if key not in result:
            continue
        value = result[key]
        if key == "stdout" and isinstance(value, str):
            value = value[:2000]
        if key == "stderr" and isinstance(value, str):
            value = value[:1000]
        summary[key] = value
    if isinstance(result.get("text"), str):
        # OCR text can include passwords/OTP rendered on screen; audit only its
        # size (the model still receives the text in the tool response).
        summary["text_length"] = len(result["text"])
    if "image" in result:
        summary["image"] = True
    return summary
