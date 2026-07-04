# Client Installation and Deployment

The client installation script is part of the `codx-junior` project and is designed to handle environment configuration, dependency management, and application building.

## Overview
This process automates the setup of the client environment by dynamically determining the project path, loading environment variables, and compiling the client application.

## Prerequisites and Environment Setup
The script performs the following initialization steps:
*   **Path Configuration:** Dynamically sets the `CODX_JUNIOR_PATH` to the parent directory of the script.
*   **Environment Loading:** Sources the `set_env.sh` file to load necessary project configurations.
*   **Node.js Initialization:** Invokes the `codx nodejs` command and initializes `nvm` (Node Version Manager) to manage the runtime environment.

## Installation Process
The installation steps occur within the `client` directory of the project:

1.  **Cleanup:** To prevent issues related to folder mapping, the script forces a clean state by removing existing `node_modules` and `dist` directories.
2.  **Runtime Installation:** The script installs Node.js version `v24.12.0` using `nvm`. Note that the script documentation mentions that v25 requires extra dependencies on Debian/Ubuntu systems.
3.  **Dependency Management:** Executes `npm i` to install the project dependencies.
4.  **Compilation:** Runs `npm run build-only` to compile the client application.

## Maintenance Notes
*   The script contains a workaround regarding the removal of `node_modules` and `dist` folders to resolve issues with directory mapping. This is marked as a temporary measure intended for future removal.

***

**References**
*   [Project: codx-junior]
*   [Category: Deployment and Operations]