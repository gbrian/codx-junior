# Development and Testing Environment Configuration

This project is configured for development and testing using the following settings.

## Testing Configuration
The project uses `pytest` as the primary testing framework. 
- **Pytest:** Enabled (`python.testing.pytestEnabled`: `true`).
- **Unittest:** Disabled (`python.testing.unittestEnabled`: `false`).
- **Unittest Arguments:** Although `unittest` is disabled, the configuration specifies parameters for test discovery:
    - Verbose mode (`-v`)
    - Search directory: `./tests`
    - Pattern matching: `*test*.py`

## SQL Tools
The project utilizes the `sqltools` extension for database management.
- **Node Runtime:** Enabled (`sqltools.useNodeRuntime`: `true`).
- **Database Connection:** 
    - **Name:** `app-ng-mro`
    - **Driver:** `SQLite`
    - **Preview Limit:** 50 records
    - **Database Path:** `/shared/app-ng-mro/.vscode/.codx/db/shared-app-ng-mro/chroma.sqlite3`

## Development Tools
- **Pylint:** The working directory for the Pylint linter is set to `${workspaceFolder}/api`.

***

**References**
- Document Category: Development and Testing
- Project: codx-junior