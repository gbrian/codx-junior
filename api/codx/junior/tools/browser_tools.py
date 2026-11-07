"""
Browser session tools for codx-junior agents.

These tools let the LLM drive the same real Chromium browser the user is
watching and controlling through the live VNC view (managed by
``BrowserManager``).  There is no separate "AI browser": user and AI share one
page, one set of cookies and one history.

The browser container also mounts the project folders under
``/home/<project_name>/<folder>`` and writes its downloads inside the project,
so the agent and the user exchange files with the project instead of being
isolated in the container.

Tools
-----
- ``start_session``      – create & start (or resume) a browser session.
- ``browse_action``      – navigate / click / fill / execute JS / read text /
                           back / forward / refresh / wait / press / select /
                           hover / scroll / links / tabs (list, open, switch,
                           close).
- ``get_screenshot``     – capture a PNG screenshot of the current page.
- ``get_source_code``    – return the current page HTML.
- ``browser_activity``   – recent user/AI actions on the session (co-browsing
                           awareness).
- ``finish_session``     – stop (default) or delete the session. Stopping keeps
                           the Chromium profile; deleting removes it too.

Settings
--------
Every tool receives ``settings`` (CODXJuniorSettings) through the
``project_settings`` injection mechanism and ``chat_id`` (from the running
SmolAgent) when its signature declares it.  All tools are ``async`` and return
:class:`ToolResponse` so the chat can render a user-facing summary while the
model receives machine-readable content.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from codx.junior.settings import CODXJuniorSettings
from codx.junior.browser import tabs as browser_tabs
from .model import ToolResponse

logger = logging.getLogger(__name__)

#: Settings metadata applied to every browser tool in the ``TOOLS`` registry.
#: Both ``async`` and ``is_async`` keys are provided for compatibility with the
#: two conventions present in the codebase.
BROWSER_TOOL_SETTINGS: Dict[str, Any] = {
    "async": True,
    "is_async": True,
    "project_settings": True,
    "dual_response": True,
    "scope": "chat",
    # Browser state changes between calls: never serve a cached result.
    "cache": False,
}

#: Hard cap on the HTML returned by ``get_source_code`` (keeps LLM context sane).
MAX_SOURCE_CHARS = 60000
#: Hard cap on visible text returned by ``browse_action(text)``.
MAX_TEXT_CHARS = 12000

#: Actions that operate on tabs instead of the current page content.
TAB_ACTIONS = ("tabs", "new_tab", "switch_tab", "close_tab")

#: Actions that can use an explicit tab index.
INDEX_ACTIONS = ("switch_tab", "close_tab")


def _settings_from(kwargs: Dict[str, Any]) -> CODXJuniorSettings:
    """Extract and validate injected project settings."""
    settings: CODXJuniorSettings = kwargs.get("settings")
    if not settings:
        raise Exception("Invalid project settings")
    return settings


def _manager(settings: CODXJuniorSettings):
    """Build a BrowserManager for the given settings."""
    from codx.junior.browser.browser_manager import BrowserManager
    return BrowserManager(settings)


def _resolve_session(manager, session_id: Optional[str] = None, chat_id: Optional[str] = None):
    """Resolve a session by id, falling back to the chat's shared session."""
    session = manager.get_session(session_id) if session_id else None
    if not session and chat_id:
        session = manager.get_session_for_chat(chat_id)
    return session


def _shared_folder_lines(session) -> List[str]:
    """Describe every folder mounted in the session (empty when none)."""
    return [
        f"  - {share.name or share.folder or '/'} → {share.mount_path}"
        f"{' (read-only)' if share.readonly else ''}"
        f"  [project: {share.folder or '/'}]"
        for share in session.shared_folders
    ]


def _summary(session) -> str:
    """Build a short human-readable summary of a session."""
    folders = ", ".join(share.mount_path for share in session.shared_folders) or "(none)"
    return (
        f"session_id={session.id}\n"
        f"name={session.name or '(unnamed)'}\n"
        f"status={session.status}\n"
        f"chats={', '.join(session.chat_ids) or '(none)'}\n"
        f"live_view={session.vnc_url or '(starting)'}\n"
        f"home={session.home_path or '(not shared)'}\n"
        f"mounted_folders={folders}\n"
        f"downloads={session.downloads_mount or '(none)'} (host: {session.downloads_path or '-'})\n"
        f"current_url={session.current_url or '(blank)'}\n"
        f"current_title={session.current_title or '(blank)'}"
    )


def _sharing_note(session) -> str:
    """Describe the folder mapping for the LLM (empty when nothing is shared)."""
    if not session.shares_files():
        return ""
    lines = _shared_folder_lines(session)
    note = ""
    if lines:
        note = (
            "The browser has these project folders mounted (open them with "
            "file://<mount_path>/<file>):\n" + "\n".join(lines) + "\n"
        )
    if session.downloads_path:
        note += (
            f"Downloads are saved inside the project at '{session.downloads_path}' "
            f"(browser path '{session.downloads_mount}')."
        )
    return note.strip()


def _persist_to_chat(settings: CODXJuniorSettings, session, chat_id: Optional[str]) -> None:
    """Persist a session into its chat's meta_data (best effort)."""
    if not chat_id:
        return
    try:
        from codx.junior.chat_manager import ChatManager
        chat_manager = ChatManager(settings)
        chat = chat_manager.find_by_id(chat_id)
        if chat:
            _manager(settings).save_session_to_chat(session, chat)
            chat_manager.save_chat(chat)
    except Exception as ex:
        logger.warning("Could not persist browser session to chat %s: %s", chat_id, ex)


async def start_session(
    name: str = None,
    chat_id: str = None,
    initial_url: str = None,
    description: str = None,
    share_project: bool = None,
    share_folders: List[str] = None,
    downloads_folder: str = None,
    **kwargs,
) -> ToolResponse:
    """
    Start (or resume) a browser session connected to the current chat.

    Creates and starts an isolated Chromium container.  The returned
    ``session_id`` is used by the other browser tools, and ``live_view`` is the
    URL the user opens to watch and control the same browser.

    Project folders are mounted inside the container under
    ``/home/<project_name>/<folder>`` and every download is saved inside the
    project, so files are shared between the user, the AI and the project.

    Args:
        name: Human-readable session name (defaults to a timestamped name).
        chat_id: Associated chat id (injected by SmolAgent); used to reuse the
            chat's existing session and to make it visible in the chat UI.
        initial_url: Optional URL opened when the browser starts.
        description: Optional free-form description of the session.
        share_project: Mount the whole project at ``/home/<project_name>``.
            Omit it to mount the project root only when ``share_folders`` is
            empty.
        share_folders: Project folders to mount (``["docs", "data"]``); each one
            keeps its relative path inside ``/home/<project_name>``.
        downloads_folder: Project-relative folder receiving the downloads
            (default ``.codx/browser_downloads/<session_id>``).
        **kwargs: Injected ``settings``.

    Returns:
        ToolResponse with the session details and live-view URL.
    """
    settings = _settings_from(kwargs)
    manager = _manager(settings)

    session_name = (name or "").strip() or f"Browser {datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

    try:
        existing = manager.get_session_for_chat(chat_id) if chat_id else None
        if existing:
            if existing.status != "running":
                try:
                    existing = await asyncio.to_thread(manager.restart_session, existing.id)
                except Exception as ex:
                    logger.warning("Could not restart browser session %s: %s", existing.id, ex)

            if existing and existing.status == "running":
                return ToolResponse(
                    user_response=(
                        f"♻️ Browser session already running.\n"
                        f"[Open the live browser]({existing.vnc_url})\n"
                        f"```\n{_summary(existing)}\n```"
                    ),
                    llm_response=(
                        "A browser session is already running for this chat. "
                        f"Use this session_id in subsequent calls: {existing.id}. "
                        f"Live view: {existing.vnc_url}. "
                        f"{_sharing_note(existing)}"
                    ),
                )

        session = await asyncio.to_thread(
            manager.create_session,
            session_name,
            chat_id,
            initial_url,
            description,
            share_project,
            share_folders,
            None,
            downloads_folder,
        )
        _persist_to_chat(settings, session, chat_id)

        llm = (
            f"Browser session '{session.name}' started. session_id: {session.id}. "
            f"Live view (same browser the user sees): {session.vnc_url}. "
            "Use browse_action/get_screenshot/get_source_code/browser_activity "
            "with this session_id. Call finish_session when done. "
            f"{_sharing_note(session)}"
        )
        return ToolResponse(
            user_response=(
                f"✅ Browser session '{session.name}' ready.\n"
                f"[Open the live browser]({session.vnc_url})\n"
                f"```\n{_summary(session)}\n```"
            ),
            llm_response=llm,
        )
    except Exception as ex:
        logger.exception("start_session failed: %s", ex)
        return ToolResponse(
            user_response=f"❌ Failed to start browser session: {ex}",
            llm_response=f"Failed to start browser session: {ex}",
        )


async def browse_action(
    action: str,
    url: str = None,
    selector: str = None,
    value: str = None,
    script: str = None,
    key: str = None,
    timeout: int = 5000,
    index: int = None,
    x: int = 0,
    y: int = 0,
    session_id: str = None,
    chat_id: str = None,
    **kwargs,
) -> ToolResponse:
    """
    Perform an action on the shared browser page or on its tabs.

    Args:
        action: One of ``navigate``, ``click``, ``fill``, ``execute``,
            ``text``, ``links``, ``back``, ``forward``, ``refresh``, ``wait``,
            ``press``, ``select``, ``hover``, ``scroll``, ``tabs``,
            ``new_tab``, ``switch_tab``, ``close_tab``.
        url: Target URL (for ``navigate`` and ``new_tab``).
        selector: CSS selector (for element actions).
        value: Text to fill or option to select.
        script: JavaScript to run (for ``execute``; use ``return ...``).
        key: Keyboard key for ``press``.
        timeout: Timeout in milliseconds for ``wait``.
        index: Tab index (0-based) for ``switch_tab`` / ``close_tab``; omit it to
            act on the active tab.
        x: Horizontal scroll offset.
        y: Vertical scroll offset.
        session_id: Session to act on (returned by ``start_session``).
        chat_id: Alternative to ``session_id`` — resolves the chat's session.
        **kwargs: Injected ``settings``.

    Returns:
        ToolResponse with the action result, current URL and title.
    """
    settings = _settings_from(kwargs)
    manager = _manager(settings)
    session = _resolve_session(manager, session_id=session_id, chat_id=chat_id)

    if not session:
        return ToolResponse(
            user_response="❌ No browser session found. Call `start_session` first.",
            llm_response="No browser session available. Start one with start_session.",
        )
    if session.status != "running":
        # A stopped container can usually be resumed without losing the profile.
        try:
            session = await asyncio.to_thread(manager.restart_session, session.id)
        except Exception as ex:
            return ToolResponse(
                user_response=f"❌ Session is not running and could not be restarted: {ex}",
                llm_response=f"Session {session.id} is not running (status: {session.status}) and restart failed: {ex}",
            )

    action = (action or "").lower().strip()
    params = {
        key_name: value
        for key_name, value in {
            "url": url,
            "selector": selector,
            "value": value,
            "script": script,
            "key": key,
            "timeout": timeout,
            "index": index,
            "x": x,
            "y": y,
        }.items()
        if value is not None
    }
    started_at = time.monotonic()
    browser = None
    try:
        browser = await manager.connect_browser(session)
        if action == "navigate":
            if not url:
                raise ValueError("url is required for navigate")
            title = await browser.navigate(url)
            data = f"navigated to {url}\ntitle: {title}"

        elif action == "click":
            if not selector:
                raise ValueError("selector is required for click")
            await browser.click(selector)
            data = f"clicked {selector}"

        elif action == "fill":
            if not selector or value is None:
                raise ValueError("selector and value are required for fill")
            await browser.fill(selector, value)
            data = f"filled {selector}"

        elif action == "execute":
            if not script:
                raise ValueError("script is required for execute")
            result = await browser.execute_script(script)
            data = f"script result: {result}"

        elif action in ("text", "read"):
            text = (await browser.get_text() or "").strip()
            data = f"page text:\n{text[:MAX_TEXT_CHARS]}"

        elif action == "links":
            links = await browser.get_links()
            lines = [f"- {link.get('text') or '(no text)'} → {link.get('href')}" for link in links[:200]]
            data = f"links ({len(links)}):\n" + "\n".join(lines)

        elif action == "back":
            title = await browser.go_back()
            data = f"went back\ntitle: {title}"

        elif action == "forward":
            title = await browser.go_forward()
            data = f"went forward\ntitle: {title}"

        elif action == "refresh":
            title = await browser.reload()
            data = f"page refreshed\ntitle: {title}"

        elif action == "wait":
            if not selector:
                raise ValueError("selector is required for wait")
            await browser.wait_for_selector(selector, timeout=timeout or 5000)
            data = f"element appeared: {selector}"

        elif action == "press":
            if not selector or not key:
                raise ValueError("selector and key are required for press")
            await browser.press(selector, key)
            data = f"pressed {key} on {selector}"

        elif action == "select":
            if not selector or value is None:
                raise ValueError("selector and value are required for select")
            await browser.select(selector, value)
            data = f"selected {value} on {selector}"

        elif action == "hover":
            if not selector:
                raise ValueError("selector is required for hover")
            await browser.hover(selector)
            data = f"hovered {selector}"

        elif action == "scroll":
            await browser.scroll(x=x or 0, y=y or 0)
            data = f"scrolled by x={x or 0}, y={y or 0}"

        elif action == "tabs":
            tabs = await browser_tabs.list_tabs(browser)
            data = f"open tabs ({len(tabs)}):\n" + browser_tabs.format_tabs(tabs)

        elif action == "new_tab":
            tab = await browser_tabs.open_tab(browser, url)
            data = (
                f"opened tab [{tab['index']}] {tab['title'] or '(untitled)'}\n"
                f"url: {tab['url']}"
            )

        elif action == "switch_tab":
            tab = await browser_tabs.switch_tab(browser, index)
            data = (
                f"switched to tab [{tab['index']}] {tab['title'] or '(untitled)'}\n"
                f"url: {tab['url']}"
            )

        elif action == "close_tab":
            tab = await browser_tabs.close_tab(browser, index)
            data = (
                f"closed tab [{tab['closed_index']}] "
                f"{tab['closed_title'] or tab['closed_url']}\n"
                f"active tab is now [{tab['index']}] {tab['title'] or '(untitled)'}\n"
                f"url: {tab['url']}"
            )

        else:
            raise ValueError(
                "unknown action '%s' (use navigate|click|fill|execute|text|links|"
                "back|forward|refresh|wait|press|select|hover|scroll|"
                "tabs|new_tab|switch_tab|close_tab)" % action
            )

        session.mark_active()
        manager.save_session(session)
        manager.log_activity(
            session,
            actor="ai",
            action=action,
            chat_id=chat_id,
            params=params,
            url=session.current_url,
            title=session.current_title,
            duration_ms=(time.monotonic() - started_at) * 1000,
            result={"message": data[:1000]},
        )
        logger.info("browse_action '%s' completed for session %s", action, session.id[:8])

        return ToolResponse(
            user_response=(
                f"✅ `{action}` done on session {session.id[:8]}.\n\n{data}\n\n"
                f"URL: {session.current_url or '(blank)'}\nTitle: {session.current_title or '(blank)'}"
            ),
            llm_response=(
                f"Action '{action}' on session {session.id} succeeded.\n{data}\n"
                f"URL: {session.current_url or '(blank)'}\nTitle: {session.current_title or '(blank)'}"
            ),
        )
    except Exception as ex:
        logger.exception("browse_action failed: %s", ex)
        manager.log_activity(
            session,
            actor="ai",
            action=action or "unknown",
            chat_id=chat_id,
            params=params,
            success=False,
            error=str(ex),
            duration_ms=(time.monotonic() - started_at) * 1000,
        )
        return ToolResponse(
            user_response=f"❌ `{action}` failed: {ex}",
            llm_response=f"Action '{action}' on session {session.id} failed: {ex}",
        )
    finally:
        if browser is not None:
            await browser.close()


async def get_screenshot(
    session_id: str = None,
    chat_id: str = None,
    full_page: bool = True,
    **kwargs,
) -> ToolResponse:
    """
    Take a screenshot of the current page.

    Args:
        session_id: Session to capture (or ``chat_id`` to resolve it).
        chat_id: Alternative to ``session_id``.
        full_page: Capture the whole scrollable page (default) or the viewport.
        **kwargs: Injected ``settings``.

    Returns:
        ToolResponse whose ``user_response`` embeds the PNG image.
    """
    settings = _settings_from(kwargs)
    manager = _manager(settings)
    session = _resolve_session(manager, session_id=session_id, chat_id=chat_id)

    if not session or session.status != "running":
        return ToolResponse(
            user_response="❌ No running browser session (call `start_session` first).",
            llm_response="No running browser session available for screenshot.",
        )

    started_at = time.monotonic()
    browser = None
    try:
        browser = await manager.connect_browser(session)
        data_uri = await browser.get_screenshot(full_page=full_page)
        session.mark_active()
        manager.save_session(session)
        manager.log_activity(
            session,
            actor="ai",
            action="screenshot",
            chat_id=chat_id,
            params={"full_page": bool(full_page)},
            url=session.current_url,
            title=session.current_title,
            duration_ms=(time.monotonic() - started_at) * 1000,
        )
        return ToolResponse(
            user_response=f"📸 Screenshot of session {session.id[:8]}:\n\n![screenshot]({data_uri})",
            llm_response=(
                f"Screenshot captured for session {session.id} "
                f"(url: {session.current_url or '(blank)'}, title: {session.current_title or '(blank)'})."
            ),
        )
    except Exception as ex:
        logger.exception("get_screenshot failed: %s", ex)
        manager.log_activity(
            session, actor="ai", action="screenshot", chat_id=chat_id,
            success=False, error=str(ex),
            duration_ms=(time.monotonic() - started_at) * 1000,
        )
        return ToolResponse(
            user_response=f"❌ Screenshot failed: {ex}",
            llm_response=f"Screenshot failed for session {session.id}: {ex}",
        )
    finally:
        if browser is not None:
            await browser.close()


async def get_source_code(
    session_id: str = None,
    chat_id: str = None,
    **kwargs,
) -> ToolResponse:
    """
    Return the current page HTML source.

    Args:
        session_id: Session to read (or ``chat_id`` to resolve it).
        chat_id: Alternative to ``session_id``.
        **kwargs: Injected ``settings``.

    Returns:
        ToolResponse with the (truncated) HTML.
    """
    settings = _settings_from(kwargs)
    manager = _manager(settings)
    session = _resolve_session(manager, session_id=session_id, chat_id=chat_id)

    if not session or session.status != "running":
        return ToolResponse(
            user_response="❌ No running browser session (call `start_session` first).",
            llm_response="No running browser session available for source retrieval.",
        )

    started_at = time.monotonic()
    browser = None
    try:
        browser = await manager.connect_browser(session)
        html = await browser.get_content()
        truncated = (html or "")[:MAX_SOURCE_CHARS]
        session.mark_active()
        manager.save_session(session)
        manager.log_activity(
            session,
            actor="ai",
            action="source",
            chat_id=chat_id,
            url=session.current_url,
            title=session.current_title,
            duration_ms=(time.monotonic() - started_at) * 1000,
            result={"chars": len(html or "")},
        )
        return ToolResponse(
            user_response=(
                f"📄 Source of session {session.id[:8]} "
                f"(url: {session.current_url}, title: {session.current_title}):\n"
                f"```html\n{truncated}\n```"
            ),
            llm_response=(
                f"HTML source for session {session.id} "
                f"(url: {session.current_url}, title: {session.current_title}):\n{truncated}"
            ),
        )
    except Exception as ex:
        logger.exception("get_source_code failed: %s", ex)
        manager.log_activity(
            session, actor="ai", action="source", chat_id=chat_id,
            success=False, error=str(ex),
            duration_ms=(time.monotonic() - started_at) * 1000,
        )
        return ToolResponse(
            user_response=f"❌ Failed to read source: {ex}",
            llm_response=f"Source retrieval failed for session {session.id}: {ex}",
        )
    finally:
        if browser is not None:
            await browser.close()


async def browser_activity(
    session_id: str = None,
    chat_id: str = None,
    limit: int = 30,
    **kwargs,
) -> ToolResponse:
    """
    Return the recent user/AI actions on the shared browser session.

    This lets the agent notice what the user did between tool calls (the user
    can click/type/navigate directly in the live view).  It is also the audit
    trail required for co-browsing.
    """
    settings = _settings_from(kwargs)
    manager = _manager(settings)
    session = _resolve_session(manager, session_id=session_id, chat_id=chat_id)

    if not session:
        return ToolResponse(
            user_response="❌ No browser session found.",
            llm_response="No browser session available. Start one with start_session.",
        )

    entries = manager.get_activity(session.id, limit=limit)
    if not entries:
        return ToolResponse(
            user_response=f"🧾 No activity recorded yet for session {session.id[:8]}.",
            llm_response=f"No activity recorded for session {session.id}.",
        )

    lines = []
    for entry in entries:
        actor = entry.get("actor") or "?"
        action = entry.get("action") or "?"
        status = "ok" if entry.get("success", True) else "error"
        url = entry.get("url") or ""
        lines.append(f"- [{entry.get('ts')}] {actor}: {action} ({status}) {url}".rstrip())
    text = "\n".join(lines)
    return ToolResponse(
        user_response=f"🧾 Recent activity for session {session.id[:8]}:\n{text}",
        llm_response=f"Recent activity for session {session.id}:\n{text}",
    )


async def finish_session(
    session_id: str = None,
    chat_id: str = None,
    delete: bool = False,
    **kwargs,
) -> ToolResponse:
    """
    Finish a browser session. Stopping keeps its profile; deleting removes it.

    Args:
        session_id: Session to finish (or ``chat_id`` to resolve it).
        chat_id: Alternative to ``session_id``.
        delete: When True the container is removed and the session folder
            (including its Chromium profile) is deleted. When False (default)
            the container is only stopped and the profile is preserved for a
            later restart.
        **kwargs: Injected ``settings``.

    Returns:
        ToolResponse with the finish result.
    """
    settings = _settings_from(kwargs)
    manager = _manager(settings)
    session = _resolve_session(manager, session_id=session_id, chat_id=chat_id)

    if not session:
        return ToolResponse(
            user_response="❌ No browser session found to finish.",
            llm_response="No browser session found to finish.",
        )

    try:
        if delete:
            await asyncio.to_thread(manager.delete_session, session.id)
            verb = "deleted"
        else:
            await asyncio.to_thread(manager.stop_session, session.id)
            verb = "stopped"

        logger.info("finish_session: %s session %s", verb, session.id[:8])
        return ToolResponse(
            user_response=f"🧹 Browser session {session.id[:8]} {verb}.",
            llm_response=(
                f"Browser session {session.id} {verb}. "
                + ("Profile preserved." if not delete else "Profile deleted with the session.")
                + (
                    f" Downloaded files stay in the project at '{session.downloads_path}'."
                    if session.downloads_path else ""
                )
            ),
        )
    except Exception as ex:
        logger.exception("finish_session failed: %s", ex)
        return ToolResponse(
            user_response=f"❌ Failed to finish session: {ex}",
            llm_response=f"Failed to finish session {session.id}: {ex}",
        )


# ---------------------------------------------------------------------------
# Tool JSON schemas
# ---------------------------------------------------------------------------

START_SESSION_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "start_session",
        "description": (
            "Start (or resume) the real Chromium browser shared with the user. Provide a short, "
            "human-readable name. Returns a session_id (use it in the other browser tools) and a "
            "live-view URL the user can open to watch and control the same browser. A session may "
            "be shared by several chats. Project folders are mounted inside the browser under "
            "/home/<project_name>/<folder> (open file://<mount>/<file>) and downloads are saved "
            "inside the project, so files can be shared with the user."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Human-readable name for the session (e.g. 'flight search').",
                },
                "initial_url": {
                    "type": "string",
                    "description": "Optional URL to open when the browser starts.",
                },
                "description": {
                    "type": "string",
                    "description": "Optional short description of the session.",
                },
                "share_project": {
                    "type": "boolean",
                    "description": (
                        "Mount the whole project at /home/<project_name>. Omit it to mount only "
                        "the folders listed in share_folders (or the whole project when the list "
                        "is empty)."
                    ),
                },
                "share_folders": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Project folders to mount, e.g. ['docs', 'data']. Each one keeps its "
                        "relative path inside /home/<project_name>."
                    ),
                },
                "downloads_folder": {
                    "type": "string",
                    "description": (
                        "Project folder receiving the browser downloads (default "
                        "'.codx/browser_downloads/<session_id>')."
                    ),
                },
                "chat_id": {
                    "type": "string",
                    "description": "Chat id used to reuse an existing session and make it visible in the chat UI (optional).",
                },
            },
            "required": ["name"],
        },
    },
}

BROWSE_ACTION_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "browse_action",
        "description": (
            "Drive the shared browser page. Supported actions: "
            "navigate (url), click (selector), fill (selector, value), "
            "execute (script), text (read visible page text), links (list links), "
            "back, forward, refresh, wait (selector, timeout), press (selector, key), "
            "select (selector, value), hover (selector), scroll (x, y), "
            "tabs (list the open tabs with their index), new_tab (url), "
            "switch_tab (index), close_tab (index)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "navigate", "click", "fill", "execute", "text", "links",
                        "back", "forward", "refresh", "wait", "press", "select",
                        "hover", "scroll", "tabs", "new_tab", "switch_tab",
                        "close_tab",
                    ],
                    "description": "Action to perform on the page or on its tabs.",
                },
                "session_id": {
                    "type": "string",
                    "description": "Session id returned by start_session.",
                },
                "url": {
                    "type": "string",
                    "description": "Target URL (navigate, or the page opened by new_tab).",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector (click / fill / wait / press / select / hover).",
                },
                "value": {"type": "string", "description": "Text to fill or option to select."},
                "script": {
                    "type": "string",
                    "description": "JavaScript to run (execute); use 'return ...' to get a value.",
                },
                "key": {"type": "string", "description": "Keyboard key for press (e.g. Enter)."},
                "timeout": {"type": "integer", "description": "Wait timeout in milliseconds."},
                "index": {
                    "type": "integer",
                    "description": (
                        "Tab index (0-based, as listed by action='tabs') for switch_tab and "
                        "close_tab. Omit it to act on the active tab."
                    ),
                },
                "x": {"type": "integer", "description": "Horizontal scroll offset."},
                "y": {"type": "integer", "description": "Vertical scroll offset."},
            },
            "required": ["action"],
        },
    },
}

GET_SCREENSHOT_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "get_screenshot",
        "description": "Capture a PNG screenshot of the current browser page.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session id returned by start_session.",
                },
                "full_page": {
                    "type": "boolean",
                    "description": "Capture the whole page (default true) or only the viewport.",
                },
            },
            "required": [],
        },
    },
}

GET_SOURCE_CODE_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "get_source_code",
        "description": "Return the HTML source of the current browser page.",
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session id returned by start_session.",
                }
            },
            "required": [],
        },
    },
}

BROWSER_ACTIVITY_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "browser_activity",
        "description": (
            "Return the recent actions performed by the user and the AI on the shared browser "
            "session. Use it to notice what the user did directly in the live view."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session id returned by start_session.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of recent entries (default 30).",
                },
            },
            "required": [],
        },
    },
}

FINISH_SESSION_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "finish_session",
        "description": (
            "Finish the browser session. By default the container is stopped and the "
            "Chromium profile is kept for a later restart; set delete=true to remove "
            "the container, session metadata and profile."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session id returned by start_session.",
                },
                "delete": {
                    "type": "boolean",
                    "description": "Delete the container and profile (true) or only stop it and keep the profile (false, default).",
                },
            },
            "required": [],
        },
    },
}