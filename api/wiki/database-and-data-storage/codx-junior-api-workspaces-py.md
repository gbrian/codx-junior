# Workspace API Documentation

The Workspace API provides an interface for managing workspace models and their associated configuration files. Operations are divided into user-accessible endpoints for listing workspaces and administrative endpoints for full CRUD management and file manipulation.

## Models

### WorkspaceCreateRequest
Used for creating or updating a workspace:
* **name**: The display name of the workspace.
* **description**: Optional text description.
* **folder_path**: The directory path under the base configuration folder.
* **project_ids**: List of associated project identifiers.
* **user_ids**: List of users authorized to access the workspace (empty list implies public access).
* **apps**: List of applications available within the workspace.

### Workspace Management
Workspaces follow a two-step lifecycle:
1. **Creation**: Basic info is defined, and default template files (e.g., `Dockerfile`, `docker-compose.yaml`, `.env`) are copied to the workspace directory.
2. **Edition**: Administrative endpoints allow for the modification, retrieval, and deletion of individual configuration files within the workspace directory.

## Access Control
The system determines access rights via the `_user_has_workspace_access` helper function, which adheres to the following logic:
1. **Admin Users**: Always granted access.
2. **Public Workspaces**: If `user_ids` is empty, all authenticated users have access.
3. **Private Workspaces**: Access is restricted to users whose `username` is present in the `user_ids` list.

Non-admin users viewing the accessible workspace list have their `apps` list filtered to only include applications where they have the required roles.

## API Endpoints

### User-facing Endpoints
* **GET /workspaces/accessible**: Returns a list of workspaces permitted for the authenticated user. Includes automatic filtering of applications based on user roles.

### Administrative Endpoints (Admin Only)
* **GET /workspaces**: Returns a list of all existing workspaces.
* **POST /workspaces**: Creates a new workspace and initializes it with template files. Requires a unique `folder_path`.
* **PUT /workspaces/{workspace_id}**: Updates the metadata (name, description, user/project lists) of an existing workspace.
* **DELETE /workspaces/{workspace_id}**: Removes a workspace record from the system.

### File Management Endpoints (Admin Only)
These endpoints allow manipulation of files within the workspace directory (`CODX_JUNIOR_WORKSPACES_FOLDER`). All file operations include validation to prevent directory traversal attacks.

* **GET /workspaces/{workspace_id}/files**: Lists all files within a workspace, including size and timestamps.
* **GET /workspaces/{workspace_id}/files/{filename}**: Retrieves the content of a specific file.
* **PUT /workspaces/{workspace_id}/files/{filename}**: Creates or updates a file (e.g., `Dockerfile`, `.env`).
* **DELETE /workspaces/{workspace_id}/files/{filename}**: Deletes a specific file from the workspace.

***

### References
* [Workspace API router](https://github.com/codx-api/codx/junior/api/workspaces.py)
* [Models Section](https://github.com/codx-api/codx/junior/api/workspaces.py#L35)
* [Helpers Section](https://github.com/codx-api/codx/junior/api/workspaces.py#L67)
* [User-facing Endpoint](https://github.com/codx-api/codx/junior/api/workspaces.py#L103)
* [Admin Workspace CRUD](https://github.com/codx-api/codx/junior/api/workspaces.py#L145)
* [Workspace File Management](https://github.com/codx-api/codx/junior/api/workspaces.py#L311)

## Dependencies
**Imports from:** codx/junior/global_settings.py, codx/junior/model/model.py, codx/junior/security/user_management.py, codx/junior/api/__init__.py