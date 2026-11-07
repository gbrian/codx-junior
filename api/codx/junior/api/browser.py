"""
Browser Session REST API Router

Handles CRUD operations for browser sessions with full async support.

REST Endpoints:
    GET    /api/browsers              - List all sessions
    POST   /api/browsers              - Create new session
    GET    /api/browsers/<session_id> - Get session details
    PUT    /api/browsers/<session_id> - Rename session
    DELETE /api/browsers/<session_id> - Stop & delete session
    POST   /api/browsers/<session_id>/action     - Execute browser action
    POST   /api/browsers/<session_id>/screenshot - Take screenshot
    GET    /api/browsers/<session_id>/source     - Get page source
    GET    /api/browsers/<session_id>/activity   - User/AI audit trail
    GET    /api/browsers/<session_id>/cost       - AI cost/usage summary
    POST   /api/browsers/<session_id>/restart    - Restart session
    POST   /api/browsers/<session_id>/stop       - Stop session (keep container)

Socket.IO Events (real-time status updates for long-running operations):
    codx-junior-browser-create   - Create session with progress
    codx-junior-browser-delete   - Delete session with progress
    codx-junior-browser-restart  - Restart session with progress
    codx-junior-browser-stop     - Stop session with progress

    Emits: codx-junior-browser-status with {status, session_id, message, error, session}
"""

import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, status

from codx.junior.engine.session import CODXJuniorSession
from codx.junior.sio.sio import sio, sio_api_endpoint
from codx.junior.sio.session_channel import SessionChannel
from codx.junior.api.browser_models import (
    BrowserSessionResponse,
    BrowserSessionListResponse,
    BrowserSessionCreateRequest,
    BrowserSessionUpdateRequest,
    BrowserSessionChatRequest,
    BrowserSessionChatResponse,
    BrowserSessionActionRequest,
    BrowserActionResponse,
    BrowserScreenshotResponse,
    BrowserSourceResponse,
    BrowserActivityResponse,
    BrowserCostResponse,
    BrowserScreenshotRequest,
)
from codx.junior.chat_manager import ChatManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browsers", tags=["browser"])

BROWSER_STATUS_EVENT = "codx-junior-browser-status"

# ============================================================================
# Helpers
# ============================================================================

async def get_session_context(request: Request) -> CODXJuniorSession:
    """Dependency: get the current session context from request state."""
    session = getattr(request.state, 'codx_junior_session', None)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active session",
        )
    return session


def _browser_manager(session: CODXJuniorSession):
    """
    Return a BrowserManager for the session.

    Reuses ``session.browser_manager`` when present so a long-lived manager can
    be injected, otherwise constructs one from the project settings.
    """
    manager = getattr(session, "browser_manager", None)
    if manager:
        return manager
    from codx.junior.browser.browser_manager import BrowserManager
    return BrowserManager(session.settings)


def _emit(channel: SessionChannel, payload: dict) -> None:
    """Send a browser status event (keeps the ts-stamping in one place)."""
    channel.send_event(BROWSER_STATUS_EVENT, payload)


# ============================================================================
# REST Endpoints
# ============================================================================

@router.get(
    "",
    response_model=BrowserSessionListResponse,
    summary="List all browser sessions",
    responses={
        200: {"description": "List of browser sessions"},
        401: {"description": "Unauthorized"},
        500: {"description": "Server error"},
    },
)
async def list_sessions(request: Request):
    """List all browser sessions for the current project."""
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)

        sessions = browser_manager.list_sessions()
        responses = [BrowserSessionResponse(**s.to_dict()) for s in sessions]
        logger.info("list_sessions: returned %d browser sessions", len(sessions))
        return BrowserSessionListResponse(count=len(responses), sessions=responses)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_sessions: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "",
    response_model=BrowserSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new browser session",
    responses={
        201: {"description": "Session created"},
        400: {"description": "Invalid request"},
        401: {"description": "Unauthorized"},
        500: {"description": "Server error"},
    },
)
async def create_session(request: Request, req: BrowserSessionCreateRequest):
    """
    Create and start a new browser session.

    Starts a Chromium Docker container with Traefik routing and a persistent profile.
    The session is named (``req.name``) and optionally connected to ``req.chat_id``.
    Multiple chats may connect to the same session.
    """
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)

        chat = None
        chat_manager = None
        if req.chat_id:
            chat_manager = ChatManager(session.settings)
            chat = chat_manager.find_by_id(req.chat_id)
            if not chat:
                logger.error("create_session: chat not found: %s", req.chat_id)
                raise HTTPException(status_code=404, detail="Chat not found")

        browser_session = browser_manager.create_session(
            name=req.name,
            chat_id=req.chat_id,
            initial_url=req.initial_url,
            description=req.description,
        )

        if chat and chat_manager:
            browser_manager.save_session_to_chat(browser_session, chat)
            chat_manager.save_chat(chat)

        logger.info(
            "create_session: created browser session %s ('%s') for chat %s",
            browser_session.id[:8],
            browser_session.name,
            req.chat_id,
        )
        return BrowserSessionResponse(**browser_session.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("create_session: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{session_id}",
    response_model=BrowserSessionResponse,
    summary="Get session details",
    responses={
        200: {"description": "Session details"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        500: {"description": "Server error"},
    },
)
async def get_session(request: Request, session_id: str):
    """Get details for a specific browser session."""
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)

        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            logger.error("get_session: session not found: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")

        logger.info("get_session: retrieved session %s", session_id[:8])
        return BrowserSessionResponse(**browser_session.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_session: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{session_id}",
    response_model=BrowserSessionResponse,
    summary="Update a browser session",
    responses={
        200: {"description": "Session updated"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        500: {"description": "Server error"},
    },
)
async def update_session(request: Request, session_id: str, req: BrowserSessionUpdateRequest):
    """Update the human-readable name of a browser session."""
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)
        browser_session = browser_manager.update_session(session_id, name=req.name)
        if not browser_session:
            raise HTTPException(status_code=404, detail="Session not found")
        return BrowserSessionResponse(**browser_session.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_session: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{session_id}/chat",
    response_model=BrowserSessionChatResponse,
    summary="Open or create the chat linked to a session",
    responses={
        200: {"description": "Chat linked to the session"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session or chat not found"},
        500: {"description": "Server error"},
    },
)
async def open_session_chat(
    request: Request,
    session_id: str,
    req: Optional[BrowserSessionChatRequest] = None,
):
    """
    Return a chat that can drive the browser session from the session view.

    If the session already has a linked chat, that chat is reused. If it has
    none (or the caller passes a different ``chat_id``), a chat is created and
    linked to the session. Chats opened this way get the built-in ``browser``
    profile so the agent receives the browser tools.
    """
    from codx.junior.db import Chat

    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)
        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            raise HTTPException(status_code=404, detail="Session not found")

        chat_manager = ChatManager(session.settings)
        chat = None

        requested_chat_id = req.chat_id if req else None
        create_new = bool(req.create_new) if req else False
        if requested_chat_id:
            chat = chat_manager.find_by_id(requested_chat_id)
            if not chat:
                raise HTTPException(status_code=404, detail="Chat not found")
        elif not create_new and browser_session.chat_ids:
            chat = chat_manager.find_by_id(browser_session.chat_ids[0])

        browser_profile_available = False
        try:
            browser_profile_available = bool(
                session.get_profile_manager().get_profiles_by_name(["browser"])
            )
        except Exception as ex:
            logger.debug("Could not check the browser profile: %s", ex)

        if not chat:
            base_name = f"Browser: {browser_session.name or browser_session.id[:8]}"
            suffix = f" ({len(browser_session.chat_ids) + 1})" if browser_session.chat_ids else ""
            chat = Chat(
                name=f"{base_name}{suffix}",
                mode="chat",
                project_id=session.settings.project_id,
                owner_project_id=session.settings.project_id,
                profiles=["browser"] if browser_profile_available else [],
                meta_data={},
            )
            chat_manager.save_chat(chat)

        # The chat explicitly asks to operate this browser: make sure the
        # browser profile (and therefore the browser tools) is active.
        if browser_profile_available and "browser" not in (chat.profiles or []):
            chat.profiles = [*(chat.profiles or []), "browser"]

        browser_manager.save_session_to_chat(browser_session, chat)
        chat_manager.save_chat(chat)
        logger.info(
            "open_session_chat: session %s linked to chat %s",
            session_id[:8], chat.id,
        )
        return BrowserSessionChatResponse(
            session=BrowserSessionResponse(**browser_session.to_dict()),
            chat=chat.model_dump(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("open_session_chat: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop and delete a session",
    responses={
        204: {"description": "Session deleted"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        500: {"description": "Server error"},
    },
)
async def delete_session(request: Request, session_id: str):
    """Stop the Docker container and delete a browser session."""
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)

        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            logger.error("delete_session: session not found: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")

        browser_manager.delete_session(session_id)
        logger.info("delete_session: deleted session %s", session_id[:8])

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("delete_session: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{session_id}/restart",
    response_model=BrowserSessionResponse,
    summary="Restart a stopped session",
    responses={
        200: {"description": "Session restarted"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        500: {"description": "Server error"},
    },
)
async def restart_session(request: Request, session_id: str):
    """Restart a stopped browser session (preserves the Chromium profile)."""
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)

        browser_session = await browser_manager.restart_session(session_id)
        if not browser_session:
            logger.error("restart_session: session not found: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")

        logger.info("restart_session: restarted session %s", session_id[:8])
        return BrowserSessionResponse(**browser_session.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("restart_session: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{session_id}/stop",
    response_model=BrowserSessionResponse,
    summary="Stop a session (keep container)",
    responses={
        200: {"description": "Session stopped"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        500: {"description": "Server error"},
    },
)
async def stop_session(request: Request, session_id: str):
    """Stop the container but keep it so it can be restarted later."""
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)

        browser_session = browser_manager.stop_session(session_id)
        if not browser_session:
            logger.error("stop_session: session not found: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")

        logger.info("stop_session: stopped session %s", session_id[:8])
        return BrowserSessionResponse(**browser_session.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("stop_session: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{session_id}/action",
    response_model=BrowserActionResponse,
    summary="Execute a browser action",
    responses={
        200: {"description": "Action executed"},
        400: {"description": "Invalid action or session not running"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        500: {"description": "Server error"},
    },
)
async def execute_action(request: Request, session_id: str, req: BrowserSessionActionRequest):
    """
    Execute a browser action on the shared page.

    The action is performed through the same CDP connection the AI uses, so the
    user's live VNC view reflects it immediately.
    """
    browser = None
    browser_manager = None
    browser_session = None
    action = (req.action or "").lower().strip()
    started_at = time.monotonic()
    params: Dict[str, Any] = {
        key: value
        for key, value in {
            "url": req.url,
            "selector": req.selector,
            "value": req.value,
            "script": req.script,
            "key": req.key,
            "timeout": req.timeout,
            "x": req.x,
            "y": req.y,
            "full_page": req.full_page,
        }.items()
        if value is not None
    }
    title = None

    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)

        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            logger.error("execute_action: session not found: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")

        if browser_session.status != "running":
            logger.error(
                "execute_action: session not running: %s (status=%s)",
                session_id, browser_session.status,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Session not running (status: {browser_session.status})",
            )

        browser = await browser_manager.connect_browser(browser_session)

        if action == "navigate":
            if not req.url:
                raise HTTPException(400, "URL required for navigate action")
            title = await browser.navigate(req.url)
            message, data = f"Navigated to {req.url}", {"title": title, "url": req.url}

        elif action == "click":
            if not req.selector:
                raise HTTPException(400, "Selector required for click action")
            await browser.click(req.selector)
            message, data = f"Clicked {req.selector}", {"selector": req.selector}

        elif action == "fill":
            if not req.selector or req.value is None:
                raise HTTPException(400, "Selector and value required for fill action")
            await browser.fill(req.selector, req.value)
            message, data = f"Filled {req.selector}", {"selector": req.selector, "value": req.value}

        elif action == "execute":
            if not req.script:
                raise HTTPException(400, "Script required for execute action")
            result = await browser.execute_script(req.script)
            message, data = "Script executed", {"result": result}

        elif action == "text" or action == "read":
            text = await browser.get_text()
            message, data = "Page text read", {"text": text}

        elif action == "links":
            links = await browser.get_links()
            message, data = "Page links read", {"links": links}

        elif action == "back":
            title = await browser.go_back()
            message, data = "Navigated back", {"title": title}

        elif action == "forward":
            title = await browser.go_forward()
            message, data = "Navigated forward", {"title": title}

        elif action == "refresh":
            title = await browser.reload()
            message, data = "Page refreshed", {"title": title}

        elif action == "wait":
            if not req.selector:
                raise HTTPException(400, "Selector required for wait action")
            await browser.wait_for_selector(req.selector, timeout=req.timeout or 5000)
            message, data = f"Element appeared: {req.selector}", {"selector": req.selector}

        elif action == "press":
            if not req.selector or not req.key:
                raise HTTPException(400, "Selector and key required for press action")
            await browser.press(req.selector, req.key)
            message, data = f"Pressed {req.key} on {req.selector}", {"selector": req.selector, "key": req.key}

        elif action == "select":
            if not req.selector or req.value is None:
                raise HTTPException(400, "Selector and value required for select action")
            await browser.select(req.selector, req.value)
            message, data = f"Selected {req.value} on {req.selector}", {"selector": req.selector, "value": req.value}

        elif action == "hover":
            if not req.selector:
                raise HTTPException(400, "Selector required for hover action")
            await browser.hover(req.selector)
            message, data = f"Hovered {req.selector}", {"selector": req.selector}

        elif action == "scroll":
            await browser.scroll(x=req.x or 0, y=req.y or 0)
            message, data = "Page scrolled", {"x": req.x or 0, "y": req.y or 0}

        elif action == "screenshot":
            screenshot = await browser.get_screenshot(full_page=bool(req.full_page))
            message, data = "Screenshot captured", {"screenshot": screenshot, "full_page": bool(req.full_page)}

        else:
            raise HTTPException(400, f"Unknown action: {req.action}")

        data.update({
            "url": browser_session.current_url,
            "title": browser_session.current_title,
        })
        browser_manager.save_session(browser_session)
        browser_manager.log_activity(
            browser_session,
            actor="user",
            action=action,
            params=params,
            url=browser_session.current_url,
            title=browser_session.current_title,
            duration_ms=(time.monotonic() - started_at) * 1000,
            result={"message": message},
        )
        logger.info("execute_action: '%s' completed for session %s", action, session_id[:8])
        return BrowserActionResponse(success=True, message=message, data=data)

    except HTTPException as ex:
        if browser_session is not None and browser_manager is not None:
            browser_manager.log_activity(
                browser_session,
                actor="user",
                action=action or "unknown",
                params=params,
                success=False,
                error=str(ex.detail),
                duration_ms=(time.monotonic() - started_at) * 1000,
            )
        raise
    except Exception as e:
        logger.exception("execute_action: unexpected error: %s", e)
        if browser_session is not None and browser_manager is not None:
            browser_manager.log_activity(
                browser_session,
                actor="user",
                action=action or "unknown",
                params=params,
                success=False,
                error=str(e),
                duration_ms=(time.monotonic() - started_at) * 1000,
            )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if browser is not None:
            await browser.close()


@router.post(
    "/{session_id}/screenshot",
    response_model=BrowserScreenshotResponse,
    summary="Take a screenshot",
    responses={
        200: {"description": "Screenshot captured"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        500: {"description": "Server error"},
    },
)
async def take_screenshot(request: Request, session_id: str, req: Optional[BrowserScreenshotRequest] = None):
    """Take a screenshot of the current page."""
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)

        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            logger.error("take_screenshot: session not found: %s", session_id)
            return BrowserScreenshotResponse(success=False, error="Session not found")

        if browser_session.status != "running":
            logger.error(
                "take_screenshot: session not running: %s (status=%s)",
                session_id, browser_session.status,
            )
            return BrowserScreenshotResponse(
                success=False,
                error=f"Session not running (status: {browser_session.status})",
            )

        browser = await browser_manager.connect_browser(browser_session)
        try:
            screenshot = await browser.get_screenshot(full_page=req.full_page if req else True)
            browser_session.mark_active()
            browser_manager.save_session(browser_session)
            browser_manager.log_activity(
                browser_session,
                actor="user",
                action="screenshot",
                params={"full_page": bool(req.full_page) if req else True},
                url=browser_session.current_url,
                title=browser_session.current_title,
            )
            logger.info("take_screenshot: screenshot completed for session %s", session_id[:8])
            return BrowserScreenshotResponse(success=True, screenshot=screenshot)
        finally:
            await browser.close()

    except Exception as e:
        logger.exception("take_screenshot: unexpected error: %s", e)
        return BrowserScreenshotResponse(success=False, error=str(e))


@router.get(
    "/{session_id}/source",
    response_model=BrowserSourceResponse,
    summary="Get page source HTML",
    responses={
        200: {"description": "Page source retrieved"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        500: {"description": "Server error"},
    },
)
async def get_source(request: Request, session_id: str):
    """Get the current page HTML source code."""
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)

        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            logger.error("get_source: session not found: %s", session_id)
            return BrowserSourceResponse(success=False, error="Session not found")

        if browser_session.status != "running":
            logger.error(
                "get_source: session not running: %s (status=%s)",
                session_id, browser_session.status,
            )
            return BrowserSourceResponse(
                success=False,
                error=f"Session not running (status: {browser_session.status})",
            )

        browser = await browser_manager.connect_browser(browser_session)
        try:
            html = await browser.get_content()
            url = browser_session.current_url
            browser_session.mark_active()
            browser_manager.save_session(browser_session)
            browser_manager.log_activity(
                browser_session,
                actor="user",
                action="source",
                url=url,
                title=browser_session.current_title,
                result={"chars": len(html or "")},
            )
            logger.info("get_source: source retrieved for session %s", session_id[:8])
            return BrowserSourceResponse(
                success=True,
                html=html,
                url=url,
                title=browser_session.current_title,
            )
        finally:
            await browser.close()

    except Exception as e:
        logger.exception("get_source: unexpected error: %s", e)
        return BrowserSourceResponse(success=False, error=str(e))


@router.get(
    "/{session_id}/activity",
    response_model=BrowserActivityResponse,
    summary="Get the user/AI audit trail",
    responses={
        200: {"description": "Activity entries"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
    },
)
async def get_activity(request: Request, session_id: str, limit: int = 100):
    """Return the most recent user and AI actions performed on the session."""
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)
        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            raise HTTPException(status_code=404, detail="Session not found")
        entries = browser_manager.get_activity(session_id, limit=limit)
        return BrowserActivityResponse(
            session_id=session_id,
            count=len(entries),
            activity=entries,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_activity: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{session_id}/cost",
    response_model=BrowserCostResponse,
    summary="Get the AI cost/usage summary",
    responses={
        200: {"description": "Cost summary"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
    },
)
async def get_cost(request: Request, session_id: str):
    """
    Return the accumulated AI cost, tokens, LLM calls and tool calls for every
    chat connected to the browser session.

    The numbers come from SmolAgent's token-usage analytics and ``Chat.cost``,
    so they reconcile with the chat header's cost indicator.
    """
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)
        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            raise HTTPException(status_code=404, detail="Session not found")
        return BrowserCostResponse(**browser_manager.get_cost_summary(session_id))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_cost: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Socket.IO Events (long-running operations with real-time updates)
# ============================================================================

@sio.on("codx-junior-browser-create")
@sio_api_endpoint
async def sio_browser_create(sid: str, data: dict, codxjunior_session: CODXJuniorSession):
    """
    Create a new browser session via Socket.IO, emitting status updates.

    Request data: ``name`` (str, required) · ``chat_id`` (str, optional) ·
    ``codx_path`` (str, injected by the client).
    Emits: ``codx-junior-browser-status`` {status, session_id, message, error, session}.
    """
    channel = SessionChannel(sio=sio, sid=sid)
    chat_id = data.get("chat_id")
    name = data.get("name")
    initial_url = data.get("initial_url")
    description = data.get("description")

    if not codxjunior_session:
        _emit(channel, {"status": "error", "message": "Missing codx_path", "error": "Missing codx_path"})
        return
    if not name:
        _emit(channel, {"status": "error", "message": "name is required", "error": "Missing name"})
        return

    try:
        chat = None
        if chat_id:
            chat_manager = ChatManager(codxjunior_session.settings)
            chat = chat_manager.find_by_id(chat_id)
            if not chat:
                _emit(channel, {"status": "error", "message": "Chat not found", "error": f"Chat {chat_id} not found"})
                return

        _emit(channel, {"status": "starting", "message": "Creating browser session...", "name": name, "chat_id": chat_id})

        browser_manager = codxjunior_session.get_browser_manager()
        browser_session = browser_manager.create_session(
            name=name,
            chat_id=chat_id,
            initial_url=initial_url,
            description=description,
        )

        _emit(channel, {
            "status": "created",
            "session_id": browser_session.id,
            "name": browser_session.name,
            "message": f"Browser session '{browser_session.name}' ({browser_session.id[:8]}) created",
            "session": browser_session.to_dict(),
        })

        if chat:
            browser_manager.save_session_to_chat(browser_session, chat)
            ChatManager(codxjunior_session.settings).save_chat(chat)

        _emit(channel, {
            "status": "ready",
            "session_id": browser_session.id,
            "name": browser_session.name,
            "message": "Browser session ready",
            "session": browser_session.to_dict(),
        })
        logger.info("sio_browser_create: created session %s for chat %s", browser_session.id[:8], chat_id)

    except Exception as e:
        logger.exception("sio_browser_create: unexpected error: %s", e)
        _emit(channel, {"status": "error", "message": "Failed to create browser session", "error": str(e)})


@sio.on("codx-junior-browser-delete")
@sio_api_endpoint
def sio_browser_delete(sid: str, data: dict, codxjunior_session: CODXJuniorSession):
    """
    Delete a browser session via Socket.IO, emitting status updates.

    Request data: ``session_id`` (str).
    Emits: ``codx-junior-browser-status``.
    """
    channel = SessionChannel(sio=sio, sid=sid)
    session_id = data.get("session_id")

    if not codxjunior_session:
        _emit(channel, {"status": "error", "message": "Missing codx_path", "error": "Missing codx_path"})
        return
    if not session_id:
        _emit(channel, {"status": "error", "message": "session_id is required", "error": "Missing session_id"})
        return

    try:
        browser_manager = codxjunior_session.get_browser_manager()

        _emit(channel, {"status": "stopping", "session_id": session_id, "message": "Stopping browser session..."})

        if not browser_manager.get_session(session_id):
            _emit(channel, {"status": "error", "session_id": session_id, "message": "Session not found", "error": f"Session {session_id} not found"})
            return

        browser_manager.delete_session(session_id)
        _emit(channel, {"status": "deleted", "session_id": session_id, "message": f"Browser session {session_id[:8]} deleted"})
        logger.info("sio_browser_delete: deleted session %s", session_id[:8])

    except Exception as e:
        logger.exception("sio_browser_delete: unexpected error: %s", e)
        _emit(channel, {"status": "error", "session_id": session_id, "message": "Failed to delete browser session", "error": str(e)})


@sio.on("codx-junior-browser-restart")
@sio_api_endpoint
async def sio_browser_restart(sid: str, data: dict, codxjunior_session: CODXJuniorSession):
    """
    Restart a browser session via Socket.IO, emitting status updates.

    Request data: ``session_id`` (str).
    Emits: ``codx-junior-browser-status``.
    """
    channel = SessionChannel(sio=sio, sid=sid)
    session_id = data.get("session_id")

    if not codxjunior_session:
        _emit(channel, {"status": "error", "message": "Missing codx_path", "error": "Missing codx_path"})
        return
    if not session_id:
        _emit(channel, {"status": "error", "message": "session_id is required", "error": "Missing session_id"})
        return

    try:
        browser_manager = codxjunior_session.get_browser_manager()

        _emit(channel, {"status": "restarting", "session_id": session_id, "message": "Restarting browser session..."})

        browser_session = await browser_manager.restart_session(session_id)
        if not browser_session:
            _emit(channel, {"status": "error", "session_id": session_id, "message": "Session not found", "error": f"Session {session_id} not found"})
            return

        _emit(channel, {
            "status": "ready",
            "session_id": session_id,
            "name": browser_session.name,
            "message": f"Browser session {session_id[:8]} restarted",
            "session": browser_session.to_dict(),
        })
        logger.info("sio_browser_restart: restarted session %s", session_id[:8])

    except Exception as e:
        logger.exception("sio_browser_restart: unexpected error: %s", e)
        _emit(channel, {"status": "error", "session_id": session_id, "message": "Failed to restart browser session", "error": str(e)})


@sio.on("codx-junior-browser-stop")
@sio_api_endpoint
def sio_browser_stop(sid: str, data: dict, codxjunior_session: CODXJuniorSession):
    """
    Stop a browser session (without deleting) via Socket.IO, emitting status updates.

    Request data: ``session_id`` (str).
    Emits: ``codx-junior-browser-status``.
    """
    channel = SessionChannel(sio=sio, sid=sid)
    session_id = data.get("session_id")

    if not codxjunior_session:
        _emit(channel, {"status": "error", "message": "Missing codx_path", "error": "Missing codx_path"})
        return
    if not session_id:
        _emit(channel, {"status": "error", "message": "session_id is required", "error": "Missing session_id"})
        return

    try:
        browser_manager = codxjunior_session.get_browser_manager()

        _emit(channel, {"status": "stopping", "session_id": session_id, "message": "Stopping browser session..."})

        browser_session = browser_manager.stop_session(session_id)
        if not browser_session:
            _emit(channel, {"status": "error", "session_id": session_id, "message": "Session not found", "error": f"Session {session_id} not found"})
            return

        _emit(channel, {"status": "stopped", "session_id": session_id, "message": f"Browser session {session_id[:8]} stopped"})
        logger.info("sio_browser_stop: stopped session %s", session_id[:8])

    except Exception as e:
        logger.exception("sio_browser_stop: unexpected error: %s", e)
        _emit(channel, {"status": "error", "session_id": session_id, "message": "Failed to stop browser session", "error": str(e)})


# Made with ❤️ by codx-junior