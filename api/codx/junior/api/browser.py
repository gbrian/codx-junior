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

Project folders (see ``codx/junior/api/browser_files.py``):
    GET    /api/browsers/<session_id>/files      - Folder mapping + downloads
"""

import asyncio
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
    BrowserControlRequest,
    BrowserControlResponse,
)
from codx.junior.chat_manager import ChatManager
from codx.junior.browser import events as browser_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/browsers", tags=["browser"])

BROWSER_STATUS_EVENT = "codx-junior-browser-status"

#: User actions that do not change the page and therefore must not pause the AI.
READ_ONLY_ACTIONS = {"text", "read", "links", "snapshot", "screenshot"}

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
    from codx.junior.browser.browser_manager import get_browser_manager
    return get_browser_manager(session.settings)


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

        sessions = await asyncio.to_thread(browser_manager.list_sessions)
        responses = [BrowserSessionResponse(**s.to_public_dict()) for s in sessions]
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
        400: {"description": "Invalid request (unknown project folder)"},
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

    Project folders listed in ``req.share_folders`` are mounted inside the
    container under ``/home/<project_name>/<folder>``; ``req.downloads_folder``
    selects the project folder receiving the browser downloads.
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

        # Docker run + readiness polling + profile setup take seconds and must
        # never block the API event loop (which also serves chats, streaming
        # and every other browser action).
        browser_session = await asyncio.to_thread(
            browser_manager.create_session,
            name=req.name,
            chat_id=req.chat_id,
            initial_url=req.initial_url,
            description=req.description,
            share_project=req.share_project,
            share_folders=req.share_folders,
            readonly=req.readonly,
            downloads_folder=req.downloads_folder,
            downloads_mount=req.downloads_mount,
            kind=req.kind,
            os_version=req.os_version,
            image=req.image,
            image_provider=req.image_provider,
            library_item_id=req.library_item_id,
            control=req.control,
            vnc_host=req.vnc_host,
            vnc_port=req.vnc_port,
            vnc_password=req.vnc_password,
            vnc_public_url=req.vnc_public_url,
            ssh_host=req.ssh_host,
            ssh_port=req.ssh_port,
            ssh_user=req.ssh_user,
            ssh_key_path=req.ssh_key_path,
            ssh_password=req.ssh_password,
            guest_share_path=req.guest_share_path,
            cpu_cores=req.cpu_cores,
            ram_size=req.ram_size,
            disk_size=req.disk_size,
            shm_size=req.shm_size,
            extra_env=req.extra_env,
            desktop_width=req.desktop_width,
            desktop_height=req.desktop_height,
        )

        if chat and chat_manager:
            browser_manager.save_session_to_chat(browser_session, chat)
            chat_manager.save_chat(chat)

        # Start the recorder/watcher without blocking the response.  If the
        # user drives before the AI, their actions must still be visible.
        try:
            asyncio.create_task(browser_manager.warm_runtime(browser_session))
        except RuntimeError:
            pass

        logger.info(
            "create_session: created browser session %s ('%s') for chat %s with %d shared folder(s)",
            browser_session.id[:8],
            browser_session.name,
            req.chat_id,
            len(browser_session.shared_folders),
        )
        return BrowserSessionResponse(**browser_session.to_public_dict())

    except HTTPException:
        raise
    except ValueError as e:
        logger.error("create_session: invalid share configuration: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
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
        return BrowserSessionResponse(**browser_session.to_public_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_session: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/{session_id}",
    response_model=BrowserSessionResponse,
    summary="Update a browser/computer session",
    responses={
        200: {"description": "Session updated"},
        401: {"description": "Unauthorized"},
        404: {"description": "Session not found"},
        500: {"description": "Server error"},
    },
)
async def update_session(request: Request, session_id: str, req: BrowserSessionUpdateRequest):
    """Update name, connection or advanced image/resource settings.

    Resource changes (image, CPUs, RAM, disk, shared memory, environment) are
    stored on the session and applied when it is restarted: Docker cannot
    change them on a running container, and the restart recreates it while
    keeping the profile and the VM disk.
    """
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)
        advanced_keys = {
            "image", "cpu_cores", "ram_size", "disk_size", "shm_size",
            "extra_env", "desktop_width", "desktop_height",
        }
        browser_session = browser_manager.update_session(
            session_id,
            name=req.name,
            description=req.description,
            control=req.control,
            vnc_host=req.vnc_host,
            vnc_port=req.vnc_port,
            vnc_password=req.vnc_password,
            vnc_public_url=req.vnc_public_url,
            ssh_host=req.ssh_host,
            ssh_port=req.ssh_port,
            ssh_user=req.ssh_user,
            ssh_key_path=req.ssh_key_path,
            ssh_password=req.ssh_password,
            advanced=req.model_dump(include=advanced_keys, exclude_unset=True),
        )
        if not browser_session:
            raise HTTPException(status_code=404, detail="Session not found")
        return BrowserSessionResponse(**browser_session.to_public_dict())
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning("update_session: invalid advanced settings: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
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

        # Browser sessions use the browser co-pilot profile; desktops/VMs use
        # the computer profile (same manager, desktop action tools).
        profile_name = "browser" if browser_session.kind == "browser" else "computer"
        profile_available = False
        try:
            profile_available = bool(
                session.get_profile_manager().get_profiles_by_name([profile_name])
            )
        except Exception as ex:
            logger.debug("Could not check the %s profile: %s", profile_name, ex)

        if not chat:
            base_name = f"{browser_session.kind_label}: {browser_session.name or browser_session.id[:8]}"
            suffix = f" ({len(browser_session.chat_ids) + 1})" if browser_session.chat_ids else ""
            chat = Chat(
                name=f"{base_name}{suffix}",
                mode="chat",
                project_id=session.settings.project_id,
                owner_project_id=session.settings.project_id,
                profiles=[profile_name] if profile_available else [],
                meta_data={},
            )
            chat_manager.save_chat(chat)

        # The chat explicitly asks to operate this computer: make sure the
        # matching profile (and therefore its tools) is active.
        if profile_available and profile_name not in (chat.profiles or []):
            chat.profiles = [*(chat.profiles or []), profile_name]

        browser_manager.save_session_to_chat(browser_session, chat)
        chat_manager.save_chat(chat)
        logger.info(
            "open_session_chat: session %s linked to chat %s",
            session_id[:8], chat.id,
        )
        return BrowserSessionChatResponse(
            session=BrowserSessionResponse(**browser_session.to_public_dict()),
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

        await asyncio.to_thread(browser_manager.delete_session, session_id)
        logger.info("delete_session: deleted session %s", session_id[:8])

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("delete_session: unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{session_id}/control",
    response_model=BrowserControlResponse,
    summary="Move the human/AI control lease",
    responses={
        200: {"description": "Control updated"},
        400: {"description": "Invalid action"},
        404: {"description": "Session not found"},
    },
)
async def control_session(request: Request, session_id: str, req: BrowserControlRequest):
    """Take control, hand it to the user/AI, or inspect the current lease.

    Co-browsing works because both actors share one page; this endpoint makes
    the hand-off explicit so the AI does not type over the human (and the human
    is not surprised by an AI navigation).
    """
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)
        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            raise HTTPException(status_code=404, detail="Session not found")

        runtime = await browser_manager.get_runtime(browser_session)
        target = "page" if browser_session.kind == "browser" else "computer"
        action = (req.action or "").strip().lower()
        if action in ("status", "info"):
            state = await runtime.state()
            message = (
                f"controller={state.get('controller')} "
                f"(user_active={state.get('user_active')}, "
                f"connected={state.get('connected')})"
            )
        elif action in ("handoff", "request_handoff", "request"):
            if not req.reason:
                raise HTTPException(400, "reason is required for a handoff")
            runtime.request_handoff(req.reason, chat_id=req.chat_id)
            message = f"Control handed to the user: {req.reason}"
        elif action in ("take_control", "take", "pause"):
            runtime.take_control(chat_id=req.chat_id, reason=req.reason or "user took control")
            message = f"The user now controls the {target}"
        elif action in ("give_back", "release", "resume"):
            runtime.release(chat_id=req.chat_id)
            message = "Control returned to the AI"
        else:
            raise HTTPException(400, f"Unknown control action: {req.action}")

        browser_session = getattr(runtime, "session", None) or browser_session
        browser_events.broadcast_control(browser_session)
        return BrowserControlResponse(
            success=True,
            message=message,
            session=BrowserSessionResponse(**browser_session.to_public_dict()),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("control_session: unexpected error: %s", e)
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
        return BrowserSessionResponse(**browser_session.to_public_dict())

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

        if browser_manager.peek_runtime(session_id) is not None:
            runtime = browser_manager.peek_runtime(session_id)
            await runtime.close()
            browser_manager._runtimes.pop(session_id, None)
        browser_session = await asyncio.to_thread(browser_manager.stop_session, session_id)
        if not browser_session:
            logger.error("stop_session: session not found: %s", session_id)
            raise HTTPException(status_code=404, detail="Session not found")

        logger.info("stop_session: stopped session %s", session_id[:8])
        return BrowserSessionResponse(**browser_session.to_public_dict())

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
    browser_manager = None
    browser_session = None
    action = (req.action or "").lower().strip()
    started_at = time.monotonic()
    params: Dict[str, Any] = {
        key: value
        for key, value in {
            "url": req.url,
            "selector": req.selector,
            "ref": req.ref,
            "text": req.text,
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
    if action == "batch":
        params["steps"] = len(req.steps or [])
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

        runtime = await browser_manager.get_runtime(browser_session)
        # The user is performing this action: it bypasses the AI control lease
        # (the human is allowed to drive at any time) and marks them active.
        if action == "navigate":
            if not req.url:
                raise HTTPException(400, "URL required for navigate action")
            title = await runtime.run("navigate", req.url, force=True)
            message, data = f"Navigated to {req.url}", {"title": title, "url": req.url}

        elif action == "click":
            if req.ref:
                await runtime.run("click_ref", req.ref, force=True)
                message, data = f"Clicked ref {req.ref}", {"ref": req.ref}
            elif req.text:
                await runtime.run("click_text", req.text, force=True)
                message, data = f"Clicked text {req.text!r}", {"text": req.text}
            elif req.selector:
                await runtime.run("click", req.selector, force=True)
                message, data = f"Clicked {req.selector}", {"selector": req.selector}
            else:
                raise HTTPException(400, "Selector, ref or text required for click action")

        elif action == "fill":
            if req.value is None:
                raise HTTPException(400, "Value required for fill action")
            if req.ref:
                await runtime.run("fill_ref", req.ref, req.value, force=True)
                message, data = f"Filled ref {req.ref}", {"ref": req.ref}
            elif req.selector:
                await runtime.run("fill", req.selector, req.value, force=True)
                message, data = f"Filled {req.selector}", {"selector": req.selector}
            else:
                raise HTTPException(400, "Selector or ref required for fill action")

        elif action == "execute":
            if not req.script:
                raise HTTPException(400, "Script required for execute action")
            result = await runtime.run("execute_script", req.script, force=True)
            message, data = "Script executed", {"result": result}

        elif action == "text" or action == "read":
            text = await runtime.run("get_text", read_only=True, force=True)
            message, data = "Page text read", {"text": text}

        elif action == "links":
            links = await runtime.run("get_links", read_only=True, force=True)
            message, data = "Page links read", {"links": links}

        elif action == "snapshot":
            snapshot = await runtime.run("get_snapshot", read_only=True, force=True)
            message, data = "Page snapshot captured", {"snapshot": snapshot}

        elif action == "back":
            title = await runtime.run("go_back", force=True)
            message, data = "Navigated back", {"title": title}

        elif action == "forward":
            title = await runtime.run("go_forward", force=True)
            message, data = "Navigated forward", {"title": title}

        elif action == "refresh":
            title = await runtime.run("reload", force=True)
            message, data = "Page refreshed", {"title": title}

        elif action == "wait":
            if req.text:
                await runtime.run("wait_for_text", req.text, timeout=req.timeout or 5000, force=True)
                message, data = f"Text appeared: {req.text!r}", {"text": req.text}
            elif req.selector:
                await runtime.run("wait_for_selector", req.selector, timeout=req.timeout or 5000, force=True)
                message, data = f"Element appeared: {req.selector}", {"selector": req.selector}
            elif req.url:
                await runtime.run("wait_for_url", req.url, timeout=req.timeout or 5000, force=True)
                message, data = f"URL matched: {req.url}", {"url": req.url}
            else:
                raise HTTPException(400, "Text, selector or URL required for wait action")

        elif action == "press":
            if not req.selector or not req.key:
                raise HTTPException(400, "Selector and key required for press action")
            await runtime.run("press", req.selector, req.key, force=True)
            message, data = f"Pressed {req.key} on {req.selector}", {"selector": req.selector, "key": req.key}

        elif action == "select":
            if not req.selector or req.value is None:
                raise HTTPException(400, "Selector and value required for select action")
            await runtime.run("select", req.selector, req.value, force=True)
            message, data = f"Selected {req.value} on {req.selector}", {"selector": req.selector, "value": req.value}

        elif action == "hover":
            if not req.selector:
                raise HTTPException(400, "Selector required for hover action")
            await runtime.run("hover", req.selector, force=True)
            message, data = f"Hovered {req.selector}", {"selector": req.selector}

        elif action == "scroll":
            await runtime.run("scroll", x=req.x or 0, y=req.y or 0, force=True)
            message, data = "Page scrolled", {"x": req.x or 0, "y": req.y or 0}

        elif action == "screenshot":
            screenshot = await runtime.run("get_screenshot", full_page=bool(req.full_page), force=True)
            message, data = "Screenshot captured", {"screenshot": screenshot, "full_page": bool(req.full_page)}

        elif action == "batch":
            if not req.steps:
                raise HTTPException(400, "Steps required for batch action")
            result = await runtime.run_steps(req.steps, req.variables or {}, force=True)
            message, data = "Batch executed", {"batch": result}

        else:
            raise HTTPException(400, f"Unknown action: {req.action}")

        browser_session = getattr(runtime, "session", None) or browser_session
        # Read-only context reads (snapshot/text/links/screenshot) must not
        # pause the AI: the "Ask AI about this page" button uses them right
        # before the user sends a message.
        if action not in READ_ONLY_ACTIONS:
            browser_session.mark_user_active(seconds=10)
        data.update({
            "url": browser_session.current_url,
            "title": browser_session.current_title,
        })
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

        runtime = await browser_manager.get_runtime(browser_session)
        screenshot = await runtime.run(
            "get_screenshot",
            full_page=req.full_page if req else True,
            read_only=True,
            force=True,
        )
        browser_session = getattr(runtime, "session", None) or browser_session
        browser_session.mark_active()
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

        runtime = await browser_manager.get_runtime(browser_session)
        html = await runtime.run("get_content", read_only=True, force=True)
        browser_session = getattr(runtime, "session", None) or browser_session
        url = browser_session.current_url
        browser_session.mark_active()
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
async def get_activity(
    request: Request,
    session_id: str,
    limit: int = 100,
    since: Optional[str] = None,
    actor: Optional[str] = None,
):
    """Return the most recent user and AI actions performed on the session.

    Args:
        limit: Maximum entries (tail-read, so the endpoint is O(limit), not
            O(file size)).
        since: Only entries with ``ts >= since`` (ISO timestamp).
        actor: Filter by ``user``, ``ai`` or ``system``.
    """
    try:
        session = await get_session_context(request)
        browser_manager = _browser_manager(session)
        browser_session = browser_manager.get_session(session_id)
        if not browser_session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Pick up live VNC input before answering (the watcher is 1 s, but the
        # UI asks right after an action and must see it immediately).
        runtime = browser_manager.peek_runtime(session_id)
        if runtime is not None:
            try:
                await runtime.drain()
            except Exception as ex:
                logger.debug("get_activity drain failed: %s", ex)

        entries = browser_manager.get_activity(session_id, limit=limit)
        if actor:
            entries = [entry for entry in entries if entry.get("actor") == actor]
        if since:
            entries = [entry for entry in entries if (entry.get("ts") or "") >= since]
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
        summary = await asyncio.to_thread(browser_manager.get_cost_summary, session_id)
        return BrowserCostResponse(**summary)
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
    ``share_project`` (bool, optional) · ``share_folders`` (list, optional) ·
    ``downloads_folder`` (str, optional) · ``codx_path`` (str, injected by the client).
    Emits: ``codx-junior-browser-status`` {status, session_id, message, error, session}.
    """
    channel = SessionChannel(sio=sio, sid=sid)
    chat_id = data.get("chat_id")
    name = data.get("name")
    initial_url = data.get("initial_url")
    description = data.get("description")
    share_project = data.get("share_project")
    share_folders = data.get("share_folders")
    readonly = data.get("readonly")
    downloads_folder = data.get("downloads_folder")
    downloads_mount = data.get("downloads_mount")
    kind = data.get("kind") or "browser"
    os_version = data.get("os_version")
    image = data.get("image")
    image_provider = data.get("image_provider")
    library_item_id = data.get("library_item_id")
    control = data.get("control")
    vnc_host = data.get("vnc_host")
    vnc_port = data.get("vnc_port")
    vnc_password = data.get("vnc_password")
    ssh_host = data.get("ssh_host")
    ssh_port = data.get("ssh_port")
    ssh_user = data.get("ssh_user")
    ssh_key_path = data.get("ssh_key_path")
    ssh_password = data.get("ssh_password")
    guest_share_path = data.get("guest_share_path")
    cpu_cores = data.get("cpu_cores")
    ram_size = data.get("ram_size")
    disk_size = data.get("disk_size")
    shm_size = data.get("shm_size")
    extra_env = data.get("extra_env")
    desktop_width = data.get("desktop_width")
    desktop_height = data.get("desktop_height")

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
            share_project=share_project,
            share_folders=share_folders,
            readonly=readonly,
            downloads_folder=downloads_folder,
            downloads_mount=downloads_mount,
            kind=kind,
            os_version=os_version,
            image=image,
            image_provider=image_provider,
            library_item_id=library_item_id,
            control=control,
            vnc_host=vnc_host,
            vnc_port=vnc_port,
            vnc_password=vnc_password,
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
            ssh_key_path=ssh_key_path,
            ssh_password=ssh_password,
            guest_share_path=guest_share_path,
            cpu_cores=cpu_cores,
            ram_size=ram_size,
            disk_size=disk_size,
            shm_size=shm_size,
            extra_env=extra_env,
            desktop_width=desktop_width,
            desktop_height=desktop_height,
        )

        _emit(channel, {
            "status": "created",
            "session_id": browser_session.id,
            "name": browser_session.name,
            "message": f"Browser session '{browser_session.name}' ({browser_session.id[:8]}) created",
            "session": browser_session.to_public_dict(),
        })

        if chat:
            browser_manager.save_session_to_chat(browser_session, chat)
            ChatManager(codxjunior_session.settings).save_chat(chat)

        _emit(channel, {
            "status": "ready",
            "session_id": browser_session.id,
            "name": browser_session.name,
            "message": "Browser session ready",
            "session": browser_session.to_public_dict(),
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
            "session": browser_session.to_public_dict(),
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

        browser_manager.forget_runtime(session_id)
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