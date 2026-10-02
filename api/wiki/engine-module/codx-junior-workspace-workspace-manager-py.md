# WorkspaceManager Documentation

The `WorkspaceManager` class is a core engine module responsible for managing the lifecycle of workspaces, including directory creation, file provisioning, and Docker container orchestration.

## Overview
This component serves as a bridge between the system's workspace models and the underlying infrastructure (file system and Docker daemon). It ensures that workspace environments are synchronized with the configured state stored in global settings.

## Core Responsibilities

### Workspace File Provisioning
The `create_workspace_files` method initializes the physical file structure for a new workspace.
- **Directory Creation:** It creates a dedicated directory based on the `Workspace` model's `folder_path`.
- **Template Initialization:** If a default template path is defined, it copies all files and subdirectories from the template folder into the new workspace directory.
- **Error Handling:** The system logs warnings if the template path is missing or invalid and ensures that existing subdirectories are refreshed during the copy process.

### Docker Container Orchestration
The class maintains the state of running environments through automated synchronization:
- **Synchronization (`synchronize_workspaces`):** Automatically detects if a workspace container is missing or outdated by comparing the `updated_at` label against the current `Workspace` object.
- **Container Lifecycle:**
    - **Creation:** The `create_workspace_container` method triggers a `docker run` command with specific configurations, including a 4GB shared memory limit and an `unless-stopped` restart policy.
    - **Removal:** The `remove_workspace_container` method uses `docker rm -f` to forcibly clean up containers associated with specific workspaces.
- **State Inspection:** The system periodically inspects running containers using `docker ps` with filters to retrieve metadata like labels, which are used to determine if the container configuration is current.

## Key Methods

| Method | Description |
| :--- | :--- |
| `create_workspace_files` | Sets up the workspace file system by copying templates. |
| `synchronize_workspaces` | Runs the main loop to ensure all workspaces have active, up-to-date containers. |
| `get_running_containers` | Interfaces with Docker to fetch active containers tagged with `workspace-id`. |
| `create_workspace_container` | Executes the container deployment process. |
| `is_workspace_up_to_date` | Compares a container's `updated_at` label to the current workspace configuration. |
| `get_workspace_paths` | Maps workspace project IDs to physical file paths. |
| `detect_changes` | Logic for identifying mismatches between local configurations and running instances. |

## Configuration & Dependencies
- **Global Settings:** The manager reads global settings via `read_global_settings` to identify available workspaces and base paths.
- **Container Configuration:** Containers are created using the image `codxjunior/codx-junior-default-workspace:latest` and are assigned labels to track the `workspace-id` and `updated_at` timestamp.

---

### References
*   **Engine Module:** `WorkspaceManager` class implementation.
*   **File Management:** `create_workspace_files` logic.
*   **Docker Integration:** `create_workspace_container`, `remove_workspace_container`, and `get_running_containers`.
*   **Synchronization:** `synchronize_workspaces` and `is_workspace_up_to_date`.

## Dependencies
**Imports from:** codx/junior/model/model.py, codx/junior/global_settings.py, codx/junior/engine.py