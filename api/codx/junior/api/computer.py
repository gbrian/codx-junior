"""
Computer session REST API.

Computer sessions generalize browser sessions: a session is a shared machine
(Chromium page, Linux desktop, Windows/macOS VM or a remote host) with one live
view for the human and one control channel for the AI.

The canonical routes live here under ``/api/computers``.  The original
``/api/browsers`` routes stay mounted (see ``api/browser.py``) for existing
clients and chats.  Both prefixes use the same manager and the same session
records, so a session created from either one is visible from the other.

Endpoints
---------
``GET    /api/computers``                    list sessions
``POST   /api/computers``                    create (kind=browser|linux|macos|windows|remote)
``GET    /api/computers/{id}``               details
``PUT    /api/computers/{id}``               rename
``DELETE /api/computers/{id}``               stop, remove and delete
``POST   /api/computers/{id}/action``        page or desktop action
``POST   /api/computers/{id}/screenshot``    PNG data URI (+ OCR text)
``GET    /api/computers/{id}/source``        browser HTML (browser kind)
``GET    /api/computers/{id}/activity``      user/AI audit trail
``GET    /api/computers/{id}/cost``          AI cost of linked chats
``GET    /api/computers/{id}/files``         mounted folders + files
``POST   /api/computers/{id}/control``       handoff / take / give back
``POST   /api/computers/{id}/restart``       restart the machine
``POST   /api/computers/{id}/stop``          stop it
``POST   /api/computers/{id}/vnc-ticket``    one-time noVNC WebSocket ticket
``WS     /api/computers/{id}/vnc``           raw RFB bridge for the built-in viewer

Made with ❤️ by codx-junior
"""

import asyncio
import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, status
from fastapi.responses import FileResponse

from codx.junior.api.browser import (
    _browser_manager,
    control_session,
    create_session,
    delete_session,
    execute_action,
    get_activity,
    get_cost,
    get_session,
    get_session_context,
    get_source,
    list_sessions,
    open_session_chat,
    restart_session,
    stop_session,
    update_session,
)
from codx.junior.api.browser_files import get_shared_files
from codx.junior.api.browser_models import (
    BrowserSessionActionRequest,
    BrowserSessionChatRequest,
    BrowserSessionCreateRequest,
    BrowserSessionListResponse,
    BrowserSessionUpdateRequest,
    BrowserActionResponse,
    BrowserControlRequest,
    BrowserControlResponse,
    BrowserSessionChatResponse,
    BrowserSessionResponse,
    BrowserScreenshotRequest,
    BrowserScreenshotResponse,
    ComputerSessionActionRequest,
    ComputerScreenshotRequest,
    ComputerVncTicketResponse,
    ComputerViewerCredentialsResponse,
)
from codx.junior.computer.images import (
    ComputerImageListResponse,
    ComputerImageTagsResponse,
    list_image_tags,
    list_images,
)
from codx.junior.computer.library import (
    SaveComputerRequest,
    SavedComputer,
    SavedComputerListResponse,
    save_session_to_library,
    saved_library_for,
)
from codx.junior.computer.backend import DesktopControlError, UnsupportedComputerActionError
from codx.junior.computer.runtime import ComputerControlError
from codx.junior.computer.vnc_proxy import bridge_vnc, vnc_tickets

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/computers", tags=["computer"])


# ============================================================================
# Helpers
# ============================================================================
def _desktop_action_params(req: ComputerSessionActionRequest) -> tuple[str, dict]:
    """Convert the API request into backend action parameters."""
    params = req.model_dump(exclude_none=True)
    action = str(params.pop("action", "") or "").lower().strip()
    if "x2" in params and "to_x" not in params:
        params["to_x"] = params["x2"]
    if "y2" in params and "to_y" not in params:
        params["to_y"] = params["y2"]
    # The UI sends the same fields a human would use; drop API-only fields.
    for key in ("session_id", "chat_id", "action"):
        params.pop(key, None)
    return action, params


def _action_message(action: str, result) -> str:
    """Human-readable summary of a desktop action result."""
    if not isinstance(result, dict):
        return f"{action} completed"
    if action == "screenshot":
        text = (result.get("text") or "").strip()
        return (
            f"Screenshot captured ({result.get('width')}x{result.get('height')})"
            + (f"; OCR read {len(text)} chars" if text else "")
        )
    if action == "ocr":
        return f"OCR read {len((result.get('text') or '').strip())} chars"
    if action == "run_command":
        return f"Command exited with {result.get('exit_code')}"
    if action == "windows":
        return f"{len(result.get('windows') or [])} window(s)"
    if action == "click_text":
        matched = result.get("matched") or {}
        return f"Clicked '{matched.get('text')}' at {matched.get('cx')},{matched.get('cy')}"
    if action == "batch":
        return f"Batch finished ({result.get('steps', 0)} step(s))"
    return f"{action} completed"


# ============================================================================
# CRUD (reuse the browser handlers; same manager and records)
# ============================================================================
@router.get("", response_model=BrowserSessionListResponse, summary="List computer sessions")
async def list_computers(request: Request):
    """List every computer session of the project (all kinds)."""
    return await list_sessions(request)


@router.post(
    "",
    response_model=BrowserSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a computer session",
)
async def create_computer(request: Request, req: BrowserSessionCreateRequest):
    """
    Create and start a computer session.

    ``kind`` selects the machine: ``browser`` (Chromium), ``linux`` (desktop
    container), ``windows``/``macos`` (QEMU VM) or ``remote`` (existing VNC/SSH
    host).  Folder sharing and downloads work for every container kind; remote
    sessions only expose the machine (no bind mounts).
    """
    return await create_session(request, req)


@router.get(
    "/images",
    response_model=ComputerImageListResponse,
    summary="Browse the desktop image library",
)
async def list_computer_images(
    request: Request,
    provider: Optional[str] = None,
    q: Optional[str] = None,
    category: Optional[str] = None,
    kind: str = "linux",
    refresh: bool = False,
):
    """
    List Kasmweb and LinuxServer desktop images with their live-view profile.

    The catalog is curated (desktops and popular applications) and is enriched
    from the LinuxServer API when reachable.  ``refresh`` bypasses the cache.
    """
    await get_session_context(request)
    images = await asyncio.to_thread(
        list_images,
        provider=provider,
        query=q,
        category=category,
        kind=kind,
        refresh=refresh,
    )
    return ComputerImageListResponse(count=len(images), images=images)


@router.get(
    "/images/tags",
    response_model=ComputerImageTagsResponse,
    summary="List tags for one image repository",
)
async def list_computer_image_tags(
    request: Request,
    provider: str,
    repository: str,
    refresh: bool = False,
):
    """Return selectable tags (Docker Hub / LinuxServer API, cached)."""
    await get_session_context(request)
    tags = await asyncio.to_thread(
        list_image_tags,
        provider=provider,
        repository=repository,
        refresh=refresh,
    )
    default = tags[0].name if tags else ""
    return ComputerImageTagsResponse(
        provider=provider,
        repository=repository,
        default_tag=default,
        count=len(tags),
        tags=tags,
    )


@router.get(
    "/library",
    response_model=SavedComputerListResponse,
    summary="List saved computers",
)
async def list_saved_computers(request: Request):
    """Return reusable computers saved by project users."""
    session_ctx = await get_session_context(request)
    library = saved_library_for(_browser_manager(session_ctx))
    computers = await asyncio.to_thread(library.list)
    return SavedComputerListResponse(count=len(computers), computers=computers)


@router.get(
    "/library/{item_id}/preview",
    summary="Saved computer preview",
)
async def get_saved_computer_preview(request: Request, item_id: str):
    """Return the screenshot captured when the computer was saved."""
    session_ctx = await get_session_context(request)
    library = saved_library_for(_browser_manager(session_ctx))
    path = library.preview_path(item_id)
    if not library.get(item_id) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Preview not found")
    return FileResponse(path, media_type="image/png")


@router.get(
    "/library/{item_id}",
    response_model=SavedComputer,
    summary="Get a saved computer",
)
async def get_saved_computer(request: Request, item_id: str):
    session_ctx = await get_session_context(request)
    library = saved_library_for(_browser_manager(session_ctx))
    item = await asyncio.to_thread(library.get, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Saved computer not found")
    return item


@router.delete(
    "/library/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved computer",
)
async def delete_saved_computer(request: Request, item_id: str):
    """Delete the library entry and its local Docker image."""
    session_ctx = await get_session_context(request)
    manager = _browser_manager(session_ctx)
    library = saved_library_for(manager)
    item = await asyncio.to_thread(library.get, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Saved computer not found")
    in_use = [
        session for session in manager.list_sessions()
        if getattr(session, "library_item_id", None) == item_id
    ]
    if in_use:
        names = ", ".join(session.name or session.id[:8] for session in in_use[:5])
        raise HTTPException(
            status_code=409,
            detail=f"Saved computer is used by running session(s): {names}",
        )
    user = getattr(session_ctx, "user", None)
    username = getattr(user, "username", "") or ""
    if item.created_by and item.created_by != username and getattr(user, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="Only the creator or an admin can delete this saved computer")
    await asyncio.to_thread(library.delete, item_id)
    return None


@router.get(
    "/{session_id}",
    response_model=BrowserSessionResponse,
    summary="Get a computer session",
)
async def get_computer(request: Request, session_id: str):
    """Return one session with its live-view and control endpoints."""
    return await get_session(request, session_id)


@router.put("/{session_id}", response_model=BrowserSessionResponse, summary="Update a computer session")
async def update_computer(request: Request, session_id: str, req: BrowserSessionUpdateRequest):
    """Update the name, connection or advanced image/resource settings."""
    return await update_session(request, session_id, req)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a computer session")
async def delete_computer(request: Request, session_id: str):
    """Stop and delete a session (profile/storage is moved to trash)."""
    return await delete_session(request, session_id)


@router.post("/{session_id}/chat", response_model=BrowserSessionChatResponse, summary="Open the session chat")
async def open_chat(request: Request, session_id: str, req: Optional[BrowserSessionChatRequest] = None):
    """Reuse or create the chat linked to the session (browser or computer profile)."""
    return await open_session_chat(request, session_id, req)


# ============================================================================
# Actions
# ============================================================================
@router.post("/{session_id}/action", response_model=BrowserActionResponse, summary="Execute an action")
async def execute_computer_action(
    request: Request,
    session_id: str,
    req: ComputerSessionActionRequest,
):
    """
    Execute an action on the shared machine.

    Browser sessions accept the page actions (navigate, click, fill, snapshot,
    batch...).  Desktop sessions accept the computer actions (screenshot, ocr,
    click, click_text, type, key, run_command, open_app, windows, batch...).

    Desktop coordinates are **display pixels**; the UI scales the rendered
    screenshot back to them before calling this endpoint.
    """
    session_ctx = await get_session_context(request)
    manager = _browser_manager(session_ctx)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.kind == "browser":
        browser_req = BrowserSessionActionRequest(
            action=req.action,
            selector=req.selector,
            ref=req.ref,
            text=req.text,
            value=req.value,
            url=req.url,
            script=req.script,
            key=req.key or req.combo,
            timeout=int(req.timeout * 1000) if req.timeout else 5000,
            x=req.x or 0,
            y=req.y or 0,
            full_page=req.full_page if req.full_page is not None else True,
            steps=req.steps,
            variables=req.variables,
        )
        return await execute_action(request, session_id, browser_req)

    if session.status != "running":
        raise HTTPException(
            status_code=400,
            detail=f"Session is not running (status: {session.status})",
        )
    action, params = _desktop_action_params(req)
    if not action:
        raise HTTPException(status_code=400, detail="action is required")
    try:
        runtime = await manager.get_runtime(session)
        if action == "batch":
            result = await runtime.run_steps(
                params.get("steps") or [],
                params.get("variables") or {},
                force=True,
                actor="user",
            )
        else:
            result = await runtime.run(action, force=True, actor="user", **params)
        session = getattr(runtime, "session", None) or session
        return BrowserActionResponse(
            success=True,
            message=_action_message(action, result),
            data=result if isinstance(result, dict) else {"result": result},
        )
    except ComputerControlError as ex:
        raise HTTPException(status_code=409, detail=str(ex))
    except UnsupportedComputerActionError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    except DesktopControlError as ex:
        logger.warning("Desktop action '%s' failed for %s: %s", action, session_id[:8], ex)
        raise HTTPException(status_code=502, detail=str(ex))
    except HTTPException:
        raise
    except Exception as ex:
        logger.exception("Desktop action '%s' failed: %s", action, ex)
        raise HTTPException(status_code=500, detail=str(ex))


@router.post("/{session_id}/screenshot", response_model=BrowserScreenshotResponse, summary="Screenshot")
async def take_computer_screenshot(
    request: Request,
    session_id: str,
    req: Optional[ComputerScreenshotRequest] = None,
):
    """Capture the page (browser) or desktop (computer) as a PNG data URI."""
    session_ctx = await get_session_context(request)
    manager = _browser_manager(session_ctx)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.kind == "browser":
        return await take_browser_screenshot(request, session_id, req)
    if session.status != "running":
        return BrowserScreenshotResponse(success=False, error="Session is not running")
    try:
        runtime = await manager.get_runtime(session)
        result = await runtime.screenshot(
            include_text=bool(req.include_text) if req and req.include_text is not None else True,
            max_width=int(req.max_width) if req and req.max_width else 1600,
            actor="user",
        )
        return BrowserScreenshotResponse(
            success=True,
            screenshot=result.get("image"),
            data={key: value for key, value in result.items() if key != "image"},
        )
    except Exception as ex:
        logger.warning("Computer screenshot failed for %s: %s", session_id[:8], ex)
        return BrowserScreenshotResponse(success=False, error=str(ex))


async def take_browser_screenshot(request: Request, session_id: str, req=None):
    """Delegate to the browser screenshot handler (lazy import avoids a cycle)."""
    from codx.junior.api.browser import take_screenshot

    browser_req = BrowserScreenshotRequest(full_page=True)
    return await take_screenshot(request, session_id, browser_req)


@router.get("/{session_id}/source", summary="Browser page source")
async def get_computer_source(request: Request, session_id: str):
    """Return the page HTML (browser sessions only)."""
    session_ctx = await get_session_context(request)
    manager = _browser_manager(session_ctx)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.kind != "browser":
        raise HTTPException(
            status_code=400,
            detail="Page source is only available for browser sessions; use action='ocr' for desktops",
        )
    return await get_source(request, session_id)


# ============================================================================
# Audit / files / control / lifecycle
# ============================================================================
@router.get("/{session_id}/activity", summary="Shared activity trail")
async def get_computer_activity(
    request: Request,
    session_id: str,
    limit: int = 100,
    actor: Optional[str] = None,
    since: Optional[str] = None,
):
    """Return recent user/AI actions on the session."""
    return await get_activity(request, session_id, limit=limit, actor=actor, since=since)


@router.get("/{session_id}/cost", summary="AI cost of linked chats")
async def get_computer_cost(request: Request, session_id: str):
    """Return the cost summary of the chats connected to the session."""
    return await get_cost(request, session_id)


@router.get("/{session_id}/files", summary="Mounted folders and shared files")
async def get_computer_files(request: Request, session_id: str, limit: int = 200):
    """Return the folder mapping and the files saved by the machine."""
    return await get_shared_files(request, session_id, limit=limit)


@router.post("/{session_id}/control", response_model=BrowserControlResponse, summary="Control lease")
async def control_computer(request: Request, session_id: str, req: BrowserControlRequest):
    """Move the human/AI control lease (take_control, give_back, handoff, pause)."""
    return await control_session(request, session_id, req)


@router.post("/{session_id}/restart", response_model=BrowserSessionResponse, summary="Restart")
async def restart_computer(request: Request, session_id: str):
    """Restart the container machine (profile/storage preserved)."""
    return await restart_session(request, session_id)


@router.post("/{session_id}/stop", response_model=BrowserSessionResponse, summary="Stop")
async def stop_computer(request: Request, session_id: str):
    """Stop the machine but keep it for restart."""
    return await stop_session(request, session_id)


@router.post(
    "/{session_id}/save",
    response_model=SavedComputer,
    summary="Save a running computer to the library",
)
async def save_computer_to_library(
    request: Request,
    session_id: str,
    req: SaveComputerRequest,
):
    """
    Commit the session container and store it as a reusable project computer.

    Linux/Kasmweb desktops only: VM state lives on a separate disk volume.
    """
    session_ctx = await get_session_context(request)
    manager = _browser_manager(session_ctx)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    user = getattr(session_ctx, "user", None)
    username = getattr(user, "username", "") or ""
    try:
        return await save_session_to_library(
            manager,
            session,
            name=req.name,
            description=req.description,
            include_profile=bool(req.include_profile),
            created_by=username,
        )
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    except Exception as ex:
        logger.exception("Could not save computer %s: %s", session_id[:8], ex)
        raise HTTPException(status_code=500, detail=str(ex))


@router.post(
    "/{session_id}/viewer-credentials",
    response_model=ComputerViewerCredentialsResponse,
    summary="Get live-view login credentials",
)
async def get_viewer_credentials(request: Request, session_id: str):
    """
    Return the KasmVNC login user/password for the embedded live view.

    The password is stored only on the session record and deliberately omitted
    from the general session response; this authenticated endpoint hands it to
    the viewer that needs to log in.
    """
    session_ctx = await get_session_context(request)
    manager = _browser_manager(session_ctx)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.viewer_password:
        raise HTTPException(
            status_code=400,
            detail="This session does not use password-protected KasmVNC",
        )
    return ComputerViewerCredentialsResponse(
        session_id=session.id,
        live_view=session.live_view or "kasmvnc",
        user=session.viewer_user or "kasm_user",
        password=session.viewer_password,
        note="Log in to the embedded KasmVNC view with these credentials.",
    )


# ============================================================================
# Live view: one-time ticket + raw RFB WebSocket bridge
# ============================================================================
@router.post(
    "/{session_id}/vnc-ticket",
    response_model=ComputerVncTicketResponse,
    summary="Issue a one-time noVNC ticket",
)
async def create_vnc_ticket(request: Request, session_id: str):
    """
    Return a short-lived WebSocket path for the built-in noVNC viewer.

    The path is relative and already contains the ticket, so the long-lived JWT
    is never placed in a WebSocket URL.  The ticket is bound to this session's
    VNC endpoint and can be redeemed once.
    """
    session_ctx = await get_session_context(request)
    manager = _browser_manager(session_ctx)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.vnc_host or session.control != "vnc":
        raise HTTPException(
            status_code=400,
            detail=(
                "Session has no raw VNC endpoint; browser/Linux sessions use "
                "their web live view (vnc_url/vnc_path)"
            ),
        )
    user = getattr(getattr(session_ctx, "user", None), "username", "") or ""
    ticket = vnc_tickets.issue(
        session.id,
        host=session.vnc_host,
        port=session.vnc_port or 5900,
        user=user,
        session=session,
        manager=manager,
    )
    return ComputerVncTicketResponse(
        session_id=session.id,
        socket_path=f"/api/computers/{session.id}/vnc?ticket={ticket.value}",
        # The ticket is already authenticated and single-use; giving the viewer
        # the session password here avoids putting it in the general session
        # record that the UI/Socket.IO receive.
        password=session.vnc_password,
        expires_in=vnc_tickets.ttl,
    )


@router.websocket("/{session_id}/vnc")
async def computer_vnc_websocket(
    websocket: WebSocket,
    session_id: str,
    ticket: str = Query("", description="Single-use ticket from POST …/vnc-ticket"),
):
    """Tunnel raw RFB bytes between the browser's noVNC client and the machine."""
    ticket_data = vnc_tickets.consume(ticket)
    if ticket_data is None:
        # Close before accept: no unauthenticated WebSocket is upgraded.
        await websocket.close(code=4401, reason="Invalid or expired VNC ticket")
        return
    if ticket_data.session_id != session_id:
        await websocket.close(code=4403, reason="Ticket does not match this session")
        return
    await websocket.accept()
    logger.info(
        "VNC bridge open: session=%s host=%s:%s user=%s",
        session_id[:8], ticket_data.host, ticket_data.port, ticket_data.user or "-",
    )

    last_input = {"at": 0.0}

    def on_user_input():
        """Mark the human active (throttled) when their RFB input crosses."""
        now = time.monotonic()
        if now - last_input["at"] < 1.0:
            return
        last_input["at"] = now
        target = ticket_data.session
        if target is None:
            return
        target.mark_user_active(seconds=10)
        manager = ticket_data.manager
        if manager is not None:
            try:
                manager.save_session(target)
                from codx.junior.browser import events as browser_events
                browser_events.broadcast_control(target)
            except Exception:
                logger.debug("Could not persist VNC user activity", exc_info=True)

    await bridge_vnc(
        websocket,
        ticket_data.host,
        ticket_data.port,
        on_input=on_user_input,
    )
    logger.info("VNC bridge closed: session=%s", session_id[:8])


# Made with ❤️ by codx-junior
