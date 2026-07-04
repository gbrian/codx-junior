# Deployment and Operations: API Execution Script

This documentation outlines the functionality and deployment requirements for the API execution script within the `codx-junior` project.

## Overview
The script serves as the primary entry point for launching the FastAPI application. It handles path configuration, environment sourcing, dependency management, and process execution.

## Configuration and Environment Setup
*   **Path Resolution**: The script dynamically determines the `CODX_JUNIOR_PATH` by identifying the parent directory of the script location.
*   **Environment Variables**: It initializes the environment by sourcing `set_env.sh` from the base project directory.
*   **Python Path**: The `PYTHONPATH` is explicitly set to the `/api` directory to ensure proper module resolution.

## Dependency Management
The script verifies the existence of the virtual environment defined by `CODX_JUNIOR_API_VENV`. If the directory structure is missing, it automatically triggers the `install_api.sh` script to perform the installation. Once verified, it activates the virtual environment using the standard `bin/activate` path.

## Operational Permissions
Prior to launching the application, the script ensures that the current user has ownership over the configuration and project storage directories to prevent permission errors during runtime:
*   `CODX_JUNIOR_CONFIG_FOLDER`
*   `CODX_JUNIOR_PROJECTS_PATH`

## Execution and Modes
The API is launched using `uvicorn`. The behavior changes based on provided configuration variables:

### Port Selection
*   If `CODX_JUNIOR_API_BACKGROUND` is set, the API uses the port defined by `CODX_JUNIOR_API_PORT_BACKGROUND`.
*   Otherwise, it defaults to `CODX_JUNIOR_API_PORT`.

### Launch Modes
*   **Production Mode**: Executed when `DEBUG` is empty. It runs with multiple workers (defaulting to 4 if `WEB_CONCURRENCY` is not set) on host `0.0.0.0`.
*   **Debug Mode**: Executed when `DEBUG` is active. It enables the `--reload` feature for development convenience.

---

### Reference Documentation
*   **Project Path**: `CODX_JUNIOR_PATH`
*   **Environment Config**: `set_env.sh`
*   **Dependency Script**: `/scripts/install_api.sh`
*   **Application Entry Point**: `codx.junior.main:app`