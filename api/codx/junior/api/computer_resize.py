"""
Desktop resize REST endpoint for computer sessions.

The live view knows how big its panel is, but the machine is created with a
fixed resolution, so the desktop is letterboxed inside the viewer.  This router
closes that gap:

* ``mode="client"`` treats ``width``/``height`` as the *viewer* size in CSS
  pixels (``scale`` = device pixel ratio) and fits the desktop to it;
* ``mode="manual"`` applies an explicit resolution (or ``"1920x1080"``).

The change itself is delegated to the backend (``runtime.run("resize", ...)``),
which uses RFB ``SetDesktopSize`` for VNC desktops and ``xrandr`` for Linux
containers.  When the machine cannot resize a running session the response says
so (``supported=false``/``applied=false``) instead of failing: the viewer keeps
scaling the framebuffer, which is the only safe fallback.

Mounted automatically by ``codx.junior.api.discover_routers`` (prefix ``/api``).

Made with ❤️ by codx-junior
"""

import logging
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from codx.junior.api.browser import _browser_manager, get_session_context
from codx.junior.api.browser_models import BrowserSessionResponse
from codx.junior.computer.backend import DesktopControlError, UnsupportedComputerActionError
from codx.junior.computer.resize import (
    MAX_HEIGHT,
    MAX_WIDTH,
    MIN_HEIGHT,
    MIN_WIDTH,
    fit_resolution,
    parse_resolution,
    resolution_from_client,
)
from codx.junior.computer.runtime import ComputerControlError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/computers", tags=["computer"])


class ComputerResizeRequest(BaseModel):
    """Request model to change the desktop resolution of a computer session."""

    model_config = ConfigDict(str_strip_whitespace=True)

    width: Optional[int] = Field(
        default=None,
        ge=MIN_WIDTH,
        le=MAX_WIDTH,
        description="Target width, or the viewer width when mode='client'",
    )
    height: Optional[int] = Field(
        default=None,
        ge=MIN_HEIGHT,
        le=MAX_HEIGHT,
        description="Target height, or the viewer height when mode='client'",
    )
    resolution: Optional[str] = Field(
        default=None,
        description="Alternative to width/height, e.g. '1920x1080' (manual mode)",
    )
    mode: str = Field(
        default="manual",
        description=(
            "'client' fits the desktop to the viewer size (width/height are CSS "
            "pixels), 'manual' applies the given resolution"
        ),
    )
    scale: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Device pixel ratio used in mode='client' (1 = CSS pixels)",
    )


class ComputerResizeResponse(BaseModel):
    """Result of a desktop resolution change."""

    success: bool = Field(default=True, description="Whether the request could be processed")
    message: str = Field(description="Human-readable outcome")
    mode: str = Field(default="manual", description="Requested mode: client or manual")
    supported: bool = Field(default=False, description="Whether this machine can resize a running desktop")
    applied: bool = Field(default=False, description="Whether the requested size is now in use")
    requested_width: Optional[int] = Field(default=None, description="Width asked for the machine")
    requested_height: Optional[int] = Field(default=None, description="Height asked for the machine")
    width: Optional[int] = Field(default=None, description="Desktop width currently in use")
    height: Optional[int] = Field(default=None, description="Desktop height currently in use")
    previous_width: Optional[int] = Field(default=None, description="Desktop width before the call")
    previous_height: Optional[int] = Field(default=None, description="Desktop height before the call")
    session: Optional[BrowserSessionResponse] = Field(
        default=None, description="Updated session (includes the live-view endpoints)"
    )


def _requested_size(req: ComputerResizeRequest) -> Tuple[int, int]:
    """
    Resolve the size requested by the client.

    Args:
        req: Resize request.

    Returns:
        Tuple[int, int]: Requested width/height (not yet fitted).

    Raises:
        HTTPException: 400 when neither ``resolution`` nor ``width``+``height``
            are provided, or when the resolution string cannot be parsed.
    """
    if req.resolution:
        parsed = parse_resolution(req.resolution)
        if not parsed:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid resolution '{req.resolution}'; use WIDTHxHEIGHT (e.g. 1920x1080)",
            )
        return parsed
    if not req.width or not req.height:
        raise HTTPException(
            status_code=400,
            detail="width and height (or resolution) are required",
        )
    return int(req.width), int(req.height)


@router.post(
    "/{session_id}/resize",
    response_model=ComputerResizeResponse,
    summary="Resize the desktop (fit to viewer or manual resolution)",
)
async def resize_computer_desktop(
    request: Request,
    session_id: str,
    req: ComputerResizeRequest,
):
    """
    Change the desktop resolution of a running computer session.

    The viewer normally sends ``mode="client"`` with its element size (and
    ``scale`` = ``window.devicePixelRatio``) after mounting and whenever the
    panel is resized; the resolution selector sends ``mode="manual"``.  A
    machine that cannot resize a running session answers ``applied=false`` and
    the viewer must keep scaling the framebuffer (``object-fit: contain``).
    """
    session_ctx = await get_session_context(request)
    manager = _browser_manager(session_ctx)
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.kind == "browser":
        raise HTTPException(
            status_code=400,
            detail=(
                "Browser sessions have no framebuffer to resize; set desktop_width/"
                "desktop_height with PUT /api/computers/{session_id} and restart it"
            ),
        )
    if session.status != "running":
        raise HTTPException(
            status_code=400,
            detail=f"Session is not running (status: {session.status})",
        )

    mode = str(req.mode or "manual").strip().lower()
    if mode not in ("client", "manual"):
        raise HTTPException(status_code=400, detail="mode must be 'client' or 'manual'")
    requested = _requested_size(req)
    try:
        if mode == "client":
            width, height = resolution_from_client(requested[0], requested[1], scale=req.scale)
        else:
            width, height = fit_resolution(requested[0], requested[1])
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))

    previous_width = session.desktop_width
    previous_height = session.desktop_height
    try:
        runtime = await manager.get_runtime(session)
        result = await runtime.run(
            "resize",
            force=True,
            actor="user",
            width=width,
            height=height,
            mode=mode,
        )
    except ComputerControlError as ex:
        raise HTTPException(status_code=409, detail=str(ex))
    except UnsupportedComputerActionError as ex:
        raise HTTPException(status_code=400, detail=str(ex))
    except DesktopControlError as ex:
        logger.warning("Desktop resize failed for %s: %s", session_id[:8], ex)
        raise HTTPException(status_code=502, detail=str(ex))
    except HTTPException:
        raise
    except Exception as ex:
        logger.exception("Desktop resize failed for %s: %s", session_id[:8], ex)
        raise HTTPException(status_code=500, detail=str(ex))

    data: Dict[str, Any] = result if isinstance(result, dict) else {}
    updated = manager.get_session(session_id) or session
    applied = bool(data.get("applied", False))
    supported = bool(data.get("supported", applied))
    current_width = int(data.get("width") or updated.desktop_width or width)
    current_height = int(data.get("height") or updated.desktop_height or height)
    message = str(data.get("message") or (
        f"Desktop resized to {current_width}x{current_height}"
        if applied else
        "The machine kept its resolution; the live view stays scaled to fit"
    ))
    return ComputerResizeResponse(
        success=True,
        message=message,
        mode=mode,
        supported=supported,
        applied=applied,
        requested_width=width,
        requested_height=height,
        width=current_width,
        height=current_height,
        previous_width=previous_width,
        previous_height=previous_height,
        session=BrowserSessionResponse(**updated.to_public_dict()),
    )

# Made with ❤️ by codx-junior