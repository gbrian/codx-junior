## Project Configuration Settings

This section outlines various development and environment configurations for testing, database connections, and code linting tools.

### Development and Testing Tools

Configuration options govern Python testing frameworks:
*   **Pytest:** Python testing using Pytest is enabled (`"python.testing.pytestEnabled": true`).
*   **Unittest:** Use of unittest is explicitly disabled (`"python.testing.unittestEnabled": false`).
*   **Unit Test Arguments:** If unit tests were run, detailed arguments are set: `["-v", "-s", "./tests", "-p", "*test*.py"]` (`"python.testing.unittestArgs"`).

### Database Connectivity (SQLTools)

The environment defines settings for SQL tools and connections:
*   **Runtime:** The connection must use the Node runtime, indicated by `"sqltools.useNodeRuntime": true`.
*   **Connection Definition:** A specific SQLite connection is configured:
    *   **Name:** `app-ng-mro` (`"name"`).
    *   **Driver:** SQLite (`"driver": "SQLite"`).
    *   **Target Database Path:** `/shared/app-ng-mro/.vscode/.codx/db/shared-app-ng-mro/chroma.sqlite3` (`"database"`).
    *   **Preview Limit:** The preview limit is set to 50 (`"previewLimit"`).

### Code Linting (Pylint)

The current working directory for Pylint analysis is set to the project's API folder:
*   `pylint.cwd`: `${workspaceFolder}/api`