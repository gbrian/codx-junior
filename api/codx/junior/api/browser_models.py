"""
Pydantic models for browser session API requests/responses.

Defines request payloads and response schemas for REST endpoints.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class BrowserSessionResponse(BaseModel):
    """Response model for a browser session."""
    
    id: str = Field(description="Unique session identifier")
    chat_id: Optional[str] = Field(default=None, description="Associated chat ID")
    container_id: Optional[str] = Field(default=None, description="Docker container ID")
    container_name: Optional[str] = Field(default=None, description="Container name")
    status: str = Field(description="Session status: idle, running, stopped, error")
    vnc_url: Optional[str] = Field(default=None, description="VNC access URL via Traefik")
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
    
    chat_id: str = Field(description="Associated chat ID")


class BrowserSessionActionRequest(BaseModel):
    """Request model for browser actions (navigate, click, fill)."""
    
    action: str = Field(description="Action type: navigate, click, fill, execute")
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