import logging
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from codx.junior.model.model import CodxUser
from codx.junior.workspaces.model import Workspace, WorkspaceStatus
from codx.junior.workspaces.manager import WorkspaceManager
from codx.junior.workspaces.templates import AVAILABLE_TEMPLATES

from codx.junior.security.user_management import get_authenticated_user
from codx.junior.api import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspaces"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _manager(request: Request) -> WorkspaceManager:
    codx_junior_session = request.state.codx_junior_session
    return WorkspaceManager(settings=codx_junior_session.settings)


def _get_workspace_or_404(manager: WorkspaceManager, workspace_id: str) -> Workspace:
    workspace = manager.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


def _user_has_workspace_access(user: CodxUser, workspace: Workspace) -> bool:
    """Empty user_ids means the workspace is visible to all users."""
    if "admin" in (getattr(user, "roles", None) or []):
        return True
    # NOTE: confirm whether workspace.user_ids stores usernames or user ids
    return not workspace.user_ids or user.username in workspace.user_ids


def _safe_workspace_file(manager: WorkspaceManager, workspace: Workspace, file_path: str) -> Path:
    """Resolve a file path inside the workspace dir, blocking path traversal."""
    workspace_dir = manager.engine.workspace_dir(workspace).resolve()
    target = (workspace_dir / file_path).resolve()
    if workspace_dir != target and workspace_dir not in target.parents:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return target


# ---------------------------------------------------------------------------
# Templates (declared before /{workspace_id} to avoid route shadowing)
# ---------------------------------------------------------------------------

@router.get("/workspaces/templates")
def list_workspace_templates(user: CodxUser = Depends(require_admin)):
    return AVAILABLE_TEMPLATES


# ---------------------------------------------------------------------------
# CRUD (admin-only mutations, users can list/read what they can access)
# ---------------------------------------------------------------------------

@router.get("/workspaces", response_model=list[Workspace])
def list_workspaces(request: Request, user: CodxUser = Depends(get_authenticated_user)):
    return [
        w for w in _manager(request).list_workspaces()
        if _user_has_workspace_access(user, w)
    ]


@router.get("/workspaces/{workspace_id}", response_model=Workspace)
def get_workspace(workspace_id: str, request: Request, user: CodxUser = Depends(get_authenticated_user)):
    workspace = _get_workspace_or_404(_manager(request), workspace_id)
    if not _user_has_workspace_access(user, workspace):
        raise HTTPException(status_code=403, detail="Access denied")
    return workspace


@router.post("/workspaces", response_model=Workspace)
def create_workspace(workspace: Workspace, request: Request, user: CodxUser = Depends(require_admin)):
    try:
        return _manager(request).create_workspace(workspace)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to create workspace '%s'", workspace.name)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/workspaces", response_model=Workspace)
def update_workspace(
    workspace: Workspace,
    request: Request,
    reprovision: bool = Query(default=False, description="Re-render template files"),
    user: CodxUser = Depends(require_admin),
):
    manager = _manager(request)
    _get_workspace_or_404(manager, workspace.id)
    try:
        return manager.update_workspace(workspace, reprovision=reprovision)
    except Exception as e:
        logger.exception("Failed to update workspace '%s'", workspace.id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workspaces/{workspace_id}")
def delete_workspace(workspace_id: str, request: Request, user: CodxUser = Depends(require_admin)):
    manager = _manager(request)
    _get_workspace_or_404(manager, workspace_id)
    try:
        manager.delete_workspace(workspace_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.exception("Failed to delete workspace '%s'", workspace_id)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Lifecycle (users with workspace access can start/stop)
# ---------------------------------------------------------------------------

@router.post("/workspaces/{workspace_id}/start", response_model=Workspace)
def start_workspace(workspace_id: str, request: Request, user: CodxUser = Depends(get_authenticated_user)):
    manager = _manager(request)
    workspace = _get_workspace_or_404(manager, workspace_id)
    if not _user_has_workspace_access(user, workspace):
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return manager.start_workspace(workspace_id)
    except Exception as e:
        logger.exception("Failed to start workspace '%s'", workspace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workspaces/{workspace_id}/stop", response_model=Workspace)
def stop_workspace(workspace_id: str, request: Request, user: CodxUser = Depends(get_authenticated_user)):
    manager = _manager(request)
    workspace = _get_workspace_or_404(manager, workspace_id)
    if not _user_has_workspace_access(user, workspace):
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        return manager.stop_workspace(workspace_id)
    except Exception as e:
        logger.exception("Failed to stop workspace '%s'", workspace_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspaces/{workspace_id}/status")
def workspace_status(workspace_id: str, request: Request, user: CodxUser = Depends(get_authenticated_user)):
    manager = _manager(request)
    workspace = _get_workspace_or_404(manager, workspace_id)
    if not _user_has_workspace_access(user, workspace):
        raise HTTPException(status_code=403, detail="Access denied")
    return {"status": manager.workspace_status(workspace_id)}


@router.get("/workspaces/{workspace_id}/logs")
def workspace_logs(
    workspace_id: str,
    request: Request,
    tail: int = Query(default=200, ge=1, le=5000),
    user: CodxUser = Depends(require_admin),
):
    manager = _manager(request)
    _get_workspace_or_404(manager, workspace_id)
    return {"logs": manager.workspace_logs(workspace_id, tail=tail)}


# ---------------------------------------------------------------------------
# Workspace files (admin-only: compose file, Dockerfile, scripts, ...)
# ---------------------------------------------------------------------------

@router.get("/workspaces/{workspace_id}/files")
def list_workspace_files(workspace_id: str, request: Request, user: CodxUser = Depends(require_admin)):
    manager = _manager(request)
    workspace = _get_workspace_or_404(manager, workspace_id)
    workspace_dir = manager.engine.workspace_dir(workspace)
    if not workspace_dir.exists():
        return []
    return sorted(
        str(f.relative_to(workspace_dir))
        for f in workspace_dir.rglob("*") if f.is_file()
    )


@router.get("/workspaces/{workspace_id}/file")
def read_workspace_file(workspace_id: str, path: str, request: Request, user: CodxUser = Depends(require_admin)):
    manager = _manager(request)
    workspace = _get_workspace_or_404(manager, workspace_id)
    target = _safe_workspace_file(manager, workspace, path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return {"path": path, "content": target.read_text()}


@router.post("/workspaces/{workspace_id}/file")
def write_workspace_file(
    workspace_id: str,
    path: str,
    request: Request,
    content: str = Body(..., embed=True),
    user: CodxUser = Depends(require_admin),
):
    manager = _manager(request)
    workspace = _get_workspace_or_404(manager, workspace_id)
    target = _safe_workspace_file(manager, workspace, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return {"path": path, "status": "saved"}