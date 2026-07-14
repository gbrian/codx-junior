# Workspaces API

## Overview

The Workspaces API provides endpoints for managing workspaces within the codx-junior platform. It covers the full lifecycle of a workspace, including creation, retrieval, updating, deletion, starting, stopping, and file management. Access control is enforced at each endpoint using role-based authentication.

---

## Authentication and Authorization

Two levels of access are enforced across endpoints:

- **Authenticated User** (`get_authenticated_user`): Any valid logged-in user. Access to specific workspaces is further filtered by workspace membership.
- **Admin** (`require_admin`): Restricted to users with the `admin` role. Required for mutating operations and sensitive file access.

### Workspace Access Rules

A user is considered to have access to a workspace if any of the following conditions are met (see `_user_has_workspace_access`):

1. The user has the `admin` role.
2. The workspace's `user_ids` list is empty (workspace is visible to all users).
3. The user's `username` is present in the workspace's `user_ids` list.

---

## Helper Utilities

### `_manager(request)`

Instantiates a `WorkspaceManager` from the current session settings attached to the request state.

### `_get_workspace_or_404(manager, workspace_id)`

Fetches a workspace by ID from the manager. Raises a `404 HTTP exception` if the workspace does not exist.

### `_safe_workspace_file(manager, workspace, file_path)`

Resolves a file path within the workspace directory, preventing path traversal attacks. Raises a `400 HTTP exception` if the resolved path falls outside the workspace directory.

---

## Endpoints

### Templates

#### `GET /workspaces/templates`

Returns the list of available workspace templates.

- **Access**: Admin only
- **Returns**: List of available templates from `AVAILABLE_TEMPLATES`

> This route is declared before `/{workspace_id}` routes to avoid route shadowing.

---

### Workspace CRUD

#### `GET /workspaces`

Lists all workspaces accessible to the authenticated user.

- **Access**: Authenticated users
- **Returns**: `list[Workspace]` — filtered by the user's access rights via `_user_has_workspace_access`

---

#### `GET /workspaces/{workspace_id}`

Retrieves a single workspace by its ID.

- **Access**: Authenticated users with access to the workspace
- **Path Parameter**: `workspace_id`
- **Returns**: `Workspace`
- **Errors**:
  - `404` — Workspace not found
  - `403` — Access denied

---

#### `POST /workspaces`

Creates a new workspace.

- **Access**: Admin only
- **Request Body**: `Workspace`
- **Returns**: `Workspace` (created)
- **Errors**:
  - `400` — Validation error (e.g., duplicate name)
  - `500` — Internal server error

---

#### `PUT /workspaces`

Updates an existing workspace.

- **Access**: Admin only
- **Query Parameter**: `reprovision` (boolean, default `false`) — Re-renders template files when set to `true`
- **Request Body**: `Workspace`
- **Returns**: `Workspace` (updated)
- **Errors**:
  - `404` — Workspace not found
  - `500` — Internal server error

---

#### `DELETE /workspaces/{workspace_id}`

Deletes a workspace by its ID.

- **Access**: Admin only
- **Path Parameter**: `workspace_id`
- **Returns**: `{"status": "deleted"}`
- **Errors**:
  - `404` — Workspace not found
  - `500` — Internal server error

---

### Workspace Lifecycle

Authenticated users with access to the workspace may start and stop it.

#### `POST /workspaces/{workspace_id}/start`

Starts the specified workspace.

- **Access**: Authenticated users with workspace access
- **Path Parameter**: `workspace_id`
- **Returns**: `Workspace`
- **Errors**:
  - `403` — Access denied
  - `404` — Workspace not found
  - `500` — Internal server error

---

#### `POST /workspaces/{workspace_id}/stop`

Stops the specified workspace.

- **Access**: Authenticated users with workspace access
- **Path Parameter**: `workspace_id`
- **Returns**: `Workspace`
- **Errors**:
  - `403` — Access denied
  - `404` — Workspace not found
  - `500` — Internal server error

---

#### `GET /workspaces/{workspace_id}/status`

Returns the current status of the workspace.

- **Access**: Authenticated users with workspace access
- **Path Parameter**: `workspace_id`
- **Returns**: `{"status": <WorkspaceStatus>}`
- **Errors**:
  - `403` — Access denied
  - `404` — Workspace not found

---

#### `GET /workspaces/{workspace_id}/logs`

Retrieves the runtime logs for the workspace.

- **Access**: Admin only
- **Path Parameter**: `workspace_id`
- **Query Parameter**: `tail` (integer, default `200`, range `1–5000`) — Number of log lines to return
- **Returns**: `{"logs": <log content>}`
- **Errors**:
  - `404` — Workspace not found

---

### Workspace File Management

These endpoints allow admins to inspect and edit the files within a workspace directory (e.g., compose files, Dockerfiles, scripts). All file access is validated against path traversal using `_safe_workspace_file`.

#### `GET /workspaces/{workspace_id}/files`

Lists all files within the workspace directory.

- **Access**: Admin only
- **Path Parameter**: `workspace_id`
- **Returns**: Sorted list of relative file paths within the workspace directory. Returns an empty list if the workspace directory does not exist.

---

#### `GET /workspaces/{workspace_id}/file`

Reads the content of a specific file within the workspace.

- **Access**: Admin only
- **Path Parameter**: `workspace_id`
- **Query Parameter**: `path` — Relative path to the file within the workspace directory
- **Returns**: `{"path": <path>, "content": <file content>}`
- **Errors**:
  - `400` — Invalid (path traversal) file path
  - `404` — File not found

---

#### `POST /workspaces/{workspace_id}/file`

Writes (creates or overwrites) a file within the workspace directory.

- **Access**: Admin only
- **Path Parameter**: `workspace_id`
- **Query Parameter**: `path` — Relative path to the target file
- **Request Body**: `{"content": "<file content>"}`
- **Returns**: `{"path": <path>, "status": "saved"}`
- **Errors**:
  - `400` — Invalid (path traversal) file path
  - `404` — Workspace not found

> Parent directories are created automatically if they do not exist.

## Dependencies
**Imports from:** codx/junior/global_settings.py, codx/junior/model/model.py, codx/junior/security/user_management.py, codx/junior/api/__init__.py