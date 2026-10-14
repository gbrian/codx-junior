"""
Data models for the Meets subsystem (WebRTC call management).

A *meet* represents a single call session. Each meet tracks:

* its participants (``MeetParticipant``),
* the WebRTC signalling messages exchanged between them (``MeetSignal``),
* and lifecycle metadata (status, timestamps, initiator).

Diagram:
```mermaid
classDiagram
    class Meet {
        +str meet_id
        +str name
        +str initiator
        +MeetStatus status
        +List~MeetParticipant~ participants
        +List~MeetSignal~ signals
    }
    class MeetParticipant {
        +str sid
        +str username
        +bool is_initiator
    }
    class MeetSignal {
        +MeetSignalType type
        +str sender
        +str to
        +Any data
    }
    Meet "1" --> "*" MeetParticipant
    Meet "1" --> "*" MeetSignal
```
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


class MeetStatus(str, Enum):
    """Lifecycle status of a meet."""

    ACTIVE = "active"
    ENDED = "ended"


class MeetSignalType(str, Enum):
    """Types of WebRTC signalling messages."""

    OFFER = "offer"
    ANSWER = "answer"
    ICE_CANDIDATE = "ice-candidate"


class MeetParticipant(BaseModel):
    """A single participant connected to a meet."""

    sid: Optional[str] = Field(
        default=None, description="Socket.IO session id used for signalling"
    )
    username: str = Field(default="", description="Authenticated username")
    name: str = Field(default="", description="Display name shown in the UI")
    avatar: str = Field(default="", description="Avatar URL")
    is_initiator: bool = Field(
        default=False, description="True for the participant who created the meet"
    )
    audio: bool = Field(default=False, description="Microphone enabled")
    video: bool = Field(default=False, description="Camera enabled")
    screen: bool = Field(default=False, description="Screen sharing enabled")
    muted: bool = Field(default=False, description="Participant is muted")
    joined_at: str = Field(
        default_factory=utc_now, description="ISO-8601 join timestamp"
    )
    updated_at: str = Field(
        default_factory=utc_now, description="ISO-8601 last update timestamp"
    )


class MeetSignal(BaseModel):
    """A WebRTC signalling message (offer, answer or ICE candidate)."""

    type: MeetSignalType = Field(description="Signalling message type")
    sender: str = Field(default="", description="Username or sid of the sender")
    to: Optional[str] = Field(
        default="",
        description="Target participant (empty = broadcast to the whole meet)",
    )
    data: Any = Field(
        default=None, description="Raw SDP offer/answer or ICE candidate payload"
    )
    created_at: str = Field(
        default_factory=utc_now, description="ISO-8601 creation timestamp"
    )


class Meet(BaseModel):
    """A WebRTC meet session."""

    meet_id: str = Field(description="Unique meet identifier")
    name: str = Field(default="", description="Human readable meet name")
    initiator: str = Field(
        default="", description="Username of the participant who created the meet"
    )
    status: MeetStatus = Field(
        default=MeetStatus.ACTIVE, description="Meet lifecycle status"
    )
    participants: List[MeetParticipant] = Field(
        default_factory=list, description="Connected participants"
    )
    invited: List[str] = Field(
        default_factory=list, description="Usernames invited to the meet"
    )
    signals: List[MeetSignal] = Field(
        default_factory=list, description="WebRTC signalling history"
    )
    project_id: Optional[str] = Field(
        default=None, description="Project the meet belongs to, if any"
    )
    created_at: str = Field(
        default_factory=utc_now, description="ISO-8601 creation timestamp"
    )
    updated_at: str = Field(
        default_factory=utc_now, description="ISO-8601 last update timestamp"
    )
    ended_at: Optional[str] = Field(
        default=None, description="ISO-8601 end timestamp"
    )

    @property
    def is_active(self) -> bool:
        """Return True while the meet status is ``active``."""
        return self.status == MeetStatus.ACTIVE

    def participant_usernames(self) -> List[str]:
        """Return the list of participant usernames."""
        return [p.username for p in self.participants if p.username]


# ---------------------------------------------------------------------------
# Request payloads – these mirror the frontend `meets` API module.
# ---------------------------------------------------------------------------


class MeetInitiateRequest(BaseModel):
    """Payload for ``POST /api/meets/initiate``."""

    meetId: Optional[str] = Field(
        default=None, description="Client supplied meet id (generated when empty)"
    )
    name: Optional[str] = Field(default="", description="Meet name")
    participants: Optional[List[Any]] = Field(
        default_factory=list, description="Invited participants (usernames or objects)"
    )
    timestamp: Optional[int] = Field(default=None, description="Client timestamp")


class MeetJoinRequest(BaseModel):
    """Payload for ``POST /api/meets/join``."""

    meetId: Optional[str] = Field(default=None, description="Meet to join")
    timestamp: Optional[int] = Field(default=None, description="Client timestamp")


class MeetLeaveRequest(BaseModel):
    """Payload for ``POST /api/meets/leave``."""

    meetId: Optional[str] = Field(default=None, description="Meet to leave")
    timestamp: Optional[int] = Field(default=None, description="Client timestamp")


class MeetEndRequest(BaseModel):
    """Payload for ``POST /api/meets/end``."""

    meetId: Optional[str] = Field(default=None, description="Meet to end")
    timestamp: Optional[int] = Field(default=None, description="Client timestamp")


class MeetOfferRequest(BaseModel):
    """Payload for ``POST /api/meets/{meet_id}/signal/offer``."""

    offer: Optional[Any] = Field(default=None, description="SDP offer")
    to: Optional[str] = Field(default="", description="Target participant")
    timestamp: Optional[int] = Field(default=None, description="Client timestamp")


class MeetAnswerRequest(BaseModel):
    """Payload for ``POST /api/meets/{meet_id}/signal/answer``."""

    answer: Optional[Any] = Field(default=None, description="SDP answer")
    to: Optional[str] = Field(default="", description="Target participant")
    timestamp: Optional[int] = Field(default=None, description="Client timestamp")


class MeetIceCandidateRequest(BaseModel):
    """Payload for ``POST /api/meets/{meet_id}/signal/ice-candidate``."""

    candidate: Optional[Any] = Field(default=None, description="ICE candidate")
    to: Optional[str] = Field(default="", description="Target participant")
    timestamp: Optional[int] = Field(default=None, description="Client timestamp")