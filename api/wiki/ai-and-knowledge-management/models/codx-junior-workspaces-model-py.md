# Workspace Models

## Overview

This module defines the core data models used to represent workspaces and their associated resources within the codx-api project. All models are built using [Pydantic](https://docs.pydantic.dev/) `BaseModel`, providing automatic validation and serialization.

---

## Enumerations

### `WorkspaceStatus`

Represents the possible lifecycle states of a workspace.

| Value | Description |
|---|---|
| `stopped` | The workspace is not running |
| `starting` | The workspace is in the process of starting |
| `running` | The workspace is active and running |
| `error` | The workspace encountered an error |

---

## Models

### `WorkspaceResources`

Defines optional resource constraints applied to a workspace container.

| Field | Type | Default | Description |
|---|---|---|---|
| `cpus` | `Optional[str]` | `None` | CPU limit (e.g. `"2"`) |
| `memory` | `Optional[str]` | `None` | Memory limit (e.g. `"4g"`) |
| `shm_size` | `Optional[str]` | `"512m"` | Shared memory size |

---

### `WorkspaceApp`

Represents a single application hosted within a workspace, typically exposed via Traefik routing.

| Field | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | `""` | Unique identifier for the app |
| `name` | `str` | `""` | Display name of the app |
| `description` | `str` | `""` | Short description of the app |
| `icon` | `str` | `""` | Icon reference for the app |
| `path` | `str` | `""` | Public path prefix routed by Traefik |
| `port` | `Optional[int]` | `None` | Container port serving this app |
| `scheme` | `str` | `"http"` | Protocol scheme (`http` or `https`) |
| `is_vnc` | `Optional[bool]` | `False` | Whether the app uses VNC |
| `container_name` | `str` | `""` | Kept for backward compatibility |
| `roles` | `List[str]` | `[]` | List of roles permitted to access the app |

#### Field Validators

- **`_coerce_port`** (`port`, `mode="before"`): Handles legacy persisted data where `port` may be stored as a string or an empty string. Empty string (`""`) and `None` values are converted to `None`; otherwise, the value is cast to `int`.

---

### `Workspace`

The primary model representing a workspace instance, including its configuration, associated projects, users, apps, and runtime state.

| Field | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | `""` | Unique identifier for the workspace |
| `name` | `str` | `""` | Display name of the workspace |
| `description` | `str` | `""` | Short description of the workspace |
| `template` | `str` | `"custom"` | Template ID: `static-site`, `dev-stack`, or `custom` |
| `folder_path` | `str` | `""` | Folder name under `CODX_JUNIOR_WORKSPACES_FOLDER` |
| `project_ids` | `List[str]` | `[]` | Projects mounted into the workspace |
| `user_ids` | `List[str]` | `[]` | Allowed users; empty list means all users are allowed |
| `apps` | `List[WorkspaceApp]` | `[]` | Applications hosted within this workspace |
| `env` | `Dict[str, str]` | `{}` | Extra environment variables injected into the workspace |
| `resources` | `WorkspaceResources` | `WorkspaceResources()` | Resource constraints for the workspace container |
| `use_sysbox` | `bool` | `False` | Run with `sysbox-runc` (enables systemd and inner Docker) |
| `status` | `WorkspaceStatus` | `STOPPED` | Current lifecycle status of the workspace |
| `updated_at` | `Optional[str]` | `None` | Timestamp of the last update |

#### Properties

| Property | Return Type | Description |
|---|---|---|
| `slug` | `str` | Returns `folder_path` as the workspace slug |
| `network_name` | `str` | Returns `codx-ws-{folder_path}`, used as the Docker network name |
| `compose_project` | `str` | Returns `codx-ws-{folder_path}`, used as the Docker Compose project name |

---

## Relationships

```
Workspace
 ├── resources: WorkspaceResources
 ├── apps: List[WorkspaceApp]
 └── status: WorkspaceStatus
```