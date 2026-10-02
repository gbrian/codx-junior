This document describes the API endpoints for managing plugins within the `codx-api` project. These endpoints are protected and require administrator privileges.

### Plugin Management

#### List Plugins

This endpoint retrieves a list of all available plugins.

*   **Endpoint:** `GET /plugins`
*   **Authentication:** Requires an administrator user.
*   **Response:** A list of plugins.

#### Add Plugin

This endpoint adds a new plugin to the system.

*   **Endpoint:** `POST /plugins`
*   **Authentication:** Requires an administrator user.
*   **Request Body:** A JSON object representing the plugin details.
    ```json
    {
      "name": "example_plugin",
      "version": "1.0.0",
      "author": "Author Name",
      "description": "A sample plugin"
    }
    ```
*   **Response:** A success message.

#### Remove Plugin

This endpoint removes a plugin by its name.

*   **Endpoint:** `DELETE /plugins/{plugin_name}`
*   **Authentication:** Requires an administrator user.
*   **Parameters:**
    *   `plugin_name` (path parameter): The name of the plugin to remove.
*   **Response:** A success message.

#### Execute Plugin

This endpoint executes a specific plugin with given context.

*   **Endpoint:** `POST /plugins/{plugin_id}/exec`
*   **Authentication:** Requires an administrator user.
*   **Parameters:**
    *   `plugin_id` (path parameter): The ID of the plugin to execute.
*   **Request Body:** A JSON object containing the context for the plugin execution.
*   **Response:** A message indicating successful execution and the result of the plugin.

#### Load Plugins from File

This endpoint loads plugins from a specified file.

*   **Endpoint:** `GET /plugins/load_from_file`
*   **Authentication:** Requires an administrator user.
*   **Query Parameters:**
    *   `file_path` (query parameter): The path to the file containing plugin definitions.
*   **Response:** A success message.

```python /codx/junior/api/global_settings.py
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
```