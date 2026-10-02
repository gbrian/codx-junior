# WorkspaceEngine — Abstract Base Class

## Overview

`WorkspaceEngine` is a backend-agnostic abstract base class (ABC) that defines the workspace lifecycle interface. It provides a unified contract for managing workspace creation, execution, and teardown regardless of the underlying infrastructure backend.

Planned implementations include:
- **DockerComposeEngine** (Phase 1)
- **KubernetesEngine** (Future)

---

## Location

`/codx/junior/workspaces/engines/base.py`

---

## Dependencies

| Import | Source |
|--------|--------|
| `ABC`, `abstractmethod` | `abc` (standard library) |
| `List` | `typing` (standard library) |
| `Workspace` | `codx.junior.workspaces.model` |
| `WorkspaceStatus` | `codx.junior.workspaces.model` |

---

## Class Definition

```python
class WorkspaceEngine(ABC):
```

All concrete engine implementations must inherit from `WorkspaceEngine` and implement every abstract method defined in the interface.

---

## Abstract Methods

### `provision(workspace: Workspace) -> None`

Renders and prepares workspace runtime files, including the compose file, environment configuration, and network setup.

> Must be called before starting a workspace.

---

### `start(workspace: Workspace) -> None`

Starts the workspace containers. Assumes the workspace has already been provisioned.

---

### `stop(workspace: Workspace) -> None`

Stops the workspace containers while preserving volumes and state. Use this for temporary suspension of a workspace.

---

### `destroy(workspace: Workspace) -> None`

Removes containers, the network, and all runtime state associated with the workspace. This is a destructive operation.

---

### `status(workspace: Workspace) -> WorkspaceStatus`

Returns the current status of the workspace as a `WorkspaceStatus` object.

---

### `logs(workspace: Workspace, tail: int = 200) -> str`

Returns recent log output from the workspace. The `tail` parameter controls how many lines are returned, defaulting to `200`.

---

## Lifecycle Flow

The typical workspace lifecycle follows this sequence:

```
provision → start → [stop ↔ start] → destroy
```

| Step | Method | Description |
|------|--------|-------------|
| 1 | `provision` | Prepare runtime files and configuration |
| 2 | `start` | Launch containers |
| 3 | `stop` | Suspend containers (state preserved) |
| 4 | `start` | Resume containers |
| 5 | `destroy` | Permanently remove all runtime resources |

---

## Implementing a Custom Engine

Any class extending `WorkspaceEngine` must implement all six abstract methods: `provision`, `start`, `stop`, `destroy`, `status`, and `logs`. Failure to implement any of these will result in a `TypeError` at instantiation time.

```python
class MyCustomEngine(WorkspaceEngine):
    def provision(self, workspace: Workspace) -> None: ...
    def start(self, workspace: Workspace) -> None: ...
    def stop(self, workspace: Workspace) -> None: ...
    def destroy(self, workspace: Workspace) -> None: ...
    def status(self, workspace: Workspace) -> WorkspaceStatus: ...
    def logs(self, workspace: Workspace, tail: int = 200) -> str: ...
```