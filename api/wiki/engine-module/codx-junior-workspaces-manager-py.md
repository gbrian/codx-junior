# Workspace Manager

## Overview

The `WorkspaceManager` class serves as the central orchestration façade for managing workspaces within a project. It combines **persistence** (reading and writing workspace metadata) with **engine lifecycle management** (provisioning, starting, stopping, and destroying workspaces).

Workspaces belong to a project and are stored under the path:

```
[project_path]/.codx/workspaces
```

Each workspace occupies its own subfolder, which holds both its metadata file (`workspace.json`) and its runtime files (e.g., `docker-compose.yaml`).

---

## Initialization

```python
WorkspaceManager(settings: CODXJuniorSettings, engine: Optional[WorkspaceEngine] = None)
```

**Parameters:**

| Parameter  | Type                    | Description                                                                 |
|------------|-------------------------|-----------------------------------------------------------------------------|
| `settings` | `CODXJuniorSettings`    | Project settings used to determine the base path for workspaces.            |
| `engine`   | `Optional[WorkspaceEngine]` | The backend engine used for workspace lifecycle operations. Defaults to `DockerComposeEngine`. |

On initialization, the manager:
1. Resolves the `workspaces_path` as `{settings.codx_path}/workspaces`.
2. Creates the `workspaces_path` directory if it does not already exist.
3. Instantiates the provided engine or defaults to `DockerComposeEngine`.

---

## Persistence

### Metadata Storage

Each workspace's metadata is stored in a file named `workspace.json` located inside the workspace's own subfolder under `workspaces_path`. The constant `WORKSPACE_METADATA_FILE = "workspace.json"` defines this filename.

### `list_workspaces() -> List[Workspace]`

Scans the `workspaces_path` directory for all `workspace.json` files using a glob pattern (`*/{WORKSPACE_METADATA_FILE}`). Each discovered file is parsed and returned as a `Workspace` object. Errors during loading are logged but do not interrupt the listing process.

### `get_workspace(workspace_id: str) -> Optional[Workspace]`

Returns the first `Workspace` whose `id` matches the given `workspace_id`, or `None` if no match is found. Internally calls `list_workspaces()`.

### `_save(workspace: Workspace) -> None`

Persists a workspace to disk by:
1. Updating the `updated_at` timestamp to the current ISO-formatted datetime.
2. Writing the workspace's data (via `model_dump()`) as indented JSON to its metadata file.
3. Creating any missing parent directories as needed.

---

## Lifecycle Operations

### `create_workspace(workspace: Workspace) -> Workspace`

Creates a new workspace. Steps performed:
1. Validates that no existing workspace shares the same `folder_path`. Raises `ValueError` if a conflict is found.
2. Assigns a new UUID to `workspace.id` if one is not already set.
3. Calls `engine.provision(workspace)` to set up the runtime environment.
4. Saves the workspace metadata to disk.
5. Logs a confirmation message including the workspace name and template.

### `update_workspace(workspace: Workspace, reprovision: bool = False) -> Workspace`

Updates an existing workspace's metadata. If `reprovision=True`, the engine's `provision` method is called before saving, allowing runtime resources to be recreated.

### `delete_workspace(workspace_id: str) -> None`

Deletes a workspace by:
1. Locating the workspace by ID. Raises `ValueError` if not found.
2. Calling `engine.destroy(workspace)`, which removes the workspace folder including its metadata.

### `start_workspace(workspace_id: str) -> Workspace`

Starts a workspace by:
1. Locating the workspace by ID. Raises `ValueError` if not found.
2. Calling `engine.start(workspace)`.
3. Refreshing the workspace `status` via `engine.status(workspace)`.
4. Saving the updated workspace metadata.

### `stop_workspace(workspace_id: str) -> Workspace`

Stops a workspace by:
1. Locating the workspace by ID. Raises `ValueError` if not found.
2. Calling `engine.stop(workspace)`.
3. Setting `workspace.status` to `WorkspaceStatus.STOPPED`.
4. Saving the updated workspace metadata.

### `workspace_status(workspace_id: str) -> WorkspaceStatus`

Returns the current status of a workspace as reported by the engine. Raises `ValueError` if the workspace is not found.

### `workspace_logs(workspace_id: str, tail: int = 200) -> str`

Retrieves the runtime logs for a workspace. The `tail` parameter (default `200`) controls how many lines are returned. Delegates to `engine.logs(workspace, tail=tail)`. Raises `ValueError` if the workspace is not found.

---

## Engine

The `WorkspaceManager` delegates all runtime operations to an implementation of the `WorkspaceEngine` base class. The default engine is `DockerComposeEngine`, initialized with `workspaces_folder` set to the `workspaces_path`. A custom engine can be injected at construction time via the `engine` parameter.

Engine operations used by the manager:

| Engine Method | Used By                            |
|---------------|------------------------------------|
| `provision`   | `create_workspace`, `update_workspace` |
| `destroy`     | `delete_workspace`                 |
| `start`       | `start_workspace`                  |
| `stop`        | `stop_workspace`                   |
| `status`      | `start_workspace`, `workspace_status` |
| `logs`        | `workspace_logs`                   |

---

## Error Handling

All lifecycle methods that look up a workspace by ID raise a `ValueError` with a descriptive message if the workspace cannot be found. The `create_workspace` method additionally raises `ValueError` if a `folder_path` conflict is detected. Errors during metadata loading in `list_workspaces` are caught, logged via `logger.exception`, and skipped without interrupting the full listing.