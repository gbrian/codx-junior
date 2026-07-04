# Deployment and Operations: Client Execution

This guide details the procedures for executing the client application within the **codx-junior** project.

## Overview
The client execution process relies on a shell script to manage environment configuration, dependency installation, and application launching.

## Prerequisites and Environment Setup
The execution process performs the following automated setup steps:
* **Path Configuration:** Automatically determines and sets the `CODX_JUNIOR_PATH` to the project's parent directory.
* **Environment Loading:** Sources the `set_env.sh` script to configure required project variables.
* **Node Version Management:** Utilizes `nvm` to ensure the environment is configured with **v24.12.0**.
    * *Note:* Users on Debian/Ubuntu systems should ensure all necessary dependencies for v24+ are present on the host machine.

## Execution Modes
The application supports two distinct execution modes based on the presence of the `DEBUG` environment variable.

### Debug Mode
When the `DEBUG` environment variable is defined, the script performs the following actions:
1. Navigates to the `{CODX_JUNIOR_PATH}/client` directory.
2. Executes `npm install` to ensure all dependencies are up to date.
3. Starts the application using `npm run dev`.

### Production Mode
When the `DEBUG` environment variable is not defined, the system defaults to production mode:
1. Navigates to the `{CODX_JUNIOR_PATH}/client` directory.
2. Launches the application using `npm run preview`.

***

### References
* [Deployment and Operations] - Script logic for environment initialization and application launching.