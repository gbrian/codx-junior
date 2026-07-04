# Deployment and Operations: Entry Point Script

This script manages the initialization, installation, and deployment lifecycle of the project. It serves as the primary entry point for setting up the environment and launching application services.

## Overview
The script is responsible for:
*   Determining the base installation path.
*   Initializing environment variables.
*   Performing first-time installation tasks.
*   Deploying additional application modules.
*   Maintaining a running process state.

## Initialization Process
The script dynamically calculates `CODX_JUNIOR_PATH` by resolving the parent directory of the execution script. Once the path is set, it performs the following setup operations:
1.  Switches user context using `su`.
2.  Sources the environment configuration via `${CODX_JUNIOR_PATH}/set_env.sh`.
3.  Displays the project logo using the script located at `${CODX_JUNIOR_PATH}/scripts/logo.sh`.

## Installation and Deployment
The script handles automated installation and app provisioning:

*   **Initial Setup:** It checks for the existence of the `codx-junior.installed` flag file. If not found, it executes the `codx-junior install` command and creates the flag file upon successful completion.
*   **Application Provisioning:** The script reads the `CODX_APPS` environment variable. If defined, it iterates through a comma-separated list of application names and executes the `codx` command for each specified app.

## Maintenance and Process Management
After completing the installation and provisioning phases, the script enters a persistent loop. It remains active by executing `sleep 10` indefinitely, ensuring the container or process remains running.

*Note: A command to start the `codx-junior supervisor` is present in the script but is currently commented out.*

***

**References**
*   Project File: `codx-junior/scripts/entrypoint.sh`
*   Category: Deployment and Operations