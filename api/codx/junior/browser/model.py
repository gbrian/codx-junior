"""
BrowserSession — data model for browser session state.

Stores session configuration and connection info, persisted in Chat.meta_data["browser"]
and in session folder as <session_id>.session JSON file.

A session is shared between chats: ``chat_ids`` holds every chat currently connected
to the session while ``name`` is the human-readable label provided at creation.
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field, model_validator


class BrowserSession(BaseModel):
    """
    Represents the state of a Firefox browser session running in Docker.

    Stores connection details, ports, and session metadata.
    Persisted as JSON in Chat.meta_data["browser"] and as file in session folder.

    A single session may be connected to **several chats** (``chat_ids``); the
    ``name`` is supplied by the caller when the session is created.
    """

    id: Optional[str] = Field(
        default=None,
        description="Unique session identifier (auto-generated)"
    )
    name: Optional[str] = Field(
        default=None,
        description="Human-readable session name given at creation"
    )
    container_id: Optional[str] = Field(
        default=None,
        description="Docker container ID"
    )
    container_name: Optional[str] = Field(
        default=None,
        description="Human-readable container name"
    )
    status: str = Field(
        default="idle",
        description="Current session status: idle, running, stopped, error"
    )
    vnc_url: Optional[str] = Field(
        default=None,
        description="VNC connection URL via Traefik routing"
    )
    debug_url: Optional[str] = Field(
        default=None,
        description="Chrome DevTools Protocol connection URL"
    )
    current_url: Optional[str] = Field(
        default=None,
        description="Currently loaded page URL in browser"
    )
    browser_profile_path: Optional[str] = Field(
        default=None,
        description="Path to persistent Firefox profile (cookies, etc.)"
    )
    chat_ids: List[str] = Field(
        default_factory=list,
        description="Chat IDs connected to this session (multiple chats can share it)"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp when session was created"
    )
    last_active: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of last activity"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if session failed"
    )
    traefik_domain: Optional[str] = Field(
        default=None,
        description="Traefik domain for routing (e.g., app.example.com)"
    )
    traefik_path_prefix: Optional[str] = Field(
        default=None,
        description="Traefik path prefix (e.g., /browser/<session_id>)"
    )

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_chat_id(cls, data: Any) -> Any:
        """
        Backwards compatibility for persisted sessions.

        Older session records stored a single ``chat_id``; map it to the new
        ``chat_ids`` list so existing sessions keep their chat association.
        """
        if isinstance(data, dict) and data.get("chat_id") and not data.get("chat_ids"):
            data = {**data, "chat_ids": [data["chat_id"]]}
        return data

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.id:
            self.id = str(uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for JSON serialization."""
        return self.model_dump(exclude_none=False)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "BrowserSession":
        """Reconstruct session from dictionary."""
        return BrowserSession(**data)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def from_json(json_str: str) -> "BrowserSession":
        """Deserialize from JSON string."""
        return BrowserSession.from_dict(json.loads(json_str))

    def mark_active(self) -> None:
        """Update last_active timestamp to now."""
        self.last_active = datetime.utcnow().isoformat()

    def add_chat(self, chat_id: str) -> None:
        """Connect a chat to this session (idempotent)."""
        if chat_id and chat_id not in self.chat_ids:
            self.chat_ids.append(chat_id)

    def remove_chat(self, chat_id: str) -> None:
        """Disconnect a chat from this session."""
        if chat_id and chat_id in self.chat_ids:
            self.chat_ids.remove(chat_id)

    def has_chat(self, chat_id: str) -> bool:
        """Return True when *chat_id* is connected to this session."""
        return bool(chat_id) and chat_id in self.chat_ids

    def __repr__(self) -> str:
        return (
            f"BrowserSession(id={self.id[:8]}, "
            f"name={self.name!r}, "
            f"status={self.status}, container={self.container_name})"
        )