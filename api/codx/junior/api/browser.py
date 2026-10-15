"""
Browser Session REST API Router

Handles CRUD operations for browser sessions with full async support.

REST Endpoints:
    GET    /api/browsers              - List all sessions
    POST   /api/browsers              - Create new session
    GET    /api/browsers/<session_id> - Get session details
    DELETE /api/browsers/<session_id> - Stop & delete session
    POST   /api/browsers/<session_id>/action     - Execute browser action
    POST   /api/browsers/<session_id>/screenshot - Take screenshot
    GET    /api/browsers/<session_id>/source     - Get page source
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
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, status

from codx.junior.engine.session import CODXJuniorSession
from codx.junior.sio.sio import sio, sio_api_endpoint
from codx.junior.sio.session_channel import SessionChannel
from codx.junior.api.browser_models import (
    BrowserSessionResponse,
    BrowserSessionListResponse,
    BrowserSessionCreateRequest,
    BrowserSessionActionRequest,
    BrowserActionResponse,
    BrowserScreenshotResponse,
    BrowserSourceResponse,
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

    Starts a Firefox Docker container with Traefik routing and a persistent profile.
    The session is named (``req.name``) and optionally connected to ``req.chat_id``.
    Multiple chats may connect to the same session.
    """
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)

        browser_session = browser_manager.create_session(name=req.name, chat_id=req.chat_id)

        if req.chat_id:
            chat_manager = ChatManager(session.settings)
            chat = chat_manager.find_by_id(req.chat_id)
            if not chat:
                logger.error("create_session: chat not found: %s", req.chat_id)
                raise HTTPException(status_code=404, detail="Chat not found")

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
    """Restart a stopped browser session (preserves the Firefox profile)."""
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
    """Execute a browser action (navigate, click, fill, execute, text)."""
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
        try:
            action = (req.action or "").lower()

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

            elif action in ("text", "read"):
                text = await browser.get_text()
                message, data = "Page text read", {"text": text}

            else:
                raise HTTPException(400, f"Unknown action: {req.action}")

            browser_session.mark_active()
            browser_manager.save_session(browser_session)
            logger.info("execute_action: '%s' completed for session %s", action, session_id[:8])
            return BrowserActionResponse(success=True, message=message, data=data)

        finally:
            await browser.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("execute_action: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


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
async def take_screenshot(request: Request, session_id: str):
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
            screenshot = await browser.get_screenshot()
            browser_session.mark_active()
            browser_manager.save_session(browser_session)
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
            logger.info("get_source: source retrieved for session %s", session_id[:8])
            return BrowserSourceResponse(success=True, html=html, url=url)
        finally:
            await browser.close()

    except Exception as e:
        logger.exception("get_source: unexpected error: %s", e)
        return BrowserSourceResponse(success=False, error=str(e))


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
        browser_session = browser_manager.create_session(name=name, chat_id=chat_id)

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