"""
MeetManager – in-memory registry and lifecycle controller for WebRTC meets.

The manager is a process-wide singleton so that meet state survives across the
short-lived ``CODXJuniorSession`` objects created per HTTP request. Meets are
cross-project by nature (a call may involve users browsing different projects);
a ``project_id`` is stored when available so listings can be scoped.

Diagram:
```mermaid
flowchart TD
    IM[initiate_meet] --> REG[(meets registry)]
    JM[join_meet] --> REG
    LM[leave_meet] --> REG
    EM[end_meet] --> REG
    GS[get_meet / list_meets] --> REG
    AS[add_signal] --> REG
```

Made with ❤️ by codx-junior
"""

import logging
import threading
import uuid
from typing import Dict, List, Optional

from codx.junior.meets.model import (
    Meet,
    MeetParticipant,
    MeetSignal,
    MeetStatus,
    utc_now,
)

logger = logging.getLogger(__name__)

# Maximum number of signalling messages kept per meet (oldest are dropped).
MAX_SIGNALS_PER_MEET = 500


class MeetManager:
    """
    Thread-safe in-memory store for WebRTC meets.

    All mutating methods acquire an internal ``RLock``; the class itself is a
    lazily created singleton accessed through :meth:`get_instance`.
    """

    _instance: Optional["MeetManager"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._meets: Dict[str, Meet] = {}
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "MeetManager":
        """Return the process-wide singleton instance."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _require_meet(self, meet_id: str) -> Meet:
        """Return the meet or raise ``KeyError`` when it does not exist."""
        meet = self._meets.get(meet_id)
        if not meet:
            raise KeyError(meet_id)
        return meet

    def _require_active(self, meet_id: str) -> Meet:
        """Return the meet or raise ``ValueError`` when it is not active."""
        meet = self._require_meet(meet_id)
        if meet.status != MeetStatus.ACTIVE:
            raise ValueError(f"Meet '{meet_id}' is not active")
        return meet

    @staticmethod
    def _normalize_invited(participants) -> List[str]:
        """Normalize the ``participants`` payload into a list of usernames."""
        invited: List[str] = []
        for participant in participants or []:
            if isinstance(participant, str):
                invited.append(participant)
            elif isinstance(participant, dict):
                value = (
                    participant.get("username")
                    or participant.get("name")
                    or participant.get("id")
                )
                if value:
                    invited.append(str(value))
        return invited

    def _upsert_participant(
        self,
        meet: Meet,
        username: str = "",
        sid: Optional[str] = None,
        name: str = "",
        avatar: str = "",
        is_initiator: bool = False,
    ) -> MeetParticipant:
        """Find an existing participant (by username or sid) or create a new one."""
        existing: Optional[MeetParticipant] = None
        for participant in meet.participants:
            if username and participant.username == username:
                existing = participant
                break
            if sid and participant.sid == sid:
                existing = participant
                break

        if existing is None:
            existing = MeetParticipant(
                sid=sid,
                username=username,
                name=name or username,
                avatar=avatar,
                is_initiator=is_initiator,
            )
            meet.participants.append(existing)
        else:
            if sid:
                existing.sid = sid
            if name:
                existing.name = name
            if avatar:
                existing.avatar = avatar
            existing.updated_at = utc_now()

        if is_initiator:
            existing.is_initiator = True
        return existing

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def initiate_meet(
        self,
        meet_id: Optional[str] = None,
        name: str = "",
        initiator: str = "",
        sid: Optional[str] = None,
        avatar: str = "",
        participants=None,
        project_id: Optional[str] = None,
    ) -> Meet:
        """
        Create a new meet or reactivate an existing ended one.

        Args:
            meet_id: Client supplied id; a UUID is generated when empty.
            name: Human readable meet name.
            initiator: Username of the participant creating the meet.
            sid: Socket.IO session id of the initiator.
            avatar: Avatar URL of the initiator.
            participants: Invited participants (usernames or objects).
            project_id: Optional owning project id.

        Returns:
            The created/reactivated :class:`Meet`.
        """
        meet_id = meet_id or str(uuid.uuid4())
        with self._lock:
            meet = self._meets.get(meet_id)
            if not meet or meet.status == MeetStatus.ENDED:
                meet = Meet(
                    meet_id=meet_id,
                    name=name or f"Meet {meet_id[:8]}",
                    initiator=initiator,
                    project_id=project_id,
                )
                self._meets[meet_id] = meet
            else:
                meet.status = MeetStatus.ACTIVE
                meet.ended_at = None
                if name:
                    meet.name = name
                if project_id:
                    meet.project_id = project_id

            meet.invited = self._normalize_invited(participants)
            meet.updated_at = utc_now()
            self._upsert_participant(
                meet,
                username=initiator,
                sid=sid,
                avatar=avatar,
                is_initiator=True,
            )
            logger.info(
                "Meet '%s' initiated by '%s' (invited=%s)",
                meet.meet_id,
                initiator,
                meet.invited,
            )
            return meet

    def join_meet(
        self,
        meet_id: str,
        username: str = "",
        sid: Optional[str] = None,
        name: str = "",
        avatar: str = "",
    ) -> Meet:
        """Add a participant to an active meet."""
        with self._lock:
            meet = self._require_active(meet_id)
            self._upsert_participant(
                meet, username=username, sid=sid, name=name, avatar=avatar
            )
            meet.updated_at = utc_now()
            logger.info("'%s' joined meet '%s'", username or sid, meet_id)
            return meet

    def leave_meet(
        self, meet_id: str, username: str = "", sid: Optional[str] = None
    ) -> Meet:
        """Remove a participant (matched by username or sid) from a meet."""
        with self._lock:
            meet = self._require_meet(meet_id)
            meet.participants = [
                participant
                for participant in meet.participants
                if not (
                    (username and participant.username == username)
                    or (sid and participant.sid == sid)
                )
            ]
            meet.updated_at = utc_now()
            logger.info("'%s' left meet '%s'", username or sid, meet_id)
            return meet

    def end_meet(self, meet_id: str, username: str = "") -> Meet:
        """Mark a meet as ended."""
        with self._lock:
            meet = self._require_meet(meet_id)
            meet.status = MeetStatus.ENDED
            meet.ended_at = utc_now()
            meet.updated_at = meet.ended_at
            logger.info("Meet '%s' ended by '%s'", meet_id, username)
            return meet

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def get_meet(self, meet_id: str) -> Optional[Meet]:
        """Return a meet by id, or ``None`` when it does not exist."""
        with self._lock:
            return self._meets.get(meet_id)

    def list_meets(
        self, active_only: bool = True, project_id: Optional[str] = None
    ) -> List[Meet]:
        """Return meets, newest first, optionally filtered by status/project."""
        with self._lock:
            meets = list(self._meets.values())
        if active_only:
            meets = [meet for meet in meets if meet.status == MeetStatus.ACTIVE]
        if project_id:
            meets = [meet for meet in meets if meet.project_id == project_id]
        return sorted(meets, key=lambda meet: meet.created_at, reverse=True)

    # -------------------------------------------------------------------------
    # Signalling
    # -------------------------------------------------------------------------

    def add_signal(
        self,
        meet_id: str,
        signal_type: str,
        sender: str = "",
        to: str = "",
        data=None,
    ) -> Meet:
        """Append a signalling message to a meet's history."""
        with self._lock:
            meet = self._require_meet(meet_id)
            meet.signals.append(
                MeetSignal(type=signal_type, sender=sender, to=to or "", data=data)
            )
            if len(meet.signals) > MAX_SIGNALS_PER_MEET:
                meet.signals = meet.signals[-MAX_SIGNALS_PER_MEET:]
            meet.updated_at = utc_now()
            return meet

    def get_signals(self, meet_id: str):
        """Return the signalling history for a meet."""
        with self._lock:
            meet = self._require_meet(meet_id)
            return list(meet.signals)

    def clear_signals(self, meet_id: str) -> Meet:
        """Clear the signalling history for a meet."""
        with self._lock:
            meet = self._require_meet(meet_id)
            meet.signals = []
            meet.updated_at = utc_now()
            return meet


def get_meet_manager() -> MeetManager:
    """Return the process-wide singleton :class:`MeetManager` instance."""
    return MeetManager.get_instance()