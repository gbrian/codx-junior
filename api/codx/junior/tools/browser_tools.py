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
- ``get_source_code``    – return the current page HTML (prefer ``snapshot``).
- ``browser_activity``   – recent user/AI actions on the session (co-browsing
                           awareness), including real VNC input.
- ``browser_status``     – connection, tabs and who controls the page.
- ``browser_control``    – handoff / take control / give back / pause.
- ``finish_session``     – stop (default) or delete the session. Stopping keeps
                           the Chromium profile; deleting removes it too.

The tools no longer open a Playwright connection per call: ``BrowserManager``
keeps one persistent runtime per session (see ``browser/runtime.py``), which
also captures human input and runs whole scripts deterministically.

Settings
--------
Every tool receives ``settings`` (CODXJuniorSettings) through the
``project_settings`` injection mechanism and ``chat_id`` (from the running
SmolAgent) when its signature declares it.  All tools are ``async`` and return
:class:`ToolResponse` so the chat can render a user-facing summary while the
model receives machine-readable content.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from codx.junior.settings import CODXJuniorSettings
from codx.junior.browser import tabs as browser_tabs
from codx.junior.browser import events as browser_events
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
MAX_SOURCE_CHARS = 20000
#: Hard cap on visible text returned by ``browse_action(text)``.
MAX_TEXT_CHARS = 8000

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
    """Return the cached BrowserManager (owns the persistent runtimes)."""
    from codx.junior.browser.browser_manager import get_browser_manager
    return get_browser_manager(settings)


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
                    existing = await manager.restart_session(existing.id)
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
        # The runtime owns the recorder/watcher; warm it in the background so
        # the first human click is captured even before the AI acts.
        try:
            asyncio.create_task(manager.warm_runtime(session))
        except RuntimeError:
            pass

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
    ref: str = None,
    text: str = None,
    steps: List[Dict[str, Any]] = None,
    variables: Dict[str, Any] = None,
    session_id: str = None,
    chat_id: str = None,
    **kwargs,
) -> ToolResponse:
    """
    Perform an action on the shared browser page or on its tabs.

    This is the single fast path for page interaction: the session's persistent
    runtime keeps the Playwright connection open, so an action no longer pays a
    ~0.5 s connect/disconnect cost.  For several actions use ``action="batch"``
    (or a saved script with ``run_browser_script``): the whole list runs on one
    connection and one LLM turn.

    Args:
        action: One of ``navigate``, ``click``, ``fill``, ``execute``,
            ``text``, ``links``, ``snapshot``, ``back``, ``forward``,
            ``refresh``, ``wait``, ``press``, ``select``, ``hover``,
            ``scroll``, ``tabs``, ``new_tab``, ``switch_tab``, ``close_tab``,
            ``batch``.
        url: Target URL (navigate/new_tab) or URL fragment to wait for.
        selector: CSS selector (element actions).
        value: Text to fill or option to select.
        script: JavaScript to run (for ``execute``; use ``return ...``).
        key: Keyboard key for ``press``.
        timeout: Timeout in milliseconds for waits.
        index: Tab index for ``switch_tab`` / ``close_tab``.
        x: Horizontal scroll offset.
        y: Vertical scroll offset.
        ref: Element ref returned by ``snapshot`` (preferred over CSS).
        text: Visible text to click/wait for.
        steps: Action list for ``batch``.
        variables: ``{{name}}`` values for ``batch``.
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
        try:
            session = await manager.restart_session(session.id)
        except Exception as ex:
            return ToolResponse(
                user_response=f"❌ Session is not running and could not be restarted: {ex}",
                llm_response=f"Session {session.id} is not running (status: {session.status}) and restart failed: {ex}",
            )
        if not session:
            return ToolResponse(
                user_response="❌ The browser session no longer exists.",
                llm_response="The browser session was deleted or cannot be resolved.",
            )

    action = (action or "").lower().strip()
    params = {
        key_name: value
        for key_name, value in {
            "url": url, "selector": selector, "value": value, "script": script,
            "key": key, "timeout": timeout, "index": index, "x": x, "y": y,
            "ref": ref, "text": text,
        }.items()
        if value is not None
    }
    if action == "batch":
        params["steps"] = len(steps or [])
    started_at = time.monotonic()
    runtime = None
    try:
        runtime = await manager.get_runtime(session)
        if action == "navigate":
            if not url:
                raise ValueError("url is required for navigate")
            title = await runtime.run("navigate", url)
            data = f"navigated to {url}\ntitle: {title}"

        elif action == "click":
            if ref:
                await runtime.run("click_ref", ref)
                data = f"clicked ref {ref}"
            elif text:
                await runtime.run("click_text", text)
                data = f"clicked text {text!r}"
            elif selector:
                await runtime.run("click", selector)
                data = f"clicked {selector}"
            else:
                raise ValueError("click needs ref, selector or text")

        elif action == "fill":
            if value is None:
                raise ValueError("value is required for fill")
            if ref:
                await runtime.run("fill_ref", ref, str(value))
                data = f"filled ref {ref}"
            elif selector:
                await runtime.run("fill", selector, str(value))
                data = f"filled {selector}"
            else:
                raise ValueError("fill needs ref or selector")

        elif action == "execute":
            if not script:
                raise ValueError("script is required for execute")
            result = await runtime.run("execute_script", script)
            serialized = json.dumps(result, ensure_ascii=False, default=str)
            data = f"script result: {serialized[:4000]}"

        elif action in ("text", "read"):
            page_text = (await runtime.run("get_text", read_only=True) or "").strip()
            data = f"page text:\n{page_text[:MAX_TEXT_CHARS]}"

        elif action == "links":
            links = await runtime.run("get_links", read_only=True)
            lines = [f"- {link.get('text') or '(no text)'} → {link.get('href')}" for link in links[:200]]
            data = f"links ({len(links)}):\n" + "\n".join(lines)

        elif action in ("snapshot", "page"):
            snapshot = await runtime.run("get_snapshot", read_only=True)
            data = _format_snapshot(snapshot)

        elif action == "back":
            title = await runtime.run("go_back")
            data = f"went back\ntitle: {title}"

        elif action == "forward":
            title = await runtime.run("go_forward")
            data = f"went forward\ntitle: {title}"

        elif action == "refresh":
            title = await runtime.run("reload")
            data = f"page refreshed\ntitle: {title}"

        elif action == "wait":
            if text:
                await runtime.run("wait_for_text", str(text), timeout=timeout or 5000)
                data = f"text appeared: {text!r}"
            elif selector:
                await runtime.run("wait_for_selector", selector, timeout=timeout or 5000)
                data = f"element appeared: {selector}"
            elif url:
                await runtime.run("wait_for_url", url, timeout=timeout or 5000)
                data = f"url matched: {url}"
            else:
                raise ValueError("wait needs text, selector or url")

        elif action == "press":
            if not selector or not key:
                raise ValueError("selector and key are required for press")
            await runtime.run("press", selector, key)
            data = f"pressed {key} on {selector}"

        elif action == "select":
            if not selector or value is None:
                raise ValueError("selector and value are required for select")
            await runtime.run("select", selector, value)
            data = f"selected {value} on {selector}"

        elif action == "hover":
            if not selector:
                raise ValueError("selector is required for hover")
            await runtime.run("hover", selector)
            data = f"hovered {selector}"

        elif action == "scroll":
            await runtime.run("scroll", x=x or 0, y=y or 0)
            data = f"scrolled by x={x or 0}, y={y or 0}"

        elif action == "tabs":
            tabs = await runtime.run_tabs("tabs")
            data = f"open tabs ({len(tabs)}):\n" + browser_tabs.format_tabs(tabs)

        elif action == "new_tab":
            tab = await runtime.run_tabs("new_tab", url=url)
            data = (
                f"opened tab [{tab['index']}] {tab['title'] or '(untitled)'}\n"
                f"url: {tab['url']}"
            )

        elif action == "switch_tab":
            tab = await runtime.run_tabs("switch_tab", index=index)
            data = (
                f"switched to tab [{tab['index']}] {tab['title'] or '(untitled)'}\n"
                f"url: {tab['url']}"
            )

        elif action == "close_tab":
            tab = await runtime.run_tabs("close_tab", index=index)
            data = (
                f"closed tab [{tab['closed_index']}] "
                f"{tab['closed_title'] or tab['closed_url']}\n"
                f"active tab is now [{tab['index']}] {tab['title'] or '(untitled)'}\n"
                f"url: {tab['url']}"
            )

        elif action == "batch":
            if not steps:
                raise ValueError("steps is required for batch")
            result = await runtime.run_steps(steps, variables or {})
            data = _format_batch(result)

        else:
            raise ValueError(
                "unknown action '%s' (use navigate|click|fill|execute|text|links|"
                "snapshot|back|forward|refresh|wait|press|select|hover|scroll|"
                "tabs|new_tab|switch_tab|close_tab|batch)" % action
            )

        session = getattr(runtime, "session", None) or session
        session.mark_active()
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
        control_error = ex.__class__.__name__ == "BrowserControlError"
        logger.info("browse_action '%s' stopped: %s", action, ex)
        session = getattr(runtime, "session", None) or session
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
        if control_error:
            return ToolResponse(
                user_response=(
                    f"⏸ Paused: {ex}\n\n"
                    f"The user is driving. [Open the live browser]({session.vnc_url or ''}) "
                    "and continue when they hand control back."
                ),
                llm_response=(
                    f"The AI paused because the human has control of the shared browser: {ex}\n"
                    f"Live view: {session.vnc_url}. Use browser_activity to see what the user did, "
                    "or browser_control(action='status'). Do not retry until the user gives control back."
                ),
            )
        return ToolResponse(
            user_response=f"❌ `{action}` failed: {ex}",
            llm_response=f"Action '{action}' on session {session.id} failed: {ex}",
        )


def _format_snapshot(snapshot: Dict[str, Any]) -> str:
    """Render a snapshot compactly for the model (JSON, bounded)."""
    if not isinstance(snapshot, dict):
        return str(snapshot)
    payload = dict(snapshot)
    interactive = payload.get("interactive") or []
    payload["interactive"] = interactive[:80]
    text = payload.get("text") or ""
    payload["text"] = text[:4000]
    return json.dumps(payload, ensure_ascii=False, indent=None)[:14000]


def _format_batch(result: Dict[str, Any]) -> str:
    """Render a batch/script result without flooding the context."""
    lines = []
    for step in result.get("steps") or []:
        status = "ok" if step.get("ok") else "FAIL"
        lines.append(
            f"- [{step.get('index')}] {status} {step.get('action')} ({step.get('ms')} ms)"
            + (f" — {step.get('error')}" if step.get("error") else "")
        )
    summary = (
        f"batch {'ok' if result.get('ok') else 'failed'} in {result.get('ms')} ms"
        + (f" at step {result.get('failed_step')}: {result.get('error')}" if result.get("error") else "")
    )
    outputs = result.get("outputs") or {}
    if outputs:
        summary += "\noutputs: " + json.dumps(outputs, ensure_ascii=False, default=str)[:4000]
    return summary + ("\n" + "\n".join(lines) if lines else "")


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
    try:
        runtime = await manager.get_runtime(session)
        data_uri = await runtime.run("get_screenshot", full_page=full_page, read_only=True)
        session = getattr(runtime, "session", None) or session
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
        logger.info("get_screenshot failed: %s", ex)
        manager.log_activity(
            session, actor="ai", action="screenshot", chat_id=chat_id,
            success=False, error=str(ex),
            duration_ms=(time.monotonic() - started_at) * 1000,
        )
        return ToolResponse(
            user_response=f"❌ Screenshot failed: {ex}",
            llm_response=f"Screenshot failed for session {session.id}: {ex}",
        )


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
    try:
        runtime = await manager.get_runtime(session)
        html = await runtime.run("get_content", read_only=True)
        truncated = (html or "")[:MAX_SOURCE_CHARS]
        session = getattr(runtime, "session", None) or session
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
        logger.info("get_source_code failed: %s", ex)
        manager.log_activity(
            session, actor="ai", action="source", chat_id=chat_id,
            success=False, error=str(ex),
            duration_ms=(time.monotonic() - started_at) * 1000,
        )
        return ToolResponse(
            user_response=f"❌ Failed to read source: {ex}",
            llm_response=f"Source retrieval failed for session {session.id}: {ex}",
        )


async def browser_activity(
    session_id: str = None,
    chat_id: str = None,
    limit: int = 30,
    actor: str = None,
    since: str = None,
    **kwargs,
) -> ToolResponse:
    """
    Return the recent user/AI actions on the shared browser session.

    This is the co-browsing awareness tool.  Human clicks, edits, submits and
    scrolls performed in the live VNC view are captured by the in-page recorder
    and drained by the session runtime, so they appear here as ``actor=user``
    entries (input values are redacted).  Use ``since`` after a long action to
    get only what changed, and ``actor="user"`` to ignore the AI's own steps.
    """
    settings = _settings_from(kwargs)
    manager = _manager(settings)
    session = _resolve_session(manager, session_id=session_id, chat_id=chat_id)

    if not session:
        return ToolResponse(
            user_response="❌ No browser session found.",
            llm_response="No browser session available. Start one with start_session.",
        )

    # Pick up events that happened since the last drain (the watcher runs every
    # second, but a just-finished user edit must be visible immediately).
    runtime = manager.peek_runtime(session.id)
    if runtime is not None:
        try:
            await runtime.drain()
        except Exception as ex:
            logger.debug("browser_activity drain failed: %s", ex)

    entries = manager.get_activity(session.id, limit=max(int(limit or 30) * 3, 100))
    if actor:
        entries = [entry for entry in entries if (entry.get("actor") or "") == actor]
    if since:
        entries = [entry for entry in entries if (entry.get("ts") or "") >= since]
    entries = entries[-max(1, min(int(limit or 30), 200)):]
    if not entries:
        return ToolResponse(
            user_response=f"🧾 No activity recorded yet for session {session.id[:8]}.",
            llm_response=f"No activity recorded for session {session.id}.",
        )

    lines = []
    for entry in entries:
        actor_name = entry.get("actor") or "?"
        action = entry.get("action") or "?"
        status = "ok" if entry.get("success", True) else "error"
        url = entry.get("url") or ""
        target = (entry.get("params") or {}).get("target") or {}
        if not isinstance(target, dict):
            target = {"text": str(target)}
        detail = target.get("text") or target.get("selector") or target.get("name") or ""
        if detail:
            detail = f" · {str(detail)[:80]}"
        lines.append(f"- [{entry.get('ts')}] {actor_name}: {action}{detail} ({status}) {url}".rstrip())
    text = "\n".join(lines)
    session = getattr(runtime, "session", None) or session
    control = (
        f"controller={session.controller}"
        + (f", handoff={session.handoff_reason}" if session.handoff_reason else "")
        + (", user_active=yes" if session.user_is_active() else "")
    )
    return ToolResponse(
        user_response=f"🧾 Recent activity for session {session.id[:8]}:\n{text}",
        llm_response=(
            f"Recent activity for session {session.id} ({control}):\n{text}"
        ),
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
        runtime = manager.peek_runtime(session.id)
        if runtime is not None:
            await runtime.close()
            manager._runtimes.pop(session.id, None)
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


async def browser_status(
    session_id: str = None,
    chat_id: str = None,
    **kwargs,
) -> ToolResponse:
    """Return cheap status of the shared browser (connection, controller, tabs)."""
    settings = _settings_from(kwargs)
    manager = _manager(settings)
    session = _resolve_session(manager, session_id=session_id, chat_id=chat_id)
    if not session:
        return ToolResponse(
            user_response="❌ No browser session found.",
            llm_response="No browser session available. Start one with start_session.",
        )
    try:
        runtime = await manager.get_runtime(session)
        state = await runtime.state()
    except Exception as ex:
        return ToolResponse(
            user_response=f"❌ Could not read the browser status: {ex}",
            llm_response=f"Browser status unavailable: {ex}",
        )
    text = "\n".join(f"{key}: {value}" for key, value in state.items())
    return ToolResponse(
        user_response=f"ℹ️ Browser status for session {session.id[:8]}:\n```\n{text}\n```",
        llm_response=f"Browser status for session {session.id}:\n{text}",
    )


async def browser_control(
    action: str,
    reason: str = None,
    session_id: str = None,
    chat_id: str = None,
    **kwargs,
) -> ToolResponse:
    """Manage the human/AI control lease of the shared browser.

    Actions:
        ``status``      — show who is driving (alias of browser_status);
        ``handoff``     — pause the AI and ask the human to take over (MFA,
                          captcha, approval). The AI must stop after this call;
        ``take_control``— the human takes control and keeps it;
        ``give_back``   — hand control back to the AI;
        ``pause``       — alias of take_control with an AI reason.
    """
    settings = _settings_from(kwargs)
    manager = _manager(settings)
    session = _resolve_session(manager, session_id=session_id, chat_id=chat_id)
    if not session:
        return ToolResponse(
            user_response="❌ No browser session found.",
            llm_response="No browser session available. Start one with start_session.",
        )
    action = (action or "status").strip().lower()
    try:
        runtime = await manager.get_runtime(session)
    except Exception as ex:
        return ToolResponse(
            user_response=f"❌ Could not open the browser runtime: {ex}",
            llm_response=f"Browser runtime unavailable: {ex}",
        )
    if action in ("status", "info"):
        state = await runtime.state()
        return ToolResponse(
            user_response=f"ℹ️ {state.get('controller', 'ai')} controls session {session.id[:8]}.",
            llm_response=f"Browser control state: {state}",
        )
    if action in ("handoff", "request_handoff", "request"):
        if not reason:
            return ToolResponse(
                user_response="❌ `reason` is required for a handoff.",
                llm_response="A handoff needs a short reason (login, MFA, captcha, approval...).",
            )
        runtime.request_handoff(reason, chat_id=chat_id)
        session = getattr(runtime, "session", None) or session
        browser_events.broadcast_control(session)
        return ToolResponse(
            user_response=(
                f"🙋 Handoff requested: {reason}\n\n"
                f"[Open the live browser]({session.vnc_url or ''}) and complete it, "
                "then click **I'm done** (or use Give back to AI)."
            ),
            llm_response=(
                f"Control handed to the user because: {reason}. "
                f"Live view: {session.vnc_url}. The AI is paused; do not act until the user "
                "finishes and control is given back."
            ),
        )
    if action in ("take_control", "take", "pause"):
        runtime.take_control(chat_id=chat_id, reason=reason or "paused by the AI")
        session = getattr(runtime, "session", None) or session
        browser_events.broadcast_control(session)
        return ToolResponse(
            user_response=f"⏸ The user now has control of session {session.id[:8]}.",
            llm_response=(
                "The human now controls the page. The AI must not act. "
                "Call browser_activity to follow their work."
            ),
        )
    if action in ("give_back", "release", "resume"):
        runtime.release(chat_id=chat_id)
        session = getattr(runtime, "session", None) or session
        browser_events.broadcast_control(session)
        return ToolResponse(
            user_response=f"▶️ Control returned to the AI for session {session.id[:8]}.",
            llm_response="The AI has control again. Continue from the current page state.",
        )
    return ToolResponse(
        user_response=f"❌ Unknown control action '{action}'.",
        llm_response="Use status, handoff, take_control, give_back or pause.",
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
            "Drive the shared browser page. Prefer action='snapshot' first: it returns "
            "interactive element refs (click/fill by ref) and the main text, much cheaper "
            "than full HTML. Use action='batch' for several steps in one call. "
            "Actions: navigate (url), click/fill (ref or selector or text), execute (script), "
            "text, links, snapshot, back, forward, refresh, wait (text/selector/url), "
            "press, select, hover, scroll, tabs, new_tab, switch_tab, close_tab, batch."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "navigate", "click", "fill", "execute", "text", "links",
                        "snapshot", "back", "forward", "refresh", "wait", "press",
                        "select", "hover", "scroll", "tabs", "new_tab",
                        "switch_tab", "close_tab", "batch",
                    ],
                    "description": "Action to perform on the page or on its tabs.",
                },
                "session_id": {
                    "type": "string",
                    "description": "Session id returned by start_session.",
                },
                "url": {
                    "type": "string",
                    "description": "Target URL (navigate/new_tab) or URL fragment to wait for.",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector (click / fill / wait / press / select / hover).",
                },
                "ref": {
                    "type": "string",
                    "description": "Element ref from action='snapshot' (preferred over CSS).",
                },
                "text": {
                    "type": "string",
                    "description": "Visible text to click or wait for.",
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
                    "description": "Tab index for switch_tab/close_tab (0-based, as listed by tabs).",
                },
                "x": {"type": "integer", "description": "Horizontal scroll offset."},
                "y": {"type": "integer", "description": "Vertical scroll offset."},
                "steps": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": (
                        "For action='batch': ordered steps, e.g. "
                        "[{action:'goto',url:'...'},{action:'fill',ref:'e3',value:'...'},"
                        "{action:'click',text:'Sign in'},{action:'wait',text:'Dashboard'}]."
                    ),
                },
                "variables": {
                    "type": "object",
                    "description": "Values for {{name}} placeholders in batch steps.",
                },
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
        "description": "Return the current page HTML (capped). Prefer browse_action(action='snapshot') for reading; use this only when the markup itself matters.",
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


BROWSER_STATUS_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "browser_status",
        "description": (
            "Return the shared browser status: connection, current URL/title, open tabs, "
            "who controls the page and whether the user is active. Cheap; use it before "
            "acting if you are unsure whether the browser is connected or the human took over."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session id (optional)."},
            },
            "required": [],
        },
    },
}

BROWSER_CONTROL_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "browser_control",
        "description": (
            "Manage the human/AI control lease of the shared browser. "
            "Use action='handoff' when the task needs the human (login, MFA, captcha, payment "
            "approval): the AI pauses and the UI shows a banner. Use action='give_back' after "
            "the user is done, and action='status' to inspect the lease."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "handoff", "take_control", "give_back", "pause"],
                    "description": "Control operation.",
                },
                "reason": {
                    "type": "string",
                    "description": "Human-readable reason for a handoff/pause.",
                },
                "session_id": {"type": "string", "description": "Session id (optional)."},
            },
            "required": ["action"],
        },
    },
}
