"""
Views API router.

Provides CRUD endpoints for desktop layout views scoped to the active project.

```mermaid
flowchart TD
    A[GET /api/views] --> B[ViewManager.list_views]
    C[POST /api/views] --> D[ViewManager.save_view]
    E[DELETE /api/views/{name}] --> F[ViewManager.delete_view]
    G[PUT /api/views/{name}] --> H[ViewManager.rename_view]
```
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from codx.junior.api import get_current_session

from codx.junior.views.model import View
from codx.junior.model.model import CodxUser
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.engine import CODXJuniorSession

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_view_manager(session: CODXJuniorSession):
    """
    Instantiate a ViewManager from the active session's settings.

    Args:
        session: The current CODX Junior session.

    Returns:
        A configured ``ViewManager`` instance.
    """
    from codx.junior.views.view_manager import ViewManager
    return ViewManager(settings=session.settings)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/views", response_model=List[View])
def list_views(
    session: CODXJuniorSession = Depends(get_current_session),
    user: CodxUser = Depends(get_authenticated_user),
) -> List[View]:
    """
    Return all saved views for the active project.

    Access is granted to any authenticated user with access to the project.
    """
    view_manager = _get_view_manager(session)
    views = view_manager.list_views()
    logger.info(
        "User '%s' listed %d views for project '%s'",
        user.username if user else "anonymous",
        len(views),
        session.settings.project_id,
    )
    return views


@router.post("/views", response_model=View)
async def save_view(
    request: Request,
    session: CODXJuniorSession = Depends(get_current_session),
    user: CodxUser = Depends(get_authenticated_user),
) -> View:
    """
    Create or overwrite a named view for the active project.

    The request body must be a JSON object matching the ``View`` schema.
    The ``project_id`` field is always set server-side to the active project.

    Args:
        request: The incoming HTTP request carrying the view payload.
        session: The current CODX Junior session.
        user: The authenticated user performing the request.

    Returns:
        The persisted ``View`` object.
    """
    view_data = await request.json()
    try:
        view = View(**view_data)
    except (TypeError, ValueError) as exc:
        logger.warning(
            "Invalid view payload from user '%s': %s",
            getattr(user, "username", "?"),
            exc,
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    view_manager = _get_view_manager(session)
    saved_view = view_manager.save_view(view)

    logger.info(
        "User '%s' saved view '%s' for project '%s'",
        user.username if user else "anonymous",
        saved_view.name,
        session.settings.project_id,
    )
    return saved_view


@router.put("/views/{name}", response_model=View)
async def rename_view(
    name: str,
    request: Request,
    session: CODXJuniorSession = Depends(get_current_session),
    user: CodxUser = Depends(get_authenticated_user),
) -> View:
    """
    Rename an existing view.

    The request body must contain ``{ "name": "<new_name>" }``.

    Args:
        name: The current view name (URL path parameter).
        request: The incoming HTTP request carrying the new name.
        session: The current CODX Junior session.
        user: The authenticated user performing the request.

    Returns:
        The updated ``View`` object under its new name.

    Raises:
        HTTPException 404: When no view with the given name exists.
        HTTPException 422: When the new name is missing or empty.
    """
    body = await request.json()
    new_name = body.get("name", "").strip()

    if not new_name:
        raise HTTPException(status_code=422, detail="Field 'name' must not be empty.")

    view_manager = _get_view_manager(session)

    try:
        updated_view = view_manager.rename_view(old_name=name, new_name=new_name)
    except FileNotFoundError as exc:
        logger.warning(
            "View '%s' not found for rename by user '%s'",
            name,
            getattr(user, "username", "?"),
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    logger.info(
        "User '%s' renamed view '%s' -> '%s' in project '%s'",
        user.username if user else "anonymous",
        name,
        new_name,
        session.settings.project_id,
    )
    return updated_view


@router.delete("/views/{name}")
def delete_view(
    name: str,
    session: CODXJuniorSession = Depends(get_current_session),
    user: CodxUser = Depends(get_authenticated_user),
) -> dict:
    """
    Delete a saved view by name.

    Args:
        name: The view name to delete (URL path parameter).
        session: The current CODX Junior session.
        user: The authenticated user performing the request.

    Returns:
        A confirmation message dict.

    Raises:
        HTTPException 404: When no view with the given name exists.
    """
    view_manager = _get_view_manager(session)
    deleted = view_manager.delete_view(name)

    if not deleted:
        logger.warning(
            "View '%s' not found for deletion by user '%s'",
            name,
            getattr(user, "username", "?"),
        )
        raise HTTPException(status_code=404, detail=f"View '{name}' not found.")

    logger.info(
        "User '%s' deleted view '%s' from project '%s'",
        user.username if user else "anonymous",
        name,
        session.settings.project_id,
    )
    return {"message": f"View '{name}' deleted successfully."}

# Made with ❤️ by codx-junior