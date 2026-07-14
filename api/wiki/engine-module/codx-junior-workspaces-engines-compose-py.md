# DockerComposeEngine

## Overview

`DockerComposeEngine` is a workspace engine implementation that runs each workspace as an isolated Docker Compose project. It handles the full lifecycle of workspaces including provisioning, starting, stopping, destroying, status checking, and log retrieval. It also integrates with Traefik for routing workspace applications.

---

## Dependencies

- **Python Standard Library**: `json`, `logging`, `shutil`, `subprocess`, `pathlib.Path`, `typing.List`
- **Internal Models**: `Workspace`, `WorkspaceApp`, `WorkspaceStatus` from `codx.junior.workspaces.model`
- **Base Class**: `WorkspaceEngine` from `codx.junior.workspaces.engines.base`

---

## Constants

| Constant | Value | Description |
|---|---|---|
| `TRAEFIK_CONTAINER_NAME` | `"codx-junior-traefik"` | The name of the Traefik container that joins each workspace network to route apps |

---

## Class: `DockerComposeEngine`

Inherits from `WorkspaceEngine`.

### Constructor

```python
def __init__(self, workspaces_folder: Path)
```

Initializes the engine with the base folder where all workspace directories are stored.

| Parameter | Type | Description |
|---|---|---|
| `workspaces_folder` | `Path` | Root directory that contains all workspace subdirectories |

---

## Helper Methods

### `workspace_dir`

```python
def workspace_dir(self, workspace: Workspace) -> Path
```

Returns the full filesystem path for a given workspace by joining `workspaces_folder` with `workspace.folder_path`.

---

### `_compose`

```python
def _compose(self, workspace: Workspace, *args: str, timeout: int = 120) -> subprocess.CompletedProcess
```

Executes a `docker compose` command scoped to the workspace's compose project and `docker-compose.yaml` file.

- Uses `-p {workspace.compose_project}` to isolate the project.
- Uses `-f {workspace_dir}/docker-compose.yaml` to specify the compose file.
- Logs the command at the `INFO` level before execution.
- Default timeout is **120 seconds**.

---

### `_connect_traefik`

```python
def _connect_traefik(self, workspace: Workspace) -> None
```

Attaches the Traefik container (`codx-junior-traefik`) to the workspace's network using `docker network connect`. This operation is idempotent — it fails silently if Traefik is already connected.

---

### `_disconnect_traefik`

```python
def _disconnect_traefik(self, workspace: Workspace) -> None
```

Detaches the Traefik container from the workspace's network using `docker network disconnect`.

---

### `traefik_labels` (static)

```python
@staticmethod
def traefik_labels(workspace: Workspace, app: WorkspaceApp) -> List[str]
```

Generates a list of Traefik routing labels for a workspace application. These labels configure:

- **Router**: Uses `PathPrefix` matching on `app.path`.
- **Service**: Routes traffic to `app.port`.
- **Middleware**: Strips the path prefix using `replacepathregex` and applies the `codx-junior-auth` middleware.
- **HTTPS**: If `app.scheme == "https"`, adds the HTTPS scheme label for the load balancer.

The router/service identifier (`rid`) is constructed as:
```
codx-ws-{workspace.slug}-{app.id or sanitized app.name}
```

---

## Lifecycle Methods

These methods implement the `WorkspaceEngine` interface.

### `provision`

```python
def provision(self, workspace: Workspace) -> None
```

Renders the workspace template into the workspace directory by calling `render_template` from `codx.junior.workspaces.templates`. This prepares the `docker-compose.yaml` and any other required files before the workspace is started.

---

### `start`

```python
def start(self, workspace: Workspace) -> None
```

Starts the workspace by running:
```
docker compose up -d --build
```
- Timeout: **600 seconds**
- Raises `RuntimeError` if the command fails.
- On success, connects Traefik to the workspace network via `_connect_traefik`.

---

### `stop`

```python
def stop(self, workspace: Workspace) -> None
```

Stops the workspace containers using:
```
docker compose stop
```
- Raises `RuntimeError` if the command fails.
- Does **not** remove containers or networks.

---

### `destroy`

```python
def destroy(self, workspace: Workspace) -> None
```

Fully removes the workspace by:
1. Disconnecting Traefik from the workspace network.
2. Running `docker compose down -v --remove-orphans` to remove containers, volumes, and orphaned services.
3. Deleting the workspace directory from the filesystem using `shutil.rmtree`.

---

### `status`

```python
def status(self, workspace: Workspace) -> WorkspaceStatus
```

Queries the current state of all workspace containers using:
```
docker compose ps --format json
```

Each line of output is parsed as JSON and the `State` field is extracted. The returned `WorkspaceStatus` is determined as follows:

| Condition | Returned Status |
|---|---|
| Command fails | `WorkspaceStatus.ERROR` |
| No containers found | `WorkspaceStatus.STOPPED` |
| All containers are `"running"` | `WorkspaceStatus.RUNNING` |
| Any container is `"restarting"` or `"created"` | `WorkspaceStatus.STARTING` |
| Any other state | `WorkspaceStatus.ERROR` |

Timeout: **15 seconds**.

---

### `logs`

```python
def logs(self, workspace: Workspace, tail: int = 200) -> str
```

Retrieves container logs using:
```
docker compose logs --tail {tail}
```

- Default tail: **200 lines**
- Timeout: **30 seconds**
- Returns `stdout` if available, otherwise falls back to `stderr`.