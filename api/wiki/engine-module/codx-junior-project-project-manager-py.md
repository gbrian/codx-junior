# Project Manager

## Overview

The Project Manager module handles project creation and initialization within the codx-api engine. It provides functionality to create new projects either from a local path or by cloning a remote Git repository, and manages user permissions for newly created projects.

---

## Dependencies

The module relies on the following internal components:

- **`UserSecurityManager`** – Handles user-to-project permission assignments.
- **`CODXJuniorSettings`** – Manages project configuration and persistence.
- **`CODXJuniorSession`** – Provides session management for the engine.
- **`CodxUser`** – Represents the user model.
- **`exec_command`** – Utility for executing shell commands.
- **`CODX_JUNIOR_PROJECTS_PATH`** – Global constant defining the default projects path.
- **`find_project_by_project_path`** / **`get_projects_root_path`** – Project discovery utilities.

---

## Functions

### `create_project(project_path: str, user: CodxUser)`

Creates a new project at the specified path or from a remote Git repository URL.

#### Parameters

| Parameter | Type | Description |
|---|---|---|
| `project_path` | `str` | A local file system path or a remote Git repository URL (starting with `http`). |
| `user` | `CodxUser` | The user who is creating the project. Used for assigning admin permissions. |

#### Returns

Returns a `CODXJuniorSettings` instance representing the newly created or already existing project.

---

#### Behavior and Logic

**1. Resolve the Projects Root Path**

The function begins by retrieving the root path where all projects are stored using `get_projects_root_path()`, and ensures the directory exists via `os.makedirs`.

**2. Git Repository Cloning**

If `project_path` starts with `"http"`, it is treated as a remote repository URL:

- The repository name is extracted from the URL.
- The repository is cloned into the projects root path using:
  ```
  git clone --depth=1 {repo_url} {project_path}
  ```
- The local `project_path` is updated to point to the cloned directory.

**3. Duplicate Project Check**

Before proceeding, the function checks whether a project already exists at the resolved `project_path` using `find_project_by_project_path`. If an existing project is found, it is returned immediately without further action.

**4. Project Settings Initialization**

A new `CODXJuniorSettings` instance is configured with:

- `project_name` – Derived from the last segment of the project path.
- `codx_path` – Set to `{project_path}/.codx`.
- `watching` – Enabled (`True`).
- `repo_url` – Set if the project originated from a remote URL.

The settings are persisted by calling `settings.save_project()`.

**5. Git Initialization**

If the project directory does not already contain a `.git` folder, a new Git repository is initialized:

```
git init
```

**6. User Permission Assignment**

If a `user` is provided, the function assigns them `admin` permissions to the newly created project using:

```python
UserSecurityManager().add_user_to_project(
    project_id=new_project.project_id,
    user=user,
    permissions='admin'
)
```

---

## Logging

The module uses Python's standard `logging` library. Key events logged include:

- Project creation initiation.
- Git repository cloning details (URL, name, path).
- Detection of an already existing project.

---

## Notes

- If `project_path` is a relative path (does not start with `/`), it is automatically resolved against `CODX_JUNIOR_PROJECTS_PATH`.
- The `git clone` operation uses `--depth=1` for a shallow clone, optimizing for speed and storage.
- The project configuration file is read back after saving from `{project_path}/.codx/project.json` to confirm the final project state.

## Dependencies
**Imports from:** codx/junior/security/user_management.py, codx/junior/settings.py, codx/junior/engine.py, codx/junior/model/model.py, codx/junior/utils/utils.py, codx/junior/project/project_discover.py
**Imported by:** codx/junior/app.py