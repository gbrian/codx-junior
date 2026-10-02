"""
Browser Session REST API Router

Handles CRUD operations for browser sessions with full async support.

REST Endpoints:
    GET    /api/browsers              - List all sessions
    POST   /api/browsers              - Create new session
    GET    /api/browsers/<session_id> - Get session details
    DELETE /api/browsers/<session_id> - Stop & delete session
    POST   /api/browsers/<session_id>/action    - Execute browser action
    POST   /api/browsers/<session_id>/screenshot - Take screenshot
    GET    /api/browsers/<session_id>/source     - Get page source
    POST   /api/browsers/<session_id>/restart    - Restart session

Socket.IO Events (Real-time operations with status updates):
    codx-junior-browser-create   - Create session with progress
    codx-junior-browser-delete   - Delete session with progress
    codx-junior-browser-restart  - Restart session with progress
    codx-junior-browser-stop     - Stop session with progress
    
    Emits: codx-junior-browser-status with {status, session_id, message, error, session}
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, status

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


# ============================================================================
# Dependencies
# ============================================================================

async def get_session_context(request: Request) -> CODXJuniorSession:
    """Dependency: get current session context from request state."""
    session = getattr(request.state, 'codx_junior_session', None)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active session"
        )
    return session


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
    }
)
async def list_sessions(request: Request):
    """
    List all browser sessions for the current project.

    Returns:
        BrowserSessionListResponse with count and list of sessions
    """
    try:
        session = await get_session_context(request)
        browser_manager = session.browser_manager if hasattr(session, 'browser_manager') else None
        if not browser_manager:
            from codx.junior.browser.browser_manager import BrowserManager
            browser_manager = BrowserManager(session.settings)
        
        sessions = browser_manager.list_sessions()
        responses = [
            BrowserSessionResponse(**s.to_dict())
            for s in sessions
        ]
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
    }
)
async def create_session(
    request: Request,
    req: BrowserSessionCreateRequest,
):
    """
    Create and start a new browser session.

    Starts a Firefox Docker container with Traefik routing and persistent profile.

    Args:
        req: BrowserSessionCreateRequest with chat_id

    Returns:
        BrowserSessionResponse with session details or error dict
    """
    try:
        session = await get_session_context(request)
        browser_manager = session.browser_manager if hasattr(session, 'browser_manager') else None
        if not browser_manager:
            from codx.junior.browser.browser_manager import BrowserManager
            browser_manager = BrowserManager(session.settings)
        
        # Validate chat exists
        chat_manager = ChatManager(session.settings)
        chat = chat_manager.find_by_id(req.chat_id)
        if not chat:
            logger.error("create_session: chat not found: %s", req.chat_id)
            raise HTTPException(status_code=404, detail="Chat not found")

        # Create browser session
        browser_session = browser_manager.create_session(req.chat_id)

        # Sync to chat metadata
        browser_manager.save_session_to_chat(browser_session, chat)
        chat_manager.save_chat(chat)

        logger.info(
            "create_session: created browser session %s for chat %s",
            browser_session.id[:8],
            req.chat_id
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
    }
)
async def get_session(
    request: Request,
    session_id: str,
):
    """
    Get details for a specific browser session.

    Args:
        session_id: Session ID

    Returns:
        BrowserSessionResponse with session details or error dict
    """
    try:
        session = await get_session_context(request)
        browser_manager = session.browser_manager if hasattr(session, 'browser_manager') else None
        if not browser_manager:
            from codx.junior.browser.browser_manager import BrowserManager
            browser_manager = BrowserManager(session.settings)
        
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
    }
)
async def delete_session(
    request: Request,
    session_id: str,
):
    """
    Stop Docker container and delete a browser session.

    Args:
        session_id: Session ID to delete

    Returns:
        Empty response on success, error dict on failure
    """
    try:
        session = await get_session_context(request)
        browser_manager = session.browser_manager if hasattr(session, 'browser_manager') else None
        if not browser_manager:
            from codx.junior.browser.browser_manager import BrowserManager
            browser_manager = BrowserManager(session.settings)
        
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
    }
)
async def restart_session(
    request: Request,
    session_id: str,
):
    """
    Restart a stopped browser session (preserves Firefox profile).

    Args:
        session_id: Session ID to restart

    Returns:
        Updated BrowserSessionResponse or error dict
    """
    try:
        session = await get_session_context(request)
        browser_manager = session.browser_manager if hasattr(session, 'browser_manager') else None
        if not browser_manager:
            from codx.junior.browser.browser_manager import BrowserManager
            browser_manager = BrowserManager(session.settings)
        
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
    "/{session_id}/action",
    response_model=BrowserActionResponse,
    summary="Execute a browser action",
    responses={
        200: {"description": "Action executed"},
        400: {"description": "Invalid action or session not running"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        500: {"description": "Server error"},
    }
)
async def execute_action(
    request: Request,
    session_id: str,
    req: BrowserSessionActionRequest,
):
    """
    Execute a browser action (navigate, click, fill, execute script).

    Args:
        session_id: Session ID
        req: BrowserSessionActionRequest with action details

    Returns:
        BrowserActionResponse with result or error dict
    """
    try:
        session = await get_session_context(request)
        browser_manager = session.browser_manager if hasattr(session, 'browser_manager') else None
        if not browser_manager:
            from codx.junior.browser.browser_manager import BrowserManager
            browser_manager = BrowserManager(session.settings)
        
        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            logger.error("execute_action: session not found: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")

        if browser_session.status != "running":
            logger.error(
                "execute_action: session not running: %s (status=%s)",
                session_id,
                browser_session.status
            )
            raise HTTPException(
                status_code=400,
                detail=f"Session not running (status: {browser_session.status})"
            )

        # Connect to browser
        browser = await browser_manager.connect_browser(browser_session)

        try:
            if req.action == "navigate":
                if not req.url:
                    logger.error("execute_action: navigate action missing URL")
                    raise HTTPException(400, "URL required for navigate action")
                title = await browser.navigate(req.url)
                browser_session.mark_active()
                browser_manager.save_session(browser_session)
                logger.info(
                    "execute_action: navigate action completed for session %s to %s",
                    session_id[:8],
                    req.url
                )
                return BrowserActionResponse(
                    success=True,
                    message=f"Navigated to {req.url}",
                    data={"title": title, "url": req.url}
                )

            elif req.action == "click":
                if not req.selector:
                    logger.error("execute_action: click action missing selector")
                    raise HTTPException(400, "Selector required for click action")
                await browser.click(req.selector)
                browser_session.mark_active()
                browser_manager.save_session(browser_session)
                logger.info(
                    "execute_action: click action completed for session %s on %s",
                    session_id[:8],
                    req.selector
                )
                return BrowserActionResponse(
                    success=True,
                    message=f"Clicked {req.selector}",
                    data={"selector": req.selector}
                )

            elif req.action == "fill":
                if not req.selector or not req.value:
                    logger.error("execute_action: fill action missing selector or value")
                    raise HTTPException(400, "Selector and value required for fill action")
                await browser.fill(req.selector, req.value)
                browser_session.mark_active()
                browser_manager.save_session(browser_session)
                logger.info(
                    "execute_action: fill action completed for session %s on %s",
                    session_id[:8],
                    req.selector
                )
                return BrowserActionResponse(
                    success=True,
                    message=f"Filled {req.selector}",
                    data={"selector": req.selector, "value": req.value}
                )

            elif req.action == "execute":
                if not req.script:
                    logger.error("execute_action: execute action missing script")
                    raise HTTPException(400, "Script required for execute action")
                result = await browser.execute_script(req.script)
                browser_session.mark_active()
                browser_manager.save_session(browser_session)
                logger.info(
                    "execute_action: execute action completed for session %s",
                    session_id[:8]
                )
                return BrowserActionResponse(
                    success=True,
                    message="Script executed",
                    data={"result": result}
                )

            else:
                logger.error("execute_action: unknown action: %s", req.action)
                raise HTTPException(400, f"Unknown action: {req.action}")

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
    }
)
async def take_screenshot(
    request: Request,
    session_id: str,
):
    """
    Take a screenshot of the current page.

    Args:
        session_id: Session ID

    Returns:
        BrowserScreenshotResponse with base64 PNG data or error response
    """
    try:
        session = await get_session_context(request)
        browser_manager = session.browser_manager if hasattr(session, 'browser_manager') else None
        if not browser_manager:
            from codx.junior.browser.browser_manager import BrowserManager
            browser_manager = BrowserManager(session.settings)
        
        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            logger.error("take_screenshot: session not found: %s", session_id)
            return BrowserScreenshotResponse(
                success=False,
                error="Session not found"
            )

        if browser_session.status != "running":
            logger.error(
                "take_screenshot: session not running: %s (status=%s)",
                session_id,
                browser_session.status
            )
            return BrowserScreenshotResponse(
                success=False,
                error=f"Session not running (status: {browser_session.status})"
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
    }
)
async def get_source(
    request: Request,
    session_id: str,
):
    """
    Get the current page HTML source code.

    Args:
        session_id: Session ID

    Returns:
        BrowserSourceResponse with HTML content or error response
    """
    try:
        session = await get_session_context(request)
        browser_manager = session.browser_manager if hasattr(session, 'browser_manager') else None
        if not browser_manager:
            from codx.junior.browser.browser_manager import BrowserManager
            browser_manager = BrowserManager(session.settings)
        
        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            logger.error("get_source: session not found: %s", session_id)
            return BrowserSourceResponse(
                success=False,
                error="Session not found"
            )

        if browser_session.status != "running":
            logger.error(
                "get_source: session not running: %s (status=%s)",
                session_id,
                browser_session.status
            )
            return BrowserSourceResponse(
                success=False,
                error=f"Session not running (status: {browser_session.status})"
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
# Socket.IO Events (Long-running operations with real-time updates)
# ============================================================================

@sio.on("codx-junior-browser-create")
@sio_api_endpoint
async def sio_browser_create(sid: str, data: dict, codxjunior_session: CODXJuniorSession):
    """
    Create a new browser session via Socket.IO.
    Sends real-time status updates as the session starts.
    
    Socket.IO Event: codx-junior-browser-create
    
    Request data:
        - chat_id: str - Associated chat ID
    
    Emits events:
        - codx-junior-browser-status: {status, session_id, message, error, session}
    """
    channel = SessionChannel(sio=sio, sid=sid)
    chat_id = data.get("chat_id")
    
    if not chat_id:
        logger.error("sio_browser_create: chat_id is required")
        channel.send_event("codx-junior-browser-status", {
            "status": "error",
            "message": "chat_id is required",
            "error": "Missing chat_id"
        })
        return
    
    try:
        from codx.junior.browser.browser_manager import BrowserManager
        
        # Validate chat exists
        chat_manager = ChatManager(codxjunior_session.settings)
        chat = chat_manager.find_by_id(chat_id)
        if not chat:
            logger.error("sio_browser_create: chat not found: %s", chat_id)
            channel.send_event("codx-junior-browser-status", {
                "status": "error",
                "message": "Chat not found",
                "error": f"Chat {chat_id} not found"
            })
            return
        
        # Emit starting event
        channel.send_event("codx-junior-browser-status", {
            "status": "starting",
            "message": "Creating browser session...",
            "chat_id": chat_id
        })
        
        # Create browser session
        browser_manager = BrowserManager(codxjunior_session.settings)
        browser_session = browser_manager.create_session(chat_id)
        
        # Emit creation event
        channel.send_event("codx-junior-browser-status", {
            "status": "created",
            "session_id": browser_session.id,
            "message": f"Browser session {browser_session.id[:8]} created",
            "session": browser_session.to_dict()
        })
        
        # Emit starting container event
        channel.send_event("codx-junior-browser-status", {
            "status": "starting_container",
            "session_id": browser_session.id,
            "message": "Starting Docker container...",
            "container_id": browser_session.container_id
        })
        
        # Sync to chat metadata
        browser_manager.save_session_to_chat(browser_session, chat)
        chat_manager.save_chat(chat)
        
        # Emit ready event
        channel.send_event("codx-junior-browser-status", {
            "status": "ready",
            "session_id": browser_session.id,
            "message": f"Browser session ready",
            "session": browser_session.to_dict()
        })
        
        logger.info(
            "sio_browser_create: created session %s for chat %s",
            browser_session.id[:8],
            chat_id
        )
        
    except Exception as e:
        logger.exception("sio_browser_create: unexpected error: %s", e)
        channel.send_event("codx-junior-browser-status", {
            "status": "error",
            "message": "Failed to create browser session",
            "error": str(e)
        })


@sio.on("codx-junior-browser-delete")
@sio_api_endpoint
def sio_browser_delete(sid: str, data: dict, codxjunior_session: CODXJuniorSession):
    """
    Delete a browser session via Socket.IO.
    Sends real-time status updates as the session stops.
    
    Socket.IO Event: codx-junior-browser-delete
    
    Request data:
        - session_id: str - Session ID to delete
    
    Emits events:
        - codx-junior-browser-status: {status, session_id, message, error}
    """
    channel = SessionChannel(sio=sio, sid=sid)
    session_id = data.get("session_id")
    
    if not session_id:
        logger.error("sio_browser_delete: session_id is required")
        channel.send_event("codx-junior-browser-status", {
            "status": "error",
            "message": "session_id is required",
            "error": "Missing session_id"
        })
        return
    
    try:
        from codx.junior.browser.browser_manager import BrowserManager
        
        browser_manager = BrowserManager(codxjunior_session.settings)
        
        # Emit stopping event
        channel.send_event("codx-junior-browser-status", {
            "status": "stopping",
            "session_id": session_id,
            "message": "Stopping browser session..."
        })
        
        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            logger.error("sio_browser_delete: session not found: %s", session_id)
            channel.send_event("codx-junior-browser-status", {
                "status": "error",
                "session_id": session_id,
                "message": "Session not found",
                "error": f"Session {session_id} not found"
            })
            return
        
        # Delete session
        browser_manager.delete_session(session_id)
        
        # Emit deleted event
        channel.send_event("codx-junior-browser-status", {
            "status": "deleted",
            "session_id": session_id,
            "message": f"Browser session {session_id[:8]} deleted"
        })
        
        logger.info("sio_browser_delete: deleted session %s", session_id[:8])
        
    except Exception as e:
        logger.exception("sio_browser_delete: unexpected error: %s", e)
        channel.send_event("codx-junior-browser-status", {
            "status": "error",
            "session_id": session_id,
            "message": "Failed to delete browser session",
            "error": str(e)
        })


@sio.on("codx-junior-browser-restart")
@sio_api_endpoint
async def sio_browser_restart(sid: str, data: dict, codxjunior_session: CODXJuniorSession):
    """
    Restart a browser session via Socket.IO.
    Sends real-time status updates as the session restarts.
    
    Socket.IO Event: codx-junior-browser-restart
    
    Request data:
        - session_id: str - Session ID to restart
    
    Emits events:
        - codx-junior-browser-status: {status, session_id, message, error, session}
    """
    channel = SessionChannel(sio=sio, sid=sid)
    session_id = data.get("session_id")
    
    if not session_id:
        logger.error("sio_browser_restart: session_id is required")
        channel.send_event("codx-junior-browser-status", {
            "status": "error",
            "message": "session_id is required",
            "error": "Missing session_id"
        })
        return
    
    try:
        from codx.junior.browser.browser_manager import BrowserManager
        
        browser_manager = BrowserManager(codxjunior_session.settings)
        
        # Emit restarting event
        channel.send_event("codx-junior-browser-status", {
            "status": "restarting",
            "session_id": session_id,
            "message": "Restarting browser session..."
        })
        
        browser_session = await browser_manager.restart_session(session_id)
        if not browser_session:
            logger.error("sio_browser_restart: session not found: %s", session_id)
            channel.send_event("codx-junior-browser-status", {
                "status": "error",
                "session_id": session_id,
                "message": "Session not found",
                "error": f"Session {session_id} not found"
            })
            return
        
        # Emit ready event
        channel.send_event("codx-junior-browser-status", {
            "status": "ready",
            "session_id": session_id,
            "message": f"Browser session {session_id[:8]} restarted",
            "session": browser_session.to_dict()
        })
        
        logger.info("sio_browser_restart: restarted session %s", session_id[:8])
        
    except Exception as e:
        logger.exception("sio_browser_restart: unexpected error: %s", e)
        channel.send_event("codx-junior-browser-status", {
            "status": "error",
            "session_id": session_id,
            "message": "Failed to restart browser session",
            "error": str(e)
        })


@sio.on("codx-junior-browser-stop")
@sio_api_endpoint
def sio_browser_stop(sid: str, data: dict, codxjunior_session: CODXJuniorSession):
    """
    Stop a browser session (without deleting) via Socket.IO.
    Sends real-time status updates as the session stops.
    
    Socket.IO Event: codx-junior-browser-stop
    
    Request data:
        - session_id: str - Session ID to stop
    
    Emits events:
        - codx-junior-browser-status: {status, session_id, message, error}
    """
    channel = SessionChannel(sio=sio, sid=sid)
    session_id = data.get("session_id")
    
    if not session_id:
        logger.error("sio_browser_stop: session_id is required")
        channel.send_event("codx-junior-browser-status", {
            "status": "error",
            "message": "session_id is required",
            "error": "Missing session_id"
        })
        return
    
    try:
        from codx.junior.browser.browser_manager import BrowserManager
        
        browser_manager = BrowserManager(codxjunior_session.settings)
        
        # Emit stopping event
        channel.send_event("codx-junior-browser-status", {
            "status": "stopping",
            "session_id": session_id,
            "message": "Stopping browser session..."
        })
        
        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            logger.error("sio_browser_stop: session not found: %s", session_id)
            channel.send_event("codx-junior-browser-status", {
                "status": "error",
                "session_id": session_id,
                "message": "Session not found",
                "error": f"Session {session_id} not found"
            })
            return
        
        # Stop the browser container
        if hasattr(browser_manager, 'stop_session'):
            browser_manager.stop_session(session_id)
        
        # Emit stopped event
        channel.send_event("codx-junior-browser-status", {
            "status": "stopped",
            "session_id": session_id,
            "message": f"Browser session {session_id[:8]} stopped"
        })
        
        logger.info("sio_browser_stop: stopped session %s", session_id[:8])
        
    except Exception as e:
        logger.exception("sio_browser_stop: unexpected error: %s", e)
        channel.send_event("codx-junior-browser-status", {
            "status": "error",
            "session_id": session_id,
            "message": "Failed to stop browser session",
            "error": str(e)
        })


# Made with ❤️ by codx-junior