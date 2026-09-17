import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from codx.junior.model.model import CodxUser

from codx.junior.api.workspace_models import (
    Workspace,
    WorkspaceDeleteResponse,
    WorkspaceFileWriteRequest,
    WorkspaceFileReadResponse,
    WorkspaceFileWriteResponse,
)
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.api import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspaces"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_session(request: Request):
    """Return the project-scoped session from the request state."""
    session = getattr(request.state, "codx_junior_session", None)
    if not session:
        raise HTTPException(status_code=400, detail="No project session — pass codx_path query param")
    return session


def _get_workspace_or_404(session, workspace_id: str) -> Workspace:
    workspace = session.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


def _user_has_workspace_access(user: CodxUser, workspace: Workspace) -> bool:
    """Admins always pass; empty user_ids means public."""
    if "admin" in (getattr(user, "roles", None) or []) or getattr(user, "role", None) == "admin":
        return True
    return not workspace.user_ids or user.username in workspace.user_ids


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.get("/workspaces", response_model=list[Workspace])
def list_workspaces(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    """
    Return all workspaces for the current project accessible to the user.

    Workspaces are stored per-project under ``{codx_path}/workspaces/``,
    mirroring how profiles and chats are stored.
    """
    session = _get_session(request)
    return [
        w for w in session.list_workspaces()
        if _user_has_workspace_access(user, w)
    ]


@router.get("/workspaces/{workspace_id}", response_model=Workspace)
def get_workspace(workspace_id: str, request: Request, user: CodxUser = Depends(get_authenticated_user)):
    """Return a single workspace by id."""
    session = _get_session(request)
    workspace = _get_workspace_or_404(session, workspace_id)
    if not _user_has_workspace_access(user, workspace):
        raise HTTPException(status_code=403, detail="Access denied")
    return workspace


@router.post("/workspaces", response_model=Workspace)
def create_workspace(
    workspace: Workspace,
    request: Request,
    user: CodxUser = Depends(require_admin)
):
    """
    Create a new workspace for the current project (admin only).

    The workspace is saved as a JSON file under ``{codx_path}/workspaces/{id}.workspace``.
    A server-side UUID is always assigned as the workspace id.
    
    """
    session = _get_session(request)
    workspace.id = ""  # Force server-side id assignment
    try:
        return session.save_workspace(workspace)
    except Exception as e:
        logger.exception("Failed to create workspace '%s'", workspace.name)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/workspaces", response_model=Workspace)
def update_workspace(
    workspace: Workspace,
    request: Request,
    user: CodxUser = Depends(require_admin),
):
    """
    Update an existing workspace (admin only).

    Send the full ``Workspace`` object. The workspace must already exist
    (identified by its ``id``).
    
    """
    session = _get_session(request)
    _get_workspace_or_404(session, workspace.id)
    try:
        return session.save_workspace(workspace)
    except Exception as e:
        logger.exception("Failed to update workspace '%s'", workspace.id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workspaces/{workspace_id}", response_model=WorkspaceDeleteResponse)
def delete_workspace(workspace_id: str, request: Request, user: CodxUser = Depends(require_admin)):
    """Delete a workspace (admin only). Removes the workspace file and folder from disk."""
    session = _get_session(request)
    _get_workspace_or_404(session, workspace_id)
    try:
        session.delete_workspace(workspace_id)
        return WorkspaceDeleteResponse()
    except Exception as e:
        logger.exception("Failed to delete workspace '%s'", workspace_id)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# File Management
# ---------------------------------------------------------------------------

@router.get("/workspaces/{workspace_id}/files", response_model=dict)
def list_workspace_files(
    workspace_id: str,
    path: str = "",
    request: Request = None,
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    List files and folders in a workspace directory.
    
    Query params:
    - path (str, optional): Relative path within workspace (default: root)
    
    Returns:
        Dict with 'files' and 'folders' lists
    """
    session = _get_session(request)
    workspace = _get_workspace_or_404(session, workspace_id)
    if not _user_has_workspace_access(user, workspace):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        manager = session.get_workspace_manager()
        return manager.list_workspace_files(workspace_id, path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Path not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to list files in workspace '%s'", workspace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/files/{file_path:path}", response_model=WorkspaceFileReadResponse)
def read_workspace_file(
    workspace_id: str,
    file_path: str,
    request: Request = None,
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Read a file from a workspace.
    
    Path params:
    - workspace_id: The workspace ID
    - file_path: Relative path to file within workspace (e.g., "docker-compose.yaml")
    
    Returns:
        WorkspaceFileReadResponse with path and content
    """
    session = _get_session(request)
    workspace = _get_workspace_or_404(session, workspace_id)
    if not _user_has_workspace_access(user, workspace):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        manager = session.get_workspace_manager()
        content = manager.read_workspace_file(workspace_id, file_path)
        return WorkspaceFileReadResponse(path=file_path, content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to read file '%s' in workspace '%s'", file_path, workspace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/files/{file_path:path}", response_model=WorkspaceFileWriteResponse)
def write_workspace_file(
    workspace_id: str,
    file_path: str,
    body: WorkspaceFileWriteRequest = Body(...),
    request: Request = None,
    user: CodxUser = Depends(get_authenticated_user),
):
    """
    Write a file to a workspace.
    
    Path params:
    - workspace_id: The workspace ID
    - file_path: Relative path to file within workspace (e.g., "docker-compose.yaml")
    
    Request body:
    {
        "content": "file content here"
    }
    
    Returns:
        WorkspaceFileWriteResponse with path and status
    """
    session = _get_session(request)
    workspace = _get_workspace_or_404(session, workspace_id)
    if not _user_has_workspace_access(user, workspace):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        manager = session.get_workspace_manager()
        manager.write_workspace_file(workspace_id, file_path, body.content)
        return WorkspaceFileWriteResponse(path=file_path, status="saved")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Workspace not found: {workspace_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to write file '%s' in workspace '%s'", file_path, workspace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/generate-files")
def regenerate_workspace_files(
    workspace_id: str,
    request: Request = None,
    user: CodxUser = Depends(require_admin),
):
    """
    Regenerate Docker and config files for a workspace using AI.
    
    This endpoint allows regenerating all workspace configuration files
    without modifying the workspace definition itself. Useful when you want
    to update generated files after changing the workspace.
    
    Returns:
        JSON with status and list of generated files
    """
    import asyncio
    
    session = _get_session(request)
    workspace = _get_workspace_or_404(session, workspace_id)
    
    try:
        manager = session.get_workspace_manager()
        workspace_folder = manager._workspace_folder_path(workspace_id)
        
        # CHANGED: Use asyncio.create_task for async-first file generation,
        # with fallback to sync when no event loop is running
        try:
            asyncio.create_task(manager._generate_workspace_files_async(workspace, workspace_folder))
            logger.info("Scheduled async file generation for workspace '%s'", workspace.name)
        except RuntimeError:
            # No running event loop; use sync fallback
            manager._generate_workspace_files_sync(workspace, workspace_folder)
            logger.info("Using sync file generation for workspace '%s'", workspace.name)
        
        return {
            "status": "success",
            "message": f"Files generation started for workspace '{workspace.name}'",
            "workspace_id": workspace_id,
        }
    except Exception as e:
        logger.exception("Failed to regenerate files for workspace '%s'", workspace_id)
        raise HTTPException(status_code=500, detail=str(e))