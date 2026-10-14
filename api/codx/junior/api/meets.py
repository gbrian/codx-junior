"""
Meets API router – REST endpoints for managing WebRTC meet calls.

The :class:`~codx.junior.meets.meet_manager.MeetManager` keeps the in-memory
registry of active meets, while this router exposes the lifecycle and
signalling operations consumed by the frontend ``meets`` API module.

Route layout
------------
POST   /api/meets/initiate                       – create a new meet
POST   /api/meets/join                           – join an existing meet
POST   /api/meets/leave                          – leave a meet
POST   /api/meets/end                            – end a meet
GET    /api/meets                                – list meets (active by default)
GET    /api/meets/{meet_id}                      – meet details/status
POST   /api/meets/{meet_id}/signal/offer         – relay an SDP offer
POST   /api/meets/{meet_id}/signal/answer        – relay an SDP answer
POST   /api/meets/{meet_id}/signal/ice-candidate – relay an ICE candidate

Diagram:
```mermaid
flowchart TD
    C[Client] -->|POST /api/meets/initiate| A[initiate_meet]
    C -->|POST /api/meets/join| B[join_meet]
    C -->|POST /api/meets/leave| D[leave_meet]
    C -->|POST /api/meets/end| E[end_meet]
    C -->|GET /api/meets| F[list_meets]
    C -->|GET /api/meets/:id| G[get_meet_info]
    C -->|POST .../signal/*| H[relay_signal]
    A --> M[(MeetManager)]
    B --> M
    D --> M
    E --> M
    F --> M
    G --> M
    H --> M
    H -->|socket.io| C
```
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request

from codx.junior.meets.meet_manager import get_meet_manager
from codx.junior.meets.model import (
    MeetAnswerRequest,
    MeetEndRequest,
    MeetIceCandidateRequest,
    MeetInitiateRequest,
    MeetJoinRequest,
    MeetLeaveRequest,
    MeetOfferRequest,
    MeetSignalType,
)
from codx.junior.security.user_management import get_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meets", tags=["meets"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_identity(request: Request) -> tuple:
    """
    Resolve the calling participant identity from the request.

    Prefers the authenticated user (``authentication`` header) and falls back
    to the ``x-username`` header or ``"guest"``. The Socket.IO session
    (``x-sid``) is used to target signalling messages.

    Returns:
        Tuple of ``(username, sid, avatar)``.
    """
    user = get_authenticated_user(request)
    username = (
        getattr(user, "username", None)
        or request.headers.get("x-username")
        or "guest"
    )
    sid = request.headers.get("x-sid")
    avatar = getattr(user, "avatar", "") or ""
    return username, sid, avatar


def _resolve_project_id(request: Request) -> Optional[str]:
    """Return the active project id from the request session, if available."""
    session = getattr(request.state, "codx_junior_session", None)
    settings = getattr(session, "settings", None)
    return getattr(settings, "project_id", None)


async def _emit(event: str, data: dict) -> None:
    """
    Emit a Socket.IO event to connected clients.

    Emission is best-effort: failures (e.g. when running in background mode)
    are logged but never break the HTTP response.
    """
    try:
        from codx.junior.sio.sio import sio_send_event

        await sio_send_event(event, data)
    except Exception as ex:
        logger.warning("Failed to emit socket.io event '%s': %s", event, ex)


async def _relay_signal(
    meet_id: str,
    signal_type: str,
    data: Any,
    to: Optional[str],
    request: Request,
) -> dict:
    """Store a signalling message and broadcast it over Socket.IO."""
    manager = get_meet_manager()
    username, sid, _ = _resolve_identity(request)

    try:
        manager.add_signal(
            meet_id=meet_id,
            signal_type=signal_type,
            sender=username,
            to=to or "",
            data=data,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Meet '{meet_id}' not found")

    await _emit(
        "codx-junior-meet-signal",
        {
            "meetId": meet_id,
            "type": signal_type,
            "from": username,
            "fromSid": sid,
            "to": to or "",
            "signal": data,
        },
    )
    return {"success": True, "meetId": meet_id, "type": signal_type, "to": to or ""}


# ---------------------------------------------------------------------------
# Lifecycle endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def list_meets(request: Request, active: bool = True):
    """Return the list of meets (active only by default)."""
    manager = get_meet_manager()
    meets = manager.list_meets(active_only=active)
    return {
        "success": True,
        "count": len(meets),
        "meets": [meet.model_dump() for meet in meets],
    }


@router.post("/initiate")
async def initiate_meet(payload: MeetInitiateRequest, request: Request):
    """Create (or reactivate) a meet and register the initiator."""
    manager = get_meet_manager()
    username, sid, avatar = _resolve_identity(request)

    meet = manager.initiate_meet(
        meet_id=payload.meetId,
        name=payload.name,
        initiator=username,
        sid=sid,
        avatar=avatar,
        participants=payload.participants,
        project_id=_resolve_project_id(request),
    )

    await _emit(
        "codx-junior-meet",
        {
            "type": "initiated",
            "meetId": meet.meet_id,
            "from": username,
            "meet": meet.model_dump(),
        },
    )
    return {"success": True, "meet": meet.model_dump()}


@router.post("/join")
async def join_meet(payload: MeetJoinRequest, request: Request):
    """Add the caller as a participant of an active meet."""
    manager = get_meet_manager()
    meet_id = payload.meetId
    if not meet_id:
        raise HTTPException(status_code=400, detail="Missing 'meetId' in request body")

    username, sid, avatar = _resolve_identity(request)
    try:
        meet = manager.join_meet(
            meet_id, username=username, sid=sid, avatar=avatar
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Meet '{meet_id}' not found")
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex))

    await _emit(
        "codx-junior-meet",
        {
            "type": "joined",
            "meetId": meet.meet_id,
            "from": username,
            "participants": meet.participant_usernames(),
        },
    )
    return {"success": True, "meet": meet.model_dump()}


@router.post("/leave")
async def leave_meet(payload: MeetLeaveRequest, request: Request):
    """Remove the caller from a meet."""
    manager = get_meet_manager()
    meet_id = payload.meetId
    if not meet_id:
        raise HTTPException(status_code=400, detail="Missing 'meetId' in request body")

    username, sid, _ = _resolve_identity(request)
    try:
        meet = manager.leave_meet(meet_id, username=username, sid=sid)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Meet '{meet_id}' not found")

    await _emit(
        "codx-junior-meet",
        {
            "type": "left",
            "meetId": meet.meet_id,
            "from": username,
            "participants": meet.participant_usernames(),
        },
    )
    return {"success": True, "meet": meet.model_dump()}


@router.post("/end")
async def end_meet(payload: MeetEndRequest, request: Request):
    """End a meet (typically called by the initiator)."""
    manager = get_meet_manager()
    meet_id = payload.meetId
    if not meet_id:
        raise HTTPException(status_code=400, detail="Missing 'meetId' in request body")

    username, _, _ = _resolve_identity(request)
    try:
        meet = manager.end_meet(meet_id, username=username)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Meet '{meet_id}' not found")

    await _emit(
        "codx-junior-meet",
        {"type": "ended", "meetId": meet.meet_id, "from": username},
    )
    return {"success": True, "meet": meet.model_dump()}


@router.get("/{meet_id}")
async def get_meet_info(meet_id: str, request: Request):
    """Return details and status for a single meet."""
    manager = get_meet_manager()
    meet = manager.get_meet(meet_id)
    if not meet:
        raise HTTPException(status_code=404, detail=f"Meet '{meet_id}' not found")
    return {"success": True, "meet": meet.model_dump()}


# ---------------------------------------------------------------------------
# WebRTC signalling endpoints
# ---------------------------------------------------------------------------

@router.post("/{meet_id}/signal/offer")
async def send_offer(meet_id: str, payload: MeetOfferRequest, request: Request):
    """Relay an SDP offer to the target participant."""
    return await _relay_signal(
        meet_id, MeetSignalType.OFFER.value, payload.offer, payload.to, request
    )


@router.post("/{meet_id}/signal/answer")
async def send_answer(meet_id: str, payload: MeetAnswerRequest, request: Request):
    """Relay an SDP answer to the target participant."""
    return await _relay_signal(
        meet_id, MeetSignalType.ANSWER.value, payload.answer, payload.to, request
    )


@router.post("/{meet_id}/signal/ice-candidate")
async def add_ice_candidate(
    meet_id: str, payload: MeetIceCandidateRequest, request: Request
):
    """Relay an ICE candidate to the target participant."""
    return await _relay_signal(
        meet_id,
        MeetSignalType.ICE_CANDIDATE.value,
        payload.candidate,
        payload.to,
        request,
    )