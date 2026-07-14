# Workspace Templates Module

## Overview

This module provides workspace template rendering functionality for the codx-api engine. It handles resolving project mount paths and generating workspace configuration files from Jinja2 templates.

---

## Available Templates

The module defines a set of built-in workspace templates through the `AVAILABLE_TEMPLATES` dictionary:

| Template Name | Description |
|---|---|
| `static-site` | Single container running a web site / dev server (e.g. Vue) |
| `dev-stack` | Sysbox container with systemd + inner Docker for full-stack development |
| `custom` | Empty workspace, admin provides all files |

Templates are stored in the `templates/` directory located relative to this module file (`TEMPLATES_DIR = Path(__file__).parent / "templates"`).

---

## Functions

### `get_project_mounts(workspace: Workspace) -> list[dict]`

Resolves host paths for the projects associated with a given workspace.

**Behavior:**
- Retrieves all available projects via `find_all_projects()`.
- If `workspace.project_ids` contains `"*"`, all discovered projects are mounted.
- Otherwise, only projects whose IDs are listed in `workspace.project_ids` are included (missing IDs are silently skipped).
- Projects are **identity-mounted**, meaning the host path and container path are identical, matching the default workspace convention.

**Returns:**

A list of dictionaries, each containing:

| Key | Description |
|---|---|
| `project_id` | The unique identifier of the project |
| `host_path` | The absolute path of the project on the host (`project.abs_project_path`) |
| `container_path` | The absolute path inside the container (same as `host_path`) |

---

### `render_template(workspace: Workspace, target_dir: Path) -> None`

Renders the workspace template files into the specified target directory.

**Behavior:**

- If `workspace.template` is `"custom"`, the target directory is created (including any missing parents) and the function returns immediately without rendering any files.
- For all other templates, the function looks up the corresponding subdirectory inside `TEMPLATES_DIR`. If the subdirectory does not exist, a `ValueError` is raised with the message: `Unknown workspace template: <template_name>`.
- A Jinja2 `Environment` is initialized with a `FileSystemLoader` pointing to the template directory, with trailing newlines preserved (`keep_trailing_newline=True`).

**Template Context Variables:**

| Variable | Source |
|---|---|
| `workspace` | The `Workspace` object passed to the function |
| `projects` | Result of `get_project_mounts(workspace)` |
| `traefik_labels` | `DockerComposeEngine.traefik_labels` |

**File Processing:**

All files within the template directory are processed recursively:

- Files with a `.j2` extension are rendered as Jinja2 templates and written to the target directory with the `.j2` suffix removed from the filename.
- All other files are copied as-is (binary copy via `read_bytes` / `write_bytes`).
- Intermediate directories are created automatically as needed.
- Each rendered or copied file is logged at `INFO` level, indicating the relative source path and the destination path.

---

## Dependencies

| Dependency | Purpose |
|---|---|
| `jinja2` | Template rendering engine |
| `codx.junior.workspaces.model.Workspace` | Workspace data model |
| `codx.junior.project.project_discover.find_all_projects` | Discovers all available projects |
| `codx.junior.workspaces.engines.compose.DockerComposeEngine` | Provides Traefik label configuration for templates |