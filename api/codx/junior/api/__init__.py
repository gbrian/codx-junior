"""
Shared API utilities used across multiple routers.
"""

import logging

from fastapi import Depends, HTTPException

from codx.junior.model.model import CodxUser
from codx.junior.security.user_management import get_authenticated_user

logger = logging.getLogger(__name__)


def require_admin(user: CodxUser = Depends(get_authenticated_user)) -> CodxUser:
    """Dependency that raises 403 unless the authenticated user is an admin."""
    if not user or user.role != "admin":
        logger.error("Access denied for user: %s", user.username if user else "anonymous")
        raise HTTPException(status_code=403, detail="Access denied. Admins only.")
    return user

# Made with ❤️ by codx-junior