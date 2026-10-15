"""
Browser session tools for codx-junior agents.

These tools let the LLM drive a real, isolated Firefox browser running in a
Docker container (managed by ``BrowserManager``). The browser is exposed to the
user through the web/VNC endpoint stored on the session.

Sessions are created with a human-readable ``name`` and can be shared by several
chats at once (``session.chat_ids``).

Tools
-----
- ``start_session``      – create & start (or resume) a browser session.
- ``browse_action``      – navigate / click / fill / execute JS / read text.
- ``get_screenshot``     – capture a PNG screenshot of the current page.
- ``get_source_code``    – return the current page HTML.
- ``finish_session``     – stop (and by default delete) the session, persisting
                           the Firefox profile.

Settings
--------
Every tool receives ``settings`` (CODXJuniorSettings) through the
``project_settings`` injection mechanism. All tools are ``async`` and return a
:class:`ToolResponse` (dual-response) so the chat can render a user-facing
summary while the model receives the machine-readable content.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from codx.junior.settings import CODXJuniorSettings
from .model import ToolResponse, ToolSettings

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
}

#: Hard cap on the HTML returned by ``get_source_code`` (keeps LLM context sane).
MAX_SOURCE_CHARS = 60000


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


def _summary(session) -> str:
    """Build a short human-readable summary of a session."""
    return (
        f"session_id={session.id}\n"
        f"name={session.name or '(unnamed)'}\n"
        f"status={session.status}\n"
        f"chats={', '.join(session.chat_ids) or '(none)'}\n"
        f"vnc_url={session.vnc_url or '(starting)'}\n"
        f"current_url={session.current_url or '(blank)'}"
    )


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


async def start_session(name: str = None, chat_id: str = None, **kwargs) -> ToolResponse:
    """
    Start (or resume) a browser session.

    Creates and starts an isolated Firefox container for the chat and returns
    the ``session_id`` plus the VNC URL the user can open to co-navigate.

    Args:
        name: Human-readable session name given at creation (defaults to a
            timestamped name when omitted).
        chat_id: Associated chat id (used to reuse an existing running session).
        **kwargs: Injected ``settings``.

    Returns:
        ToolResponse with the session details.
    """
    settings = _settings_from(kwargs)
    manager = _manager(settings)

    session_name = (name or "").strip() or f"Browser {datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

    try:
        existing = manager.get_session_for_chat(chat_id) if chat_id else None
        if existing and existing.status == "running":
            return ToolResponse(
                user_response=f"♻️ Browser session already running.\n```\n{_summary(existing)}\n```",
                llm_response=(
                    "A browser session is already running for this chat. "
                    f"Use this session_id in subsequent calls: {existing.id}."
                ),
            )

        session = await asyncio.to_thread(manager.create_session, session_name, chat_id)
        _persist_to_chat(settings, session, chat_id)

        llm = (
            f"Browser session '{session.name}' started. session_id: {session.id}. "
            f"Live view (VNC): {session.vnc_url}. "
            "Use browse_action/get_screenshot/get_source_code with this session_id. "
            "Call finish_session when done."
        )
        return ToolResponse(
            user_response=f"✅ Browser session '{session.name}' ready.\n```\n{_summary(session)}\n```",
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
    session_id: str = None,
    chat_id: str = None,
    **kwargs,
) -> ToolResponse:
    """
    Perform an action on the shared browser page.

    Args:
        action: One of ``navigate``, ``click``, ``fill``, ``execute``, ``text``.
        url: Target URL (for ``navigate``).
        selector: CSS selector (for ``click`` / ``fill``).
        value: Text to fill (for ``fill``).
        script: JavaScript to run (for ``execute``; use ``return ...``).
        session_id: Session to act on (returned by ``start_session``).
        chat_id: Alternative to ``session_id`` — resolves the chat's session.
        **kwargs: Injected ``settings``.

    Returns:
        ToolResponse with the action result.
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
        return ToolResponse(
            user_response=f"❌ Session is not running (status: {session.status}).",
            llm_response=f"Session {session.id} is not running (status: {session.status}).",
        )

    action = (action or "").lower().strip()
    browser = await manager.connect_browser(session)
    try:
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
            text = await browser.get_text()
            text = (text or "").strip()
            data = f"page text:\n{text[:8000]}"

        else:
            raise ValueError(
                f"unknown action '{action}' (use navigate|click|fill|execute|text)"
            )

        session.mark_active()
        manager.save_session(session)
        logger.info("browse_action '%s' completed for session %s", action, session.id[:8])

        return ToolResponse(
            user_response=f"✅ `{action}` done on session {session.id[:8]}.\n\n{data}",
            llm_response=f"Action '{action}' on session {session.id} succeeded.\n{data}",
        )
    except Exception as ex:
        logger.exception("browse_action failed: %s", ex)
        return ToolResponse(
            user_response=f"❌ `{action}` failed: {ex}",
            llm_response=f"Action '{action}' on session {session.id} failed: {ex}",
        )
    finally:
        await browser.close()


async def get_screenshot(
    session_id: str = None,
    chat_id: str = None,
    **kwargs,
) -> ToolResponse:
    """
    Take a screenshot of the current page.

    Args:
        session_id: Session to capture (or ``chat_id`` to resolve it).
        chat_id: Alternative to ``session_id``.
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

    browser = await manager.connect_browser(session)
    try:
        data_uri = await browser.get_screenshot()
        session.mark_active()
        manager.save_session(session)
        return ToolResponse(
            user_response=f"📸 Screenshot of session {session.id[:8]}:\n\n![screenshot]({data_uri})",
            llm_response=f"Screenshot captured for session {session.id}.",
        )
    except Exception as ex:
        logger.exception("get_screenshot failed: %s", ex)
        return ToolResponse(
            user_response=f"❌ Screenshot failed: {ex}",
            llm_response=f"Screenshot failed for session {session.id}: {ex}",
        )
    finally:
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

    browser = await manager.connect_browser(session)
    try:
        html = await browser.get_content()
        truncated = (html or "")[:MAX_SOURCE_CHARS]
        session.mark_active()
        manager.save_session(session)
        return ToolResponse(
            user_response=f"📄 Source of session {session.id[:8]} (url: {session.current_url}):\n```html\n{truncated}\n```",
            llm_response=f"HTML source for session {session.id} (url: {session.current_url}):\n{truncated}",
        )
    except Exception as ex:
        logger.exception("get_source_code failed: %s", ex)
        return ToolResponse(
            user_response=f"❌ Failed to read source: {ex}",
            llm_response=f"Source retrieval failed for session {session.id}: {ex}",
        )
    finally:
        await browser.close()


async def finish_session(
    session_id: str = None,
    chat_id: str = None,
    delete: bool = True,
    **kwargs,
) -> ToolResponse:
    """
    Finish a browser session, persisting its profile.

    Args:
        session_id: Session to finish (or ``chat_id`` to resolve it).
        chat_id: Alternative to ``session_id``.
        delete: When True (default) the container is removed and the session
            folder deleted. When False the container is only stopped (the
            session can be restarted later).
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
            llm_response=f"Browser session {session.id} {verb}. Profile persisted.",
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
            "Start (or resume) a real, isolated Firefox browser session. Provide a short, "
            "human-readable name for the session. Returns a session_id (use it in the other "
            "browser tools) and a VNC url the user can open to watch/co-navigate. A session "
            "may be shared by several chats."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Human-readable name for the session (e.g. 'flight search').",
                },
                "chat_id": {
                    "type": "string",
                    "description": "Chat id used to reuse an existing running session and to connect this chat to it (optional).",
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
            "execute (script), text (read visible page text)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["navigate", "click", "fill", "execute", "text"],
                    "description": "Action to perform on the page.",
                },
                "session_id": {
                    "type": "string",
                    "description": "Session id returned by start_session.",
                },
                "url": {"type": "string", "description": "Target URL (navigate)."},
                "selector": {
                    "type": "string",
                    "description": "CSS selector (click / fill).",
                },
                "value": {"type": "string", "description": "Text to fill (fill)."},
                "script": {
                    "type": "string",
                    "description": "JavaScript to run (execute); use 'return ...' to get a value.",
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
                }
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

FINISH_SESSION_TOOL_JSON = {
    "type": "function",
    "function": {
        "name": "finish_session",
        "description": (
            "Finish the browser session, persisting its profile. By default the "
            "container is deleted; set delete=false to only stop it (restartable)."
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
                    "description": "Delete the container (default true) or just stop it (false).",
                },
            },
            "required": [],
        },
    },
}