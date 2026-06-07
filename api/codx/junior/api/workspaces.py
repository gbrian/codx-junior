"""
Workspace API router.

Provides CRUD operations for workspaces (admin-only) and a user-facing
endpoint that returns only the workspaces the authenticated user may access.
"""

import logging
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from codx.junior.global_settings import read_global_settings, write_global_settings
from codx.junior.model.model import CodxUser, Workspace
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.api import require_admin

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _user_has_workspace_access(user: CodxUser, workspace: Workspace) -> bool:
    """
    Return True when *user* is allowed to see *workspace*.

    Rules (evaluated in order):
    1. Admin users always have access.
    2. An empty ``user_ids`` list means the workspace is public → all users
       have access.
    3. Otherwise only users whose ``username`` appears in ``user_ids`` are
       granted access.
    """
    if user and user.role == "admin":
        return True
    if not workspace.user_ids:
        return True
    return user is not None and user.username in workspace.user_ids

def _get_and_save_workspaces(updated_workspaces: List[Workspace]) -> None:
    """Persist the supplied workspace list to global settings."""
    global_settings = read_global_settings()
    global_settings.workspaces = updated_workspaces
    write_global_settings(global_settings)


# ---------------------------------------------------------------------------
# User-facing endpoint (non-admin)
# ---------------------------------------------------------------------------

@router.get("/workspaces/accessible", response_model=List[Workspace])
def list_accessible_workspaces(
    user: CodxUser = Depends(get_authenticated_user),
) -> List[Workspace]:
    """
    Return the workspaces that the authenticated user is allowed to access.

    Access rules are identical to those applied in ``/api/projects``:
    - Admin users see all workspaces.
    - Non-admin users see workspaces where ``user_ids`` is empty **or**
      their username is present in ``user_ids``.
    - App entries are further filtered by the user's role.

    ```mermaid
    flowchart TD
        A[Request] --> B{Is admin?}
        B -- Yes --> C[Return all workspaces]
        B -- No  --> D[Filter by user_ids]
        D --> E[Filter app.roles per workspace]
        E --> F[Return filtered workspaces]
    ```
    """
    global_settings = read_global_settings()
    accessible = [
        w for w in global_settings.workspaces
        if user_has_workspace_access(user, w)
    ]

    # For non-admin users strip apps they are not permitted to use.
    if user and user.role != "admin":
        for workspace in accessible:
            workspace.apps = [
                app for app in workspace.apps
                if not app.roles or user.role in app.roles
            ]

    logger.info(
        "User '%s' (role=%s) can access %d of %d workspaces",
        user.username if user else "anonymous",
        user.role if user else "none",
        len(accessible),
        len(global_settings.workspaces),
    )
    return accessible


# ---------------------------------------------------------------------------
# Admin CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("/workspaces", response_model=List[Workspace])
def list_workspaces(
    user: CodxUser = Depends(require_admin),
) -> List[Workspace]:
    """Return all workspaces (admin only)."""
    global_settings = read_global_settings()
    logger.info("Admin '%s' listed all workspaces (%d total)", user.username, len(global_settings.workspaces))
    return global_settings.workspaces


@router.post("/workspaces", response_model=Workspace)
async def create_workspace(
    request: Request,
    user: CodxUser = Depends(require_admin),
) -> Workspace:
    """
    Create a new workspace (admin only).

    The request body must be a JSON object matching the ``Workspace`` schema.
    A fresh UUID is always assigned server-side so callers need not supply one.
    """
    new_workspace_data = await request.json()
    # Always generate a new id server-side to prevent collisions.
    new_workspace_data.pop("id", None)
    new_workspace = Workspace(id=str(uuid4()), **new_workspace_data)

    global_settings = read_global_settings()
    global_settings.workspaces.append(new_workspace)
    write_global_settings(global_settings)

    logger.info("Workspace '%s' (id=%s) created by admin '%s'", new_workspace.name, new_workspace.id, user.username)
    return new_workspace


@router.put("/workspaces/{workspace_id}", response_model=Workspace)
async def update_workspace(
    workspace_id: str,
    request: Request,
    user: CodxUser = Depends(require_admin),
) -> Workspace:
    """
    Replace an existing workspace's data (admin only).

    ``user_ids`` supplied in the body controls who may access the workspace.
    Passing an empty list makes the workspace visible to all users.
    """
    update_data = await request.json()
    global_settings = read_global_settings()

    for index, workspace in enumerate(global_settings.workspaces):
        if workspace.id == workspace_id:
            updated_workspace = workspace.copy(update=update_data)
            global_settings.workspaces[index] = updated_workspace
            write_global_settings(global_settings)

            logger.info(
                "Workspace '%s' (id=%s) updated by admin '%s'; user_ids=%s",
                updated_workspace.name,
                workspace_id,
                user.username,
                updated_workspace.user_ids,
            )
            return updated_workspace

    logger.warning("Workspace id=%s not found for update by admin '%s'", workspace_id, user.username)
    raise HTTPException(status_code=404, detail="Workspace not found")


@router.delete("/workspaces/{workspace_id}")
def delete_workspace(
    workspace_id: str,
    user: CodxUser = Depends(require_admin),
) -> dict:
    """Delete a workspace by its id (admin only)."""
    global_settings = read_global_settings()

    workspace_to_delete = next(
        (w for w in global_settings.workspaces if w.id == workspace_id), None
    )
    if not workspace_to_delete:
        logger.warning("Workspace id=%s not found for deletion by admin '%s'", workspace_id, user.username)
        raise HTTPException(status_code=404, detail="Workspace not found")

    global_settings.workspaces.remove(workspace_to_delete)
    write_global_settings(global_settings)

    logger.info("Workspace '%s' (id=%s) deleted by admin '%s'", workspace_to_delete.name, workspace_id, user.username)
    return {"message": "Workspace deleted successfully"}

# Made with ❤️ by codx-junior