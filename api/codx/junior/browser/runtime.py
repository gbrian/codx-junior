"""One persistent browser runtime per session.

Why this exists
---------------
The original tools opened a Playwright driver, connected over CDP, performed a
single action and disconnected on every call.  Measured cost: ~0.45-0.55 s of
pure overhead per action, plus a Node driver process per call.  For a 20-step
automation that is 10+ seconds before the model even starts thinking.

``BrowserRuntime`` owns the connection instead:

* one Playwright connection per session, lazily created;
* a per-session ``asyncio.Lock`` so two chats (or the human and the AI) never
  interleave half-finished actions;
* one place to apply download behavior, keep-alive tab and the page recorder;
* a 1 s watcher that drains the in-page user-event buffer into the activity
  log, which is what makes ``browser_activity`` truthful about VNC input;
* an idle disconnect so a forgotten session does not keep a driver process
  forever;
* deterministic ``run_steps`` for scripts/batches, all on the same connection.

The runtime is stored on the (cached) ``BrowserManager``; tools and API
handlers resolve it with ``manager.get_runtime(session)``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from codx.junior.browser.browser import Browser
from codx.junior.browser.actions import READ_ONLY_ACTIONS, run_steps
from codx.junior.browser import tabs as browser_tabs

logger = logging.getLogger(__name__)

#: Disconnect the Playwright driver after this many seconds without use.  The
#: Chromium page stays alive; the next action reconnects in ~0.4 s.  A long
#: window keeps the human-event recorder active during long reading sessions.
DEFAULT_IDLE_SECONDS = 900

#: How long the AI waits for a human who is actively typing before giving up.
DEFAULT_USER_WAIT_SECONDS = 3

#: How long after an AI action a URL change is attributed to the AI.
AI_NAVIGATION_GRACE_SECONDS = 2.5


class BrowserControlError(RuntimeError):
    """The AI is not allowed to act because the human owns the page."""


class BrowserRuntime:
    """Persistent, serialized access to one shared Chromium session."""

    def __init__(self, manager, session, idle_seconds: int = DEFAULT_IDLE_SECONDS):
        self.manager = manager
        self.session = session
        self.idle_seconds = max(30, int(idle_seconds or DEFAULT_IDLE_SECONDS))
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()
        self._closed = False
        self._connected_at = 0.0
        self._last_used = 0.0
        self._last_ai_action = 0.0
        self._watch_task: Optional[asyncio.Task] = None
        self._last_url = (getattr(session, "current_url", None) or "").strip()
        self._recorded_pages: set = set()
        self.loop = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    async def _ensure_browser(self) -> Browser:
        if self._browser is not None and self._browser.is_alive():
            return self._browser
        await self._disconnect_browser()
        browser = Browser(self.session, self.manager.docker_manager)
        try:
            await browser.connect()
        except Exception as ex:
            # Same recovery contract as the old connect_browser(): a dead
            # window/DevTools endpoint is fixed by relaunching the container
            # entrypoint once, keeping the mounted Chromium profile.
            if not getattr(self.session, "container_id", None):
                raise
            logger.warning(
                "Browser of session %s is not reachable (%s); restarting it",
                str(self.session.id)[:8], ex,
            )
            await browser.close()
            self.session = await asyncio.to_thread(
                self.manager._restart_browser, self.session
            )
            browser = Browser(self.session, self.manager.docker_manager)
            await browser.connect()
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = None
        self._browser = browser
        self._connected_at = time.monotonic()
        self._last_used = time.monotonic()
        self._last_url = (self.session.current_url or "").strip()
        # These are browser-wide / one-per-connection concerns.  Doing them
        # here (not on every action) is part of why actions are fast now.
        await self.manager._apply_downloads_path(browser, self.session)
        await self.manager._ensure_keep_alive_tab(browser, self.session)
        await browser.install_recorder()
        self._start_watcher()
        return browser

    async def _disconnect_browser(self) -> None:
        self._stop_watcher()
        self._recorded_pages.clear()
        browser, self._browser = self._browser, None
        if browser is not None:
            try:
                await browser.close()
            except Exception as ex:
                logger.debug("Could not close browser runtime: %s", ex)

    async def close(self) -> None:
        """Disconnect the runtime (the Chromium container keeps running)."""
        self._closed = True
        await self._disconnect_browser()

    def _touch(self) -> None:
        self._last_used = time.monotonic()

    def _start_watcher(self) -> None:
        if self._watch_task is not None and not self._watch_task.done():
            return
        try:
            self._watch_task = asyncio.get_running_loop().create_task(self._watch())
        except RuntimeError:
            self._watch_task = None

    def _stop_watcher(self) -> None:
        task, self._watch_task = self._watch_task, None
        if task is None or task.done():
            return
        try:
            if task is asyncio.current_task():
                # The watcher itself is disconnecting the idle browser; it will
                # exit after this call, so cancelling it here would interrupt
                # the close sequence.
                return
            task.cancel()
        except RuntimeError:
            pass

    async def _watch(self) -> None:
        """Drain human events and disconnect an idle driver.

        Runs while a browser connection exists.  The lock keeps a drain from
        racing with an action; a 1 s cadence is fast enough to feel live and
        cheap enough to leave open.
        """
        while not self._closed and self._browser is not None:
            try:
                await asyncio.sleep(1.0)
                if self._browser is None:
                    break
                async with self._lock:
                    if self._browser is None:
                        break
                    await self._drain_user_events_locked()
                    if self.session.user_is_active():
                        # Keep the recorder alive while the human is working,
                        # even if the AI has not acted for a while.
                        self._touch()
                    if time.monotonic() - self._last_used > self.idle_seconds:
                        logger.info(
                            "Idle browser runtime for session %s; disconnecting driver",
                            str(self.session.id)[:8],
                        )
                        await self._disconnect_browser()
                        break
            except asyncio.CancelledError:
                break
            except Exception as ex:
                logger.debug("Browser runtime watcher error: %s", ex)
        self._watch_task = None

    # ------------------------------------------------------------------
    # Control lease
    # ------------------------------------------------------------------
    def _refresh_session(self) -> None:
        """Reload the control fields written by the REST/UI layer."""
        latest = self.manager.get_session(getattr(self.session, "id", ""))
        if latest is not None:
            self.session = latest
            if self._browser is not None:
                self._browser.session = latest

    async def _wait_for_control(self, read_only: bool = False) -> None:
        self._refresh_session()
        if read_only:
            return
        if self.session.can_ai_act():
            return
        if self.session.controller == "user":
            reason = self.session.handoff_reason or "the user is controlling the page"
            raise BrowserControlError(
                f"The AI does not have control of this browser: {reason}. "
                "Wait for the user to give control back."
            )
        # Recent user input: give the human a short window to finish typing.
        deadline = time.monotonic() + DEFAULT_USER_WAIT_SECONDS
        while time.monotonic() < deadline:
            await asyncio.sleep(0.25)
            self._refresh_session()
            if self.session.can_ai_act():
                return
        raise BrowserControlError(
            "The user is interacting with the page; the AI paused to avoid typing "
            "over their input. Call browser_activity to see what changed, then retry."
        )

    def request_handoff(self, reason: str, chat_id: Optional[str] = None) -> None:
        """Pause the AI and ask the human to take over."""
        self.session.request_handoff(reason, chat_id=chat_id)
        self.manager.save_session(self.session)
        self.manager.log_activity(
            self.session,
            actor="system",
            action="handoff",
            chat_id=chat_id,
            params={"reason": reason},
            url=self.session.current_url,
            title=self.session.current_title,
        )

    def release(self, chat_id: Optional[str] = None) -> None:
        """Give control back to the AI."""
        self.session.set_controller("ai", chat_id=chat_id)
        self.manager.save_session(self.session)
        self.manager.log_activity(
            self.session, actor="system", action="resume", chat_id=chat_id
        )

    def take_control(self, chat_id: Optional[str] = None, reason: Optional[str] = None) -> None:
        """Move the control lease to the human."""
        self.session.set_controller("user", chat_id=chat_id, reason=reason)
        self.session.mark_user_active(seconds=600)
        self.manager.save_session(self.session)
        self.manager.log_activity(
            self.session, actor="user", action="take_control", chat_id=chat_id,
            params={"reason": reason},
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    async def run(self, method: str, *args, read_only: bool = False, force: bool = False, **kwargs):
        """Run one browser method on the shared connection.

        Args:
            method: ``Browser`` method name (``navigate``, ``click``...).
            read_only: Read actions are allowed while the human is active.
            *args/**kwargs: Forwarded to the method.
        """
        if self._closed:
            raise RuntimeError("Browser runtime is closed")
        read_only = read_only or method in {
            "get_text", "get_links", "get_snapshot", "get_content", "get_screenshot"
        } or method in READ_ONLY_ACTIONS
        if not force:
            await self._wait_for_control(read_only=read_only)
        async with self._lock:
            browser = await self._ensure_browser()
            self._touch()
            await browser.set_actor("ai")
            try:
                result = await getattr(browser, method)(*args, **kwargs)
            except Exception:
                if not browser.is_alive():
                    await self._disconnect_browser()
                raise
            finally:
                try:
                    await browser.set_actor("user")
                except Exception:
                    pass
            # Mark the AI action before draining so a navigation it caused is
            # not attributed to the human.
            self._last_ai_action = time.monotonic()
            await self._drain_user_events_locked()
            return result

    async def run_steps(
        self,
        steps: List[Dict[str, Any]],
        variables: Optional[Dict[str, Any]] = None,
        *,
        read_only: bool = False,
        force: bool = False,
        on_step: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Execute a whole action list on one connection under one lease."""
        if self._closed:
            raise RuntimeError("Browser runtime is closed")
        if not force:
            await self._wait_for_control(read_only=read_only)
        async with self._lock:
            browser = await self._ensure_browser()
            self._touch()
            await browser.set_actor("ai")
            try:
                result = await run_steps(
                    browser, steps, variables, on_step=on_step, stop_on_error=True
                )
            except Exception:
                if not browser.is_alive():
                    await self._disconnect_browser()
                raise
            finally:
                try:
                    await browser.set_actor("user")
                except Exception:
                    pass
            # Mark the AI action before draining so a navigation it caused is
            # not attributed to the human.
            self._last_ai_action = time.monotonic()
            await self._drain_user_events_locked()
            return result

    async def run_tabs(
        self,
        action: str,
        url: Optional[str] = None,
        index: Optional[int] = None,
    ) -> Any:
        """Run a tab operation under the same lock/lease as page actions."""
        await self._wait_for_control(read_only=action == "tabs")
        async with self._lock:
            browser = await self._ensure_browser()
            self._touch()
            await browser.set_actor("ai")
            try:
                if action == "tabs":
                    result = await browser_tabs.list_tabs(browser)
                elif action == "new_tab":
                    result = await browser_tabs.open_tab(browser, url)
                elif action == "switch_tab":
                    result = await browser_tabs.switch_tab(browser, index)
                elif action == "close_tab":
                    result = await browser_tabs.close_tab(browser, index)
                else:
                    raise ValueError(f"unknown tab action '{action}'")
                self._last_ai_action = time.monotonic()
                return result
            finally:
                try:
                    await browser.set_actor("user")
                except Exception:
                    pass

    async def drain(self) -> Dict[str, Any]:
        """Public drain used by the activity endpoint (no action performed)."""
        async with self._lock:
            browser = await self._ensure_browser()
            self._touch()
            await self._drain_user_events_locked()
            return {
                "url": self.session.current_url,
                "title": self.session.current_title,
                "controller": self.session.controller,
            }

    async def snapshot(self) -> Dict[str, Any]:
        """Compact page snapshot (read-only, allowed while the human drives)."""
        return await self.run("get_snapshot", read_only=True)

    async def state(self) -> Dict[str, Any]:
        """Return cheap status for the diagnostics/status tools."""
        self._refresh_session()
        connected = bool(self._browser is not None and self._browser.is_alive())
        tabs = []
        if connected:
            try:
                async with self._lock:
                    tabs = [tab.get("index") for tab in await browser_tabs.list_tabs(self._browser)]
            except Exception:
                tabs = []
        return {
            "session_id": self.session.id,
            "status": self.session.status,
            "connected": connected,
            "controller": self.session.controller,
            "handoff_reason": self.session.handoff_reason,
            "user_active": self.session.user_is_active(),
            "user_active_until": self.session.user_active_until,
            "current_url": self.session.current_url,
            "current_title": self.session.current_title,
            "tabs": tabs,
            "connection_age_s": round(time.monotonic() - self._connected_at, 1) if connected else None,
            "last_used_s": round(time.monotonic() - self._last_used, 1) if self._last_used else None,
        }

    # ------------------------------------------------------------------
    # Human event capture
    # ------------------------------------------------------------------
    async def _drain_user_events_locked(self) -> None:
        """Read the in-page recorder buffers and persist human actions.

        The user can switch tabs in the VNC view, so every page is drained (not
        just the one the AI last drove).  The visible page becomes the AI's
        active page: following the human's tab is the whole point of
        co-browsing.  Called under the runtime lock.
        """
        browser = self._browser
        if browser is None or not browser.is_alive():
            return
        try:
            pages = list(browser.context.pages) if browser.context else [browser.page]
        except Exception:
            pages = [browser.page]

        visible = None
        all_events = []
        url = ""
        title = ""
        for page in pages:
            if page is None:
                continue
            try:
                is_visible = await asyncio.wait_for(
                    page.evaluate("document.visibilityState === 'visible'"), timeout=1.0
                )
                if is_visible:
                    visible = page
            except Exception:
                continue
            if id(page) not in self._recorded_pages:
                try:
                    await asyncio.wait_for(browser.install_recorder_on(page), timeout=1.5)
                except Exception:
                    pass
                self._recorded_pages.add(id(page))
            try:
                data = await asyncio.wait_for(browser.drain_events(page), timeout=1.5)
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            all_events.extend(data.get("events") or [])
            if page is browser.page:
                url = (data.get("url") or "").strip()
                title = (data.get("title") or "").strip()
                if url:
                    self.session.current_url = url
                if title:
                    self.session.current_title = title

        # The human switched tabs in the live view: follow the visible tab.
        if visible is not None and visible is not browser.page:
            try:
                if not browser_tabs.is_keep_alive_page(visible) and not visible.is_closed():
                    browser.page = visible
                    self._recorded_pages.add(id(visible))
                    await browser.install_recorder_on(visible)
                    await browser._sync_location()
                    url = browser.session.current_url or url
                    title = browser.session.current_title or title
                    self.session.mark_user_active(seconds=10)
                    self.manager.log_activity(
                        self.session,
                        actor="user",
                        action="switch_tab",
                        params={"url": url},
                        url=url,
                        title=title,
                    )
            except Exception as ex:
                logger.debug("Could not follow the user's visible tab: %s", ex)

        seen = set()
        for event in all_events:
            if not isinstance(event, dict):
                continue
            target = event.get("target") or {}
            dedupe_key = (
                event.get("kind"),
                int(float(event.get("ts") or 0) // 500),
                (target or {}).get("selector"),
                (target or {}).get("text"),
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            params = {
                "target": {
                    "tag": target.get("tag"),
                    "id": target.get("id"),
                    "name": target.get("name"),
                    "role": target.get("role"),
                    "type": target.get("type"),
                    "text": (target.get("text") or "")[:120],
                    "selector": target.get("selector"),
                }
            }
            if target.get("value") is not None and not target.get("sensitive"):
                params["value"] = str(target.get("value"))[:120]
            if target.get("value_length") is not None:
                params["value_length"] = target.get("value_length")
            if target.get("sensitive"):
                params["sensitive"] = True
            if event.get("x") is not None or event.get("y") is not None:
                params.update({"x": event.get("x"), "y": event.get("y")})
            self.session.mark_user_active(seconds=10)
            self.manager.log_activity(
                self.session,
                actor="user",
                action=str(event.get("kind") or "input"),
                params=params,
                url=event.get("url") or url,
                title=title,
                result={"client_ts": event.get("ts")},
            )

        # Detect a user navigation that happened while no AI action was running.
        if (
            url
            and url != self._last_url
            and time.monotonic() - self._last_ai_action > AI_NAVIGATION_GRACE_SECONDS
        ):
            self.session.mark_user_active(seconds=10)
            self.manager.log_activity(
                self.session,
                actor="user",
                action="navigate",
                params={"url": url},
                url=url,
                title=title,
            )
        self._last_url = url or self._last_url

        # ``log_activity`` already persists the session for each event.
