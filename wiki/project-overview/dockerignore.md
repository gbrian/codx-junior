# Project Overview

The project is structured to exclude unnecessary files and directories from version control and build processes. This ensures a clean repository and prevents sensitive or local-specific configuration data from being committed.

## Ignored Components

Based on the project configuration, the following elements are excluded:

### Version Control and Environment
*   **Version Control:** The `.git` directory is ignored.
*   **Environment Management:** The `.venv` directory and all `*egg-*` files are excluded, likely to prevent tracking local Python environment configurations.
*   **Node Modules:** The `node_modules` directory is ignored, as standard in JavaScript/TypeScript projects.

### Caching and Build Artifacts
*   **Python:** `__pycache__` and `.pytest_cache` are excluded to keep the repository clean of test and execution metadata.
*   **Client Build:** The `client/.vite` directory is ignored to avoid committing build outputs.

### Configuration and Local Data
*   **System Settings:** `**/global_settings.json` is excluded to protect environment-specific configurations.
*   **Database and Storage:** `.codx/db`, `filebrowser.db`, and `ollama_models` are ignored to prevent tracking large local data stores.
*   **Project Metadata:** The `.codx` directory is excluded.

### Development and Utility Files
*   **Editor Configuration:** `.vscode` is ignored to prevent user-specific IDE settings from being shared.
*   **Project Utilities:** The `assets`, `logs`, `tests`, and `wiki` directories are explicitly ignored, indicating that these are either generated locally or managed outside the core codebase tracking.

***

### References
*   Project Overview: `/.dockerignore`