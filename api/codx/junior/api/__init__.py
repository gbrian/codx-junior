"""
Shared API utilities used across multiple routers.
"""

import logging

from fastapi import Depends, HTTPException, Request

from codx.junior.model.model import CodxUser
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.engine import CODXJuniorSession

logger = logging.getLogger(__name__)


def require_admin(user: CodxUser = Depends(get_authenticated_user)) -> CodxUser:
    """Dependency that raises 403 unless the authenticated user is an admin."""
    if not user or user.role != "admin":
        logger.error("Access denied for user: %s", user.username if user else "anonymous")
        raise HTTPException(status_code=403, detail="Access denied. Admins only.")
    return user

def get_current_session(request: Request) -> CODXJuniorSession:
    """
    Extract the active CODXJuniorSession from the incoming request state.

    This mirrors the pattern used in the wiki router where the session is
    injected into ``request.state`` by middleware before reaching the endpoint.

    Args:
        request: The incoming HTTP request.

    Returns:
        The active ``CODXJuniorSession`` attached to the request state.
    """
    return request.state.codx_junior_session

# Made with ❤️ by codx-junior