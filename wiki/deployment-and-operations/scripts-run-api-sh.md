# API Deployment and Operations

This script manages the lifecycle and execution of the FastAPI application for the codx-junior project.

## Overview
The deployment process handles environment initialization, dependency management, and server execution.

## Operational Workflow

### Initialization
*   **Path Configuration**: The script dynamically determines the `CODX_JUNIOR_PATH` by identifying the parent directory of the script location.
*   **Environment Setup**: It sources the `set_env.sh` file to load project-specific configurations.
*   **Python Path**: The `PYTHONPATH` is explicitly set to the project's `api` directory.

### Dependency Management
*   **Virtual Environment Validation**: Before starting the service, the script verifies if the virtual environment exists at the location defined by `CODX_JUNIOR_API_VENV`.
*   **Automated Installation**: If the virtual environment directory is missing, the script automatically triggers the `install_api.sh` script to set up the environment.

### Permissions
Prior to launching the application, the script ensures the current user has ownership of the following directories:
*   `CODX_JUNIOR_CONFIG_FOLDER`
*   `CODX_JUNIOR_PROJECTS_PATH`

### Execution Modes
The FastAPI application is executed using `uvicorn`. The behavior is determined by the following logic:

*   **Port Selection**: 
    *   If `CODX_JUNIOR_API_BACKGROUND` is set, the application uses `CODX_JUNIOR_API_PORT_BACKGROUND`.
    *   Otherwise, it defaults to `CODX_JUNIOR_API_PORT`.
*   **Debug Mode**:
    *   **Debug Enabled**: Runs with `--reload` enabled.
    *   **Debug Disabled (Production)**: Runs with multiple workers (defaulting to 4 or the value of `WEB_CONCURRENCY`).

## References
*   **Category**: Deployment and Operations
*   **Keywords**: deployment, operations, scripts, maintenance