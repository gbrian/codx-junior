import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ApiCallEvent:
    """
    Record of a single API (HTTP) call for performance analysis.

    Captures the endpoint, HTTP method, status code, duration and request
    context (user, project, session) for every HTTP request handled by the
    API. Used to surface slow endpoints, error rates and traffic patterns.

    Diagram:
    classDiagram
        class ApiCallEvent {
            +str path
            +str method
            +int status_code
            +float duration_seconds
            +str endpoint
            +Optional str request_id
            +str username
            +str project_name
            +str project_id
            +Optional str session_id
            +str client_ip
            +str query_string
            +int request_size_bytes
            +int response_size_bytes
            +Optional str error
            +float timestamp
            +str iso_date
        }
    """

    path: str
    """Request path (route template when available), e.g. /api/projects/{project_id}."""

    method: str
    """HTTP method, e.g. GET, POST."""

    status_code: int
    """HTTP response status code."""

    duration_seconds: float
    """Wall-clock seconds taken to process the request."""

    endpoint: str = ""
    """Matched route name (endpoint function), when available."""

    request_id: Optional[str] = None
    """Unique request identifier for traceability (x-request-id header)."""

    username: str = ""
    """Authenticated user (empty when anonymous)."""

    project_name: str = ""
    """Project context name, when available."""

    project_id: str = ""
    """Project identifier, when available."""

    session_id: Optional[str] = None
    """Socket/session identifier (x-sid header), when available."""

    client_ip: str = ""
    """Client IP address, when available."""

    query_string: str = ""
    """Raw query string of the request (may be empty)."""

    request_size_bytes: int = 0
    """Request body size in bytes, when available."""

    response_size_bytes: int = 0
    """Response body size in bytes, when available."""

    error: Optional[str] = None
    """Error message if the request failed."""

    timestamp: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    """Unix timestamp when the request completed."""

    iso_date: str = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"))
    """ISO date (YYYY-MM-DD) for file partitioning."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ApiCallEvent":
        """Create instance from dictionary."""
        known = {f for f in ApiCallEvent.__dataclass_fields__}
        return ApiCallEvent(**{k: v for k, v in data.items() if k in known})

# Made with ❤️ by codx-junior
