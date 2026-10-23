"""
Pydantic models for browser session API requests/responses.

Defines request payloads and response schemas for REST endpoints and the
Socket.IO request/event models used by the long-running browser lifecycle
operations (create / stop / restart / delete).
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class BrowserSessionResponse(BaseModel):
    """Response model for a browser session."""

    id: str = Field(description="Unique session identifier")
    name: Optional[str] = Field(default=None, description="Human-readable session name")
    chat_ids: List[str] = Field(default_factory=list, description="Chat IDs connected to this session")
    container_id: Optional[str] = Field(default=None, description="Docker container ID")
    container_name: Optional[str] = Field(default=None, description="Container name")
    status: str = Field(description="Session status: idle, running, stopped, error")
    vnc_url: Optional[str] = Field(default=None, description="VNC access URL via Traefik")
    debug_url: Optional[str] = Field(default=None, description="DevTools/CDP connection URL")
    browser_profile_path: Optional[str] = Field(default=None, description="Persistent Firefox profile path")
    current_url: Optional[str] = Field(default=None, description="Currently loaded page URL")
    created_at: str = Field(description="ISO timestamp when created")
    last_active: str = Field(description="ISO timestamp of last activity")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    traefik_domain: Optional[str] = Field(default=None, description="Traefik domain")
    traefik_path_prefix: Optional[str] = Field(default=None, description="Traefik path prefix")


class BrowserSessionListResponse(BaseModel):
    """Response model for listing browser sessions."""

    count: int = Field(description="Total number of sessions")
    sessions: List[BrowserSessionResponse] = Field(description="List of sessions")


class BrowserSessionCreateRequest(BaseModel):
    """Request model to create a new browser session."""

    name: str = Field(description="Human-readable session name")
    chat_id: Optional[str] = Field(default=None, description="Optional chat ID to connect the session to")


class BrowserSessionActionRequest(BaseModel):
    """Request model for browser actions (navigate, click, fill)."""

    action: str = Field(description="Action type: navigate, click, fill, execute, text")
    selector: Optional[str] = Field(default=None, description="CSS selector (for click/fill)")
    value: Optional[str] = Field(default=None, description="Value to fill (for fill action)")
    url: Optional[str] = Field(default=None, description="URL to navigate to")
    script: Optional[str] = Field(default=None, description="JavaScript to execute")


class BrowserActionResponse(BaseModel):
    """Response model for browser actions."""

    success: bool = Field(description="Whether action succeeded")
    message: str = Field(description="Action result message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Action-specific data")


class BrowserScreenshotResponse(BaseModel):
    """Response model for screenshot."""

    success: bool = Field(description="Whether screenshot succeeded")
    screenshot: Optional[str] = Field(default=None, description="Base64-encoded PNG data URI")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class BrowserSourceResponse(BaseModel):
    """Response model for page source."""

    success: bool = Field(description="Whether retrieval succeeded")
    html: Optional[str] = Field(default=None, description="HTML content (truncated)")
    url: Optional[str] = Field(default=None, description="Current page URL")
    error: Optional[str] = Field(default=None, description="Error message if failed")


# ============================================================================
# Socket.IO Browser Session Models
# ============================================================================

class SioBrowserCreateRequest(BaseModel):
    """Socket.IO request model to create a new browser session."""

    codx_path: str = Field(description="Project codx path")
    name: str = Field(description="Human-readable session name")
    chat_id: Optional[str] = Field(default=None, description="Optional chat ID to connect the session to")


class SioBrowserDeleteRequest(BaseModel):
    """Socket.IO request model to delete a browser session."""

    codx_path: str = Field(description="Project codx path")
    session_id: str = Field(description="Session ID to delete")


class SioBrowserRestartRequest(BaseModel):
    """Socket.IO request model to restart a browser session."""

    codx_path: str = Field(description="Project codx path")
    session_id: str = Field(description="Session ID to restart")


class SioBrowserStopRequest(BaseModel):
    """Socket.IO request model to stop a browser session."""

    codx_path: str = Field(description="Project codx path")
    session_id: str = Field(description="Session ID to stop")


class BrowserStatusEvent(BaseModel):
    """Socket.IO event model for browser session status updates."""

    status: str = Field(
        description=(
            "Operation status: starting, created, starting_container, ready, "
            "restarting, stopping, stopped, deleted, error"
        )
    )
    session_id: Optional[str] = Field(default=None, description="Session ID")
    name: Optional[str] = Field(default=None, description="Human-readable session name")
    chat_ids: List[str] = Field(default_factory=list, description="Chats connected to the session")
    container_id: Optional[str] = Field(default=None, description="Docker container ID")
    message: str = Field(description="Human-readable status message")
    error: Optional[str] = Field(default=None, description="Error message if status is error")
    session: Optional[BrowserSessionResponse] = Field(
        default=None, description="Full session details (included in ready status)"
    )
    ts: Optional[int] = Field(default=None, description="Timestamp of event")

# Made with ❤️ by codx-junior