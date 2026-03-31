
import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.model.model import CodxUser, Workspace, GlobalSettings
from typing import List
from uuid import uuid4

logger = logging.getLogger(__name__)

router = APIRouter()

# Function to check if the user has the admin role
def is_admin_user(user: CodxUser = Depends(get_authenticated_user)) -> CodxUser:
    if user.role != 'admin':
        logger.error("Access denied for user: %s", user.username)
        raise HTTPException(status_code=403, detail="Access denied. Admins only.")
    return user

# Create a new workspace
@router.post("/workspaces", response_model=Workspace)
async def create_workspace(request: Request, user: CodxUser = Depends(is_admin_user)) -> Workspace:
    try:
        # Parse the incoming request.
        new_workspace_data = await request.json()
        new_workspace = Workspace(id=str(uuid4()), **new_workspace_data)

        # Access global settings
        global_settings = request.state.codx_junior_session.settings
        global_settings.workspaces.append(new_workspace)

        logger.info("Workspace %s created successfully by user %s", new_workspace.name, user.username)
        return new_workspace
    except Exception as e:
        logger.error("Failed to create workspace: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# List all workspaces
@router.get("/workspaces", response_model=List[Workspace])
async def list_workspaces(user: CodxUser = Depends(is_admin_user)) -> List[Workspace]:
    global_settings = request.state.codx_junior_session.settings
    return global_settings.workspaces

# Update an existing workspace
@router.put("/workspaces/{workspace_id}", response_model=Workspace)
async def update_workspace(workspace_id: str, request: Request, user: CodxUser = Depends(is_admin_user)) -> Workspace:
    try:
        update_data = await request.json()
        global_settings = request.state.codx_junior_session.settings
        for workspace in global_settings.workspaces:
            if workspace.id == workspace_id:
                updated_workspace = workspace.copy(update=update_data)
                workspace_index = global_settings.workspaces.index(workspace)
                global_settings.workspaces[workspace_index] = updated_workspace
                logger.info("Workspace %s updated by user %s", updated_workspace.name, user.username)
                return updated_workspace
        raise HTTPException(status_code=404, detail="Workspace not found")
    except Exception as e:
        logger.error("Failed to update workspace: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# Delete a workspace
@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: str, user: CodxUser = Depends(is_admin_user)) -> dict:
    try:
        global_settings = request.state.codx_junior_session.settings
        workspace_to_delete = next((w for w in global_settings.workspaces if w.id == workspace_id), None)
        if workspace_to_delete:
            global_settings.workspaces.remove(workspace_to_delete)
            logger.info("Workspace %s deleted by user %s", workspace_to_delete.name, user.username)
            return {"message": "Workspace deleted successfully"}
        raise HTTPException(status_code=404, detail="Workspace not found")
    except Exception as e:
        logger.error("Failed to delete workspace: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

# Made with ❤️ by codx-junior