import logging
# Import necessary modules and dependencies
from fastapi import APIRouter, Request, HTTPException, Depends
from codx.junior.security.user_management import get_authenticated_user
from codx.junior.model.model import CodxUser
from codx.junior.plugins.plugin_manager import PluginManager, Plugin

router = APIRouter()

logger = logging.getLogger(__name__)
# Function to check if the user has admin role
def is_admin_user(user: CodxUser = Depends(get_authenticated_user)):
    if 'admin' != user.role:
        logger.error("No allowed {}", user)
        raise HTTPException(status_code=403, detail="Access denied. Admins only.")
    return user

# Initialize PluginManager with global settings path


# Router to list plugins
@router.get("/plugins")
async def read_plugins(user: CodxUser = Depends(is_admin_user)):
    plugin_manager = PluginManager()
    return plugin_manager.list_plugins()

# Router to add a new plugin
@router.post("/plugins")
async def add_plugin(request: Request, user: CodxUser = Depends(is_admin_user)):
    plugin_manager = PluginManager()
    plugin_data = await request.json()
    plugin = Plugin(**plugin_data)
    plugin_manager.add_plugin(plugin)
    return {"message": "Plugin added successfully"}

# Router to remove a plugin
@router.delete("/plugins/{plugin_name}")
async def remove_plugin(plugin_name: str, user: CodxUser = Depends(is_admin_user)):
    plugin_manager = PluginManager()
    plugin_manager.remove_plugin(plugin_name)
    return {"message": "Plugin removed successfully"}

# Router to remove a plugin
@router.post("/plugins/{plugin_id}/exec")
async def exec_plugin(plugin_id: str, user: CodxUser = Depends(is_admin_user)):
    codx_junior_session = request.state.codx_junior_session
    settings = codx_junior_session.settings
    plugin_manager = PluginManager(project_settings=settings, user=user)
    context = await request.json()
    result = await plugin_manager.exec_plugin(plugin_id=plugin_id, context=context)
    return {
      "message": "Plugin executed successfully",
      "result": result
    }

# Router to load plugins from a file
@router.get("/plugins/load_from_file")
async def load_plugins_from_file(request: Request, user: CodxUser = Depends(is_admin_user)):
    plugin_manager = PluginManager()
    file_path = request.query_params.get("file_path")
    plugin_manager.load_from_file(file_path)
    return {"message": "Plugins loaded from file successfully"}