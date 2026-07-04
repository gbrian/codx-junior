# Workspace Data Models

The `codx-api` project utilizes structured data models to manage workspaces and their associated applications. These models are defined using Pydantic for validation and schema enforcement.

## WorkspaceApp
The `WorkspaceApp` model defines the configuration for individual applications running within a workspace.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | `str` | `""` | Unique identifier for the application. |
| `name` | `str` | `""` | Name of the application. |
| `description` | `str` | `""` | Description of the application. |
| `icon` | `str` | `""` | Icon path or URL. |
| `path` | `str` | `""` | The URL path for the application. |
| `port` | `Optional[str]` | `""` | Port number for the application. |
| `is_vnc` | `Optional[bool]` | `False` | Whether the application uses VNC. |
| `container_name` | `str` | `""` | Name of the associated container. |
| `roles` | `List[str]` | `[]` | List of roles authorized to access this app. |

## Workspace
The `Workspace` model represents a collection of projects and applications, defining how the environment is structured and who can access it.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `id` | `str` | `""` | Unique identifier for the workspace. |
| `name` | `str` | `""` | Name of the workspace. |
| `description` | `str` | `""` | Description of the workspace. |
| `project_ids` | `List[str]` | `[]` | List of associated project IDs. |
| `apps` | `Optional[List[WorkspaceApp]]` | `[]` | List of `WorkspaceApp` objects. |
| `updated_at` | `Optional[str]` | `None` | Timestamp of the last update. |
| `folder_path` | `str` | `""` | Folder name under `CODX_JUNIOR_WORKSPACES_FOLDER` where files are stored. |
| `user_ids` | `Optional[List[str]]` | `[]` | Allowed user accounts (empty list implies all users). |

## Default Workspace Configuration
The system provides a default workspace configuration (`DEFAULT_WORKSPACE`) used for initialization:

*   **Name**: `codx-junior`
*   **Description**: Default codx-junior workspace
*   **Folder Path**: `codx-junior-workspace-default`
*   **Default Apps**:
    *   **Coder**: Coding environment located at `/workspace-default/coder/`.
    *   **Desktop**: Virtual desktop located at `/workspace-default/preview/index.html`.
    *   **LiteLLM**: Models manager located at `/litellm/ui`.
*   **Project Access**: Allows all projects (`"*"`)

***

**References**
*   `codx/junior/model/workspace.py` - Workspace and WorkspaceApp Pydantic definitions.
*   `codx/junior/model/workspace.py` - DEFAULT_WORKSPACE instance configuration.