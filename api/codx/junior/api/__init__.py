"""
Shared API utilities used across multiple routers.
"""

import logging
import os
import importlib
from pathlib import Path
from typing import List

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


def discover_routers() -> List[dict]:
    """
    Dynamically discover all routers in the api package.
    Each router module should export a 'router' attribute.
    
    Returns:
        List of dicts with 'router', 'prefix', and 'module' keys.
    """
    routers = []
    api_package_path = Path(__file__).parent
    
    # Get all Python files in the api directory (excluding __init__.py and test files)
    router_files = [
        f.stem for f in api_package_path.glob('*.py')
        if f.is_file() and f.stem not in ['__init__', '__pycache__']
        and not f.name.startswith('test_')
    ]
    
    for module_name in sorted(router_files):
        try:
            # Import the module dynamically
            module = importlib.import_module(f'codx.junior.api.{module_name}')
            
            # Check if module has a 'router' attribute
            if hasattr(module, 'router'):
                router_obj = getattr(module, 'router')
                routers.append({
                    'router': router_obj,
                    'prefix': '/api',
                    'module': module_name
                })
                logger.info(f"Loaded router from module: {module_name}")
            else:
                logger.debug(f"Module {module_name} does not export 'router' attribute")
        except ImportError as e:
            logger.error(f"Failed to import router module {module_name}: {e}")
        except Exception as e:
            logger.error(f"Error loading router from {module_name}: {e}")
    
    logger.info(f"Successfully discovered {len(routers)} routers")
    return routers

# Made with ❤️ by codx-junior