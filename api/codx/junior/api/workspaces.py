"""
Workspace API router.

Provides CRUD operations for workspaces (admin-only) and a user-facing
endpoint that returns only the workspaces the authenticated user may access.
Also provides file management for workspace configuration files.

Workspace creation follows a two-step process:
1. Create: Basic info (create a model and copy default template files)
2. Edition: Edit workspace files (Dockerfile, docker-compose.yaml, .env, etc.)
"""

import logging
from typing import List
from uuid import uuid4
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from codx.junior.global_settings import read_global_settings, write_global_settings
from codx.junior.model.model import CodxUser, Workspace
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.api import require_admin
from codx.junior.globals import CODX_JUNIOR_WORKSPACES_FOLDER
from codx.junior.workspace.workspace_manager import WorkspaceManager
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class WorkspaceCreateRequest(BaseModel):
    """Request model for creating a new workspace."""
    name: str
    description: str = ""
    folder_path: str
    project_ids: List[str] = []
    user_ids: List[str] = []
    apps: List = []


class WorkspaceFileContent(BaseModel):
    """Workspace file content model."""
    filename: str
    content: str


class WorkspaceFileResponse(BaseModel):
    """Response model for workspace files."""
    filename: str
    size: int
    created_at: str
    updated_at: str


class WorkspaceResponse(BaseModel):
    """Response model for workspace creation/update."""
    message: str
    workspace: Workspace


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


def _get_workspace_dir(folder_path: str) -> Path:
    """Get the full directory path for a workspace."""
    return Path(CODX_JUNIOR_WORKSPACES_FOLDER) / folder_path


def _ensure_workspace_dir(folder_path: str) -> Path:
    """Ensure workspace directory exists and return its path."""
    workspace_dir = _get_workspace_dir(folder_path)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    return workspace_dir


def _get_workspace_by_id(workspace_id: str) -> Workspace:
    """Get workspace from global settings by id."""
    global_settings = read_global_settings()
    workspace = next(
        (w for w in global_settings.workspaces if w.id == workspace_id), None
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


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
        if _user_has_workspace_access(user, w)
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
# Admin Workspace CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("/workspaces", response_model=List[Workspace])
def list_workspaces(
    user: CodxUser = Depends(require_admin),
) -> List[Workspace]:
    """Return all workspaces (admin only)."""
    global_settings = read_global_settings()
    logger.info("Admin '%s' listed all workspaces (%d total)", user.username, len(global_settings.workspaces))
    return global_settings.workspaces


@router.post("/workspaces", response_model=WorkspaceResponse)
async def create_workspace(
    workspace_request: WorkspaceCreateRequest,
    user: CodxUser = Depends(require_admin),
) -> WorkspaceResponse:
    """
    Create a new workspace (admin only) - Step 1: Basic Info.

    This endpoint creates the workspace model and copies default template files
    from CODX_JUNIOR_DEFAULT_WORKSPACE_PATH to the new workspace folder.

    Required fields:
    - name (str): Workspace name
    - folder_path (str): Folder name under CODX_JUNIOR_WORKSPACES_FOLDER

    Optional fields:
    - description (str): Workspace description
    - project_ids (List[str]): Projects accessible in this workspace
    - user_ids (List[str]): Users who can access this workspace (empty = all users)
    - apps (List[WorkspaceApp]): Apps available in the workspace

    Template files copied include:
    - Dockerfile
    - docker-compose.yaml
    - .env
    - Any other files/directories in the template directory

    Returns:
        WorkspaceResponse with the created workspace and confirmation message
    """
    # Validate required fields
    if not workspace_request.name or not workspace_request.name.strip():
        raise HTTPException(status_code=400, detail="Workspace name is required")
    if not workspace_request.folder_path or not workspace_request.folder_path.strip():
        raise HTTPException(status_code=400, detail="Workspace folder_path is required")

    # Check for duplicate folder_path
    global_settings = read_global_settings()
    if any(w.folder_path == workspace_request.folder_path for w in global_settings.workspaces):
        raise HTTPException(status_code=409, detail=f"Workspace with folder_path '{workspace_request.folder_path}' already exists")

    # Create workspace model with server-generated ID and timestamp
    new_workspace = Workspace(
        id=str(uuid4()),
        name=workspace_request.name.strip(),
        description=workspace_request.description or "",
        folder_path=workspace_request.folder_path.strip(),
        project_ids=workspace_request.project_ids or [],
        user_ids=workspace_request.user_ids or [],
        apps=workspace_request.apps or [],
        updated_at=datetime.now().isoformat(),
    )

    # Copy default template files to new workspace
    workspace_manager = WorkspaceManager()
    if not workspace_manager.create_workspace_files(new_workspace):
        raise HTTPException(status_code=500, detail="Failed to create workspace and copy template files")

    # Save workspace to global settings
    global_settings.workspaces.append(new_workspace)
    write_global_settings(global_settings)

    logger.info(
        "Workspace '%s' (id=%s, folder_path=%s) created by admin '%s'",
        new_workspace.name,
        new_workspace.id,
        new_workspace.folder_path,
        user.username
    )

    return WorkspaceResponse(
        message=f"Workspace '{new_workspace.name}' created successfully with template files. You can now edit workspace files.",
        workspace=new_workspace
    )


@router.put("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    workspace_request: WorkspaceCreateRequest,
    user: CodxUser = Depends(require_admin),
) -> WorkspaceResponse:
    """
    Update an existing workspace's basic information (admin only).

    ``user_ids`` supplied in the body controls who may access the workspace.
    Passing an empty list makes the workspace visible to all users.
    
    To edit workspace files (Dockerfile, docker-compose.yaml, .env, etc.),
    use the file management endpoints instead.
    """
    global_settings = read_global_settings()

    for index, workspace in enumerate(global_settings.workspaces):
        if workspace.id == workspace_id:
            # Update workspace with new data
            updated_data = {
                "id": workspace.id,
                "name": workspace_request.name.strip() if workspace_request.name else workspace.name,
                "description": workspace_request.description or workspace.description,
                "folder_path": workspace.folder_path,  # folder_path is not updatable
                "project_ids": workspace_request.project_ids or workspace.project_ids,
                "user_ids": workspace_request.user_ids or workspace.user_ids,
                "apps": workspace_request.apps or workspace.apps,
                "updated_at": datetime.now().isoformat(),
            }

            updated_workspace = Workspace(**updated_data)
            global_settings.workspaces[index] = updated_workspace
            write_global_settings(global_settings)

            logger.info(
                "Workspace '%s' (id=%s) updated by admin '%s'; user_ids=%s",
                updated_workspace.name,
                workspace_id,
                user.username,
                updated_workspace.user_ids,
            )

            return WorkspaceResponse(
                message=f"Workspace '{updated_workspace.name}' updated successfully.",
                workspace=updated_workspace
            )

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

    logger.info(
        "Workspace '%s' (id=%s) deleted by admin '%s'",
        workspace_to_delete.name,
        workspace_id,
        user.username
    )
    return {"message": "Workspace deleted successfully"}


# ---------------------------------------------------------------------------
# Workspace File Management (Admin only) - Step 2: File Editing
# ---------------------------------------------------------------------------

@router.get("/workspaces/{workspace_id}/files", response_model=List[WorkspaceFileResponse])
def list_workspace_files(
    workspace_id: str,
    user: CodxUser = Depends(require_admin),
) -> List[WorkspaceFileResponse]:
    """
    List all files in a workspace (admin only).
    
    Files are stored in CODX_JUNIOR_WORKSPACES_FOLDER/{workspace.folder_path}/
    """
    workspace = _get_workspace_by_id(workspace_id)
    workspace_dir = _get_workspace_dir(workspace.folder_path)
    
    if not workspace_dir.exists():
        logger.info("Workspace directory does not exist yet: %s", workspace_dir)
        return []
    
    files = []
    try:
        for file_path in workspace_dir.glob("*"):
            if file_path.is_file():
                stat_info = file_path.stat()
                files.append(WorkspaceFileResponse(
                    filename=file_path.name,
                    size=stat_info.st_size,
                    created_at=str(stat_info.st_ctime),
                    updated_at=str(stat_info.st_mtime)
                ))
        
        logger.info("Admin '%s' listed %d files in workspace '%s'", user.username, len(files), workspace.name)
    except Exception as e:
        logger.error("Error listing files in workspace '%s': %s", workspace_id, str(e))
        raise HTTPException(status_code=500, detail="Error listing workspace files")
    
    return files


@router.get("/workspaces/{workspace_id}/files/{filename}", response_model=WorkspaceFileContent)
def get_workspace_file(
    workspace_id: str,
    filename: str,
    user: CodxUser = Depends(require_admin),
) -> WorkspaceFileContent:
    """
    Get the content of a specific workspace file (admin only).
    
    Filenames are validated to prevent directory traversal.
    """
    workspace = _get_workspace_by_id(workspace_id)
    
    # Prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    workspace_dir = _get_workspace_dir(workspace.folder_path)
    file_path = workspace_dir / filename
    
    # Verify the file is within the workspace directory
    try:
        if not file_path.resolve().is_relative_to(workspace_dir.resolve()):
            raise HTTPException(status_code=400, detail="Invalid file path")
    except ValueError:
        # is_relative_to raises ValueError if paths don't have common base
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(file_path, "r") as f:
            content = f.read()
        
        logger.info("Admin '%s' read file '%s' from workspace '%s'", user.username, filename, workspace.name)
        return WorkspaceFileContent(filename=filename, content=content)
    except Exception as e:
        logger.error("Error reading file '%s' from workspace '%s': %s", filename, workspace_id, str(e))
        raise HTTPException(status_code=500, detail="Error reading file")


@router.put("/workspaces/{workspace_id}/files/{filename}", response_model=WorkspaceFileContent)
async def update_workspace_file(
    workspace_id: str,
    filename: str,
    body: WorkspaceFileContent,
    user: CodxUser = Depends(require_admin),
) -> WorkspaceFileContent:
    """
    Create or update a workspace file (admin only).
    
    Filenames are validated to prevent directory traversal.
    The workspace directory is created if it doesn't exist.
    
    Common files to edit:
    - Dockerfile: Base image and custom setup
    - docker-compose.yaml: Service configuration and ports
    - .env: Environment variables
    - coder/coder-init.sh: Custom coder initialization
    """
    workspace = _get_workspace_by_id(workspace_id)
    
    # Prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    workspace_dir = _ensure_workspace_dir(workspace.folder_path)
    file_path = workspace_dir / filename
    
    # Verify the file is within the workspace directory
    try:
        if not file_path.resolve().is_relative_to(workspace_dir.resolve()):
            raise HTTPException(status_code=400, detail="Invalid file path")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    try:
        with open(file_path, "w") as f:
            f.write(body.content)
        
        # Update workspace updated_at timestamp
        global_settings = read_global_settings()
        for idx, ws in enumerate(global_settings.workspaces):
            if ws.id == workspace_id:
                ws.updated_at = datetime.now().isoformat()
                write_global_settings(global_settings)
                break
        
        logger.info("Admin '%s' updated file '%s' in workspace '%s'", user.username, filename, workspace.name)
        return WorkspaceFileContent(filename=filename, content=body.content)
    except Exception as e:
        logger.error("Error writing file '%s' to workspace '%s': %s", filename, workspace_id, str(e))
        raise HTTPException(status_code=500, detail="Error writing file")


@router.delete("/workspaces/{workspace_id}/files/{filename}")
def delete_workspace_file(
    workspace_id: str,
    filename: str,
    user: CodxUser = Depends(require_admin),
) -> dict:
    """
    Delete a workspace file (admin only).
    """
    workspace = _get_workspace_by_id(workspace_id)
    
    # Prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    workspace_dir = _get_workspace_dir(workspace.folder_path)
    file_path = workspace_dir / filename
    
    # Verify the file is within the workspace directory
    try:
        if not file_path.resolve().is_relative_to(workspace_dir.resolve()):
            raise HTTPException(status_code=400, detail="Invalid file path")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        file_path.unlink()
        logger.info("Admin '%s' deleted file '%s' from workspace '%s'", user.username, filename, workspace.name)
        return {"message": f"File '{filename}' deleted successfully"}
    except Exception as e:
        logger.error("Error deleting file '%s' from workspace '%s': %s", filename, workspace_id, str(e))
        raise HTTPException(status_code=500, detail="Error deleting file")


# Made with ❤️ by codx-junior